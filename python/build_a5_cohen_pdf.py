#!/usr/bin/env python3
"""
Build docs/A5_Cohen.pdf from docs/assessments/a5_angstrom_cohen.md.  SAMMY.

    python3 python/sammy_module8_a5_write.py        (writes the Markdown, the figures and the CSV files)
    python3 python/build_a5_cohen_pdf.py            (run from the repository root)

The Markdown file is the single source of the A5 text; this script only lays it out in the house style of A1 and A2
(serif font, plain numbered headings, a metadata block under the title, grid tables with a grey header row, an "n / N" footer).
It is Kapil's python/build_a5_pdf.py with the file names, the author and the font search changed. It understands the small
subset of Markdown the A5 file uses: headings, paragraphs, "- " bullets, pipe tables, fenced code blocks, images, **bold**,
*italic*, `code`, and <sub>/<sup>.

The Git checkpoint on the first page is the commit checked out when the PDF is built (git rev-parse HEAD), which holds the code,
data, figures and the Markdown source cited in the PDF.
"""

import os
import re
import subprocess

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                Table, TableStyle, Preformatted, KeepTogether)

SRC = "docs/assessments/a5_angstrom_cohen.md"
OUT = "docs/A5_Cohen.pdf"
REPO_URL = "https://github.com/kapilnaidu1/phys39-naidu-cohen"

HEADER_FILL = colors.HexColor("#ECECEC")
GRID = colors.HexColor("#999999")
GREY = colors.HexColor("#555555")
MARGIN = 54
TEXT_WIDTH = letter[0] - 2 * MARGIN


def font_dirs():
    dirs = ["/usr/share/fonts/truetype/dejavu"]
    try:
        import matplotlib
        dirs.insert(0, os.path.join(matplotlib.get_data_path(), "fonts", "ttf"))
    except ImportError:
        pass
    return dirs


def register_fonts():
    faces = [("DJSerif", "DejaVuSerif.ttf"), ("DJSerif-Bold", "DejaVuSerif-Bold.ttf"),
             ("DJSerif-Italic", "DejaVuSerif-Italic.ttf"), ("DJSerif-BoldItalic", "DejaVuSerif-BoldItalic.ttf"),
             ("DJMono", "DejaVuSansMono.ttf"), ("DJSans", "DejaVuSans.ttf")]
    for d in font_dirs():
        if all(os.path.exists(os.path.join(d, f)) for _, f in faces):
            for name, filename in faces:
                pdfmetrics.registerFont(TTFont(name, os.path.join(d, filename)))
            pdfmetrics.registerFontFamily("DJSerif", normal="DJSerif", bold="DJSerif-Bold", italic="DJSerif-Italic",
                                          boldItalic="DJSerif-BoldItalic")
            return True
    return False


if not register_fonts():
    raise SystemExit("DejaVu fonts not found (matplotlib's bundled fonts or /usr/share/fonts/truetype/dejavu).")
SERIF, SERIF_B, MONO = "DJSerif", "DJSerif-Bold", "DJMono"
SANS_ONLY = set(pdfmetrics.getFont("DJSans").face.charToGlyph) - set(pdfmetrics.getFont(SERIF).face.charToGlyph)

title = ParagraphStyle("title", fontName=SERIF_B, fontSize=17, leading=20, spaceAfter=7)
meta = ParagraphStyle("meta", fontName=SERIF, fontSize=8.6, leading=11.2)
h1 = ParagraphStyle("h1", fontName=SERIF_B, fontSize=11, leading=13.4, spaceBefore=9, spaceAfter=3, keepWithNext=1)
h2 = ParagraphStyle("h2", fontName=SERIF_B, fontSize=9.6, leading=12, spaceBefore=6, spaceAfter=2, keepWithNext=1)
body = ParagraphStyle("body", fontName=SERIF, fontSize=8.7, leading=11.0, spaceAfter=4, allowWidows=0)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=12, bulletIndent=2, spaceAfter=2.5)
cap = ParagraphStyle("cap", fontName=SERIF, fontSize=7.9, leading=10.0, textColor=GREY, spaceBefore=2, spaceAfter=6)
tcap = ParagraphStyle("tcap", parent=cap, spaceBefore=3, spaceAfter=2.5)
mono = ParagraphStyle("mono", fontName=MONO, fontSize=7.8, leading=10.2, leftIndent=14, spaceBefore=1, spaceAfter=5)
TABLE_SIZE = 7.6


