"""
BA Copilot
Turn messy notes or a BRD into a client-ready Requirements & High-Level Design pack.
Generate -> review -> edit -> improve with AI -> save -> approve -> export (Word / PDF).

Run:  streamlit run app.py
"""
import copy
import json
import os
import re
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from core.demo_content import DEMO_DIAGRAMS, DEMO_SECTIONS, SAMPLE_CONTEXT, SAMPLE_INPUT
from core.diagrams import preview_html, render_png
from core.exporters import export_docx, export_pdf
from core.input_reader import read_uploaded
from core.llm import PROVIDERS, LLMError, call_llm, strip_fences
from core.sections import (ATTACH_OPTIONS, DIAGRAM_TYPES, IMPROVE_PRESETS, SECTION_BY_ID, SECTIONS,
                           SYSTEM_PROMPT, build_diagram_fix_prompt, build_diagram_prompt,
                           build_improve_prompt, build_section_prompt)

APP_DIR = Path(__file__).parent
PROJECTS_DIR = APP_DIR / "projects"
PROJECTS_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="BA Copilot", page_icon="📘", layout="wide")
st.markdown("""
<style>
  .block-container {padding-top: 1.6rem; max-width: 1400px;}
  .badge {display:inline-block;padding:2px 10px;border-radius:999px;font-size:0.8rem;font-weight:600;}
  .b-none {background:#f1f5f9;color:#475569;} .b-draft {background:#fef3c7;color:#92400e;}
  .b-saved {background:#dbeafe;color:#1e40af;} .b-ok {background:#dcfce7;color:#166534;}
  textarea {font-family: ui-monospace, Consolas, monospace !important; font-size: 0.86rem !important;}
</style>""", unsafe_allow_html=True)


# =====================================================================  state

def new_project() -> dict:
    return {
        "meta": {"project_name": "", "client": "", "author": "", "version": "0.1",
                 "doc_title": "Business Requirements & High-Level Design", "domain": "",
                 "system_context": ""},
        "raw_input": "",
        "sections": {s["id"]: "" for s in SECTIONS},     # working copy (what you see)
        "saved": {s["id"]: "" for s in SECTIONS},        # last saved version
        "approved": {s["id"]: False for s in SECTIONS},
        "history": {s["id"]: [] for s in SECTIONS},      # for Undo
        "diagrams": [],
        "updated_at": "",
    }


if "project" not in st.session_state:
    st.session_state.project = new_project()
if "flash" not in st.session_state:
    st.session_state.flash = []
P = st.session_state.project


def flash(kind: str, msg: str):
    st.session_state.flash.append((kind, msg))


def reset_widget_keys():
    for k in list(st.session_state.keys()):
        if k.startswith(("ed_", "m_", "dg_", "raw_input")):
            del st.session_state[k]


