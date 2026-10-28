#!/usr/bin/env python3
"""Create a separate TEC-base-sensor addendum for Sammy's Module 7 run.

Run from the repository root:
    python3 python/analysis/sammy_module7_tec_sensor_addendum.py

The TEC-base sensor is reported separately from the rod profile. It is not
treated as a rod sensor at x < 0 and is not included in the fin-model fit.
"""

import csv
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "data/module_07_sammy/sammy_rod_run_20261028_114042.csv"
ROD_COLS = ["T_T1_C", "T_T2_C", "T_T3_C", "T_T4_C", "T_T5_C"]
ALL_COLS = ["temperature_C"] + ROD_COLS
OUT_MD = ROOT / "data/module_07_sammy/sammy_tec_sensor_addendum_20261028.md"
OUT_FIG = ROOT / "docs/figures/module_07_sammy/sammy_tec_vs_rod_base_20261028.png"


def mean(rows, column):
    return statistics.mean(float(row[column]) for row in rows)


def summarize(rows, column):
    values = [float(row[column]) for row in rows]
    times = [float(row["time_s"]) for row in rows]
    return {
        "n": len(values),
        "start": times[0],
        "end": times[-1],
        "mean": statistics.mean(values),
        "sd": statistics.stdev(values),
        "minimum": min(values),
        "maximum": max(values),
        "first": values[0],
        "last": values[-1],
        "drift": values[-1] - values[0],
    }


