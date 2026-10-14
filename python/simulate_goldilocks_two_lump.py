#!/usr/bin/env python3
"""
Phys 39 Module 6 Part II. Naidu / Cohen

The six two-lump simulation Goldilocks plots for A3 Question 3, each one the
simulated counterpart of an experimental run from 13 October.

    python3 python/simulate_goldilocks_two_lump.py   (run from the repository root)

MODEL

    The course simulator's own code, python/Lab_6_7_modeling_tec.py, imported
    and stepped directly: constants_from_measurements() for C, H, P_u,c and r,
    advance_model() for the Euler update and the controller (including its
    conditional-integration anti-windup), two_lump_p_damping_ratio() and
    two_lump_pi_critical_integral_gain() for the displayed stability numbers.
    Nothing in the physics or the controller is reimplemented here.

    It is run outside the GUI only because the GUI rounds K_i to steps of
    0.02, so Run 4's K_i = 0.05 cannot be entered there.

ONE SHARED PARAMETER SET, the same for all six

    measured inputs   chi_c 0.181, chi_h 0.501 C/PWM, tau 62.9 s,
                      V_TEC 12.0 V (instructor's value), R_M 1.50 ohm,
                      T_amb 21.54 C
    derived by the simulator   C 74.0 J/K, H 1.176 W/K, P_u,c 0.2129 W/PWM,
                               r 2.77
    internal structure  G 3.5 W/K, C_T/C 0.35, chosen once so that the
                        K_p = 64 step overshoots like Run 3 (see the Part II
                        note), then locked
    PWM limit 255, anti-windup on, dt 0.05 s

MATCHED CONDITIONS

    Each simulation starts at the temperature the plate had when control was
    switched on in that run, holds 30 C for as long as the run did, steps to
    35 C, then back to 30 C, with the same stage lengths as the experiment.
    Only the controller mode, K_p and K_i change between runs.

    Two differences from the bench remain and are stated on every figure:
    the model updates its command every 0.05 s and does not round it, where
    the real controller updated every 0.56 s in whole counts; and both lumps
    start at the same temperature.

OUTPUT  docs/figures/module_06/goldilocks_sim/run1_sim.png ... run6_sim.png
        docs/figures/module_06/goldilocks_sim/sim_vs_experiment.png
        data/module_06/goldilocks_sim_metrics.csv
"""

import csv
import importlib.util
import os
import sys
from dataclasses import replace

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sim = _load("lab67", "Lab_6_7_modeling_tec.py")
exp = _load("goldilocks_experiment", "plot_goldilocks_experiment.py")

FIG_DIR = "docs/figures/module_06/goldilocks_sim"
METRICS_CSV = "data/module_06/goldilocks_sim_metrics.csv"

CHI_C, CHI_H, TAU = 0.181, 0.501, 62.9
V_TEC, R_M = 12.0, 1.50
T_AMB = 21.54
G = 3.5
CT_FRACTION = 0.35
DT = 0.05

SIM_COLOR = "#1F4E79"
EXP_COLOR = "#9A9A9A"


def shared_config():
    d = sim.constants_from_measurements(CHI_C, CHI_H, TAU, V_TEC, R_M)
    return replace(
        sim.ModelConfig(),
        ambient_c=T_AMB,
        measured_cooling_chi_c_per_pwm=CHI_C,
        measured_heating_chi_c_per_pwm=CHI_H,
        measured_tau_s=TAU,
        tec_voltage_v=V_TEC,
        tec_resistance_ohm=R_M,
        total_capacitance_j_per_c=d.total_capacitance_j_per_c,
        heat_loss_w_per_c=d.heat_loss_w_per_c,
        tec_power_w_per_pwm=d.cooling_power_w_per_pwm,
        heating_to_cooling_ratio=d.heating_to_cooling_ratio,
        coupling_w_per_c=G,
        tec_capacitance_fraction=CT_FRACTION,
        pwm_limit=float(exp.PWM_LIMIT),
        dt_s=DT,
        anti_windup=True,
    )


