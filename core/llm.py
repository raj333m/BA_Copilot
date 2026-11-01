"""
LLM provider layer.
Uses plain HTTP (requests) so you don't need three different SDKs.
Supported: Demo (no key), Google Gemini, OpenAI, Anthropic Claude.
"""
import re
import requests

PROVIDERS = {
    "Demo mode (no API key)": {"default_model": "demo"},
    "Google Gemini": {"default_model": "gemini-2.5-flash"},
    "OpenAI": {"default_model": "gpt-4o-mini"},
    "Anthropic Claude": {"default_model": "claude-sonnet-5-5"},
}

TIMEOUT = 180


class LLMError(Exception):
    pass


def call_llm(provider: str, model: str, api_key: str, system: str, prompt: str,
             max_tokens: int = 6000, temperature: float = 0.3) -> str:
    """Send one prompt to the chosen provider and return plain text."""
    if provider.startswith("Demo"):
        raise LLMError("Demo mode does not call an LLM.")
    if not api_key:
        raise LLMError("Please enter your API key in the sidebar.")

    try:
        if provider == "Google Gemini":
            url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                   f"{model}:generateContent")
            body = {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature,
                                     "maxOutputTokens": max_tokens},
            }
            r = requests.post(url, params={"key": api_key}, json=body, timeout=TIMEOUT)
            _raise_for(r)
            data = r.json()
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts).strip()

        if provider == "OpenAI":
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "temperature": temperature,
                      "max_tokens": max_tokens,
                      "messages": [{"role": "system", "content": system},
                                   {"role": "user", "content": prompt}]},
                timeout=TIMEOUT)
            _raise_for(r)
            return r.json()["choices"][0]["message"]["content"].strip()

        if provider == "Anthropic Claude":
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": model, "max_tokens": max_tokens,
                      "temperature": temperature, "system": system,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=TIMEOUT)
            _raise_for(r)
            blocks = r.json()["content"]
            return "".join(b.get("text", "") for b in blocks).strip()

    except requests.RequestException as e:
        raise LLMError(f"Network error: {e}") from e
    except (KeyError, IndexError) as e:
        raise LLMError(f"Unexpected response format from {provider}: {e}") from e

    raise LLMError(f"Unknown provider: {provider}")


def transcribe_audio(provider: str, api_key: str, wav_bytes: bytes) -> str:
    """Speech-to-text for dictated notes.
    - OpenAI key  -> Whisper (best for long, domain-heavy dictation)
    - Gemini key  -> Gemini audio understanding
    - otherwise   -> free Google Web Speech via the SpeechRecognition package (no key)
    """
    import base64
    try:
        if provider == "OpenAI" and api_key:
            r = requests.post("https://api.openai.com/v1/audio/transcriptions",
                              headers={"Authorization": f"Bearer {api_key}"},
                              files={"file": ("dictation.wav", wav_bytes, "audio/wav")},
                              data={"model": "whisper-1"}, timeout=TIMEOUT)
            _raise_for(r)
            return r.json()["text"].strip()
        if provider == "Google Gemini" and api_key:
            body = {"contents": [{"role": "user", "parts": [
                {"inline_data": {"mime_type": "audio/wav", "data": base64.b64encode(wav_bytes).decode()}},
                {"text": "Transcribe this business dictation verbatim in English. "
                         "Return only the transcript text."}]}]}
            r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                              params={"key": api_key}, json=body, timeout=TIMEOUT)
            _raise_for(r)
            return "".join(p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"]).strip()
    except requests.RequestException as e:
        raise LLMError(f"Network error during transcription: {e}") from e

    # Free fallback: Google Web Speech API (needs internet, no key). Long audio is sent in 50s chunks.
    try:
        import io
        import speech_recognition as sr
    except ImportError as e:
        raise LLMError("Install SpeechRecognition (pip install SpeechRecognition) or use an "
                       "OpenAI / Gemini key for dictation.") from e
    rec = sr.Recognizer()
    parts = []
    with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
        total = source.DURATION
        offset = 0.0
        while offset < total:
            chunk = rec.record(source, duration=50)
            offset += 50
            try:
                parts.append(rec.recognize_google(chunk, language="en-IN"))
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                raise LLMError(f"Speech service unavailable: {e}") from e
    if not parts:
        raise LLMError("Could not understand the audio. Try speaking closer to the microphone.")
    return " ".join(parts)


def _raise_for(r: requests.Response):
    if r.status_code >= 400:
        try:
            msg = r.json()
        except ValueError:
            msg = r.text[:500]
        raise LLMError(f"API error {r.status_code}: {msg}")


def strip_fences(text: str) -> str:
    """Remove a wrapping ```markdown / ```mermaid fence if the model added one."""
    t = text.strip()
    m = re.match(r"^```[a-zA-Z]*\s*\n(.*)\n```\s*$", t, re.S)
    return m.group(1).strip() if m else t
