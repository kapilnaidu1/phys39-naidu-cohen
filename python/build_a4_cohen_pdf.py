#!/usr/bin/env python3
"""Build the independent Cohen A4 PDF from its Markdown source."""

import html
import re
import subprocess
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (Paragraph, Preformatted, SimpleDocTemplate,
                                Spacer, Table, TableStyle)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "assessments" / "a4_finite_length_biot_cohen.md"
OUTPUT = ROOT / "docs" / "A4_Cohen.pdf"
PAGE_WIDTH = letter[0]
MARGIN = 52
TEXT_WIDTH = PAGE_WIDTH - 2 * MARGIN

INK = colors.HexColor("#202B35")
MUTED = colors.HexColor("#5A6872")
ACCENT = colors.HexColor("#176B73")
RULE = colors.HexColor("#D5DEE5")
TABLE_FILL = colors.HexColor("#E7EDF1")
CODE_FILL = colors.HexColor("#F1F5F7")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("A4Title", fontName="Times-Bold", fontSize=17,
                          leading=20, textColor=INK, spaceAfter=7))
styles.add(ParagraphStyle("A4Meta", fontName="Times-Roman", fontSize=8.3,
                          leading=10.4, textColor=MUTED))
styles.add(ParagraphStyle("A4H1", fontName="Times-Bold", fontSize=11.2,
                          leading=13, textColor=ACCENT, spaceBefore=7,
                          spaceAfter=2, keepWithNext=True))
styles.add(ParagraphStyle("A4H2", fontName="Times-Bold", fontSize=9.4,
                          leading=11, textColor=INK, spaceBefore=5,
                          spaceAfter=1.5, keepWithNext=True))
styles.add(ParagraphStyle("A4Body", fontName="Times-Roman", fontSize=8.2,
                          leading=10.4, textColor=INK, spaceAfter=3.2))
styles.add(ParagraphStyle("A4BodyKeep", parent=styles["A4Body"],
                          keepWithNext=True))
styles.add(ParagraphStyle("A4Bullet", parent=styles["A4Body"],
                          leftIndent=12, firstLineIndent=-8, spaceAfter=2))
styles.add(ParagraphStyle("A4Code", fontName="Courier", fontSize=7.0,
                          leading=8.6, textColor=INK, leftIndent=3))
styles.add(ParagraphStyle("A4Cell", fontName="Times-Roman", fontSize=6.9,
                          leading=8.1, textColor=INK))


def inline(text):
    links = []

    def preserve_link(match):
        links.append((match.group(1), match.group(2)))
        return f"LINKTOKEN{len(links) - 1}ENDTOKEN"

    text = re.sub(r"\[([^]]+)\]\((https?://[^)]+)\)", preserve_link, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<i>\1</i>", text)
    for index, (label, url) in enumerate(links):
        token = f"LINKTOKEN{index}ENDTOKEN"
        text = text.replace(token, f'<link href="{html.escape(url, quote=True)}">{html.escape(label)}</link>')
    return text


def make_table(lines):
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    column_count = len(rows[0])
    lengths = [max(len(re.sub(r"`", "", row[i])) for row in rows)
               for i in range(column_count)]
    weights = [min(54, max(10, length)) for length in lengths]
    widths = [TEXT_WIDTH * weight / sum(weights) for weight in weights]
    header_style = ParagraphStyle("A4TableHeader", fontName="Times-Bold",
                                  fontSize=7.0, leading=8.6, textColor=INK)
    data = [[Paragraph(inline(cell), header_style) for cell in rows[0]]]
    data += [[Paragraph(inline(cell), styles["A4Cell"]) for cell in row]
             for row in rows[1:]]
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_FILL),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    return table


def git_head():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.line(MARGIN, 0.52 * inch, PAGE_WIDTH - MARGIN, 0.52 * inch)
    canvas.setFont("Times-Roman", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 0.34 * inch, "Phys 39 | A4 | Samuel Cohen")
    canvas.drawRightString(PAGE_WIDTH - MARGIN, 0.34 * inch, str(doc.page))
    canvas.restoreState()


def story():
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError("A4 source must begin with a level-one heading")
    flow = [Paragraph(inline(lines[0][2:]), styles["A4Title"])]
    index = 1
    while index < len(lines) and lines[index].strip():
        flow.append(Paragraph(inline(lines[index].rstrip()), styles["A4Meta"]))
        index += 1
    flow.append(Paragraph("Git checkpoint: " + git_head(), styles["A4Meta"]))
    flow.append(Paragraph("Markdown source: docs/assessments/a4_finite_length_biot_cohen.md",
                          styles["A4Meta"]))
    flow.append(Spacer(1, 5))

    index += 1
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
        elif line.startswith("## "):
            flow.append(Paragraph(inline(line[3:]), styles["A4H1"]))
            index += 1
        elif line.startswith("### "):
            flow.append(Paragraph(inline(line[4:]), styles["A4H2"]))
            index += 1
        elif line.startswith("```"):
            index += 1
            code_lines = []
            while index < len(lines) and not lines[index].startswith("```"):
                code_lines.append(lines[index])
                index += 1
            if index == len(lines):
                raise ValueError("Unclosed code fence in A4 source")
            code = Preformatted("\n".join(code_lines), styles["A4Code"])
            box = Table([[code]], colWidths=[TEXT_WIDTH], hAlign="LEFT")
            box.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), CODE_FILL),
                ("BOX", (0, 0), (-1, -1), 0.4, RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            flow.extend([box, Spacer(1, 3)])
            index += 1
        elif line.startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].startswith("|"):
                table_lines.append(lines[index])
                index += 1
            flow.extend([make_table(table_lines), Spacer(1, 4)])
        elif line.startswith("- "):
            flow.append(Paragraph("&#8226; " + inline(line[2:]), styles["A4Bullet"]))
            index += 1
        else:
            paragraph = [line.strip()]
            index += 1
            while (index < len(lines) and lines[index].strip()
                   and not lines[index].startswith(("#", "```", "|", "- "))):
                paragraph.append(lines[index].strip())
                index += 1
            next_index = index
            while next_index < len(lines) and not lines[next_index].strip():
                next_index += 1
            paragraph_style = (styles["A4BodyKeep"]
                               if next_index < len(lines)
                               and lines[next_index].startswith("```")
                               else styles["A4Body"])
            flow.append(Paragraph(inline(" ".join(paragraph)), paragraph_style))
    return flow


def main():
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=letter, leftMargin=MARGIN,
        rightMargin=MARGIN, topMargin=44, bottomMargin=0.64 * inch,
        title="A4: Finite-Rod Model and Validity Checks - Samuel Cohen",
        author="Samuel Cohen",
        subject="Individual A4 assessment")
    doc.build(story(), onFirstPage=footer, onLaterPages=footer)
    print(f"Wrote {OUTPUT} with checkpoint {git_head()}")


if __name__ == "__main__":
    main()