def main():
    with RUN.open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    baseline = [row for row in rows if float(row["time_s"]) <= 30.0]
    room_channels = [mean(baseline, column) for column in ROD_COLS]
    room = statistics.mean(room_channels)
    start = min(float(row["time_s"]) for row in rows
                if row["control_on"] == "1"
                and row["setpoint_C"] == "45.00")
    end = max(float(row["time_s"]) for row in rows
              if row["control_on"] == "1"
              and row["setpoint_C"] == "45.00")

    windows = {
        "last40": [row for row in rows if end - 2400 <= float(row["time_s"]) <= end
                   and row["control_on"] == "1"],
        "last10": [row for row in rows if end - 600 <= float(row["time_s"]) <= end
                   and row["control_on"] == "1"],
        "last5": [row for row in rows if end - 300 <= float(row["time_s"]) <= end
                  and row["control_on"] == "1"],
    }
    stats = {window: {column: summarize(data, column)
                      for column in ["temperature_C", "T_T1_C"]}
             for window, data in windows.items()}

    # Plot full time history with a zoomed final steady-state interval.
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True,
                             layout="constrained")
    time_min = [float(row["time_s"])/60 for row in rows]
    tec = [float(row["temperature_C"]) for row in rows]
    t1 = [float(row["T_T1_C"]) for row in rows]
    setpoint = [float(row["setpoint_C"]) for row in rows]
    axes[0].plot(time_min, tec, color="#C74343", lw=1.2,
                 label="TEC-base sensor (A0; insulated)")
    axes[0].plot(time_min, t1, color="#176B73", lw=1.2,
                 label="Rod T1 (A1; x=0 boundary)")
    axes[0].plot(time_min, setpoint, color="#777777", ls="--", lw=1,
                 label="TEC setpoint")
    axes[0].axvspan((end-600)/60, end/60, color="#a6cee3", alpha=.22,
                    label="final 10 min")
    axes[0].set_ylabel("Temperature (deg C)")
    axes[0].set_title("TEC-base sensor and rod-base T1 are distinct measurements")
    axes[0].grid(alpha=.25)
    axes[0].legend(fontsize=8, ncol=2)

    axes[1].plot(time_min, [v-room for v in tec], color="#C74343", lw=1.2,
                 label="TEC-base excess above estimated room")
    axes[1].plot(time_min, [v-room for v in t1], color="#176B73", lw=1.2,
                 label="T1 excess above estimated room")
    axes[1].axhline(0, color="#777777", lw=.8)
    axes[1].axvspan((end-600)/60, end/60, color="#a6cee3", alpha=.22)
    axes[1].set_xlabel("Elapsed time (min)")
    axes[1].set_ylabel("Excess temperature (deg C)")
    axes[1].grid(alpha=.25)
    axes[1].legend(fontsize=8)
    OUT_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_FIG, dpi=170)
    plt.close(fig)

    final_tec = stats["last10"]["temperature_C"]["mean"]
    final_t1 = stats["last10"]["T_T1_C"]["mean"]
    theta_tec = final_tec - room
    theta_t1 = final_t1 - room
    difference = final_tec - final_t1

    lines = [
        "# TEC-Base Thermistor Addendum — Module 7 Run, 28 October 2026\n\n",
        "This is a new addendum to the rod analysis. It does not change the raw CSV, "
        "sensor map, or rod-only fit.\n\n",
        "## Important model distinction\n\n",
        "The TEC-base thermistor is fully insulated inside/on the TEC assembly and, "
        "as reported, is about 1 inch from rod T1. It measures the actuator assembly, "
        "not a point on the aluminum rod. The course defines the rod-analysis origin "
        "at T1 (the first rod hole, x=0); T1 supplies the rod boundary condition. "
        "Therefore the TEC-base channel must not be relabeled as rod theta0 or added "
        "to the finite/semi-infinite rod fit at x=-25.4 mm. Its insulation and separate "
        "thermal contact can also give it a response different from the rod.\n\n",
        f"Approximate physical separation from TEC sensor to T1 supplied by the user: "
        f"about 25.4 mm. This is not a measured rod coordinate.\n\n",
        "## Room reference and final windows\n\n",
        f"For this analysis, room reference is estimated from the mean of the five rod "
        f"channels during the first 30 s: T_room = {room:.5f} deg C. This is a startup "
        f"baseline, not a controlled common-bath calibration.\n\n",
        "| Window | TEC mean (deg C) | TEC SD | T1 mean (deg C) | T1 SD | TEC − T1 (deg C) | "
        "TEC excess over room (deg C) | T1 excess over room (deg C) |\n",
        "|---|---:|---:|---:|---:|---:|---:|---:|\n",
    ]
    for label in ["last40", "last10", "last5"]:
        tec_stats = stats[label]["temperature_C"]
        t1_stats = stats[label]["T_T1_C"]
        tec_mean = tec_stats["mean"]
        t1_mean = t1_stats["mean"]
        lines.append(
            f"| {label} ({tec_stats['n']} points) | {tec_mean:.4f} | "
            f"{tec_stats['sd']:.4f} | {t1_mean:.4f} | {t1_stats['sd']:.4f} | "
            f"{tec_mean-t1_mean:.4f} | {tec_mean-room:.4f} | "
            f"{t1_mean-room:.4f} |\n"
        )
    lines.extend([
        "\n## Fully worked final-10-minute calculation\n\n",
        "The logger reports 537 points in the final 300 s and 1,073 points in the "
        "final 600 s. Use the final 10-minute averages here.\n\n",
        "```text\n",
        f"T_TEC,mean = {final_tec:.5f} deg C\n",
        f"T_T1,mean  = {final_t1:.5f} deg C\n",
        f"T_room,estimated from initial rod baseline = {room:.5f} deg C\n\n",
        f"theta_TEC = T_TEC,mean − T_room = {final_tec:.5f} − {room:.5f} "
        f"= {theta_tec:.5f} deg C\n",
        f"theta_T1  = T_T1,mean − T_room  = {final_t1:.5f} − {room:.5f} "
        f"= {theta_t1:.5f} deg C\n",
        f"T_TEC,mean − T_T1,mean = {final_tec:.5f} − {final_t1:.5f} "
        f"= {difference:.5f} deg C\n",
        "```\n\n",
        "So the insulated TEC sensor reads about "
        f"{difference:.2f} deg C warmer than rod T1 during this final window. "
        "That difference is useful actuator/boundary context, but it does not mean "
        "the rod profile starts at the TEC sensor. In the rod fit, theta0 means "
        "theta(x=0)=T1−T_room.\n\n",
        "![TEC-base sensor versus rod T1 across the run](../../docs/figures/module_07_sammy/"
        "sammy_tec_vs_rod_base_20261028.png)\n\n",
        "## Interpretation and caveats\n\n",
        "- The TEC-base sensor follows the controlled actuator temperature; T1 measures "
        "the first rod hole. Heat must conduct from the TEC/base into the rod, so they "
        "can differ substantially.\n",
        "- The insulated TEC probe is not part of the one-dimensional rod and is not an "
        "extra spatial sample. Do not fit it as if it were a rod point one inch before T1.\n",
        "- T1 remains the base boundary condition for the rod model. The initial room "
        "reference is from rod channels; the initial six-channel spread was about 0.96 C, "
        "so the common-bath calibration check is not established by this run.\n",
        "- Tape mounting and insulation can add thermal lag. Preserve the raw trace; do not "
        "filter the logged measurements to conceal it.\n",
        "\nSource: [`sammy_rod_run_20261028_114042.csv`](sammy_rod_run_20261028_114042.csv).\n",
    ])
    OUT_MD.write_text("".join(lines))
    print("Wrote", OUT_MD)


if __name__ == "__main__":
    main()