def simulate_run(base, run, measured):
    """Simulate one run under the measured run's conditions."""
    mode, kp, ki, _, _ = exp.RUNS[run]
    controller = "p" if mode == "P" else "pi"
    t = measured["time_s"]
    stages = [(30.0, t[measured["i_up"]] - t[0]),
              (35.0, t[measured["i_down"]] - t[measured["i_up"]]),
              (30.0, t[-1] - t[measured["i_down"]] + 0.56)]
    T0 = float(measured["temperature_C"][0])
    cfg = replace(base, kp_pwm_per_c=kp, ki_pwm_per_c_s=ki, initial_c=T0)
    sim.validate_config(cfg)
    state = sim.ModelState(0.0, T0, T0, 0.0)

    rows, end = [], 0.0
    for setpoint, length in stages:
        end += length
        stage_cfg = replace(cfg, setpoint_c=setpoint)
        while state.time_s < end - 1e-9:
            r = sim.advance_model(state, stage_cfg, "two_lump", controller)
            rows.append((r.time_s, r.measured_temperature_c, setpoint,
                         r.applied_pwm, r.p_pwm, r.i_pwm, int(r.saturated)))
    a = np.array(rows)
    out = {"time_s": a[:, 0], "temperature_C": a[:, 1], "setpoint_C": a[:, 2],
           "pwm": a[:, 3], "u_P": a[:, 4], "u_I": a[:, 5],
           "saturated": a[:, 6].astype(int)}
    sp = out["setpoint_C"]
    out["i_up"] = int(np.flatnonzero(np.isclose(sp, 35.0))[0])
    out["i_down"] = out["i_up"] + int(np.flatnonzero(np.isclose(sp[out["i_up"]:], 30.0))[0])

    heating_cfg = replace(cfg, setpoint_c=35.0)
    if mode == "P":
        out["zeta"] = sim.two_lump_p_damping_ratio(heating_cfg)
    else:
        out["ki_crit"] = sim.two_lump_pi_critical_integral_gain(heating_cfg)
        out["rho"] = ki / out["ki_crit"]
    return out


def kp_crit(cfg):
    CT, Cm = cfg.tec_capacitance_j_per_c, cfg.measured_capacitance_j_per_c
    H, Puh = cfg.heat_loss_w_per_c, sim.heating_tec_coefficient(cfg)
    a = CT * (cfg.coupling_w_per_c + H) + Cm * cfg.coupling_w_per_c
    return (a ** 2 / (4 * CT * Cm * cfg.coupling_w_per_c) - H) / Puh


def stability_text(run, s):
    mode, kp, ki, _, _ = exp.RUNS[run]
    if mode == "P":
        return f"$\\zeta_{{2L,P}}$ = {s['zeta']:.2f}"
    return (f"$K_{{i,crit}}$ = {s['ki_crit']:.2f} PWM/(°C s),  "
            f"$\\rho_I$ = {s['rho']:.3f}")


def model_note(wrap=False):
    gap = "\n" if wrap else " "
    return (f"Two-lump model, one shared set: χc 0.181, χh 0.501 "
            f"°C/PWM, τ 62.9 s, V 12.0 V, R 1.50 Ω, T_amb "
            f"{T_AMB} °C (C 74.0 J/K, H 1.18 W/K),{gap}G {G} W/K, "
            f"C_T/C {CT_FRACTION}. Course simulator code, Δt {DT} s.")


