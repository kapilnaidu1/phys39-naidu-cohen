#!/usr/bin/env python3
"""
Build A2_Naidu_Cohen.pdf from the Module 4 results.

    python3 python/build_a2_pdf.py        (run from the repository root)

Two pages, matching the seven items the assignment lists, in its order.
Deliberately dense: the brief says one to two pages, and the rubric gives a
point for being concise and legible, so the layout is tight rather than airy.

Numbers come from data/module_04/steady_state.csv via
python/plot_open_loop_calibration.py, and from the Laird CP14-127-045 data
sheet as recorded in docs/assessments/a2_open_loop_tec.md.
"""

import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                Table, TableStyle, KeepTogether)

OUT = "A2_Naidu_Cohen.pdf"
FIG = "docs/figures/module_04/steady_temperature_vs_signed_pwm.png"

HEAT = colors.HexColor("#C0392B")
COOL = colors.HexColor("#1F77B4")
GREY = colors.HexColor("#555555")
RULE = colors.HexColor("#BBBBBB")

ss = getSampleStyleSheet()

title = ParagraphStyle("title", parent=ss["Title"], fontSize=15, spaceAfter=2,
                       textColor=colors.HexColor("#222222"))
byline = ParagraphStyle("byline", parent=ss["Normal"], fontSize=8.5,
                        textColor=GREY, spaceAfter=8, alignment=1)
h = ParagraphStyle("h", parent=ss["Heading2"], fontSize=10, spaceBefore=7,
                   spaceAfter=2, textColor=colors.HexColor("#1F4E79"))
body = ParagraphStyle("body", parent=ss["Normal"], fontSize=8.6, leading=10.8,
                      alignment=TA_JUSTIFY, spaceAfter=3)
mono = ParagraphStyle("mono", parent=ss["Normal"], fontName="Courier",
                      fontSize=7.8, leading=9.8, leftIndent=10, spaceAfter=3,
                      textColor=colors.HexColor("#333333"))
cap = ParagraphStyle("cap", parent=ss["Normal"], fontSize=7.2, leading=8.6,
                     textColor=GREY, spaceAfter=4)


def tbl(data, widths, align_right=(), size=7.8):
    # Table cells only render <sub>, <super> and <b> when they hold Paragraph
    # objects; plain strings come out as literal markup. Wrap every cell.
    hdr = ParagraphStyle("th", parent=ss["Normal"], fontName="Helvetica-Bold",
                         fontSize=size, leading=size + 2,
                         textColor=colors.HexColor("#1F4E79"))
    cell = ParagraphStyle("td", parent=ss["Normal"], fontName="Helvetica",
                          fontSize=size, leading=size + 2)
    wrapped = [[Paragraph(str(c), hdr) for c in data[0]]]
    wrapped += [[Paragraph(str(c), cell) for c in row] for row in data[1:]]
    t = Table(wrapped, colWidths=widths, hAlign="LEFT")
    style = [
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, RULE),
        ("LINEBELOW", (0, -1), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
    ]
    for c in align_right:
        style.append(("ALIGN", (c, 0), (c, -1), "RIGHT"))
    t.setStyle(TableStyle(style))
    return t


