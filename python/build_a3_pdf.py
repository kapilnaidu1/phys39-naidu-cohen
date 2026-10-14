#!/usr/bin/env python3
"""
Build docs/A3_Naidu_Cohen.pdf from docs/assessments/a3_feedback_model.md.

    python3 python/build_a3_pdf.py        (run from the repository root)

The Markdown file is the single source of the A3 text; this script only lays
it out, in the house style of A1 and A2 (DejaVu Serif, plain numbered
headings, a metadata block under the title, grid tables with a grey header
row, an "n / N" footer). It understands the small subset of Markdown the A3
file uses: headings, paragraphs, "- " bullets, pipe tables, fenced code
blocks, images, **bold**, *italic*, `code`, and <sub>/<sup>.

The Git checkpoint on the first page is the commit checked out when the PDF
is built (git rev-parse HEAD), which holds the code, data, figures and the
Markdown source cited in the PDF.

Figures come from python/plot_a3_figures.py.
"""

import os
import re
import subprocess

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                Table, TableStyle, Preformatted, KeepTogether)

SRC = "docs/assessments/a3_feedback_model.md"
OUT = "docs/A3_Naidu_Cohen.pdf"

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
HEADER_FILL = colors.HexColor("#ECECEC")
GRID = colors.HexColor("#999999")
GREY = colors.HexColor("#555555")
MARGIN = 57
TEXT_WIDTH = letter[0] - 2 * MARGIN


def register_fonts():
    faces = [("DJSerif", "DejaVuSerif.ttf"),
             ("DJSerif-Bold", "DejaVuSerif-Bold.ttf"),
             ("DJSerif-Italic", "DejaVuSerif-Italic.ttf"),
             ("DJSerif-BoldItalic", "DejaVuSerif-BoldItalic.ttf"),
             ("DJMono", "DejaVuSansMono.ttf")]
    for name, filename in faces:
        path = os.path.join(FONT_DIR, filename)
        if not os.path.exists(path):
            return False
        pdfmetrics.registerFont(TTFont(name, path))
    pdfmetrics.registerFontFamily("DJSerif", normal="DJSerif",
                                  bold="DJSerif-Bold", italic="DJSerif-Italic",
                                  boldItalic="DJSerif-BoldItalic")
    return True


if not register_fonts():
    raise SystemExit(f"DejaVu fonts not found in {FONT_DIR}.")
SERIF, SERIF_B, MONO = "DJSerif", "DJSerif-Bold", "DJMono"

title = ParagraphStyle("title", fontName=SERIF_B, fontSize=17, leading=20,
                       spaceAfter=7)
meta = ParagraphStyle("meta", fontName=SERIF, fontSize=8.6, leading=11.2)
h1 = ParagraphStyle("h1", fontName=SERIF_B, fontSize=11, leading=13.4,
                    spaceBefore=9, spaceAfter=3, keepWithNext=1)
body = ParagraphStyle("body", fontName=SERIF, fontSize=8.7, leading=11.2,
                      spaceAfter=4)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=12, bulletIndent=2,
                        spaceAfter=2.5)
cap = ParagraphStyle("cap", fontName=SERIF, fontSize=7.9, leading=10.0,
                     textColor=GREY, spaceBefore=2, spaceAfter=6)
mono = ParagraphStyle("mono", fontName=MONO, fontSize=7.8, leading=10.2,
                      leftIndent=14, spaceBefore=1, spaceAfter=5)
TABLE_SIZE = 7.6


def inline(text):
    """Markdown inline markup to ReportLab paragraph markup."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for tag, rl in (("sub", "sub"), ("sup", "super")):
        text = text.replace(f"&lt;{tag}&gt;", f"<{rl}>")
        text = text.replace(f"&lt;/{tag}&gt;", f"</{rl}>")
    text = re.sub(r"`([^`]+)`", rf'<font name="{MONO}">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<i>\1</i>", text)
    return text


def table(rows):
    th = ParagraphStyle("th", fontName=SERIF_B, fontSize=TABLE_SIZE,
                        leading=TABLE_SIZE + 2.4)
    td = ParagraphStyle("td", fontName=SERIF, fontSize=TABLE_SIZE,
                        leading=TABLE_SIZE + 2.4)
    ncol = len(rows[0])
    lengths = [max(len(re.sub(r"<[^>]+>", "", r[i])) for r in rows)
               for i in range(ncol)]
    weights = [min(n, 46) + 6 for n in lengths]
    widths = [TEXT_WIDTH * w / sum(weights) for w in weights]
    data = [[Paragraph(inline(c), th) for c in rows[0]]]
    data += [[Paragraph(inline(c), td) for c in r] for r in rows[1:]]
    t = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_FILL),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    return t


def image(rel_path):
    path = os.path.normpath(os.path.join(os.path.dirname(SRC), rel_path))
    if not os.path.exists(path):
        raise SystemExit(f"{path} not found. Run python/plot_a3_figures.py first.")
    img = Image(path)
    img._restrictSize(TEXT_WIDTH, 6.6 * inch)
    img.hAlign = "CENTER"
    return img


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"],
                                       text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "(not available)"


def story():
    lines = open(SRC, encoding="utf-8").read().splitlines()
    s, i = [], 0
    pending_image = None

    # Title and metadata block
    assert lines[0].startswith("# ")
    s.append(Paragraph(inline(lines[0][2:]), title))
    i = 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    while i < len(lines) and lines[i].strip():
        s.append(Paragraph(inline(lines[i].rstrip()), meta))
        i += 1
    s.append(Paragraph(f"Git checkpoint: commit {git_head()}", meta))
    s.append(Paragraph("Markdown source of this memo: " + SRC, meta))
    s.append(Spacer(1, 6))

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("## "):
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
            s.append(table(rows))
            s.append(Spacer(1, 5))
        elif line.startswith("!["):
            m = re.match(r"!\[[^\]]*\]\(([^)]+)\)", line)
            pending_image = image(m.group(1))
            i += 1
        elif line.startswith("- "):
            s.append(Paragraph(inline(line[2:]), bullet, bulletText="•"))
            i += 1
        else:
            if line.startswith("**Figure") and pending_image is not None:
                s.append(KeepTogether([pending_image,
                                       Paragraph(inline(line), cap)]))
                pending_image = None
            else:
                s.append(Paragraph(inline(line), body))
            i += 1
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
        doc = SimpleDocTemplate(
            OUT, pagesize=letter, leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=0.62 * inch,
            title="A3: Feedback Data and Lumped-Model Memo",
            author="Kapil Naidu and Samuel Cohen",
            subject="Phys 39 Module 6, P/PI control and lumped thermal models")
        doc.build(story(), onFirstPage=footer, onLaterPages=footer)
        if pass_number == 1:
            footer.total = footer.count
    print(f"wrote {OUT}, {footer.total} pages, checkpoint {git_head()}")


if __name__ == "__main__":
    build()