def run_figure(run, s, up, down, path):
    t = s["time_s"] - s["time_s"][s["i_up"]]
    keep = t >= exp.X_LIM[0]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.6, 5.4), sharex=True,
                                 gridspec_kw={"height_ratios": [2.0, 1.0],
                                              "hspace": 0.12})
    fig.patch.set_facecolor("white")
    for ax in (a1, a2):
        exp.style(ax)

    a1.step(t[keep], s["setpoint_C"][keep], where="post", color=exp.SET,
            linewidth=1.2, linestyle="--", label="Setpoint", zorder=2)
    a1.plot(t[keep], s["temperature_C"][keep], color=SIM_COLOR, linewidth=1.5,
            label="Simulated $T_m$", zorder=3)
    a1.set_xlim(*exp.X_LIM)
    a1.set_ylim(*exp.T_LIM)
    a1.set_ylabel("Temperature  (°C)", color=exp.TEXT)
    a1.set_title(exp.title_for(run).replace(f"Run {run}:",
                                            f"Run {run}, simulated:"),
                 fontsize=11.5, color=exp.TEXT, pad=24)
    a1.text(0.5, 1.025,
            f"{stability_text(run, s)},   end of each stage "
            f"{up['T_initial_C']:.2f} → {up['T_final_C']:.2f} → "
            f"{down['T_final_C']:.2f} °C", transform=a1.transAxes,
            fontsize=9.3, color=SIM_COLOR, ha="center", va="bottom")
    a1.tick_params(axis="x", which="both", bottom=True, labelbottom=False,
                   length=3.5, color="#868686")
    leg = a1.legend(loc="lower right", frameon=True, fontsize=9)
    leg.get_frame().set_edgecolor("#BFBFBF")
    leg.get_frame().set_linewidth(0.8)

    u = s["pwm"][keep]
    a2.plot(t[keep], u, color="#BBBBBB", linewidth=0.8, zorder=2)
    a2.plot(t[keep], np.where(u > 0, u, np.nan), color=exp.HEAT, linewidth=1.3)
    a2.plot(t[keep], np.where(u < 0, u, np.nan), color=exp.COOL, linewidth=1.3)
    a2.axhline(0, color="#868686", linewidth=0.8, zorder=1)
    lo, hi = u.min(), u.max()
    if max(abs(lo), abs(hi)) > 0.8 * exp.PWM_LIMIT:
        for sign in (1, -1):
            a2.axhline(sign * exp.PWM_LIMIT, color=exp.HEAT if sign > 0 else exp.COOL,
                       linewidth=0.9, linestyle=":", zorder=1)
    pad = 0.15 * max(hi - lo, 10)
    a2.set_ylim(min(lo, 0) - pad, max(hi, 0) + pad)
    a2.set_ylabel("Signed PWM\n(+ heat, − cool)", color=exp.TEXT)
    a2.set_xlabel("Time from the 30 → 35 °C setpoint step  (s)",
                  color=exp.TEXT)

    fig.text(0.01, 0.01,
             model_note(wrap=True) + " Same start temperature, setpoints "
             f"and stage lengths as experimental run {run}.\nPWM limit 255, "
             "anti-windup on. Stage values are means of its last 30 s. The "
             "model updates its command every 0.05 s without rounding;\nthe "
             "bench controller updated every 0.56 s in whole counts.",
             fontsize=7.4, color="#595959", va="bottom")
    fig.subplots_adjust(left=0.1, right=0.985, top=0.885, bottom=0.22)
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)


def comparison_figure(sims, measured, path):
    fig, axes = plt.subplots(2, 3, figsize=(12.0, 6.4), sharex=True,
                             sharey=True, gridspec_kw={"hspace": 0.3,
                                                       "wspace": 0.08})
    fig.patch.set_facecolor("white")
    for k, run in enumerate(exp.RUNS):
        ax = axes[k // 3][k % 3]
        exp.style(ax)
        m, s = measured[run], sims[run]
        tm = m["time_s"] - m["time_s"][m["i_up"]]
        ts = s["time_s"] - s["time_s"][s["i_up"]]
        ax.step(ts, s["setpoint_C"], where="post", color=exp.SET,
                linewidth=1.0, linestyle="--")
        ax.plot(tm, m["temperature_C"], color=EXP_COLOR, linewidth=2.2,
                label="Measured")
        ax.plot(ts, s["temperature_C"], color=SIM_COLOR, linewidth=1.2,
                label="Simulated $T_m$")
        ax.set_xlim(*exp.X_LIM)
        ax.set_ylim(*exp.T_LIM)
        mode, kp, ki, _, _ = exp.RUNS[run]
        gains = f"P, $K_p$ {kp:g}" if mode == "P" else f"PI, $K_i$ {ki:g}"
        ax.set_title(f"Run {run} ({gains}): {stability_text(run, s)}",
                     fontsize=9.6, color=exp.TEXT, pad=5)
        if k % 3 == 0:
            ax.set_ylabel("Temperature  (°C)", color=exp.TEXT)
        if k // 3 == 1:
            ax.set_xlabel("Time from the 30 → 35 °C step  (s)",
                          color=exp.TEXT)
        if k == 0:
            leg = ax.legend(loc="lower right", frameon=True, fontsize=8.6)
            leg.get_frame().set_edgecolor("#BFBFBF")
    fig.suptitle("Six experiments against one two-lump model",
                 fontsize=13, color=exp.TEXT, y=0.985)
    fig.text(0.01, 0.01, model_note() + "  Kp in PWM/°C, Ki in "
             "PWM/(°C s).", fontsize=7.4, color="#595959", va="bottom")
    fig.subplots_adjust(left=0.065, right=0.99, top=0.89, bottom=0.12)
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)