def slug(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", name or "untitled").strip("_").lower() or "untitled"


def save_to_disk():
    P["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path = PROJECTS_DIR / f"{slug(P['meta']['project_name'])}.json"
    data = {k: v for k, v in P.items() if k != "history"}
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def load_project(data: dict):
    base = new_project()
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k].update(v)
        else:
            base[k] = v
    st.session_state.project = base
    reset_widget_keys()


def section_status(sid: str) -> tuple[str, str]:
    if not P["sections"][sid].strip():
        return "Not started", "b-none"
    if P["approved"][sid]:
        return "Approved", "b-ok"
    if P["sections"][sid] == P["saved"][sid]:
        return "Saved", "b-saved"
    return "Draft - unsaved", "b-draft"


ICON = {"Not started": "⚪", "Draft - unsaved": "📝", "Saved": "💾", "Approved": "✅"}


def ctx() -> dict:
    m = P["meta"]
    return {**m, "raw_input": P["raw_input"]}


def is_demo() -> bool:
    return st.session_state.get("ai_provider", "").startswith("Demo")


def ai(prompt: str, max_tokens: int = 6000) -> str:
    return strip_fences(call_llm(st.session_state.ai_provider, st.session_state.ai_model,
                                 st.session_state.ai_key, SYSTEM_PROMPT, prompt, max_tokens))


def set_section(sid: str, text: str, keep_history=True):
    if keep_history and P["sections"][sid].strip() and P["sections"][sid] != text:
        P["history"][sid] = (P["history"][sid] + [P["sections"][sid]])[-10:]
    P["sections"][sid] = text
    st.session_state[f"ed_{sid}"] = text


def generate_section(sid: str) -> bool:
    if not P["raw_input"].strip():
        flash("warning", "Add your notes or BRD on the Input page first.")
        return False
    try:
        if is_demo():
            text = DEMO_SECTIONS[sid]
        else:
            text = ai(build_section_prompt(sid, ctx(), P["sections"]))
        set_section(sid, text)
        P["approved"][sid] = False
        return True
    except LLMError as e:
        flash("error", f"{SECTION_BY_ID[sid]['title']}: {e}")
        return False


# =====================================================================  callbacks

def cb_generate(sid):
    if generate_section(sid):
        flash("success", f"Generated '{SECTION_BY_ID[sid]['title']}'. Review, edit, then Save or Approve.")


def cb_editor_change(sid):
    P["sections"][sid] = st.session_state[f"ed_{sid}"]


def cb_save(sid):
    P["saved"][sid] = P["sections"][sid]
    path = save_to_disk()
    flash("success", f"Saved section. Project stored at projects/{path.name}")


def cb_approve(sid):
    P["saved"][sid] = P["sections"][sid]
    P["approved"][sid] = True
    save_to_disk()
    flash("success", f"Approved '{SECTION_BY_ID[sid]['title']}' - it is now locked.")


def cb_reopen(sid):
    P["approved"][sid] = False
    save_to_disk()


def cb_undo(sid):
    if P["history"][sid]:
        prev = P["history"][sid].pop()
        P["sections"][sid] = prev
        st.session_state[f"ed_{sid}"] = prev
        flash("info", "Restored the previous version.")


def cb_improve(sid):
    preset = st.session_state.get(f"imp_preset_{sid}")
    custom = st.session_state.get(f"imp_custom_{sid}", "").strip()
    instruction = " ".join(x for x in [IMPROVE_PRESETS.get(preset, ""), custom] if x)
    if not instruction:
        flash("warning", "Pick an improvement or type an instruction.")
        return
    if is_demo():
        flash("info", "Demo mode can't rewrite text. Choose an AI provider in the sidebar to use 'Improve with AI'.")
        return
    try:
        text = ai(build_improve_prompt(SECTION_BY_ID[sid]["title"], P["sections"][sid], instruction))
        set_section(sid, text)
        flash("success", "Improved. Not happy? Click Undo.")
    except LLMError as e:
        flash("error", str(e))


def cb_meta(field):
    P["meta"][field] = st.session_state[f"m_{field}"]


def cb_raw():
    P["raw_input"] = st.session_state["raw_input"]


def cb_load_sample():
    P["raw_input"] = SAMPLE_INPUT
    P["meta"].update({**SAMPLE_CONTEXT, "author": P["meta"].get("author") or "Business Analyst"})
    reset_widget_keys()
    flash("success", "Sample loaded. Go to 'Sections' and click 'Generate all'.")


def cb_new_project():
    st.session_state.project = new_project()
    reset_widget_keys()


# ---- diagrams

def _diagram_code(dtype, extra):
    if is_demo():
        return DEMO_DIAGRAMS.get(dtype) or "flowchart TD\n    A[Start] --> B[Describe your process]\n    B --> C[End]"
    return ai(build_diagram_prompt(dtype, extra, ctx(), P["sections"]), max_tokens=2500)


def cb_add_diagrams():
    chosen = st.session_state.get("dg_new_types", [])
    custom = st.session_state.get("dg_new_custom", "").strip()
    jobs = [(t, "") for t in chosen]
    if custom:
        jobs.append((custom, custom))
    if not jobs:
        flash("warning", "Choose at least one diagram type or describe a custom diagram.")
        return
    for dtype, extra in jobs:
        try:
            code = _diagram_code(dtype, extra)
        except LLMError as e:
            flash("error", f"{dtype}: {e}")
            continue
        did = f"d{datetime.now().strftime('%H%M%S%f')}"
        P["diagrams"].append({"id": did, "type": dtype, "title": dtype if not extra else extra[:60],
                              "code": code,
                              "attach": DIAGRAM_TYPES.get(dtype, {}).get("attach", "appendix"),
                              "include": True, "approved": False})
    st.session_state["dg_new_types"] = []
    st.session_state["dg_new_custom"] = ""
    save_to_disk()
    flash("success", f"Created {len(jobs)} diagram(s). Review the preview, edit the code or use 'Fix with AI'.")


def _dg(did):
    return next(d for d in P["diagrams"] if d["id"] == did)


def cb_dg_field(did, field):
    _dg(did)[field] = st.session_state[f"dg_{field}_{did}"]
    save_to_disk()


def cb_dg_fix(did):
    d = _dg(did)
    instr = st.session_state.get(f"dg_fixtxt_{did}", "").strip() or \
        "Fix any Mermaid syntax errors and improve layout and readability."
    if is_demo():
        flash("info", "Demo mode can't edit diagrams with AI. Choose an AI provider in the sidebar.")
        return
    try:
        d["code"] = ai(build_diagram_fix_prompt(d["code"], instr), max_tokens=2500)
        st.session_state[f"dg_code_{did}"] = d["code"]
        d["approved"] = False
        save_to_disk()
    except LLMError as e:
        flash("error", str(e))


def cb_dg_delete(did):
    P["diagrams"] = [d for d in P["diagrams"] if d["id"] != did]
    save_to_disk()


def cb_dg_approve(did, value):
    _dg(did)["approved"] = value
    save_to_disk()


# =====================================================================  sidebar
PAGES = ["1 · Input", "2 · Sections", "3 · Diagrams", "4 · Preview & Export"]


def go(p):
    st.session_state.nav = p


with st.sidebar:
    st.markdown("## 📘 BA Copilot")
    st.caption("Notes / BRD → client-ready Requirements & HLD pack")
    page = st.radio("Navigate", PAGES, key="nav", label_visibility="collapsed")

    st.divider()
    st.markdown("**AI settings**")
    if "ai_provider" not in st.session_state:
        st.session_state.ai_provider = "Demo mode (no API key)"
        st.session_state.ai_model = PROVIDERS["Demo mode (no API key)"]["default_model"]

    def _provider_changed():
        prov = st.session_state.ai_provider
        st.session_state.ai_model = PROVIDERS[prov]["default_model"]
        env = {"Google Gemini": "GEMINI_API_KEY", "OpenAI": "OPENAI_API_KEY",
               "Anthropic Claude": "ANTHROPIC_API_KEY"}.get(prov)
        st.session_state.ai_key = os.environ.get(env, "") if env else ""

    st.selectbox("Provider", list(PROVIDERS), key="ai_provider", on_change=_provider_changed)
    if not is_demo():
        st.text_input("Model", key="ai_model")
        st.text_input("API key", type="password", key="ai_key",
                      help="Stays in this browser session only. You can also set GEMINI_API_KEY / "
                           "OPENAI_API_KEY / ANTHROPIC_API_KEY as environment variables.")
    else:
        st.caption("Demo mode uses a built-in UK credit-reporting example. Pick a provider to use AI on your own notes.")
        st.session_state.setdefault("ai_key", "")

    st.divider()
    done = sum(1 for s in SECTIONS if P["approved"][s["id"]])
    st.markdown(f"**Progress:** {done}/{len(SECTIONS)} sections approved")
    st.progress(done / len(SECTIONS))

    st.divider()
    st.markdown("**Project**")
    if st.button("💾 Save project", use_container_width=True, type="primary"):
        flash("success", f"Project saved to projects/{save_to_disk().name}")
        st.rerun()
    saved_files = sorted(PROJECTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if saved_files:
        pick = st.selectbox("Open saved project", ["—"] + [f.stem for f in saved_files])
        if pick != "—" and st.button("Open", use_container_width=True):
            load_project(json.loads((PROJECTS_DIR / f"{pick}.json").read_text(encoding="utf-8")))
            flash("success", f"Opened project '{pick}'.")
            st.rerun()
    up = st.file_uploader("Import project (.json)", type=["json"], key="proj_upload")
    if up is not None and st.button("Import", use_container_width=True):
        load_project(json.loads(up.getvalue()))
        flash("success", "Project imported.")
        st.rerun()
    st.download_button("⬇ Download project (.json)",
                       data=json.dumps({k: v for k, v in P.items() if k != "history"}, indent=2),
                       file_name=f"{slug(P['meta']['project_name'])}.json", mime="application/json",
                       use_container_width=True)
    st.button("＋ New project", on_click=cb_new_project, use_container_width=True)


for kind, msg in st.session_state.flash:
    getattr(st, kind)(msg)
st.session_state.flash = []


def bound_input(label, field, area=False, **kw):
    key = f"m_{field}"
    if key not in st.session_state:
        st.session_state[key] = P["meta"].get(field, "")
    fn = st.text_area if area else st.text_input
    fn(label, key=key, on_change=cb_meta, args=(field,), **kw)


# =====================================================================  1. INPUT

if page.startswith("1"):
    st.title("1 · Input")
    st.write("Paste messy meeting notes, an email thread or a BRD — or upload a file. "
             "The more context you give (systems, tables, current process), the sharper the output.")

    c1, c2 = st.columns([1, 1])
    with c1:
        bound_input("Project name *", "project_name", placeholder="e.g. CRA Arrangement Reporting Remediation")
        bound_input("Client / business unit", "client")
        bound_input("Document title", "doc_title")
    with c2:
        bound_input("Prepared by", "author")
        bound_input("Version", "version")
        bound_input("Domain / regulatory context", "domain",
                    placeholder="e.g. UK Consumer Credit - CRA reporting / FCA Consumer Duty")

    st.subheader("Requirement input")
    files = st.file_uploader("Upload BRD / notes (.docx, .pdf, .txt, .md)", type=["docx", "pdf", "txt", "md"],
                             accept_multiple_files=True)
    if files and st.button("Add uploaded text to input"):
        texts = []
        for f in files:
            try:
                texts.append(f"--- {f.name} ---\n{read_uploaded(f)}")
            except Exception as e:  # noqa: BLE001
                st.error(f"Could not read {f.name}: {e}")
        P["raw_input"] = (P["raw_input"] + "\n\n" + "\n\n".join(texts)).strip()
        st.session_state["raw_input"] = P["raw_input"]
        st.success(f"Added text from {len(texts)} file(s).")

    if "raw_input" not in st.session_state:
        st.session_state["raw_input"] = P["raw_input"]
    st.text_area("Notes / BRD text *", key="raw_input", on_change=cb_raw, height=320,
                 placeholder="Paste your notes here…")
    bound_input("Known systems, tables, current process (optional but recommended)", "system_context",
                area=True, height=110,
                placeholder="e.g. Source: CollectPro arrangement table. Target: Teradata credit reporting mart…")

    b1, b2, _ = st.columns([1, 1, 3])
    b1.button("Load sample example", on_click=cb_load_sample, use_container_width=True)
    b2.button("Next: Sections →", type="primary", use_container_width=True, on_click=go, args=(PAGES[1],))


# =====================================================================  2. SECTIONS

elif page.startswith("2"):
    st.title("2 · Sections")
    st.caption("Each section is generated from your input **and** the sections before it, so IDs "
               "(REQ → US → DM → TC) stay consistent. Review, edit, improve, save, then approve.")

    g1, g2, g3 = st.columns([1.2, 1.4, 3])
    overwrite = g2.checkbox("Overwrite unapproved drafts", value=False)
    if g1.button("⚡ Generate all sections", type="primary", use_container_width=True):
        todo = [s for s in SECTIONS if not P["approved"][s["id"]]
                and (overwrite or not P["sections"][s["id"]].strip())]
        if not todo:
            st.info("Nothing to generate - all sections already have content. Tick 'Overwrite' to regenerate drafts.")
        bar = st.progress(0.0, text="Starting…")
        for i, s in enumerate(todo):
            bar.progress(i / len(todo), text=f"Writing {s['title']}…")
            if not generate_section(s["id"]):
                break
        bar.progress(1.0, text="Done")
        st.rerun()

    left, right = st.columns([1, 3.2], gap="large")
    with left:
        labels = [f"{ICON[section_status(s['id'])[0]]}  {i + 1}. {s['title']}" for i, s in enumerate(SECTIONS)]
        idx = st.radio("Sections", range(len(SECTIONS)), format_func=lambda i: labels[i],
                       key="sec_pick", label_visibility="collapsed")
        st.caption("⚪ not started · 📝 unsaved · 💾 saved · ✅ approved")

    s = SECTIONS[idx]
    sid = s["id"]
    status, css = section_status(sid)
    with right:
        st.markdown(f"### {idx + 1}. {s['title']} &nbsp; <span class='badge {css}'>{status}</span>",
                    unsafe_allow_html=True)
        missing = [SECTION_BY_ID[d]["title"] for d in s["depends_on"] if not P["sections"][d].strip()]
        if missing:
            st.caption("ℹ️ Works best after: " + ", ".join(missing))

        locked = P["approved"][sid]
        a, b, c, d, e = st.columns(5)
        a.button("Regenerate" if P["sections"][sid].strip() else "Generate", key=f"gen_{sid}",
                 on_click=cb_generate, args=(sid,), disabled=locked, use_container_width=True)
        b.button("💾 Save", key=f"save_{sid}", on_click=cb_save, args=(sid,),
                 disabled=locked or not P["sections"][sid].strip(), use_container_width=True)
        if locked:
            c.button("🔓 Reopen", key=f"reopen_{sid}", on_click=cb_reopen, args=(sid,), use_container_width=True)
        else:
            c.button("✅ Approve", key=f"appr_{sid}", on_click=cb_approve, args=(sid,), type="primary",
                     disabled=not P["sections"][sid].strip(), use_container_width=True)
        d.button(f"↶ Undo ({len(P['history'][sid])})", key=f"undo_{sid}", on_click=cb_undo, args=(sid,),
                 disabled=locked or not P["history"][sid], use_container_width=True)

        key = f"ed_{sid}"
        if key not in st.session_state:
            st.session_state[key] = P["sections"][sid]
        t_edit, t_prev = st.tabs(["✏️ Edit", "👁 Preview"])
        with t_edit:
            st.text_area("Section content (Markdown)", key=key, height=520, on_change=cb_editor_change,
                         args=(sid,), disabled=locked, label_visibility="collapsed",
                         placeholder="Click Generate, or write/paste your own content here.")
            if locked:
                st.caption("🔒 Approved sections are locked. Click Reopen to edit.")
        with t_prev:
            st.markdown(P["sections"][sid] or "_Nothing yet._")

        with st.expander("✨ Improve with AI", expanded=False):
            st.selectbox("Quick improvement", ["—"] + list(IMPROVE_PRESETS), key=f"imp_preset_{sid}")
            st.text_input("Or tell the AI what to change",
                          placeholder="e.g. Add a negative scenario for each story; use RBI terminology",
                          key=f"imp_custom_{sid}")
            st.button("Apply", key=f"imp_go_{sid}", on_click=cb_improve, args=(sid,),
                      disabled=locked or not P["sections"][sid].strip())
        with st.expander("Markdown tips"):
            st.code("## Heading\n### Sub-heading\n- bullet\n1. numbered\n**bold**\n"
                    "| Col A | Col B |\n|---|---|\n| x | y |\n```sql\nSELECT 1;\n```", language="markdown")


# =====================================================================  3. DIAGRAMS

elif page.startswith("3"):
    st.title("3 · Diagrams")
    st.caption("Diagrams are written as Mermaid code: edit the code and the preview updates. "
               "Choose which section each diagram appears in; untick 'Include' to leave it out.")

    st.toggle("Image preview mode (use if the live preview stays blank, e.g. on a restricted network)",
              key="img_preview")
    with st.container(border=True):
        st.markdown("**Add diagrams**")
        st.multiselect("Diagram types", list(DIAGRAM_TYPES), key="dg_new_types",
                       placeholder="e.g. TO-BE process flow, Customer journey, State chart…")
        st.text_input("Custom diagram (optional)", key="dg_new_custom",
                      placeholder="e.g. Swimlane of the month-end sign-off between Ops, Credit Reporting and Compliance")
        st.button("Create diagrams", type="primary", on_click=cb_add_diagrams)

    if not P["diagrams"]:
        st.info("No diagrams yet. Tip: generate the sections first; diagrams are drawn from them.")

    attach_keys = list(ATTACH_OPTIONS)
    for d in P["diagrams"]:
        did = d["id"]
        badge = "✅" if d["approved"] else "📝"
        with st.expander(f"{badge}  {d['title']}  ·  {ATTACH_OPTIONS.get(d['attach'], 'Appendix')}", expanded=True):
            for f in ("title", "code", "attach", "include"):
                if f"dg_{f}_{did}" not in st.session_state:
                    st.session_state[f"dg_{f}_{did}"] = d[f]
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.text_input("Title / caption", key=f"dg_title_{did}", on_change=cb_dg_field, args=(did, "title"))
            c2.selectbox("Place in section", attach_keys, format_func=lambda k: ATTACH_OPTIONS[k],
                         key=f"dg_attach_{did}", on_change=cb_dg_field, args=(did, "attach"))
            c3.checkbox("Include", key=f"dg_include_{did}", on_change=cb_dg_field, args=(did, "include"))

            ec, pc = st.columns([1, 1.4])
            with ec:
                st.text_area("Mermaid code", key=f"dg_code_{did}", height=380, on_change=cb_dg_field,
                             args=(did, "code"), disabled=d["approved"])
            with pc:
                if st.session_state.get("img_preview"):
                    png = render_png(d["code"])
                    if png:
                        st.image(png, use_container_width=True)
                    else:
                        st.warning("Could not render - check the Mermaid syntax or your internet connection.")
                else:
                    components.html(preview_html(d["code"], 410), height=420, scrolling=False)

            f1, f2, f3, f4 = st.columns([3, 1, 1, 1])
            f1.text_input("Change with AI", key=f"dg_fixtxt_{did}", label_visibility="collapsed",
                          placeholder="Tell AI what to change (blank = fix errors & tidy layout)")
            f2.button("✨ Fix with AI", key=f"dg_fix_{did}", on_click=cb_dg_fix, args=(did,),
                      disabled=d["approved"], use_container_width=True)
            if d["approved"]:
                f3.button("🔓 Reopen", key=f"dg_re_{did}", on_click=cb_dg_approve, args=(did, False),
                          use_container_width=True)
            else:
                f3.button("✅ Approve", key=f"dg_ok_{did}", on_click=cb_dg_approve, args=(did, True),
                          use_container_width=True)
            f4.button("🗑 Delete", key=f"dg_del_{did}", on_click=cb_dg_delete, args=(did,),
                      use_container_width=True)

    with st.expander("Mermaid quick reference"):
        st.code("flowchart TD\n  A[Step] --> B{Decision?}\n  B -- Yes --> C[Do X]\n  B -- No --> D[Do Y]\n\n"
                "stateDiagram-v2\n  [*] --> Open\n  Open --> Closed: settle\n\n"
                "sequenceDiagram\n  Ops->>DW: request\n  DW-->>Ops: response", language="text")


# =====================================================================  4. PREVIEW & EXPORT

else:
    st.title("4 · Preview & Export")

    rows = []
    for i, s in enumerate(SECTIONS):
        stt, _ = section_status(s["id"])
        rows.append({"#": i + 1, "Section": s["title"], "Status": f"{ICON[stt]} {stt}",
                     "Diagrams": sum(1 for d in P["diagrams"] if d["attach"] == s["id"] and d["include"])})
    st.dataframe(rows, hide_index=True, use_container_width=True)

    unsaved = [s["title"] for s in SECTIONS if section_status(s["id"])[0] == "Draft - unsaved"]
    if unsaved:
        st.warning("Unsaved changes in: " + ", ".join(unsaved) + ". They will still be exported as drafts.")

    include_drafts = st.toggle("Include sections that are not yet approved", value=True,
                               help="Turn off to export only approved sections (final client version).")

    def export_project():
        p = copy.deepcopy(P)
        p["status"] = {sid: ("Approved" if P["approved"][sid] else
                             "Saved" if P["sections"][sid] == P["saved"][sid] else "Draft")
                       for sid in P["sections"]}
        return p

    has_content = any(P["sections"][s["id"]].strip() for s in SECTIONS)
    c1, c2 = st.columns(2)
    name = slug(P["meta"]["project_name"]) or "ba_document"
    with c1:
        if st.button("Build Word document (.docx)", use_container_width=True, disabled=not has_content):
            with st.spinner("Building Word document and rendering diagrams…"):
                data, warns = export_docx(export_project(), include_drafts)
            st.session_state["docx_bytes"] = data
            for w in warns:
                st.warning(w)
        if st.session_state.get("docx_bytes"):
            st.download_button("⬇ Download Word", st.session_state["docx_bytes"], f"{name}_HLD.docx",
                               "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               type="primary", use_container_width=True)
    with c2:
        if st.button("Build PDF", use_container_width=True, disabled=not has_content):
            with st.spinner("Building PDF and rendering diagrams…"):
                data, warns = export_pdf(export_project(), include_drafts)
            st.session_state["pdf_bytes"] = data
            for w in warns:
                st.warning(w)
        if st.session_state.get("pdf_bytes"):
            st.download_button("⬇ Download PDF", st.session_state["pdf_bytes"], f"{name}_HLD.pdf",
                               "application/pdf", type="primary", use_container_width=True)
    st.caption("In Word, the table of contents fills in when you open the file (click 'Yes' to update fields).")

    st.divider()
    st.subheader("Document preview")
    n = 0
    for s in SECTIONS:
        sid = s["id"]
        if not P["sections"][sid].strip() or (not include_drafts and not P["approved"][sid]):
            continue
        n += 1
        st.markdown(f"## {n}. {s['title']}")
        st.markdown(P["sections"][sid])
        for d in P["diagrams"]:
            if d["attach"] == sid and d["include"]:
                components.html(preview_html(d["code"], 430), height=440)
                st.caption(f"Figure: {d['title']}")
    if n == 0:
        st.info("Nothing to preview yet.")
