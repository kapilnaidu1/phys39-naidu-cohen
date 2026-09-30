#!/usr/bin/env python3
"""
Phys 39 Module 4, Part 5.3 and 5.4. Naidu / Cohen

Laird CP14-127-045 maximum-current prediction, and the comparison with our
measured slope ratio.

FILL IN THE FOUR DATA-SHEET VALUES BELOW. Read them off the PDF yourself; the
assignment forbids getting them from an AI before you have found them. Once
they are in, run:

    python3 python/laird_comparison.py

WHAT IT DOES

    At the data-sheet maximum-current condition the passive conduction term
    vanishes, because that condition is specified at dT = 0. The symmetric TEC
    model puts half the total Joule heat on each face, so

        Qj_max = 0.5 * I_max^2 * R_M

    Cooling at the object face is Peltier pumping minus that Joule heat,

        Qc_max = Qp_max - Qj_max     =>     Qp_max = Qc_max + Qj_max

    and the data-sheet prediction for our ratio is

        r_Laird,max = (Qp_max + Qj_max) / (Qp_max - Qj_max)

    which is the same algebraic form as the measured r, so the two are
    directly comparable even though they come from different conditions.
"""

# =====================================================================
# DATA-SHEET VALUES   <-- fill these in from the PDF
# =====================================================================

R_M = 1.50        # ohm,  module resistance
I_MAX = 8.6       # A,    current giving maximum dT
QC_MAX = 71.3     # W,    max cold-side pumping, at dT = 0
DT_MAX = 70.5     # K,    max temperature difference, at Qc = 0

HOT_SIDE_C = 27.0     # the column these were read from
V_MAX = 13.9      # V,    voltage at dT_max (not required, used as a cross-check)
SOURCE = ("Laird CP14-127-045-L2-W4.5, MFG 58910-501, SPECIFICATIONS table,\n          Hot Side Temperature = 27.0 C column")

# =====================================================================
# OUR MEASUREMENT, Module 4 Part 3, 30 September 2026
# =====================================================================

M_H = 0.50127     # C per PWM count, heating branch,  u = 0 to +50
M_C = 0.18091     # C per PWM count, cooling branch,  u = -65 to 0


def main():
    if None in (R_M, I_MAX, QC_MAX, DT_MAX):
        print(__doc__)
        print("Data-sheet values not filled in yet. Edit the four constants "
              "at the top of this file.")
        return

    r_meas = M_H / M_C
    qj_qp_meas = (r_meas - 1.0) / (r_meas + 1.0)

    print(f"SOURCE: {SOURCE}\n")
    print("DATA-SHEET VALUES")
    print(f"  R_M      = {R_M:8.4f} ohm")
    print(f"  I_max    = {I_MAX:8.3f} A")
    print(f"  Qc_max   = {QC_MAX:8.3f} W      (at dT = 0)")
    print(f"  dT_max   = {DT_MAX:8.2f} K      (at Qc = 0)")

    # Keep the units visible at every line; the rubric asks for a
    # "dimensionally clear calculation".
    qj_max = 0.5 * I_MAX**2 * R_M          # A^2 * ohm = W
    qp_max = QC_MAX + qj_max               # W + W = W

    print("\nOBJECT-FACE HEAT RATES AT THE DATA-SHEET MAXIMUM CURRENT")
    print(f"  Qj_max = 0.5 * I_max^2 * R_M")
    print(f"         = 0.5 * ({I_MAX:.3f} A)^2 * {R_M:.4f} ohm")
    print(f"         = {qj_max:.3f} W")
    print(f"  Qp_max = Qc_max + Qj_max")
    print(f"         = {QC_MAX:.3f} W + {qj_max:.3f} W")
    print(f"         = {qp_max:.3f} W")

    denom = qp_max - qj_max
    if denom <= 0:
        print("\n  Qp_max - Qj_max is not positive. Check the values: this "
              "would mean Joule heating exceeds Peltier pumping, so the "
              "module could not cool at all.")
        return

    r_laird = (qp_max + qj_max) / denom
    qj_qp_laird = qj_max / qp_max

    print("\nDATA-SHEET PREDICTION")
    print(f"  r_Laird,max = (Qp_max + Qj_max) / (Qp_max - Qj_max)")
    print(f"              = ({qp_max:.3f} + {qj_max:.3f}) / "
          f"({qp_max:.3f} - {qj_max:.3f})")
    print(f"              = {r_laird:.3f}")
    print(f"  Qj/Qp at that condition = {qj_qp_laird:.3f}")

    print("\nCOMPARISON")
    print(f"  measured    r = {r_meas:.3f}   (m_h/m_c = {M_H:.5f}/{M_C:.5f})")
    print(f"  data sheet  r = {r_laird:.3f}")
    print(f"  ratio         = {r_meas / r_laird:.3f}")
    print(f"  measured    Qj/Qp = {qj_qp_meas:.3f}")
    print(f"  data sheet  Qj/Qp = {qj_qp_laird:.3f}")

    print("\n  These are NOT expected to agree. The data-sheet numbers are a")
    print("  maximum-current, dT = 0 condition. Our bench at D = 1 is neither:")
    print("  the actual current is set by supply voltage and current limit,")
    print("  H-bridge drop, wiring and TEC resistance, and the apparatus runs")
    print("  at finite dT where conduction matters. See section 5.5 of the")
    print("  module note for the full list.")

    if qj_qp_meas > qj_qp_laird:
        print("\n  Our Qj/Qp is the LARGER, meaning Joule heating is a bigger")
        print("  share of the object-face budget on our bench than at the")
        print("  data-sheet condition. Consistent with running below I_max,")
        print("  where pumping falls off linearly but the Joule share does")
        print("  not fall as fast relative to it.")
    else:
        print("\n  Our Qj/Qp is the SMALLER of the two. Worth saying why in")
        print("  the write-up rather than leaving it unremarked.")


if __name__ == "__main__":
    main()
