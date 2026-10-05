#!/usr/bin/env python3
"""
Build docs/A2_Naidu_Cohen.pdf from the Module 4 results.

    python3 python/build_a2_pdf.py        (run from the repository root)

Typography follows docs/A1_Naidu_Cohen.pdf: DejaVu Serif throughout, plain
black numbered headings, a metadata block under the title, grid tables with a
grey header row, and an "n / N" page footer.

Numbers come from data/module_04/steady_state.csv via
python/plot_open_loop_calibration.py, and from the Laird CP14-127-045 data
sheet as recorded in docs/assessments/a2_open_loop_tec.md.
"""

import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                Table, TableStyle, KeepTogether)

OUT = "docs/A2_Naidu_Cohen.pdf"
FIG = "docs/figures/module_04/steady_temperature_vs_signed_pwm.png"

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
HEADER_FILL = colors.HexColor("#ECECEC")
GRID = colors.HexColor("#999999")
GREY = colors.HexColor("#555555")

MARGIN = 57          # points, matching A1
TEXT_WIDTH = letter[0] - 2 * MARGIN


def register_fonts():
    """A1 embeds DejaVu Serif, so use the same family here."""
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
                                  bold="DJSerif-Bold",
                                  italic="DJSerif-Italic",
                                  boldItalic="DJSerif-BoldItalic")
    return True


HAVE_DEJAVU = register_fonts()
SERIF = "DJSerif" if HAVE_DEJAVU else "Times-Roman"
SERIF_B = "DJSerif-Bold" if HAVE_DEJAVU else "Times-Bold"
MONO = "DJMono" if HAVE_DEJAVU else "Courier"

title = ParagraphStyle("title", fontName=SERIF_B, fontSize=17, leading=20,
                       spaceAfter=7)
meta = ParagraphStyle("meta", fontName=SERIF, fontSize=8.4, leading=11.0,
                      spaceAfter=0)
h1 = ParagraphStyle("h1", fontName=SERIF_B, fontSize=9.8, leading=11.8,
                    spaceBefore=5.5, spaceAfter=2, keepWithNext=1)
h2 = ParagraphStyle("h2", fontName=SERIF_B, fontSize=8.5, leading=10.4,
                    spaceBefore=4, spaceAfter=1.5, keepWithNext=1)
body = ParagraphStyle("body", fontName=SERIF, fontSize=7.6, leading=9.5,
                      spaceAfter=2.6)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=11,
                        bulletIndent=1, bulletFontName=SERIF,
                        bulletFontSize=7.6, spaceAfter=1.6)
mono = ParagraphStyle("mono", fontName=MONO, fontSize=7.0, leading=9.6,
                      leftIndent=13, spaceBefore=1.5, spaceAfter=3.5)
cap = ParagraphStyle("cap", fontName=SERIF, fontSize=7.1, leading=8.9,
                     textColor=GREY, spaceBefore=3, spaceAfter=2)


def table(rows, widths, size=7.5):
    """Grid table with a grey header row. Cells must be Paragraph objects or
    the <sub> and <super> markup renders literally."""
    th = ParagraphStyle("th", fontName=SERIF_B, fontSize=size,
                        leading=size + 2.6)
    td = ParagraphStyle("td", fontName=SERIF, fontSize=size,
                        leading=size + 2.6)
    data = [[Paragraph(str(c), th) for c in rows[0]]]
    data += [[Paragraph(str(c), td) for c in r] for r in rows[1:]]
    t = Table(data, colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_FILL),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.9),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


class Footer:
    """Draws "n / N" bottom right, as A1 does. Needs the total, so the
    document is built twice and the count from the first pass is reused."""

    def __init__(self):
        self.total = None
        self.count = 0

    def __call__(self, canvas, doc):
        self.count = max(self.count, doc.page)
        label = f"{doc.page} / {self.total}" if self.total else str(doc.page)
        canvas.saveState()
        canvas.setFont(SERIF, 8.5)
        canvas.setFillColor(colors.black)
        canvas.drawRightString(letter[0] - MARGIN, 0.40 * inch, label)
        canvas.restoreState()


