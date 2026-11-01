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
