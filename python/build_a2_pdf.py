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
h1 = ParagraphStyle("h1", fontName=SERIF_B, fontSize=10.2, leading=12.2,
                    spaceBefore=6, spaceAfter=2.5, keepWithNext=1)
h2 = ParagraphStyle("h2", fontName=SERIF_B, fontSize=8.8, leading=10.8,
                    spaceBefore=4.5, spaceAfter=1.5, keepWithNext=1)
body = ParagraphStyle("body", fontName=SERIF, fontSize=7.9, leading=9.9,
                      spaceAfter=2.8)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=11,
                        bulletIndent=1, bulletFontName=SERIF,
                        bulletFontSize=7.9, spaceAfter=1.8)
mono = ParagraphStyle("mono", fontName=MONO, fontSize=7.2, leading=10.0,
                      leftIndent=13, spaceBefore=1.5, spaceAfter=3.5)
cap = ParagraphStyle("cap", fontName=SERIF, fontSize=7.3, leading=9.1,
                     textColor=GREY, spaceBefore=3, spaceAfter=2)


def table(rows, widths, size=7.7):
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

    # ------------------------------------------------------------------ 1
    A(Paragraph("1. Steady-state temperature versus signed PWM", h1))
    img = Image(FIG)
    img._restrictSize(TEXT_WIDTH, 2.30 * inch)
    img.hAlign = "CENTER"
    A(img)
    A(Paragraph(
        "<b>Figure 1.</b> Steady-state plate temperature against the signed "
        "PWM command u, positive for heating and negative for cooling. Ten "
        "points, five per branch, about the zero-command temperature "
        "T<sub>0</sub> = 21.54 &deg;C. Each trendline is fitted only over "
        "its own branch. <b>Steady-state criterion:</b> after each step the "
        "trace was watched for about three driven time constants "
        "(&tau; &asymp; 70 s) plus one further minute, and the point was "
        "accepted once its net drift over that minute was no larger than the "
        "measured noise of 0.16 &deg;C peak to peak. Points that had not "
        "fully arrived are reported as the asymptote of an exponential fit, "
        "and data/module_04/steady_state.csv records which.", cap))

    # ------------------------------------------------------------------ 2
    A(Paragraph("2. Slopes, units, fit ranges and ratio", h1))
    A(table([["Branch", "Susceptibility dT/du", "Fit range",
              "R<super>2</super>", "Intercept"],
             ["Heating", "m<sub>h</sub> = 0.5013 &deg;C per PWM count",
              "u = 0 to +50", "1.0000", "21.55 &deg;C"],
             ["Cooling", "m<sub>c</sub> = 0.1809 &deg;C per PWM count",
              "u = &minus;65 to 0", "0.9989", "21.66 &deg;C"]],
            [0.66 * inch, 2.36 * inch, 1.12 * inch, 0.60 * inch, 0.70 * inch]))
    A(Spacer(1, 3))
    A(Paragraph(
        "Both branches are linear with no visible curvature, so neither "
        "slope is a local estimate. <b>r = m<sub>h</sub> / m<sub>c</sub> = "
        "2.771.</b> The intercepts differ by 0.11 &deg;C and the cooling one "
        "sits 0.12 &deg;C above T<sub>0</sub>, consistent with the room "
        "drifting over a two-hour session.", body))

    # ------------------------------------------------------------------ 3
    A(Paragraph("3. Derivation", h1))

    A(Paragraph("3.1 PWM current averages", h2))
    A(Paragraph(
        "Over one PWM period &tau; the bridge delivers current I for a time "
        "D&tau; and zero for the remaining (1&minus;D)&tau;, with duty "
        "D = |u| / 255. Both integrands vanish outside the on-interval, so",
        body))
    A(Paragraph(
        "&lt;I&gt;  = (1/&tau;) &int; I dt  = (1/&tau;) &middot; I &middot; "
        "D&tau;  = <b>D I</b><br/>"
        "&lt;I<super>2</super>&gt; = (1/&tau;) &int; I<super>2</super> dt = "
        "(1/&tau;) &middot; I<super>2</super> &middot; D&tau; = "
        "<b>D I<super>2</super></b>", mono))
    A(Paragraph(
        "&lt;I<super>2</super>&gt; is not &lt;I&gt;<super>2</super> = "
        "D<super>2</super>I<super>2</super>: squaring and averaging do not "
        "commute, and for a two-level waveform the two differ by a factor "
        "1/D. Peltier transport follows &lt;I&gt; and Joule heating follows "
        "&lt;I<super>2</super>&gt;, and under PWM both are linear in D, so "
        "the susceptibility dT/du is constant and the graph is straight. Had "
        "the Joule term gone as D<super>2</super> the branches would curve "
        "visibly; they do not.", body))

    A(Paragraph("3.2 Steady-state energy balance", h2))
    A(Paragraph(
        "With C the heat capacity of the object and G the conductance "
        "between it and the room, C dT/dt = Q<sub>TEC</sub> &minus; "
        "G(T &minus; T<sub>0</sub>). At steady state dT/dt = 0, so the "
        "individual flows are not zero but their sum is, and "
        "G(T &minus; T<sub>0</sub>) = Q<sub>TEC</sub>. With signed duty "
        "d = u / 255, Peltier transport reverses with the current and Joule "
        "heating does not, so Q<sub>TEC</sub> = d Q<sub>P</sub> + "
        "|d| Q<sub>J</sub>. On the heating branch d &gt; 0 and both terms "
        "deliver heat into the object; on the cooling branch d &lt; 0 and "
        "Peltier removes heat while Joule still adds it. Hence", body))
    A(Paragraph(
        "T<sub>h</sub> &minus; T<sub>0</sub> = d (Q<sub>P</sub> + "
        "Q<sub>J</sub>) / G &nbsp;&nbsp;&rarr;&nbsp;&nbsp; "
        "<b>dT<sub>h</sub>/dd = (Q<sub>P</sub> + Q<sub>J</sub>) / G</b><br/>"
        "T<sub>c</sub> &minus; T<sub>0</sub> = d (Q<sub>P</sub> &minus; "
        "Q<sub>J</sub>) / G &nbsp;&nbsp;&rarr;&nbsp;&nbsp; "
        "<b>dT<sub>c</sub>/dd = (Q<sub>P</sub> &minus; Q<sub>J</sub>) / G</b>",
        mono))

    A(Paragraph("3.3 Slope ratio and numerical result", h2))
    A(Paragraph(
        "Since d = u / 255, each measured slope carries the same factor "
        "1/255, and that factor and G are common to both branches, so both "
        "cancel from the ratio:", body))
    A(Paragraph(
        "r = m<sub>h</sub>/m<sub>c</sub> = (Q<sub>P</sub> + Q<sub>J</sub>) / "
        "(Q<sub>P</sub> &minus; Q<sub>J</sub>) &nbsp;&nbsp;&rArr;&nbsp;&nbsp; "
        "<b>Q<sub>J</sub>/Q<sub>P</sub> = (r &minus; 1)/(r + 1)</b>"
        "&nbsp;&nbsp;&nbsp;&nbsp;check: r = 2 gives exactly 1/3<br/>"
        "r = 2.771 gives Q<sub>J</sub>/Q<sub>P</sub> = 1.771 / 3.771 = "
        "<b>0.470</b>", mono))
    A(Paragraph(
        "Joule heat reaching the object face is about 47% of the Peltier "
        "pumping. G cancels from r, which matters because G was never "
        "measured.", body))

    # ------------------------------------------------------------------ 4
    A(Paragraph("4. Laird data sheet", h1))
    A(Paragraph(
        "Source: Laird CP14-127-045-L2-W4.5, MFG part 58910-501, "
        "SPECIFICATIONS table, hot side temperature 27.0 &deg;C column.",
        body))
    A(table([["Quantity", "Value", "Meaning, and the condition attached"],
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
        "<b>55.47 W</b><br/>"
        "Q<sub>P,max</sub> = Q<sub>c,max</sub> + Q<sub>J,max</sub> = 71.3 W + "
        "55.47 W = <b>126.77 W</b><br/>"
        "r<sub>Laird</sub> = (126.77 + 55.47) / (126.77 &minus; 55.47) = "
        "<b>2.556</b>", mono))
    A(Paragraph(
        "<b>Cross-check.</b> V<sub>max</sub>/I<sub>max</sub> = 13.9 / 8.6 = "
        "1.616 &Omega;, 8% above the quoted R<sub>M</sub>, because at "
        "&Delta;T<sub>max</sub> the module develops a Seebeck back-EMF: "
        "V<sub>max</sub> = I<sub>max</sub>R<sub>M</sub> + "
        "S&middot;&Delta;T<sub>max</sub> gives S = 0.0142 V/K, a reasonable "
        "coefficient for 127 bismuth telluride couples. The right rows were "
        "read.", body))

    # ------------------------------------------------------------------ 5
    A(Paragraph("5. Comparison", h1))
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
        "<b>Finite &Delta;T.</b> The data-sheet relation is stated at "
        "&Delta;T = 0, while the plate ran 25 &deg;C above and 12 &deg;C "
        "below ambient, where conduction through the module is absorbed "
        "into G.",
        "<b>Coefficients move with temperature.</b> R<sub>M</sub> rises from "
        "1.50 to 1.68 &Omega; between 27 and 50 &deg;C, and one slope is "
        "fitted across each whole branch.",
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

    # ------------------------------------------------------------------ 6
    A(Paragraph("6. Passive conduction", h1))
    A(Paragraph(
        "When the object is hotter than the room, heat flows out of it; when "
        "it is colder, heat flows in. Either way the flow drives the object "
        "back toward room temperature, so conduction opposes the TEC on both "
        "branches, which is why it enters as &minus;G(T &minus; "
        "T<sub>0</sub>) with a single positive G.", body))
    A(Paragraph(
        "It cannot explain the unequal slopes. The same G appears in the "
        "denominator of both dT<sub>h</sub>/dd and dT<sub>c</sub>/dd, so it "
        "sets how steep the branches are, a larger G flattening both, but it "
        "cancels exactly from their ratio: a symmetric term cannot produce "
        "an asymmetric result. The asymmetry survives only in the numerators, "
        "where Q<sub>J</sub> is added on the heating branch and subtracted on "
        "the cooling one.", body))

    # ------------------------------------------------------------------ 7
    A(Paragraph("7. Conclusion", h1))
    A(Paragraph(
        "Steady-state temperature is linear in signed PWM on both branches "
        "(R<super>2</super> = 1.0000 heating, 0.9989 cooling), which is what "
        "the PWM averages predict: Peltier transport follows &lt;I&gt; = DI "
        "and Joule heating follows &lt;I<super>2</super>&gt; = "
        "DI<super>2</super>, so both scale with duty and the susceptibility "
        "stays constant. Had &lt;I<super>2</super>&gt; gone as "
        "D<super>2</super>, the branches would curve. The slopes differ by "
        "r = 2.771 because reversing the current reverses Peltier pumping "
        "but not Joule heating, so the two add when heating and oppose when "
        "cooling, giving Q<sub>J</sub>/Q<sub>P</sub> = (r &minus; 1)/(r + 1) "
        "= 0.470. Conduction enters both branches through the same G and "
        "cancels from the ratio, setting how steep the lines are but not "
        "making them unequal. The Laird maximum-current figures predict "
        "r = 2.556, within 8% of a condition this apparatus never reaches.",
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