def story():
    s = []
    A = s.append

    A(Paragraph("A2: TEC Heating and Cooling Analysis", title))
    for line in [
        "Assessment code: A2",
        "Team members: Kapil Naidu and Samuel Cohen",
        "Date: September 30, 2026 (data collection)",
        "Repository: https://github.com/kapilnaidu1/phys39-naidu-cohen, "
        "branch main",
    ]:
        A(Paragraph(line, meta))
    A(Spacer(1, 9))

    # ------------------------------------------- Part 4
    A(Paragraph("Part 4: Combined graph and fits", h1))
    img = Image(FIG)
    img._restrictSize(TEXT_WIDTH, 2.95 * inch)
    img.hAlign = "CENTER"
    A(img)
    A(Paragraph(
        "<b>Figure 1.</b> Steady-state plate temperature against the signed "
        "PWM command u, positive for heating and negative for cooling, with "
        "both branches on one graph. Ten points, five per branch, about the "
        "zero-command temperature T<sub>0</sub> = 21.54 &deg;C. Each "
        "trendline is drawn only over the PWM range used for its own fit: "
        "u = 0 to +50 counts for heating, u = &minus;65 to 0 counts for "
        "cooling. <b>Steady-state criterion:</b> after each step the trace "
        "was watched for about three driven time constants "
        "(&tau; &asymp; 70 s) plus one further minute, and the point was "
        "accepted once its net drift over that minute was no larger than the "
        "measured noise of 0.16 &deg;C peak to peak. Points that had not "
        "fully arrived are reported as the asymptote of an exponential fit, "
        "and data/module_04/steady_state.csv records which.", cap))

    # ------------------------------------------- Part 5.1
    A(Paragraph("Part 5.1: Measured slopes", h1))
    A(table([["Branch", "Susceptibility dT/du", "Fit range (counts)",
              "R<super>2</super>", "Intercept"],
             ["Heating", "m<sub>h</sub> = 0.5013 &deg;C per PWM count",
              "u = 0 to +50", "1.0000", "21.55 &deg;C"],
             ["Cooling", "m<sub>c</sub> = 0.1809 &deg;C per PWM count",
              "u = &minus;65 to 0", "0.9989", "21.66 &deg;C"]],
            [0.66 * inch, 2.36 * inch, 1.12 * inch, 0.60 * inch, 0.70 * inch]))
    A(Spacer(1, 3))
    A(Paragraph(
        "Against signed u both slopes are positive, so the cooling entry is "
        "already the magnitude |&chi;<sub>T,c</sub>|. The ratio is "
        "<b>r = m<sub>h</sub> / m<sub>c</sub> = 0.5013 / 0.1809 = "
        "2.771</b>, dimensionless because both slopes carry the same units.",
        body))
    A(Paragraph(
        "<b>Curvature and choice of fit range.</b> Neither data set shows "
        "visible curvature, so each branch was fitted over its full measured "
        "range rather than a restricted sub-range; the ranges above are "
        "simply the PWM values used in Part 3. The branches are fitted "
        "separately because the slope changes abruptly at u = 0, not because "
        "either bends. The intercepts differ by 0.11 &deg;C and the cooling "
        "one sits 0.12 &deg;C above T<sub>0</sub>, consistent with the room "
        "drifting over a two-hour session.", body))

    # ------------------------------------------- Part 5.2
    A(Paragraph("Part 5.2: PWM and the slope-ratio model", h1))

    A(Paragraph("Step 1. The steady-state balance", h2))
    A(Paragraph(
        "With C the heat capacity of the object and G the effective passive "
        "conductance to the room, C dT/dt = Q<sub>TEC</sub> &minus; "
        "G(T &minus; T<sub>0</sub>). At steady state dT/dt = 0, so the "
        "individual flows are not zero but their sum is, and "
        "G(T &minus; T<sub>0</sub>) = Q<sub>TEC</sub>. Taking the two terms "
        "in turn: <b>heating</b>, Peltier transport and Joule dissipation "
        "both carry heat <i>into</i> the object while conduction carries heat "
        "<i>out of</i> it to the cooler room; <b>cooling</b>, Peltier "
        "transport carries heat <i>out of</i> the object, Joule dissipation "
        "still carries heat <i>into</i> it, and conduction carries heat "
        "<i>into</i> it from the warmer room.", body))

    A(Paragraph("Step 2. PWM current averages", h2))
    A(Paragraph(
        "Over one PWM period &tau; the bridge delivers the on-state current I "
        "for a time D&tau; and zero for the remaining (1&minus;D)&tau;, with "
        "duty D = |u| / 255. Both integrands vanish outside the on-interval, "
        "so each integral is just the integrand times D&tau;:", body))
    A(Paragraph(
        "&lt;I&gt;  = (1/&tau;) &int;<sub>0</sub><super>&tau;</super> I(t) dt "
        " = (1/&tau;) &middot; I &middot; D&tau;  = <b>D I</b><br/>"
        "&lt;I<super>2</super>&gt; = (1/&tau;) "
        "&int;<sub>0</sub><super>&tau;</super> I<super>2</super>(t) dt = "
        "(1/&tau;) &middot; I<super>2</super> &middot; D&tau; = "
        "<b>D I<super>2</super></b>", mono))
    A(Paragraph(
        "&lt;I<super>2</super>&gt; is not &lt;I&gt;<super>2</super> = "
        "D<super>2</super>I<super>2</super>: squaring and averaging do not "
        "commute, and for a two-level waveform the two differ by a factor "
        "1/D. Peltier transport follows &lt;I&gt; and Joule heating follows "
        "&lt;I<super>2</super>&gt;, and under PWM both are linear in D, so "
        "the susceptibility is constant and the branches are straight. Had "
        "the Joule term gone as D<super>2</super> the susceptibility would "
        "vary with duty and the branches would curve measurably; the measured "
        "R<super>2</super> of 1.0000 and 0.9989 says they do not. With a DAC "
        "supplying a steady current of variable amplitude instead, "
        "&lt;I<super>2</super>&gt; = &lt;I&gt;<super>2</super> would hold, so "
        "the distinction is a property of PWM.", body))

    A(Paragraph("Step 3. The slope ratio", h2))
    A(Paragraph(
        "With signed duty d = u / 255 and D = |d|, Peltier transport reverses "
        "with the current and Joule heating does not, so "
        "Q<sub>TEC</sub> = d Q<sub>P</sub> + |d| Q<sub>J</sub>. Substituting "
        "each branch into G(T &minus; T<sub>0</sub>) = Q<sub>TEC</sub> and "
        "differentiating with respect to d:", body))
    A(Paragraph(
        "heating, d &gt; 0:&nbsp; G(T<sub>h</sub> &minus; T<sub>0</sub>) = "
        "d(Q<sub>P</sub> + Q<sub>J</sub>) &nbsp;&rarr;&nbsp; T<sub>h</sub> "
        "&minus; T<sub>0</sub> = d(Q<sub>P</sub> + Q<sub>J</sub>)/G "
        "&nbsp;&rarr;&nbsp; <b>dT<sub>h</sub>/dd = (Q<sub>P</sub> + "
        "Q<sub>J</sub>)/G</b><br/>"
        "cooling, d &lt; 0:&nbsp; G(T<sub>c</sub> &minus; T<sub>0</sub>) = "
        "d(Q<sub>P</sub> &minus; Q<sub>J</sub>) &nbsp;&rarr;&nbsp; "
        "T<sub>c</sub> &minus; T<sub>0</sub> = d(Q<sub>P</sub> &minus; "
        "Q<sub>J</sub>)/G &nbsp;&rarr;&nbsp; <b>dT<sub>c</sub>/dd = "
        "(Q<sub>P</sub> &minus; Q<sub>J</sub>)/G</b>", mono))
    A(Paragraph(
        "Both are positive while Q<sub>P</sub> &gt; Q<sub>J</sub>, and the "
        "heating one is larger. Since d = u / 255, each measured slope "
        "carries the same factor 1/255, and that factor and G are common to "
        "both branches, so both cancel from the ratio:", body))
    A(Paragraph(
        "r = m<sub>h</sub>/m<sub>c</sub> = (Q<sub>P</sub> + Q<sub>J</sub>) / "
        "(Q<sub>P</sub> &minus; Q<sub>J</sub>) &nbsp;&nbsp;&rArr;&nbsp;&nbsp; "
        "<b>Q<sub>J</sub>/Q<sub>P</sub> = (r &minus; 1)/(r + 1)</b>"
        "&nbsp;&nbsp;&nbsp;&nbsp;check: r = 2 gives 1/3 exactly<br/>"
        "r = 2.771:&nbsp; Q<sub>J</sub>/Q<sub>P</sub> = (2.771 &minus; 1) / "
        "(2.771 + 1) = 1.771 / 3.771 = <b>0.470</b>", mono))
    A(Paragraph(
        "Joule heat reaching the object face is 47.0% of the Peltier pumping. "
        "Both are heat rates in watts, so the ratio is dimensionless. G "
        "cancels from r, which matters because G was never measured.", body))

    # ------------------------------------------- Part 5.3
    A(Paragraph("Part 5.3: Laird data-sheet calculation", h1))
    A(Paragraph(
        "<b>Source.</b> Laird CP14-127-045-L2-W4.5, MFG part 58910-501, from "
        "the SPECIFICATIONS table on the first page of the CP14-127-045 data "
        "sheet, hot-side temperature T<sub>h</sub> = 27.0 &deg;C column.",
        body))
    A(table([["Quantity", "Value", "Meaning, and the operating condition attached"],
             ["R<sub>M</sub>", "1.50 &Omega;",
              "Ohmic resistance of the 127 couples in series, quoted at "
              "T<sub>h</sub> = 27 &deg;C and rising to 1.68 &Omega; at "
              "50 &deg;C"],
             ["I<sub>max</sub>", "8.6 A",
              "The current giving the largest temperature difference, not a "
              "safety ceiling. Condition: I at &Delta;T<sub>max</sub>"],
             ["Q<sub>c,max</sub>", "71.3 W",
              "Most heat the cold face can absorb. Condition: "
              "<b>&Delta;T = 0</b>, no difference to pump against"],
             ["&Delta;T<sub>max</sub>", "70.5 &deg;C",
              "Largest sustainable temperature difference. Condition: "
              "<b>Q<sub>c</sub> = 0</b>, no heat load"]],
            [0.66 * inch, 0.60 * inch, 5.64 * inch]))
    A(Spacer(1, 3))
    A(Paragraph(
        "The last two sit at opposite ends of one trade-off: maximum pumping "
        "needs zero temperature difference, maximum difference needs zero "
        "load. At the data-sheet condition &Delta;T = 0, so conduction "
        "through the module vanishes and the symmetric model puts half the "
        "Joule heat on each face:", body))
    A(Paragraph(
        "Q<sub>J,max</sub> = &frac12; I<sub>max</sub><super>2</super> "
        "R<sub>M</sub> = &frac12; (8.6 A)<super>2</super> (1.50 &Omega;) = "
        "&frac12; (73.96 A<super>2</super>)(1.50 &Omega;) = <b>55.47 W</b>"
        "<br/>"
        "Q<sub>c,max</sub> = Q<sub>P,max</sub> &minus; Q<sub>J,max</sub> "
        "&nbsp;&rarr;&nbsp; Q<sub>P,max</sub> = 71.3 W + 55.47 W = "
        "<b>126.77 W</b><br/>"
        "r<sub>Laird,max</sub> = (Q<sub>P,max</sub> + Q<sub>J,max</sub>) / "
        "(Q<sub>P,max</sub> &minus; Q<sub>J,max</sub>) = (126.77 + 55.47) / "
        "(126.77 &minus; 55.47) = 182.24 / 71.30 = <b>2.556</b>", mono))
    A(Paragraph(
        "Every quantity above is a heat rate in watts, so "
        "r<sub>Laird,max</sub> is dimensionless and directly comparable with "
        "the measured r. <b>Cross-check:</b> V<sub>max</sub>/I<sub>max</sub> "
        "= 13.9 V / 8.6 A = 1.616 &Omega;, 8% above R<sub>M</sub>, because at "
        "&Delta;T<sub>max</sub> the module develops a Seebeck back-EMF: "
        "V<sub>max</sub> = I<sub>max</sub>R<sub>M</sub> + "
        "S&middot;&Delta;T<sub>max</sub> gives S = 0.0142 V/K, reasonable for "
        "127 bismuth telluride couples. The right rows were read.", body))

    # ------------------------------------------- Part 5.4 comparison
    A(Paragraph("Part 5.4: Compare the ratios", h1))
    A(table([["", "r", "Q<sub>J</sub>/Q<sub>P</sub>", "Condition"],
             ["Measured, this apparatus", "2.771", "0.470",
              "PWM drive, finite &Delta;T, current set by the supply and "
              "bridge"],
             ["Laird, at I<sub>max</sub>", "2.556", "0.438",
              "steady DC at 8.6 A, &Delta;T = 0"],
             ["ratio", "1.084", "1.073", "agreement to 8%"]],
            [1.54 * inch, 0.50 * inch, 0.66 * inch, 4.20 * inch]))
    A(Spacer(1, 3))
    A(Paragraph(
        "The two agree to 8%, closer than the comparison warrants, since the "
        "data-sheet figures describe a condition this apparatus never "
        "reaches:", body))
    for text in [
        "<b>D = 1 does not mean I = I<sub>max</sub>.</b> Full duty only means "
        "the bridge is continuously on. The current is set by the 12 V supply "
        "and its limit, the H-bridge forward drop, wiring resistance and "
        "R<sub>M</sub>, which together hold the bench current well below "
        "8.6 A.",
        "<b>PWM, not steady DC.</b> The bench current is chopped; the data "
        "sheet assumes a steady one.",
        "<b>Finite &Delta;T and passive heat paths.</b> The data-sheet "
        "relation is stated at &Delta;T = 0, while the plate ran 25 &deg;C "
        "above and 12 &deg;C below ambient. There the module's own conduction "
        "and the mounting and air paths are not negligible, and all of them "
        "are absorbed into the single G.",
        "<b>Coefficients move with temperature, and one slope is fitted per "
        "branch.</b> R<sub>M</sub> rises from 1.50 to 1.68 &Omega; between 27 "
        "and 50 &deg;C, so a single fit averages over a range in which the "
        "coefficients are not strictly constant.",
    ]:
        A(Paragraph(text, bullet, bulletText="\u2022"))
    A(Spacer(1, 2))
    A(Paragraph(
        "<b>Direction of the difference.</b> The measured ratio is the "
        "larger, yet running below I<sub>max</sub> should <i>reduce</i> "
        "Q<sub>J</sub>/Q<sub>P</sub>, since that ratio scales as I. The "
        "opposite sign points to dissipation this model assigns to the "
        "object face that the data sheet does not carry, such as lead and "
        "contact resistance in series with the module.", body))

    # ------------------------------------------- Part 5.4 conduction
    A(Paragraph("Part 5.4: Passive conduction", h1))
    A(Paragraph(
        "When the object is hotter than the room, passive heat flows <b>out "
        "of</b> the object. When it is colder, passive heat flows <b>into</b> "
        "it. Either way the flow drives the object back toward room "
        "temperature, so conduction opposes the TEC on both branches, which "
        "is why it enters as &minus;G(T &minus; T<sub>0</sub>) with a single "
        "positive G.", body))
    A(Paragraph(
        "It cannot by itself explain the unequal slope magnitudes. The same G "
        "appears in the denominator of both dT<sub>h</sub>/dd and "
        "dT<sub>c</sub>/dd, so it sets how steep the branches are, a larger G "
        "flattening both, but it cancels exactly from their ratio: a "
        "symmetric term cannot produce an asymmetric result. The asymmetry "
        "survives only in the numerators, where Q<sub>J</sub> is added on the "
        "heating branch and subtracted on the cooling one, because Peltier "
        "transport reverses with the current and Joule heating does not.",
        body))

    return s


def build():
    footer = Footer()
    for pass_number in (1, 2):
        doc = SimpleDocTemplate(
            OUT, pagesize=letter,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=0.62 * inch,
            title="A2: TEC Heating and Cooling Analysis",
            author="Kapil Naidu and Samuel Cohen",
            subject="Phys 39 Module 4, open-loop TEC calibration")
        doc.build(story(), onFirstPage=footer, onLaterPages=footer)
        if pass_number == 1:
            footer.total = footer.count
    print(f"wrote {OUT}, {footer.total} pages")


if __name__ == "__main__":
    if not os.path.exists(FIG):
        raise SystemExit(f"{FIG} not found. Run the plot script first.")
    if not HAVE_DEJAVU:
        print(f"DejaVu fonts not found in {FONT_DIR}; falling back to Times.")
    build()