def inline(text):
    """Markdown inline markup to ReportLab paragraph markup (characters the serif face lacks are set in DejaVu Sans)."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = "".join(f'<font name="DJSans">{c}</font>' if ord(c) in SANS_ONLY else c for c in text)
    for tag, rl in (("sub", "sub"), ("sup", "super")):
        text = text.replace(f"&lt;{tag}&gt;", f"<{rl}>")
        text = text.replace(f"&lt;/{tag}&gt;", f"</{rl}>")
    text = re.sub(r"`([^`]+)`", rf'<font name="{MONO}">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<i>\1</i>", text)
    return text


def column_widths(rows):
    """Column widths from the text itself. Body cells are kept on one line where they are short (up to ONE_LINE points); headers may wrap
    but not inside a word. If the table is wider than the page the long columns give way first; if it is narrower the slack is spread evenly."""
    pad, one_line = 7.0, 95.0
    ncol = len(rows[0])
    nat, low = [], []
    for i in range(ncol):
        head = re.sub(r"<[^>]+>", "", rows[0][i])
        body = [re.sub(r"<[^>]+>", "", r[i]) for r in rows[1:]]
        w_head = stringWidth(head, SERIF_B, TABLE_SIZE)
        w_body = max([stringWidth(c, SERIF, TABLE_SIZE) for c in body] + [0.0])
        word_head = max(stringWidth(w, SERIF_B, TABLE_SIZE) for w in (head.split() or [""]))
        word_body = max([stringWidth(w, SERIF, TABLE_SIZE) for c in body for w in (c.split() or [""])] + [0.0])
        nat.append(max(w_head, w_body) + pad)
        low.append(max(word_head, word_body, min(w_body, one_line)) + pad)
    total = sum(nat)
    if total <= TEXT_WIDTH:
        return [w * TEXT_WIDTH / total for w in nat]
    for cap in (95.0, 80.0, 65.0, 50.0, 0.0):
        low = []
        for i in range(ncol):
            head = re.sub(r"<[^>]+>", "", rows[0][i])
            body = [re.sub(r"<[^>]+>", "", r[i]) for r in rows[1:]]
            w_body = max([stringWidth(c, SERIF, TABLE_SIZE) for c in body] + [0.0])
            word_head = max(stringWidth(w, SERIF_B, TABLE_SIZE) for w in (head.split() or [""]))
            word_body = max([stringWidth(w, SERIF, TABLE_SIZE) for c in body for w in (c.split() or [""])] + [0.0])
            low.append(max(word_head, word_body, min(w_body, cap)) + pad)
        if sum(low) <= TEXT_WIDTH:
            break
    slack = [a - b for a, b in zip(nat, low)]
    need = total - TEXT_WIDTH
    if sum(slack) >= need:
        return [a - need * s / sum(slack) for a, s in zip(nat, slack)]
    return [w * TEXT_WIDTH / sum(low) for w in low]


def table(rows):
    th = ParagraphStyle("th", fontName=SERIF_B, fontSize=TABLE_SIZE, leading=TABLE_SIZE + 2.4)
    td = ParagraphStyle("td", fontName=SERIF, fontSize=TABLE_SIZE, leading=TABLE_SIZE + 2.4)
    widths = column_widths(rows)
    data = [[Paragraph(inline(c), th) for c in rows[0]]]
    data += [[Paragraph(inline(c), td) for c in r] for r in rows[1:]]
    t = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_FILL),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    return t


def image(rel_path):
    path = os.path.normpath(os.path.join(os.path.dirname(SRC), rel_path))
    if not os.path.exists(path):
        raise SystemExit(f"{path} not found. Run python/sammy_module8_a5_write.py first.")
    img = Image(path)
    img._restrictSize(TEXT_WIDTH, 6.6 * inch)
    img.hAlign = "CENTER"
    return img


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "(not available)"


class FloatBlock(KeepTogether):
    """A figure with its caption or a table with its caption."""


class FlushMarker(Spacer):
    """Last flowable of the story: releases floats that are still waiting."""

    def __init__(self):
        super().__init__(0, 0)


class FloatDoc(SimpleDocTemplate):
    """A float that does not fit in the space left on the page waits while the text after it fills the page; it is then placed at the top
    of the next page, in its original order relative to the other floats."""

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._waiting, self._wait_page, self._final, self._rest = [], 0, False, None

    def build(self, flowables, **kw):
        super().build(list(flowables) + [FlushMarker()], **kw)

    def handle_flowable(self, flowables):
        first = flowables[0]
        if self._waiting:
            if isinstance(first, FlushMarker):
                self._final = True
            if self._final or self.page > self._wait_page:
                if first is self._rest and not self._final:
                    released, self._waiting, self._rest = self._waiting, [], None
                    super().handle_flowable(flowables)
                    flowables[0:0] = released
                    return
                flowables[0:0] = self._waiting
                self._waiting = []
                first = flowables[0]
            elif isinstance(first, FloatBlock):
                self._waiting.append(flowables.pop(0))
                return
        if isinstance(first, FloatBlock) and not self._final:
            first.wrapOn(self.canv, self.frame._getAvailableWidth(), 10 ** 6)
            if first._H > self.frame._y - self.frame._y1p and not self.frame._atTop:
                self._waiting, self._wait_page = [flowables.pop(0)], self.page
                return
        follower = flowables[1] if len(flowables) > 1 else None
        super().handle_flowable(flowables)
        if self._waiting and isinstance(first, Paragraph) and not getattr(first.style, "keepWithNext", 0) and flowables and flowables[0] is not follower \
                and isinstance(flowables[0], Paragraph):
            self._rest = flowables[0]


def story():
    lines = open(SRC, encoding="utf-8").read().splitlines()
    s, i = [], 0
    pending_image = None
    pending_caption = None
    block_starts = ("#", "|", "![", "- ", "```")

    def take(i, skip=0):
        """The paragraph or bullet starting at line i with its soft-wrapped continuation lines; returns (text, next line)."""
        parts = [lines[i].strip()[skip:]]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(block_starts):
            parts.append(lines[i].strip())
            i += 1
        return " ".join(parts), i

    assert lines[0].startswith("# ")
    s.append(Paragraph(inline(lines[0][2:]), title))
    i = 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    while i < len(lines) and lines[i].strip():
        s.append(Paragraph(inline(lines[i].rstrip()), meta))
        i += 1
    s.append(Paragraph(f"Git checkpoint: commit {git_head()}", meta))
    url = f"{REPO_URL}/commit/{git_head()}"
    s.append(Paragraph(f'<a href="{url}" color="#1F4E79">{url}</a>', ParagraphStyle("url", parent=meta, fontSize=7.8)))
    s.append(Paragraph("Markdown source: " + SRC, meta))
    s.append(Spacer(1, 6))

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("### "):
            s.append(Paragraph(inline(line[4:]), h2))
            i += 1
        elif line.startswith("## "):
            s.append(Paragraph(inline(line[3:]), h1))
            i += 1
        elif line.startswith("```"):
            j = i + 1
            block = []
            while not lines[j].startswith("```"):
                block.append(lines[j])
                j += 1
            s.append(Preformatted("\n".join(block), mono))
            i = j + 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            t = table(rows)
            s.append(FloatBlock([Paragraph(inline(pending_caption), tcap), t]) if pending_caption else t)
            pending_caption = None
            s.append(Spacer(1, 5))
        elif line.startswith("!["):
            m = re.match(r"!\[[^\]]*\]\(([^)]+)\)", line)
            pending_image = image(m.group(1))
            i += 1
        elif line.startswith("- "):
            text, i = take(i, 2)
            s.append(Paragraph(inline(text), bullet, bulletText="\u2022"))
        else:
            text, i = take(i)
            if text.startswith("**Figure") and pending_image is not None:
                s.append(FloatBlock([pending_image, Paragraph(inline(text), cap)]))
                pending_image = None
            elif text.startswith("**Table"):
                pending_caption = text
            else:
                s.append(Paragraph(inline(text), body))
    if pending_image is not None:
        s.append(pending_image)
    return s


class Footer:
    def __init__(self):
        self.total = None
        self.count = 0

    def __call__(self, canvas, doc):
        self.count = max(self.count, doc.page)
        label = f"{doc.page} / {self.total}" if self.total else str(doc.page)
        canvas.saveState()
        canvas.setFont(SERIF, 8.5)
        canvas.drawRightString(letter[0] - MARGIN, 0.40 * inch, label)
        canvas.restoreState()


def build():
    footer = Footer()
    for pass_number in (1, 2):
        doc = FloatDoc(OUT, pagesize=letter, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN,
                       bottomMargin=0.58 * inch, title="A5: S18 Evidence, Boundary-Control Analysis and Angstrom Theory",
                       author="Samuel Cohen", subject="Phys 39 Module 8, Angstrom method")
        doc.build(story(), onFirstPage=footer, onLaterPages=footer)
        if pass_number == 1:
            footer.total = footer.count
    print(f"wrote {OUT}, {footer.total} pages, checkpoint {git_head()}")


if __name__ == "__main__":
    build()
