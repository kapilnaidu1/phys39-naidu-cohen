#!/usr/bin/env python3
"""
Phys 39 A3. Naidu / Cohen

Print-size versions of the Module 6 figures for the A3 PDF. Same data, same
functions and same axes as the repository figures; only the size and type
change so that each figure is readable at the width of a letter page.

    python3 python/plot_a3_figures.py      (run from the repository root)

INPUT   data/module_06/pi_run_20261013_094149.csv  (Runs 1, 2, 4, 5)
        data/module_06/pi_run_20261014_111720.csv  (Runs 3, 6)
        through python/plot_goldilocks_experiment.py and
        python/simulate_goldilocks_two_lump.py

OUTPUT  docs/figures/module_06/a3/a3_experimental.png
        docs/figures/module_06/a3/a3_simulated.png
        docs/figures/module_06/a3/a3_high_gain_metrics.png
        docs/figures/module_06/a3/a3_sim_vs_experiment.png
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


exp = _load("goldilocks_experiment", "plot_goldilocks_experiment.py")
two = _load("goldilocks_two_lump", "simulate_goldilocks_two_lump.py")

OUT_DIR = "docs/figures/module_06/a3"
FS = 7.6
SIZE = (7.0, 6.2)
DPI = 300


def main():
    exp.house_style(FS)
    os.makedirs(OUT_DIR, exist_ok=True)
    cuts, metrics = exp.collect()
    six = {k: cuts[k] for k in exp.RUNS}
    base = two.shared_config()
    sims = {k: two.simulate_run(base, exp.RUNS[k], cuts[k]) for k in exp.RUNS}

    exp.reference_figure(
        six, os.path.join(OUT_DIR, "a3_experimental.png"), figsize=SIZE, fs=FS,
        dpi=DPI,
        note="Measured. Runs 1, 2, 4, 5 on 13 October; Runs 3 and 6 on 14 "
             "October. Setpoints 30, 35, 30 °C; PWM limit 255; anti-windup on.\n"
             "Control-on rows only; readings every 0.56 s, each the mean of "
             "1000 ADC samples. Darker = higher gain.")
    exp.reference_figure(
        sims, os.path.join(OUT_DIR, "a3_simulated.png"), figsize=SIZE, fs=FS,
        dpi=DPI, temp_label="simulated $T_m$ (°C)",
        note="Two-lump model, one shared set: χc 0.181, χh 0.501 °C/PWM, "
             "τ 62.9 s, V 12.0 V, R 1.50 Ω, T_amb 21.54 °C, G 3.5 W/K, "
             "$C_T/C$ 0.35.\nEach run replays its experiment's start, "
             "setpoints and timing. Course simulator code, Δt 0.05 s.")
    exp.high_gain_figure(cuts, metrics,
                         os.path.join(OUT_DIR, "a3_high_gain_metrics.png"),
                         figsize=(7.0, 4.2), fs=FS, dpi=DPI, note=False,
                         text=False)
    two.comparison_figure(six, sims,
                          os.path.join(OUT_DIR, "a3_sim_vs_experiment.png"),
                          figsize=(7.0, 4.6), fs=FS, dpi=DPI)
    print(f"Figures written to {OUT_DIR}")


if __name__ == "__main__":
    main()
