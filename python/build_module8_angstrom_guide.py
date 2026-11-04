#!/usr/bin/env python3
"""Build the plain-language Module 8 Angstrom study guide PDF."""

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (Paragraph, Preformatted, SimpleDocTemplate,
                                Spacer, Table, TableStyle)


ROOT = Path(__file__).resolve().parents[1]
GUIDE_DIR = ROOT / "docs" / "sammy_module_08_guide"
SOURCE = GUIDE_DIR / "Phys39_Module_8_Angstrom_Study_Guide.md"
OUTPUT = GUIDE_DIR / "Phys39_Module_8_Angstrom_Study_Guide.pdf"

INK = colors.HexColor("#202B35")
MUTED = colors.HexColor("#596874")
ACCENT = colors.HexColor("#176B73")
RULE = colors.HexColor("#D5DEE5")
CODE_FILL = colors.HexColor("#F1F5F7")
TABLE_FILL = colors.HexColor("#E7EDF1")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("GuideTitle", parent=styles["Title"],
                          fontName="Times-Bold", fontSize=21, leading=25,
                          alignment=0, textColor=INK, spaceAfter=6))
styles.add(ParagraphStyle("GuideSubtitle", fontName="Times-Italic",
                          fontSize=10.2, leading=13, textColor=MUTED,
                          spaceAfter=10))
styles.add(ParagraphStyle("GuideH1", fontName="Times-Bold", fontSize=13.2,
                          leading=16, textColor=ACCENT, spaceBefore=9,
                          spaceAfter=4, keepWithNext=True))
styles.add(ParagraphStyle("GuideH2", fontName="Times-Bold", fontSize=10.2,
                          leading=12.5, textColor=INK, spaceBefore=6,
                          spaceAfter=3, keepWithNext=True))
styles.add(ParagraphStyle("GuideBody", fontName="Times-Roman", fontSize=8.7,
                          leading=11.6, textColor=INK, spaceAfter=4))
styles.add(ParagraphStyle("GuideBullet", parent=styles["GuideBody"],
                          leftIndent=13, firstLineIndent=-9, spaceAfter=2.5))
styles.add(ParagraphStyle("GuideSmall", fontName="Times-Roman", fontSize=7.1,
                          leading=8.8, textColor=INK))
styles.add(ParagraphStyle("GuideCode", fontName="Courier", fontSize=7.1,
                          leading=9.2, textColor=INK, leftIndent=4))


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return text


def parse_table(lines):
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    count = len(rows[0])
    width = 7.18 * inch
    col_widths = [width / count] * count
    header = ParagraphStyle("GuideTableHeader", fontName="Times-Bold",
                            fontSize=6.9, leading=8.4, textColor=INK)
    cell_style = styles["GuideSmall"]
    data = [[Paragraph(inline(cell), header) for cell in rows[0]]]
    data.extend([[Paragraph(inline(cell), cell_style) for cell in row]
                 for row in rows[1:]])
    table = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_FILL),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.line(0.66 * inch, 0.55 * inch, 7.84 * inch, 0.55 * inch)
    canvas.setFont("Times-Roman", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.68 * inch, 0.36 * inch,
                      "Phys 39 | Module 8 Angstrom method study guide")
    canvas.drawRightString(7.82 * inch, 0.36 * inch, str(doc.page))
    canvas.restoreState()


def build_story():
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    story = []
    index = 0

    while index < len(lines) and not lines[index].strip():
        index += 1
    if not lines[index].startswith("# "):
        raise ValueError("Guide source must begin with a level-one title")
    story.append(Paragraph(inline(lines[index][2:]), styles["GuideTitle"]))
    index += 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index < len(lines) and not lines[index].startswith("#"):
        story.append(Paragraph(inline(lines[index]), styles["GuideSubtitle"]))
        index += 1

    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith("## "):
            story.append(Paragraph(inline(line[3:]), styles["GuideH1"]))
            index += 1
        elif line.startswith("### "):
            story.append(Paragraph(inline(line[4:]), styles["GuideH2"]))
            index += 1
        elif line.startswith("```"):
            index += 1
            block = []
            while index < len(lines) and not lines[index].startswith("```"):
                block.append(lines[index])
                index += 1
            if index == len(lines):
                raise ValueError("Unclosed fenced code block in guide source")
            code = Preformatted("\n".join(block), styles["GuideCode"])
            box = Table([[code]], colWidths=[7.18 * inch], hAlign="LEFT")
            box.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), CODE_FILL),
                ("BOX", (0, 0), (-1, -1), 0.4, RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.extend([box, Spacer(1, 4)])
            index += 1
        elif line.startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].startswith("|"):
                table_lines.append(lines[index])
                index += 1
            story.extend([parse_table(table_lines), Spacer(1, 4)])
        elif line.startswith("- "):
            story.append(Paragraph("&#8226; " + inline(line[2:]),
                                   styles["GuideBullet"]))
            index += 1
        elif re.match(r"\d+\. ", line):
            match = re.match(r"(\d+)\. (.*)", line)
            story.append(Paragraph(match.group(1) + ". " + inline(match.group(2)),
                                   styles["GuideBullet"]))
            index += 1
        else:
            paragraph = [line.strip()]
            index += 1
            while (index < len(lines) and lines[index].strip()
                   and not lines[index].startswith(("#", "```", "|", "- "))
                   and not re.match(r"\d+\. ", lines[index])):
                paragraph.append(lines[index].strip())
                index += 1
            story.append(Paragraph(inline(" ".join(paragraph)),
                                   styles["GuideBody"]))
    return story


def main():
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=letter, rightMargin=0.66 * inch,
        leftMargin=0.66 * inch, topMargin=0.62 * inch,
        bottomMargin=0.72 * inch, title="Module 8 Angstrom Study Guide",
        author="Phys 39 course companion")
    doc.build(build_story(), onFirstPage=footer, onLaterPages=footer)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()