def main():
    exp.house_style()
    os.makedirs(FIG_DIR, exist_ok=True)
    base = shared_config()
    data = exp.load()
    measured, sims, metrics = {}, {}, []

    for run in exp.RUNS:
        m = exp.cut_run(data, run)
        s = simulate_run(base, run, m)
        measured[run], sims[run] = m, s
        end = len(s["time_s"]) - 1
        up = exp.step_metrics(s, s["i_up"], s["i_down"] - 1, run, "up")
        down = exp.step_metrics(s, s["i_down"], end, run, "down")
        m_up = exp.step_metrics(m, m["i_up"], m["i_down"] - 1, run, "up")
        m_down = exp.step_metrics(m, m["i_down"], len(m["time_s"]) - 1, run, "down")
        for which, sm, mm in (("up", up, m_up), ("down", down, m_down)):
            row = {"run": run, "step": which, "mode": exp.RUNS[run][0],
                   "kp": exp.RUNS[run][1], "ki": exp.RUNS[run][2],
                   "zeta_2L_P": s.get("zeta", np.nan),
                   "ki_crit": s.get("ki_crit", np.nan),
                   "rho_I": s.get("rho", np.nan)}
            for key in ("T_initial_C", "T_final_C", "rise_10_90_s",
                        "overshoot_C", "overshoot_pct", "settling_2pct_s",
                        "ss_error_C", "period_s"):
                row["sim_" + key] = sm[key]
                row["exp_" + key] = mm[key]
            row["sim_saturated_rows"] = sm["saturated_rows"]
            metrics.append(row)
        run_figure(run, s, up, down, os.path.join(FIG_DIR, f"run{run}_sim.png"))

    comparison_figure(sims, measured, os.path.join(FIG_DIR, "sim_vs_experiment.png"))

    with open(METRICS_CSV, "w", newline="") as f:
        w = csv.writer(f)
        keys = list(metrics[0].keys())
        w.writerow(keys)
        for row in metrics:
            w.writerow([f"{row[k]:.3f}" if isinstance(row[k], float) else row[k]
                        for k in keys])

    print(f"Shared set: C {base.total_capacitance_j_per_c:.2f} J/K, "
          f"H {base.heat_loss_w_per_c:.4f} W/K, P_u,c "
          f"{base.tec_power_w_per_pwm:.4f} W/PWM, r "
          f"{base.heating_to_cooling_ratio:.3f}, G {G}, C_T/C {CT_FRACTION}, "
          f"K_p,crit {kp_crit(base):.2f} PWM/C")
    hdr = (f"{'run':>3} {'step':>4} {'stability':>14} | {'final sim/exp':>13} | "
           f"{'rise sim/exp':>13} | {'overshoot % sim/exp':>19} | "
           f"{'settle sim/exp':>15} | {'period sim/exp':>14}")
    print(hdr)
    for r in metrics:
        stab = (f"zeta {r['zeta_2L_P']:.2f}" if r["mode"] == "P"
                else f"rho {r['rho_I']:.3f}")
        print(f"{r['run']:>3} {r['step']:>4} {stab:>14} | "
              f"{r['sim_T_final_C']:6.2f}/{r['exp_T_final_C']:6.2f} | "
              f"{r['sim_rise_10_90_s']:6.1f}/{r['exp_rise_10_90_s']:6.1f} | "
              f"{r['sim_overshoot_pct']:9.1f}/{r['exp_overshoot_pct']:9.1f} | "
              f"{r['sim_settling_2pct_s']:7.1f}/{r['exp_settling_2pct_s']:7.1f} | "
              f"{r['sim_period_s']:6.1f}/{r['exp_period_s']:6.1f}")
    print(f"\nFigures in {FIG_DIR}, metrics in {METRICS_CSV}")


if __name__ == "__main__":
    main()