def build():
    doc = SimpleDocTemplate(OUT, pagesize=letter,
                            leftMargin=0.62 * inch, rightMargin=0.62 * inch,
                            topMargin=0.5 * inch, bottomMargin=0.45 * inch,
                            title="A2: TEC Heating and Cooling Analysis",
                            author="K. Naidu, S. Cohen")
    s = []
    A = s.append

    A(Paragraph("A2: TEC Heating and Cooling Analysis", title))
    A(Paragraph("K. Naidu and S. Cohen &middot; Phys 39 Module 4 &middot; "
                "open-loop TEC calibration &middot; data taken 30 September 2026",
                byline))

    # ---------------------------------------------------------------- 1
    A(Paragraph("1. Steady-state temperature versus signed PWM", h))
    img = Image(FIG)
    img._restrictSize(6.6 * inch, 3.55 * inch)
    img.hAlign = "CENTER"
    A(img)
    A(Paragraph(
        "Ten steady-state points, five per branch, about the zero-PWM "
        "temperature T<sub>0</sub> = 21.54 &deg;C. Steady state: after each "
        "PWM step the trace was watched for about three thermal time "
        "constants (&tau; &asymp; 70 s driven) and then one further minute, "
        "and a point was accepted once its net drift over that minute was no "
        "larger than the measured short-term noise of 0.16 &deg;C "
        "peak-to-peak. Points that had not fully arrived within the session "
        "are reported as the asymptote of an exponential fit to the approach; "
        "data/module_04/steady_state.csv records which. Trendlines are fitted "
        "only over the range of each branch.", cap))

    # ---------------------------------------------------------------- 2
    A(Paragraph("2. Measured susceptibilities and their ratio", h))
    A(tbl([["Branch", "Susceptibility dT/du", "Fit range (counts)", "R²",
            "Intercept"],
           ["Heating", "m<sub>h</sub> = 0.5013 °C per PWM count",
            "u = 0 to +50", "1.0000", "21.55 °C"],
           ["Cooling", "m<sub>c</sub> = 0.1809 °C per PWM count",
            "u = −65 to 0", "0.9989", "21.66 °C"]],
          [0.75 * inch, 2.5 * inch, 1.3 * inch, 0.7 * inch, 0.9 * inch],
          align_right=(3,)))
    A(Spacer(1, 3))
    A(Paragraph(
        "Both branches are linear; neither needs to be reported as a local "
        "estimate. <b>r = m<sub>h</sub>/m<sub>c</sub> = 2.771.</b> The two "
        "intercepts differ by 0.11 &deg;C and the cooling one sits 0.12 "
        "&deg;C above the measured T<sub>0</sub>, most likely the room "
        "drifting over a two-hour session.", body))

    # ---------------------------------------------------------------- 3
    A(Paragraph("3. PWM averaging, steady-state balance, and the slope ratio", h))
    A(Paragraph(
        "<b>(a) How PWM averages current.</b> Over one period the current is "
        "I for a time D&tau; and zero for the remaining (1&minus;D)&tau;, "
        "with D = |u|/255. Both integrands vanish off the on-interval, so",
        body))
    A(Paragraph(
        "&lt;I&gt; = (1/&tau;)&int;I dt = (1/&tau;)&middot;I&middot;D&tau; = "
        "<b>DI</b>&nbsp;&nbsp;&nbsp;&nbsp;&lt;I<super>2</super>&gt; = "
        "(1/&tau;)&int;I<super>2</super> dt = "
        "(1/&tau;)&middot;I<super>2</super>&middot;D&tau; = "
        "<b>DI<super>2</super></b>", mono))
    A(Paragraph(
        "&lt;I<super>2</super>&gt; is not &lt;I&gt;<super>2</super> = "
        "D<super>2</super>I<super>2</super>: squaring and averaging do not "
        "commute, and for a two-level waveform they differ by exactly 1/D. "
        "This is what makes the graph straight. Peltier transport follows "
        "&lt;I&gt; and Joule heating follows &lt;I<super>2</super>&gt;, and "
        "both are <i>linear in D</i>, so the susceptibility is constant. Had "
        "the Joule term gone as D<super>2</super> the branches would curve "
        "measurably; the heating branch is linear to one part in a thousand, "
        "so the measurement supports the result. (With a DAC supplying steady "
        "current, &lt;I<super>2</super>&gt; = &lt;I&gt;<super>2</super> would "
        "hold; the distinction is a property of PWM.)", body))
    A(Paragraph(
        "<b>(b) Steady state.</b> From C dT/dt = Q<sub>TEC</sub> &minus; "
        "G(T&minus;T<sub>0</sub>) with dT/dt = 0, the individual flows are "
        "not zero but their sum is, so G(T&minus;T<sub>0</sub>) = "
        "Q<sub>TEC</sub>. With signed duty d = u/255, Peltier reversing with "
        "the current and Joule heating not: Q<sub>TEC</sub> = "
        "dQ<sub>P</sub> + |d|Q<sub>J</sub>. On the heating branch d &gt; 0 so "
        "both terms deliver heat into the object and conduction carries it "
        "out; on the cooling branch d &lt; 0, Peltier removes heat while "
        "Joule still adds it, and conduction supplies heat inward. Hence",
        body))
    A(Paragraph(
        "T<sub>h</sub>&minus;T<sub>0</sub> = d(Q<sub>P</sub>+Q<sub>J</sub>)/G"
        "&nbsp;&nbsp;&nbsp;&nbsp;"
        "T<sub>c</sub>&minus;T<sub>0</sub> = d(Q<sub>P</sub>&minus;Q<sub>J</sub>)/G"
        "<br/>dT<sub>h</sub>/dd = (Q<sub>P</sub>+Q<sub>J</sub>)/G"
        "&nbsp;&nbsp;&nbsp;&nbsp;"
        "dT<sub>c</sub>/dd = (Q<sub>P</sub>&minus;Q<sub>J</sub>)/G", mono))
    A(Paragraph(
        "<b>(c) The ratio.</b> Since d = u/255, each measured slope carries a "
        "factor 1/255, and that factor and G are common to both, so both "
        "cancel from r:", body))
    A(Paragraph(
        "r = (Q<sub>P</sub>+Q<sub>J</sub>)/(Q<sub>P</sub>&minus;Q<sub>J</sub>)"
        "&nbsp;&nbsp;&rArr;&nbsp;&nbsp;"
        "<b>Q<sub>J</sub>/Q<sub>P</sub> = (r&minus;1)/(r+1)</b>"
        "&nbsp;&nbsp;&nbsp;check: r = 2 gives exactly 1/3", mono))
    A(Paragraph(
        "With r = 2.771: <b>Q<sub>J</sub>/Q<sub>P</sub> = 0.470.</b> Joule "
        "heat delivered to the object face is about 47% of the Peltier "
        "pumping. That r is independent of G, which was never measured, is "
        "what makes it the useful quantity here.", body))

    # ---------------------------------------------------------------- 4
    A(Paragraph("4. Laird CP14-127-045 data sheet, hot side 27.0 &deg;C", h))
    A(tbl([["Quantity", "Value", "Meaning and the operating condition attached"],
           ["R<sub>M</sub>", "1.50 Ω",
            "Ohmic resistance of the 127 couples in series, quoted at "
            "T<sub>h</sub> = 27 °C; rises to 1.68 Ω at 50 °C"],
           ["I<sub>max</sub>", "8.6 A",
            "The current giving the <i>largest temperature difference</i>, "
            "not a safety ceiling. Condition: I at ΔT<sub>max</sub>"],
           ["Q<sub>c,max</sub>", "71.3 W",
            "Most heat the cold face can absorb. Condition: "
            "<b>ΔT = 0</b>, no difference to pump against"],
           ["ΔT<sub>max</sub>", "70.5 °C",
            "Largest sustainable temperature difference. Condition: "
            "<b>Q<sub>c</sub> = 0</b>, no heat load"]],
          [0.62 * inch, 0.6 * inch, 4.93 * inch]))
    A(Spacer(1, 2))
    A(Paragraph(
        "The last two sit at opposite ends of one trade-off: maximum pumping "
        "requires zero temperature difference, maximum difference requires "
        "zero load. At the data-sheet condition &Delta;T = 0, so conduction "
        "vanishes and the symmetric model puts half the Joule heat on each "
        "face:", body))
    A(Paragraph(
        "Q<sub>J,max</sub> = ½ I<sub>max</sub><super>2</super> "
        "R<sub>M</sub> = ½ (8.6 A)<super>2</super>(1.50 Ω) = "
        "<b>55.47 W</b><br/>"
        "Q<sub>P,max</sub> = Q<sub>c,max</sub> + Q<sub>J,max</sub> = "
        "71.3 W + 55.47 W = <b>126.77 W</b><br/>"
        "r<sub>Laird,max</sub> = (126.77 + 55.47)/(126.77 − 55.47) = "
        "<b>2.556</b>", mono))
    A(Paragraph(
        "<i>Cross-check that the right rows were read:</i> "
        "V<sub>max</sub>/I<sub>max</sub> = 13.9/8.6 = 1.616 &Omega;, which is "
        "8% above the quoted R<sub>M</sub>. Not an inconsistency &mdash; at "
        "&Delta;T<sub>max</sub> the module develops a Seebeck back-EMF, so "
        "V<sub>max</sub> = I<sub>max</sub>R<sub>M</sub> + "
        "S&middot;&Delta;T<sub>max</sub>, giving S = 0.0142 V/K, a sensible "
        "coefficient for 127 bismuth telluride couples.", body))

    # ---------------------------------------------------------------- 5
    A(Paragraph("5. Comparison of measured and data-sheet ratios", h))
    A(tbl([["", "r", "Q<sub>J</sub>/Q<sub>P</sub>", "Condition"],
           ["Measured, this apparatus", "2.771", "0.470",
            "PWM, finite ΔT, current set by the supply and bridge"],
           ["Laird, at I<sub>max</sub>", "2.556", "0.438",
            "steady DC at 8.6 A, ΔT = 0"],
           ["ratio", "1.084", "", "agreement to 8%"]],
          [1.6 * inch, 0.6 * inch, 0.75 * inch, 3.2 * inch]))
    A(Spacer(1, 2))
    A(Paragraph(
        "<b>They are not expected to agree, and 8% is closer than this "
        "comparison deserves.</b> D = 1 does not imply I = I<sub>max</sub>: "
        "full duty only means the bridge is continuously on, while the actual "
        "current is set by the 12 V supply and its limit, the H-bridge "
        "forward drop, wiring resistance and R<sub>M</sub>, which together "
        "put the bench current well below 8.6 A. Beyond that: our current is "
        "chopped rather than steady DC; the data-sheet relation holds at "
        "&Delta;T = 0 whereas the plate ran 25 &deg;C above and 12 &deg;C "
        "below ambient, where the conduction term is not negligible and is "
        "absorbed into G; the coefficients move with temperature (the same "
        "sheet shows R<sub>M</sub> rising 1.50 &rarr; 1.68 &Omega; between 27 "
        "and 50 &deg;C); and one slope is fitted to each branch. "
        "<i>Direction of the difference:</i> ours is the larger, yet "
        "operating below I<sub>max</sub> should <i>reduce</i> "
        "Q<sub>J</sub>/Q<sub>P</sub>, since that ratio scales as I. The "
        "opposite sign points at dissipation our model assigns to the object "
        "face that the data sheet does not carry, such as lead and contact "
        "resistance in series with the module.", body))

    # ---------------------------------------------------------------- 6
    A(Paragraph("6. Passive conduction", h))
    A(Paragraph(
        "When the object is hotter than the room, heat flows <b>out</b> of "
        "it; when colder, heat flows <b>in</b>. Either way the flow drives "
        "the object back toward room temperature, so conduction opposes the "
        "TEC on both branches, which is why it enters as &minus;G(T&minus;"
        "T<sub>0</sub>) with a single positive G. It cannot explain the "
        "unequal slopes: the <i>same</i> G appears in the denominator of both "
        "dT<sub>h</sub>/dd and dT<sub>c</sub>/dd, so it sets how steep the "
        "two branches are &mdash; a larger G flattens both &mdash; but "
        "cancels exactly from their ratio. A symmetric term cannot produce an "
        "asymmetric result. The asymmetry survives only in the numerators, "
        "where Q<sub>J</sub> is added on the heating branch and subtracted on "
        "the cooling one, because Peltier transport reverses with the current "
        "and Joule heating does not.", body))

    # ---------------------------------------------------------------- 7
    A(Paragraph("7. Conclusion", h))
    A(Paragraph(
        "Steady-state temperature is linear in signed PWM on both branches "
        "(R<super>2</super> = 1.0000 heating, 0.9989 cooling), which is what "
        "the PWM averages predict: Peltier transport follows &lt;I&gt; = DI "
        "and Joule heating follows &lt;I<super>2</super>&gt; = "
        "DI<super>2</super>, so both scale with duty and the susceptibility "
        "stays constant. Had &lt;I<super>2</super>&gt; gone as "
        "D<super>2</super>, the branches would curve. The two slopes differ "
        "by a factor r = 2.771 because reversing the current reverses Peltier "
        "pumping but not Joule heating: the two add when heating and oppose "
        "when cooling, giving Q<sub>J</sub>/Q<sub>P</sub> = (r&minus;1)/(r+1) "
        "= 0.470. Passive conduction enters both branches through the same G "
        "and cancels from the ratio, so it sets how steep the lines are but "
        "cannot make them unequal. The Laird maximum-current figures predict "
        "r = 2.556, within 8% despite describing a steady-DC, zero-&Delta;T "
        "condition our apparatus never reaches.", body))

    A(Spacer(1, 5))
    A(Paragraph(
        "Code and data: <font face='Courier' size='7'>"
        "arduino/module_04/tec_open_loop_safety</font> (safety interlock), "
        "<font face='Courier' size='7'>python/tec_control_gui.py</font>, "
        "<font face='Courier' size='7'>python/plot_open_loop_calibration.py"
        "</font>, <font face='Courier' size='7'>python/laird_comparison.py"
        "</font>; raw traces and the steady-state table in "
        "<font face='Courier' size='7'>data/module_04/</font>.", cap))

    doc.build(s)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    if not os.path.exists(FIG):
        raise SystemExit(f"{FIG} not found. Run the plot script first.")
    build()
