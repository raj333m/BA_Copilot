"""
Mermaid diagram rendering.
- Live preview in the browser uses mermaid.js (see app.py).
- For Word/PDF export we need a PNG:
    1) local Mermaid CLI (mmdc) if installed  -> works offline
    2) otherwise the free mermaid.ink web service -> needs internet
"""
import base64
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

import requests

_CACHE: dict[str, bytes] = {}


def render_png(code: str) -> bytes | None:
    key = hashlib.md5(code.encode()).hexdigest()
    if key in _CACHE:
        return _CACHE[key]
    png = _render_mmdc(code) or _render_mermaid_ink(code)
    if png:
        _CACHE[key] = png
    return png


def _render_mmdc(code: str) -> bytes | None:
    exe = shutil.which("mmdc") or shutil.which("mmdc.cmd")
    if not exe:
        return None
    with tempfile.TemporaryDirectory() as d:
        src, out = Path(d) / "d.mmd", Path(d) / "d.png"
        src.write_text(code, encoding="utf-8")
        try:
            subprocess.run([exe, "-i", str(src), "-o", str(out), "-b", "white", "-s", "2"],
                           capture_output=True, timeout=90, check=True)
            return out.read_bytes() if out.exists() else None
        except (subprocess.SubprocessError, OSError):
            return None


def _render_mermaid_ink(code: str) -> bytes | None:
    b64 = base64.urlsafe_b64encode(code.encode("utf-8")).decode("ascii")
    try:
        r = requests.get(f"https://mermaid.ink/img/{b64}",
                         params={"type": "png", "bgColor": "FFFFFF", "scale": "2"}, timeout=30)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
            return r.content
    except requests.RequestException:
        pass
    return None


def preview_html(code: str, height: int = 480) -> str:
    """HTML snippet that renders Mermaid in the browser (for st.components.html)."""
    safe = (code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    return f"""
<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:12px;
            height:{height - 30}px;overflow:auto;">
  <pre class="mermaid">{safe}</pre>
  <div id="err" style="color:#b91c1c;font-family:sans-serif;font-size:13px;"></div>
</div>
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({{ startOnLoad: false, theme: 'default', securityLevel: 'strict' }});
  try {{ await mermaid.run({{ querySelector: '.mermaid' }}); }}
  catch (e) {{ document.getElementById('err').innerText =
      'Diagram syntax error - edit the code or use "Fix with AI": ' + (e.message || e); }}
</script>"""
