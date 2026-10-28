#!/usr/bin/env python3
"""Compare TEC-base and rod-base normalizations without changing the fin fit."""

import csv
import math
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "data/module_07_sammy/sammy_rod_run_20261028_114042.csv"
OUT = ROOT / "data/module_07_sammy/sammy_reference_ratio_addendum_20261028.md"
FIG = ROOT / "docs/figures/module_07_sammy/sammy_reference_ratio_20261028.png"
ROD_COLS = ["T_T1_C", "T_T2_C", "T_T3_C", "T_T4_C", "T_T5_C"]
T_END_AFTER_STOP = 3012.67
FINAL_WINDOW_S = 600.0
ROOM_WINDOW_S = 30.0
TEC_TO_T1_MM = 25.4  # approximately one inch, supplied by the user


def mean(rows, key):
    return statistics.mean(float(row[key]) for row in rows)


def main():
    with RUN.open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    baseline = [row for row in rows if float(row["time_s"]) <= ROOM_WINDOW_S]
    room_by_rod_sensor = [mean(baseline, key) for key in ROD_COLS]
    t_room = statistics.mean(room_by_rod_sensor)
    steady = [row for row in rows
              if T_END_AFTER_STOP - FINAL_WINDOW_S <= float(row["time_s"]) <= T_END_AFTER_STOP
              and row["control_on"] == "1"]

    temperatures = {key: mean(steady, key)
                    for key in ["temperature_C", "T_T1_C", "T_T5_C"]}
    theta_tec = temperatures["temperature_C"] - t_room
    theta_t1 = temperatures["T_T1_C"] - t_room
    theta_t5 = temperatures["T_T5_C"] - t_room
    target = 1.0 / math.e
    ratio_rod = theta_t5 / theta_t1
    ratio_tec = theta_t5 / theta_tec
    tec_rel_difference_pct = 100.0 * (ratio_tec / target - 1.0)
    rod_rel_difference_pct = 100.0 * (ratio_rod / target - 1.0)

    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.5, 5), layout="constrained")
    labels = ["Rod definition\nT5 / T1", "Separate sensor comparison\nT5 / TEC-base"]
    values = [ratio_rod, ratio_tec]
    bars = ax.bar(labels, values, color=["#176B73", "#C47B32"], width=0.55)
    ax.axhline(target, color="#333333", ls="--", lw=1.5,
               label="1/e rod-placement target = %.5f" % target)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, value + 0.008,
                "%.5f" % value, ha="center", va="bottom", fontsize=10)
    ax.set_ylim(0, 0.65)
    ax.set_ylabel("Normalized excess-temperature ratio")
    ax.set_title("The reference sensor changes the ratio")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper right")
    ax.text(0.5, -0.22,
            "TEC-base is insulated and not on the rod; second bar is descriptive, not the fin criterion.",
            transform=ax.transAxes, ha="center", va="top", fontsize=8.5,
            color="#596874")
    fig.savefig(FIG, dpi=170)
    plt.close(fig)

    report = f"""# TEC Reference versus Rod T1: Ratio Addendum

Supplement to [`sammy_stationary_fin_analysis_20261028.md`](sammy_stationary_fin_analysis_20261028.md). The raw CSV and original rod fit are unchanged.

## The distinction

The official rod coordinate starts at T1, the first rod hole: **x = 0 and theta0 = T1 - T_room**. The insulated TEC-base thermistor is about {TEC_TO_T1_MM:.1f} mm (one inch) away, but it measures the TEC assembly, not a point on the aluminum rod. It is not an extra point in the one-dimensional fin profile and must not replace T1 in the official rod placement test.

It is still useful to calculate a separate descriptive ratio from the TEC sensor to T5. This includes the TEC/rod interface and insulation, so it describes the whole actuator-to-sensor path rather than just decay along the rod.

## Data window and worked arithmetic

Use the same final 10-minute control-on window as the rod analysis. Estimate room temperature as the mean of the five rod channels in the first {ROOM_WINDOW_S:.0f} seconds: **T_room = {t_room:.5f} deg C**. The final-window means are:

```text
T_TEC = {temperatures['temperature_C']:.5f} deg C
T1    = {temperatures['T_T1_C']:.5f} deg C
T5    = {temperatures['T_T5_C']:.5f} deg C

theta_TEC = T_TEC - T_room = {temperatures['temperature_C']:.5f} - {t_room:.5f} = {theta_tec:.5f} deg C
theta_T1  = T1 - T_room    = {temperatures['T_T1_C']:.5f} - {t_room:.5f} = {theta_t1:.5f} deg C
theta_T5  = T5 - T_room    = {temperatures['T_T5_C']:.5f} - {t_room:.5f} = {theta_t5:.5f} deg C
```

**Official rod ratio**

```text
theta_T5 / theta_T1 = {theta_t5:.5f} / {theta_t1:.5f} = {ratio_rod:.5f}
1/e = {target:.5f}
relative difference = 100 * (ratio / (1/e) - 1) = {rod_rel_difference_pct:+.2f}%
```

This does **not** meet the rod criterion: T5 retains {ratio_rod:.3f} of T1's excess temperature, versus a target no greater than {target:.3f}.

**Separate TEC-to-T5 comparison**

```text
theta_T5 / theta_TEC = {theta_t5:.5f} / {theta_tec:.5f} = {ratio_tec:.5f}
1/e = {target:.5f}
relative difference = {tec_rel_difference_pct:+.3f}%
```

This number is remarkably close to 1/e, but it does **not** show that the rod placement meets the target. Its denominator is a sensor in the insulated TEC assembly, not the rod-base boundary at T1. The two ratios answer different physical questions.

## Effect on the fitted model

No additional fin fit is made with TEC as a sixth point. That would violate the model's domain: the finite/semi-infinite formulas describe points along a uniform rod with T1 as the x=0 boundary. The TEC sensor is separated by an interface, is insulated, and can have a distinct contact lag. Including it as a fictitious x = -{TEC_TO_T1_MM:.1f} mm rod point would bias the fitted decay coefficient rather than improve it.

The rod-only finite fit remains **m = 4.716 1/m** from the prior analysis, provisional because actual measured positions, rod diameter, resistor values, and a controlled common-bath check are not yet in the sensor map. This addendum changes the interpretation only; it does not change the original rod fit.

![Rod and TEC reference ratios](../../docs/figures/module_07_sammy/sammy_reference_ratio_20261028.png)

Source: [`sammy_rod_run_20261028_114042.csv`](sammy_rod_run_20261028_114042.csv).
"""
    OUT.write_text(report)
    print("Wrote", OUT)
    print("TEC ratio %.5f vs rod ratio %.5f; target %.5f" %
          (ratio_tec, ratio_rod, target))


if __name__ == "__main__":
    main()