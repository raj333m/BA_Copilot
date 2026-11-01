"""
Export the project to Word (.docx) and PDF.

Both exporters share one small Markdown parser that understands what the
sections contain: ## / ### headings, paragraphs, bullet & numbered lists,
tables, ```code``` blocks, **bold** and `inline code`.
"""
import io
import re
from datetime import date
from pathlib import Path

from .diagrams import render_png
from .sections import SECTIONS

# ------------------------------------------------------------------ parser

def parse_markdown(md: str) -> list[dict]:
    blocks, lines, i = [], md.replace("\r\n", "\n").split("\n"), 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        if s.startswith("```"):
            lang, code = s[3:].strip(), []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            blocks.append({"type": "code", "lang": lang, "text": "\n".join(code)})
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", s)
        if m:
            blocks.append({"type": "heading", "level": len(m.group(1)), "text": m.group(2).strip()})
            i += 1
            continue
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = lines[i].strip().strip("|")
                cells = [c.strip() for c in re.split(r"(?<!\\)\|", row)]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    rows.append(cells)
                i += 1
            if rows:
                width = max(len(r) for r in rows)
                rows = [r + [""] * (width - len(r)) for r in rows]
                blocks.append({"type": "table", "rows": rows})
            continue
        m = re.match(r"^(\s*)[-*+]\s+(.*)", line)
        if m:
            blocks.append({"type": "bullet", "level": len(m.group(1)) // 2, "text": m.group(2)})
            i += 1
            continue
        m = re.match(r"^(\s*)(\d+)[.)]\s+(.*)", line)
        if m:
            blocks.append({"type": "number", "level": len(m.group(1)) // 2,
                           "num": m.group(2), "text": m.group(3)})
            i += 1
            continue
        blocks.append({"type": "para", "text": s})
        i += 1
    return blocks


INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*)")


def inline_runs(text: str) -> list[tuple[str, str]]:
    """Split text into (style, text) runs. style in {'', 'b', 'i', 'code'}."""
    out = []
    for part in INLINE_RE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            out.append(("b", part[2:-2]))
        elif part.startswith("`") and part.endswith("`"):
            out.append(("code", part[1:-1]))
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            out.append(("i", part[1:-1]))
        else:
            out.append(("", part))
    return out


# ------------------------------------------------------------------ assembly

def collect_document(project: dict, include_drafts: bool) -> list[dict]:
    """Return ordered list of {title, content, diagrams:[{title, png}]} to export."""
    sections, status = project["sections"], project["status"]
    diagrams = [d for d in project.get("diagrams", []) if d.get("include", True) and d.get("code")]
    out, n = [], 0
    for s in SECTIONS:
        sid = s["id"]
        content = sections.get(sid, "").strip()
        if not content:
            continue
        if not include_drafts and status.get(sid) != "Approved":
            continue
        n += 1
        out.append({"title": f"{n}. {s['title']}", "content": content,
                    "diagrams": [d for d in diagrams if d.get("attach") == sid]})
    # Diagrams go to the appendix if asked, or if their target section is not exported.
    exported_ids = {s["id"] for s in SECTIONS
                    if sections.get(s["id"], "").strip()
                    and (include_drafts or status.get(s["id"]) == "Approved")}
    appendix = [d for d in diagrams if d.get("attach") not in exported_ids]
    if appendix:
        out.append({"title": "Appendix A. Diagrams", "content": "", "diagrams": appendix})
    return out


def _render_diagrams(doc_sections: list[dict]) -> list[str]:
    warnings = []
    for sec in doc_sections:
        for d in sec["diagrams"]:
            d["_png"] = render_png(d["code"])
            if not d["_png"]:
                warnings.append(f"Could not render diagram '{d['title']}' - code included instead.")
    return warnings


# ------------------------------------------------------------------ WORD

def export_docx(project: dict, include_drafts: bool = True) -> tuple[bytes, list[str]]:
    from docx import Document
    from docx.enum.section import WD_SECTION
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor, Cm, Inches

    meta = project["meta"]
    doc_sections = collect_document(project, include_drafts)
    warnings = _render_diagrams(doc_sections)
    NAVY = RGBColor(0x1F, 0x3A, 0x5F)

    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    for side in ("left_margin", "right_margin"):
        setattr(sec, side, Cm(2))
    sec.top_margin = sec.bottom_margin = Cm(2)

    styles = doc.styles
    styles["Normal"].font.name = "Calibri"
    styles["Normal"].font.size = Pt(10.5)
    for name, size in (("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11.5)):
        st = styles[name]
        st.font.name, st.font.size, st.font.color.rgb, st.font.bold = "Calibri", Pt(size), NAVY, True

    def shade(cell, hex_fill):
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_fill)
        tcPr.append(shd)

    def add_runs(par, text, size=None, bold_all=False):
        for style, t in inline_runs(text):
            r = par.add_run(t)
            r.bold = bold_all or style == "b"
            r.italic = style == "i"
            if style == "code":
                r.font.name = "Consolas"
            if size:
                r.font.size = Pt(size)

    def add_field(par, instr):
        r = par.add_run()
        for tag, attr in (("w:fldChar", "begin"), ("w:instrText", None), ("w:fldChar", "separate")):
            el = OxmlElement(tag)
            if attr:
                el.set(qn("w:fldCharType"), attr)
            else:
                el.set(qn("xml:space"), "preserve"); el.text = instr
            r._r.append(el)
        t = OxmlElement("w:t"); t.text = "Right-click and choose 'Update Field' to build the table of contents."
        r._r.append(t)
        end = OxmlElement("w:fldChar"); end.set(qn("w:fldCharType"), "end"); r._r.append(end)

    # ---- cover page
    for _ in range(6):
        doc.add_paragraph()
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(meta.get("project_name") or "Untitled Project"); r.bold = True
    r.font.size = Pt(28); r.font.color.rgb = NAVY
    p = doc.add_paragraph()
    r = p.add_run(meta.get("doc_title") or "Business Requirements & High-Level Design")
    r.font.size = Pt(16); r.font.color.rgb = RGBColor(0x4B, 0x55, 0x63)
    doc.add_paragraph()
    for label, val in (("Client / Business unit", meta.get("client")),
                       ("Prepared by", meta.get("author")),
                       ("Version", meta.get("version") or "0.1"),
                       ("Date", date.today().strftime("%d %B %Y")),
                       ("Status", _doc_status(project, include_drafts))):
        if val:
            p = doc.add_paragraph()
            r = p.add_run(f"{label}: "); r.bold = True
            p.add_run(str(val))
    doc.add_page_break()

    # ---- document control
    doc.add_heading("Document Control", level=1)
    t = doc.add_table(rows=2, cols=5); t.style = "Table Grid"
    for i, h in enumerate(("Version", "Date", "Author", "Status", "Change Description")):
        c = t.rows[0].cells[i]; c.text = ""; add_runs(c.paragraphs[0], h, 9.5, True); shade(c, "1F3A5F")
        c.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    for i, v in enumerate((meta.get("version") or "0.1", date.today().strftime("%d/%m/%Y"),
                           meta.get("author") or "", _doc_status(project, include_drafts),
                           "Generated with BA Copilot; reviewed by author")):
        t.rows[1].cells[i].text = v
    doc.add_paragraph()
    doc.add_heading("Section Review Status", level=2)
    t = doc.add_table(rows=1, cols=2); t.style = "Table Grid"
    for i, h in enumerate(("Section", "Status")):
        c = t.rows[0].cells[i]; c.text = ""; add_runs(c.paragraphs[0], h, 9.5, True); shade(c, "E5E9F0")
    for s in SECTIONS:
        if project["sections"].get(s["id"], "").strip():
            row = t.add_row().cells
            row[0].text = s["title"]; row[1].text = project["status"].get(s["id"], "Draft")
    doc.add_page_break()

    doc.add_heading("Contents", level=1)
    add_field(doc.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u')
    doc.add_page_break()

    # ---- body
    fig = 0
    for sec_i, s in enumerate(doc_sections):
        if sec_i > 0:
            doc.add_page_break()
        doc.add_heading(s["title"], level=1)
        for b in parse_markdown(s["content"]):
            if b["type"] == "heading":
                doc.add_heading(b["text"].replace("**", ""), level=min(b["level"], 3) if b["level"] > 1 else 2)
            elif b["type"] == "para":
                add_runs(doc.add_paragraph(), b["text"])
            elif b["type"] in ("bullet", "number"):
                style = "List Bullet" if b["type"] == "bullet" else "List Number"
                if b["level"] >= 1:
                    style += " 2"
                p = doc.add_paragraph(style=style)
                add_runs(p, b["text"])
            elif b["type"] == "code":
                tbl = doc.add_table(rows=1, cols=1); tbl.style = "Table Grid"
                cell = tbl.rows[0].cells[0]; shade(cell, "F3F4F6")
                cell.text = ""
                par = cell.paragraphs[0]
                r = par.add_run(b["text"]); r.font.name = "Consolas"; r.font.size = Pt(8.5)
                doc.add_paragraph()
            elif b["type"] == "table":
                rows = b["rows"]
                tbl = doc.add_table(rows=len(rows), cols=len(rows[0])); tbl.style = "Table Grid"
                tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                size = 9 if len(rows[0]) <= 5 else 7.5
                widths = _col_widths(rows, 482, char_w=size * 0.55, pad=12)
                tbl.autofit = False
                for ci, w in enumerate(widths):
                    tbl.columns[ci].width = Pt(w)
                for ri, row in enumerate(rows):
                    for ci, val in enumerate(row):
                        c = tbl.rows[ri].cells[ci]; c.text = ""
                        c.width = Pt(widths[ci])
                        add_runs(c.paragraphs[0], val, size, bold_all=(ri == 0))
                        if ri == 0:
                            shade(c, "1F3A5F")
                            for run in c.paragraphs[0].runs:
                                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                        elif ri % 2 == 0:
                            shade(c, "F5F7FA")
                doc.add_paragraph()
        for d in s["diagrams"]:
            fig += 1
            if d.get("_png"):
                doc.add_picture(io.BytesIO(d["_png"]), width=Inches(6.3))
                last = doc.paragraphs[-1]; last.alignment = WD_ALIGN_PARAGRAPH.CENTER
                _cap_height_guard(last)
            else:
                p = doc.add_paragraph(); r = p.add_run(d["code"]); r.font.name = "Consolas"; r.font.size = Pt(8)
            cap = doc.add_paragraph(); cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = cap.add_run(f"Figure {fig}: {d['title']}"); r.italic = True; r.font.size = Pt(9)

    # ---- header / footer with page numbers
    sec = doc.sections[0]
    sec.different_first_page_header_footer = True
    hp = sec.header.paragraphs[0]
    hp.text = f"{meta.get('project_name') or ''}  |  {meta.get('client') or ''}"
    hp.runs[0].font.size = Pt(8); hp.runs[0].font.color.rgb = RGBColor(0x6B, 0x72, 0x80)
    fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = fp.add_run("Page "); r.font.size = Pt(8)
    rr = fp.add_run(); rr.font.size = Pt(8)
    for tag, attr, text in (("w:fldChar", "begin", None), ("w:instrText", None, "PAGE"), ("w:fldChar", "end", None)):
        el = OxmlElement(tag)
        if attr:
            el.set(qn("w:fldCharType"), attr)
        else:
            el.set(qn("xml:space"), "preserve"); el.text = text
        rr._r.append(el)

    # ask Word to refresh the TOC when the file is opened
    settings = doc.settings.element
    upd = OxmlElement("w:updateFields"); upd.set(qn("w:val"), "true"); settings.append(upd)

    buf = io.BytesIO(); doc.save(buf)
    return buf.getvalue(), warnings


def _cap_height_guard(par):
    """Limit very tall diagrams to ~17cm height so they fit on a page."""
    from docx.shared import Cm
    for inline in par._p.xpath(".//wp:inline"):
        ext = inline.xpath("./wp:extent")[0]
        cx, cy = int(ext.get("cx")), int(ext.get("cy"))
        max_cy = Cm(17)
        if cy > max_cy:
            scale = max_cy / cy
            new_cx, new_cy = int(cx * scale), int(max_cy)
            ext.set("cx", str(new_cx)); ext.set("cy", str(new_cy))
            for e in inline.xpath(".//a:ext"):
                e.set("cx", str(new_cx)); e.set("cy", str(new_cy))


def _col_widths(rows, avail_w, char_w=4.6, pad=10):
    """Each column gets at least the width of its longest single word (so IDs like
    REQ-01 never wrap); remaining space is shared in proportion to text length."""
    n = len(rows[0])
    min_w, weight = [], []
    for i in range(n):
        words = [w for r in rows for w in re.split(r"\s+", r[i].replace("**", "")) if w]
        longest = max((len(w) for w in words), default=3)
        min_w.append(min(longest, 18) * char_w + pad)
        weight.append(min(max(len(r[i]) for r in rows), 80) + 1)
    base = sum(min_w)
    if base >= avail_w:
        return [avail_w * m / base for m in min_w]
    extra = avail_w - base
    tot = sum(weight)
    return [m + extra * w / tot for m, w in zip(min_w, weight)]


def _doc_status(project, include_drafts):
    ids = [s["id"] for s in SECTIONS if project["sections"].get(s["id"], "").strip()]
    if ids and all(project["status"].get(i) == "Approved" for i in ids):
        return "Final - all sections approved"
    return "Draft" if include_drafts else "Approved sections only"


# ------------------------------------------------------------------ PDF

def _register_font():
    """Use a Unicode TTF font if one exists (for symbols like → ≥ £), else Helvetica."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.fonts import addMapping
    candidates = [
        ("C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/calibrib.ttf"),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
        ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ]
    for reg, bold in candidates:
        if Path(reg).exists() and Path(bold).exists():
            pdfmetrics.registerFont(TTFont("DocFont", reg))
            pdfmetrics.registerFont(TTFont("DocFont-Bold", bold))
            addMapping("DocFont", 0, 0, "DocFont"); addMapping("DocFont", 1, 0, "DocFont-Bold")
            addMapping("DocFont", 0, 1, "DocFont"); addMapping("DocFont", 1, 1, "DocFont-Bold")
            return "DocFont", "DocFont-Bold", True
    return "Helvetica", "Helvetica-Bold", False


def export_pdf(project: dict, include_drafts: bool = True) -> tuple[bytes, list[str]]:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (BaseDocTemplate, Frame, Image, PageBreak, PageTemplate,
                                    Paragraph, Preformatted, Spacer, Table, TableStyle, KeepTogether)
    from reportlab.platypus.tableofcontents import TableOfContents
    from reportlab.lib.utils import ImageReader

    meta = project["meta"]
    doc_sections = collect_document(project, include_drafts)
    warnings = _render_diagrams(doc_sections)
    font, font_b, unicode_ok = _register_font()
    NAVY = colors.HexColor("#1F3A5F")

    def clean(t):
        if not unicode_ok:
            for a, b in (("→", "->"), ("≥", ">="), ("≤", "<="), ("—", "-"), ("–", "-"), ("✓", "Y")):
                t = t.replace(a, b)
        return t

    def to_rl(text):
        out = []
        for style, t in inline_runs(clean(text)):
            t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if style == "b":
                out.append(f"<b>{t}</b>")
            elif style == "i":
                out.append(f"<i>{t}</i>")
            elif style == "code":
                out.append(f'<font face="Courier">{t}</font>')
            else:
                out.append(t)
        return "".join(out)

    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["Normal"], fontName=font, fontSize=9.5, leading=13, spaceAfter=4)
    h1 = ParagraphStyle("h1", parent=body, fontName=font_b, fontSize=16, leading=20, textColor=NAVY, spaceBefore=4, spaceAfter=10)
    h2 = ParagraphStyle("h2", parent=body, fontName=font_b, fontSize=12.5, leading=16, textColor=NAVY, spaceBefore=10, spaceAfter=5)
    h3 = ParagraphStyle("h3", parent=body, fontName=font_b, fontSize=10.5, leading=14, textColor=NAVY, spaceBefore=8, spaceAfter=4)
    cell = ParagraphStyle("cell", parent=body, fontSize=8, leading=10, spaceAfter=0)
    cell_h = ParagraphStyle("cellh", parent=cell, fontName=font_b, textColor=colors.white)
    code = ParagraphStyle("code", parent=body, fontName="Courier", fontSize=7.8, leading=9.5,
                          backColor=colors.HexColor("#F3F4F6"), borderPadding=6, spaceBefore=4, spaceAfter=8)
    cap = ParagraphStyle("cap", parent=body, fontSize=8.5, alignment=TA_CENTER, textColor=colors.HexColor("#4B5563"))

    page_w, page_h = A4
    margin = 2 * cm
    avail_w = page_w - 2 * margin

    class Doc(BaseDocTemplate):
        def afterFlowable(self, f):
            if isinstance(f, Paragraph) and f.style.name in ("h1", "h2"):
                lvl = 0 if f.style.name == "h1" else 1
                key = f"h{id(f)}"
                self.canv.bookmarkPage(key)
                self.notify("TOCEntry", (lvl, f.getPlainText(), self.page, key))

    def decorate(canv, d):
        if d.page == 1:
            return
        canv.saveState()
        canv.setFont(font, 7.5); canv.setFillColor(colors.HexColor("#6B7280"))
        canv.drawString(margin, page_h - 1.2 * cm, f"{meta.get('project_name') or ''}  |  {meta.get('client') or ''}")
        canv.drawRightString(page_w - margin, 1.1 * cm, f"Page {d.page}")
        canv.setStrokeColor(colors.HexColor("#E5E7EB")); canv.line(margin, page_h - 1.35 * cm, page_w - margin, page_h - 1.35 * cm)
        canv.restoreState()

    buf = io.BytesIO()
    doc = Doc(buf, pagesize=A4, leftMargin=margin, rightMargin=margin, topMargin=margin, bottomMargin=margin,
              title=meta.get("project_name") or "Project Document", author=meta.get("author") or "")
    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(margin, margin, avail_w, page_h - 2 * margin, id="f")],
                                       onPage=decorate)])

    def make_table(rows, header_fill=NAVY, col_widths=None):
        data = [[Paragraph(to_rl(c), cell_h if ri == 0 else cell) for c in r] for ri, r in enumerate(rows)]
        n = len(rows[0])
        if not col_widths:
            col_widths = _col_widths(rows, avail_w)
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), header_fill),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    story = []
    # cover
    story += [Spacer(1, 6 * cm),
              Paragraph(to_rl(meta.get("project_name") or "Untitled Project"),
                        ParagraphStyle("t", parent=h1, fontSize=26, leading=32)),
              Paragraph(to_rl(meta.get("doc_title") or "Business Requirements & High-Level Design"),
                        ParagraphStyle("st", parent=body, fontSize=14, leading=18, textColor=colors.HexColor("#4B5563"))),
              Spacer(1, 1 * cm)]
    for label, val in (("Client / Business unit", meta.get("client")), ("Prepared by", meta.get("author")),
                       ("Version", meta.get("version") or "0.1"), ("Date", date.today().strftime("%d %B %Y")),
                       ("Status", _doc_status(project, include_drafts))):
        if val:
            story.append(Paragraph(f"<b>{label}:</b> {to_rl(str(val))}", body))
    story.append(PageBreak())

    # document control
    story.append(Paragraph("Document Control", ParagraphStyle("dc", parent=h1)))
    story.append(make_table([["Version", "Date", "Author", "Status", "Change Description"],
                             [meta.get("version") or "0.1", date.today().strftime("%d/%m/%Y"), meta.get("author") or "",
                              _doc_status(project, include_drafts), "Generated with BA Copilot; reviewed by author"]]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Section Review Status", ParagraphStyle("dc2", parent=h2)))
    rows = [["Section", "Status"]] + [[s["title"], project["status"].get(s["id"], "Draft")]
                                       for s in SECTIONS if project["sections"].get(s["id"], "").strip()]
    story.append(make_table(rows, col_widths=[avail_w * 0.7, avail_w * 0.3]))
    story.append(PageBreak())

    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("toc1", parent=body, fontName=font_b, fontSize=10.5, leftIndent=0, spaceBefore=4),
                       ParagraphStyle("toc2", parent=body, fontSize=9, leftIndent=14)]
    story += [Paragraph("Contents", ParagraphStyle("ct", parent=h1)), toc, PageBreak()]

    fig = 0
    for si, s in enumerate(doc_sections):
        if si > 0:
            story.append(PageBreak())
        story.append(Paragraph(to_rl(s["title"]), h1))
        for b in parse_markdown(s["content"]):
            if b["type"] == "heading":
                story.append(Paragraph(to_rl(b["text"].replace("**", "")), h2 if b["level"] <= 2 else h3))
            elif b["type"] == "para":
                story.append(Paragraph(to_rl(b["text"]), body))
            elif b["type"] == "bullet":
                story.append(Paragraph(to_rl(b["text"]), ParagraphStyle("bl", parent=body, leftIndent=12 + 12 * b["level"],
                                                                        bulletIndent=2 + 12 * b["level"]),
                                       bulletText="•" if unicode_ok else "-"))
            elif b["type"] == "number":
                story.append(Paragraph(to_rl(b["text"]), ParagraphStyle("nl", parent=body, leftIndent=16 + 12 * b["level"],
                                                                        bulletIndent=2 + 12 * b["level"]),
                                       bulletText=f"{b['num']}."))
            elif b["type"] == "code":
                import textwrap
                wrapped = "\n".join(textwrap.fill(l, 98, subsequent_indent="    ") if len(l) > 98 else l
                                    for l in clean(b["text"]).split("\n"))
                story.append(Preformatted(wrapped, code))
            elif b["type"] == "table":
                story.append(make_table(b["rows"]))
                story.append(Spacer(1, 6))
        for d in s["diagrams"]:
            fig += 1
            if d.get("_png"):
                ir = ImageReader(io.BytesIO(d["_png"]))
                iw, ih = ir.getSize()
                max_h = page_h - 2 * margin - 3 * cm
                scale = min(avail_w / iw, max_h / ih, 1.0 if iw < avail_w * 0.5 else 99)
                img = Image(io.BytesIO(d["_png"]), width=iw * scale, height=ih * scale)
                story.append(KeepTogether([Spacer(1, 8), img, Spacer(1, 4),
                                           Paragraph(f"<i>Figure {fig}: {to_rl(d['title'])}</i>", cap)]))
            else:
                story.append(Preformatted(d["code"], code))
                story.append(Paragraph(f"<i>Figure {fig}: {to_rl(d['title'])} (Mermaid source)</i>", cap))

    doc.multiBuild(story)
    return buf.getvalue(), warnings
