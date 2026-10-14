#!/usr/bin/env python3
"""
Phys 39 Module 6 Part II. Naidu / Cohen

The six two-lump simulation Goldilocks plots for A3 Question 3, each one the
simulated counterpart of an experimental run.

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

ONE SHARED PARAMETER SET, the same for every run

    measured inputs   chi_c 0.181, chi_h 0.501 C/PWM, tau 62.9 s,
                      V_TEC 12.0 V (instructor's value), R_M 1.50 ohm,
                      T_amb 21.54 C
    derived by the simulator   C 74.0 J/K, H 1.176 W/K, P_u,c 0.2129 W/PWM,
                               r 2.77
    internal structure  G 3.5 W/K, C_T/C 0.35, chosen once on the 13 October
                        Kp = 64 run, whose ringing decays and so can be
                        matched by this model, then locked. The 14 October
                        Kp = 200 run oscillates without decaying, which no
                        choice of G and C_T/C can reproduce (a two-state loop
                        under P control is always damped), so it could not
                        be used to fix them.
    PWM limit 255, anti-windup on, dt 0.05 s

MATCHED CONDITIONS

    Each simulation replays the run's own sequence: it starts at the plate
    temperature and integral state when control was switched on, and follows
    the same setpoints for the same durations, including the 25 s with
    control off in the 14 October Run 6 (zero command, integral held, as the
    GUI did). Only the controller mode, K_p and K_i change between runs.

    Two differences from the bench remain and are stated on every figure:
    the model updates its command every 0.05 s without rounding, where the
    real controller updated every 0.56 s in whole counts; and both lumps
    start at the same temperature.

OUTPUT  docs/figures/module_06/goldilocks_sim/run*_sim.png
        docs/figures/module_06/goldilocks_sim/overlay_p_and_pi_sim.png
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
        open_loop_pwm=0.0,
    )


def kp_crit(cfg):
    CT, Cm = cfg.tec_capacitance_j_per_c, cfg.measured_capacitance_j_per_c
    H, Puh = cfg.heat_loss_w_per_c, sim.heating_tec_coefficient(cfg)
    a = CT * (cfg.coupling_w_per_c + H) + Cm * cfg.coupling_w_per_c
    return (a ** 2 / (4 * CT * Cm * cfg.coupling_w_per_c) - H) / Puh


def simulate_run(base, spec, measured):
    """Replay one measured run in the model. Returns a cut-like dict."""
    controller = "p" if spec.mode == "P" else "pi"
    T0 = float(measured["temperature_C"][0])
    cfg = replace(base, kp_pwm_per_c=spec.kp, ki_pwm_per_c_s=spec.ki,
                  initial_c=T0)
    sim.validate_config(cfg)
    state = sim.ModelState(0.0, T0, T0, float(measured["q_start"]))

    rows, end = [], 0.0
    for setpoint, on, length in measured["segments"]:
        end += length
        seg_cfg = replace(cfg, setpoint_c=setpoint)
        mode = controller if on else "open_loop"
        while state.time_s < end - 1e-9:
            r = sim.advance_model(state, seg_cfg, "two_lump", mode)
            rows.append((r.time_s, r.measured_temperature_c, setpoint,
                         r.applied_pwm, int(r.saturated), int(on)))
    a = np.array(rows)
    out = {"time_s": a[:, 0], "temperature_C": a[:, 1], "setpoint_C": a[:, 2],
           "pwm_sent": a[:, 3], "saturated": a[:, 4].astype(int),
           "on": a[:, 5].astype(bool), "q_held": np.zeros(len(a), int),
           "spec": spec}
    out["i_up"], out["up_end"], out["i_down"], out["end"] = exp.stage_indices(
        out["time_s"], out["setpoint_C"], out["on"])
    heating_cfg = replace(cfg, setpoint_c=35.0)
    if spec.mode == "P":
        out["zeta"] = sim.two_lump_p_damping_ratio(heating_cfg)
    else:
        out["ki_crit"] = sim.two_lump_pi_critical_integral_gain(heating_cfg)
        out["rho"] = spec.ki / out["ki_crit"]
    return out


def stability_text(spec, s):
    if spec.mode == "P":
        return f"$\\zeta_{{2L,P}}$ = {s['zeta']:.2f}"
    return (f"$K_{{i,crit}}$ = {s['ki_crit']:.2f} PWM/(°C s),  "
            f"$\\rho_I$ = {s['rho']:.3f}")


def model_note(wrap=False):
    gap = "\n" if wrap else " "
    return (f"Two-lump model, one shared set: χc 0.181, χh 0.501 °C/PWM, "
            f"τ 62.9 s, V 12.0 V, R 1.50 Ω, T_amb {T_AMB} °C (C 74.0 J/K, "
            f"H 1.18 W/K),{gap}G {G} W/K, C_T/C {CT_FRACTION}. Course "
            f"simulator code, Δt {DT} s.")


def run_figure(label, s, path):
    spec = s["spec"]
    t = s["time_s"] - s["time_s"][s["i_up"]]
    keep = t >= exp.X_LIM[0]
    T = np.where(s["on"], s["temperature_C"], np.nan)
    u = np.where(s["on"], s["pwm_sent"], np.nan)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.6, 5.4), sharex=True,
                                 gridspec_kw={"height_ratios": [2.0, 1.0],
                                              "hspace": 0.12})
    fig.patch.set_facecolor("white")
    for ax in (a1, a2):
        exp.style(ax)
    a1.step(t[keep], s["setpoint_C"][keep], where="post", color=exp.SET,
            linewidth=1.2, linestyle="--", label="Setpoint", zorder=2)
    a1.plot(t[keep], T[keep], color=SIM_COLOR, linewidth=1.5,
            label="Simulated $T_m$", zorder=3)
    a1.set_xlim(*exp.X_LIM)
    a1.set_ylim(*exp.T_LIM)
    a1.set_ylabel("Temperature  (°C)", color=exp.TEXT)
    a1.set_title(exp.title_for(label, spec).replace("):", "), simulated:"),
                 fontsize=11, color=exp.TEXT, pad=24)
    a1.text(0.5, 1.025, stability_text(spec, s), transform=a1.transAxes,
            fontsize=9.3, color=SIM_COLOR, ha="center", va="bottom")
    a1.tick_params(axis="x", which="both", bottom=True, labelbottom=False,
                   length=3.5, color="#868686")
    leg = a1.legend(loc="lower right", frameon=True, fontsize=9)
    leg.get_frame().set_edgecolor("#BFBFBF")
    a2.plot(t[keep], u[keep], color="#BBBBBB", linewidth=0.8, zorder=2)
    a2.plot(t[keep], np.where(u[keep] > 0, u[keep], np.nan), color=exp.HEAT,
            linewidth=1.3)
    a2.plot(t[keep], np.where(u[keep] < 0, u[keep], np.nan), color=exp.COOL,
            linewidth=1.3)
    a2.axhline(0, color="#868686", linewidth=0.8, zorder=1)
    lo, hi = np.nanmin(u[keep]), np.nanmax(u[keep])
    if max(abs(lo), abs(hi)) > 0.8 * exp.PWM_LIMIT:
        for sign in (1, -1):
            a2.axhline(sign * exp.PWM_LIMIT, color=exp.HEAT if sign > 0 else exp.COOL,
                       linewidth=0.9, linestyle=":", zorder=1)
    pad = 0.15 * max(hi - lo, 10)
    a2.set_ylim(min(lo, 0) - pad, max(hi, 0) + pad)
    a2.set_ylabel("Signed PWM\n(+ heat, − cool)", color=exp.TEXT)
    a2.set_xlabel("Time from the 30 → 35 °C setpoint step  (s)", color=exp.TEXT)
    fig.text(0.01, 0.01,
             model_note(wrap=True) + " Same start, setpoints and stage "
             f"lengths as experimental run {label}.\nPWM limit 255, anti-windup "
             "on. The model updates its command every 0.05 s without rounding; "
             "the bench controller updated every 0.56 s in whole counts.",
             fontsize=7.4, color="#595959", va="bottom")
    fig.subplots_adjust(left=0.1, right=0.985, top=0.885, bottom=0.22)
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)


def comparison_figure(measured, sims, path, figsize=(12.0, 6.6), fs=10.0,
                      dpi=200):
    fig, axes = plt.subplots(2, 3, figsize=figsize, sharex=True, sharey=True,
                             gridspec_kw={"hspace": 0.32, "wspace": 0.07})
    fig.patch.set_facecolor("white")
    for k, run in enumerate(exp.RUNS):
        ax = axes[k // 3][k % 3]
        exp.style(ax)
        ax.grid(True, color="#E4E4E4", linewidth=0.6)
        m, s = measured[run], sims[run]
        tm = m["time_s"] - m["time_s"][m["i_up"]]
        ts = s["time_s"] - s["time_s"][s["i_up"]]
        ax.step(ts, s["setpoint_C"], where="post", color=exp.SET,
                linewidth=0.8, linestyle="--")
        ax.plot(tm, exp.masked(m, "temperature_C"), color=EXP_COLOR,
                linewidth=1.8, label="Measured")
        ax.plot(ts, np.where(s["on"], s["temperature_C"], np.nan),
                color=SIM_COLOR, linewidth=0.8, label="Simulated $T_m$")
        ax.set_xlim(*exp.X_LIM)
        ax.set_ylim(*exp.T_LIM)
        spec = s["spec"]
        g = (f"$K_p$ {spec.kp:g}" if spec.mode == "P" else f"$K_i$ {spec.ki:g}")
        stab = (f"$\\zeta_{{2L,P}}$ = {s['zeta']:.2f}" if spec.mode == "P"
                else f"$\\rho_I$ = {s['rho']:.2f}")
        ax.set_title(f"Run {run} ({spec.mode}, {g}): {stab}", fontsize=fs - 0.4,
                     color=exp.TEXT, pad=3)
        if k % 3 == 0:
            ax.set_ylabel("Temperature (°C)", color=exp.TEXT)
        if k // 3 == 1:
            ax.set_xlabel("Time from the 30 → 35 °C step (s)", color=exp.TEXT)
        if k == 0:
            leg = ax.legend(loc="upper right", frameon=True, fontsize=fs - 1)
            leg.get_frame().set_edgecolor("#BFBFBF")
    fig.text(0.01, 0.008,
             "Grey: measured (Runs 1, 2, 4, 5 on 13 October, 3 and 6 on 14 "
             "October). Blue: two-lump model with one shared parameter set "
             "(G = 3.5 W/K, $C_T/C$ = 0.35,\nmeasured χ and τ). Each "
             "simulation replays its run's start, setpoints and timing. "
             "$K_p$ in PWM/°C, $K_i$ in PWM/(°C s).",
             fontsize=fs - 1.6, color="#595959", va="bottom")
    fig.subplots_adjust(left=0.07, right=0.99, top=0.94, bottom=0.17)
    fig.savefig(path, dpi=dpi, facecolor="white")
    plt.close(fig)


def collect(base):
    measured, sims = {}, {}
    for label, spec in list(exp.RUNS.items()) + list(exp.EARLIER.items()):
        m = exp.cut(spec)
        measured[label] = m
        sims[label] = simulate_run(base, spec, m)
    return measured, sims


def main():
    exp.house_style()
    os.makedirs(FIG_DIR, exist_ok=True)
    base = shared_config()
    measured, sims = collect(base)

    metrics = []
    for label in measured:
        s, m = sims[label], measured[label]
        s_up, s_down = exp.run_metrics(s, label)
        m_up, m_down = exp.run_metrics(m, label)
        for which, sm, mm in (("up", s_up, m_up), ("down", s_down, m_down)):
            row = {"run": label, "step": which, "mode": s["spec"].mode,
                   "kp": s["spec"].kp, "ki": s["spec"].ki,
                   "zeta_2L_P": s.get("zeta", np.nan),
                   "ki_crit": s.get("ki_crit", np.nan),
                   "rho_I": s.get("rho", np.nan)}
            for key in ("T_initial_C", "T_final_C", "rise_10_90_s",
                        "overshoot_C", "overshoot_pct", "settling_2pct_s",
                        "ss_error_C", "period_s", "sustained", "cycle_min_C",
                        "cycle_max_C", "cycle_p2p_C", "at_limit_pct"):
                row["sim_" + key] = sm[key]
                row["exp_" + key] = mm[key]
            metrics.append(row)
        if label in exp.RUNS:
            run_figure(label, s, os.path.join(FIG_DIR, f"run{label}_sim.png"))

    six = {k: sims[k] for k in exp.RUNS}
    exp.reference_figure(
        six, os.path.join(FIG_DIR, "overlay_p_and_pi_sim.png"),
        title="Simulated step responses, one shared two-lump parameter set",
        temp_label="simulated $T_m$ (°C)",
        note=model_note() + " Each run replays its experiment's start, "
             "setpoints and timing.")
    comparison_figure({k: measured[k] for k in exp.RUNS}, six,
                      os.path.join(FIG_DIR, "sim_vs_experiment.png"))

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
    print(f"{'run':>10} {'step':>4} {'stability':>12} | final sim/exp | "
          f"over% sim/exp | settle sim/exp | period sim/exp | sust | "
          f"p2p sim/exp | lim% sim/exp")
    for r in metrics:
        stab = (f"zeta {r['zeta_2L_P']:.2f}" if r["mode"] == "P"
                else f"rho {r['rho_I']:.3f}")
        print(f"{str(r['run']):>10} {r['step']:>4} {stab:>12} | "
              f"{r['sim_T_final_C']:6.2f}/{r['exp_T_final_C']:6.2f} | "
              f"{r['sim_overshoot_pct']:6.1f}/{r['exp_overshoot_pct']:6.1f} | "
              f"{r['sim_settling_2pct_s']:6.1f}/{r['exp_settling_2pct_s']:6.1f} | "
              f"{r['sim_period_s']:5.1f}/{r['exp_period_s']:5.1f} | "
              f"{r['sim_sustained']}/{r['exp_sustained']} | "
              f"{r['sim_cycle_p2p_C']:5.2f}/{r['exp_cycle_p2p_C']:5.2f} | "
              f"{r['sim_at_limit_pct']:4.1f}/{r['exp_at_limit_pct']:4.1f}")
    print(f"\nFigures in {FIG_DIR}, metrics in {METRICS_CSV}")


if __name__ == "__main__":
    main()
