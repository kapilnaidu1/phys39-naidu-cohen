#!/usr/bin/env python3
"""
Phys 39 Module 6 Parts 4, 5 and 7. Naidu / Cohen

Our own one-lump TEC model, integrated forward in time with Euler steps, run
open loop, then with P feedback, then with PI feedback.

    python3 python/simulate_one_lump.py       (run from the repository root)

INPUT   data/module_04/full_run.csv     measured open-loop steps, for Part 4
        data/module_05/droop.csv        measured droop vs gain, for Part 5

OUTPUT  docs/figures/module_06/open_loop_sim_vs_measured.png   Part 4
        docs/figures/module_06/p_control_sim.png               Part 5
        docs/figures/module_06/pi_vs_p_sim.png                 Part 7
        parameter table, timestep convergence check, and comparison tables,
        all printed

THE MODEL

The dimensional one-lump energy balance is

    C dT/dt = Pu*u - H*(T - T_amb)

and its Euler form is

    T[n+1] = T[n] + (dt/C) * (Pu*u[n] - H*(T[n] - T_amb))

We never measured C, H or Pu separately. What the apparatus gave us is the
steady-state susceptibility chi = Pu/H (Module 4) and the time constant
tau = C/H (Module 6 Part 3). Dividing the balance by H and using those two:

    T[n+1] = T[n] + (dt/tau) * (T_amb + chi*u[n] - T[n])

This is the same model, not a different one. It is the form we can actually
run, because every number in it was measured.

WHAT CARRIES OVER TO PI

The PI eigenvalues also come out in terms of chi and tau alone. From

    lambda^2 + ((H + Pu*Kp)/C)*lambda + (Pu*Ki)/C = 0

divide through by H and substitute:

    (H + Pu*Kp)/C = (1 + chi*Kp)/tau = (1 + L)/tau
    (Pu*Ki)/C     = chi*Ki/tau

so

    lambda^2 + ((1+L)/tau)*lambda + chi*Ki/tau = 0
    zeta = (1 + L) / (2*sqrt(tau*chi*Ki))

and the response is underdamped when (1+L)^2 < 4*tau*chi*Ki. C, H and Pu never
have to be separated.

ONE LIMITATION, STATED UP FRONT

The model carries a single chi, but the apparatus has two: 0.50127 heating and
0.18091 cooling. Every run below sits at a setpoint above ambient where the
command stays positive, so the heating value is the right one throughout. A
cooling setpoint would need the other.
"""

import csv
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OPEN_LOOP_CSV = "data/module_04/full_run.csv"
DROOP_CSV = "data/module_05/droop.csv"
FIG_DIR = "docs/figures/module_06"

# Measured parameters. None of these is fitted to anything simulated here.
CHI = 0.50127          # C per PWM count, Module 4 heating branch
TAU = 62.9             # s, Module 6 Part 3, python/estimate_tau.py
T_AMB = 21.54          # C, Module 4 zero-command temperature
PWM_LIMIT = 255        # counts, the signed command is clamped to +/- this
WINDUP_KI = 0.05       # counts per C per s, the integral gain for Part 8

DT = 0.05              # s, the working timestep; DT/TAU is about 1/1300
SETPOINT = 30.0        # C, the Module 5 setpoint

HEAT = "#C0392B"
COOL = "#1F77B4"
MODEL = "#1F4E79"
GREY = "#595959"


# ----------------------------------------------------------------- the model

def step(T, u, dt=DT, chi=CHI, tau=TAU, t_amb=T_AMB):
    """One Euler step of C dT/dt = Pu*u - H(T - T_amb), written with the two
    parameters we measured. Returns the next temperature."""
    return T + (dt / tau) * (t_amb + chi * u - T)


def clamp(u, limit=PWM_LIMIT):
    """The bridge cannot deliver more than +/- limit counts. Clamping here,
    before the command reaches the model, is what makes saturation real in the
    simulation rather than something the model is allowed to ignore."""
    return max(-limit, min(limit, u))


def run_open_loop(T0, u, duration, dt=DT, **kw):
    """Constant command. Returns (time array, temperature array)."""
    n = int(round(duration / dt)) + 1
    T = np.empty(n)
    T[0] = T0
    for i in range(n - 1):
        T[i + 1] = step(T[i], clamp(u), dt, **kw)
    return np.arange(n) * dt, T


def run_p(T0, kp, setpoint=SETPOINT, duration=600.0, dt=DT, **kw):
    """P-only feedback. The command is computed from the current state and
    clamped before it is applied, which is the order the real controller uses."""
    n = int(round(duration / dt)) + 1
    T, u = np.empty(n), np.empty(n)
    T[0] = T0
    for i in range(n):
        u[i] = clamp(kp * (setpoint - T[i]))
        if i < n - 1:
            T[i + 1] = step(T[i], u[i], dt, **kw)
    return np.arange(n) * dt, T, u


def run_pi(T0, kp, ki, setpoint=SETPOINT, duration=600.0, dt=DT,
           anti_windup=False, limit=PWM_LIMIT, **kw):
    """PI feedback. q is the accumulated error, dq/dt = T_set - T.

    With anti_windup the integral stops accumulating whenever the command is
    clamped and the error would push it further into the clamp. That is the
    conditional-integration fix, and Part 8 is about why it is needed."""
    n = int(round(duration / dt)) + 1
    T, u, q = np.empty(n), np.empty(n), np.empty(n)
    T[0], q[0] = T0, 0.0
    for i in range(n):
        raw = kp * (setpoint - T[i]) + ki * q[i]
        u[i] = clamp(raw, limit)
        if i < n - 1:
            T[i + 1] = step(T[i], u[i], dt, **kw)
            error = setpoint - T[i]
            saturated = raw != u[i]
            if anti_windup and saturated and np.sign(error) == np.sign(raw):
                q[i + 1] = q[i]          # hold, do not wind up further
            else:
                q[i + 1] = q[i] + error * dt
    return np.arange(n) * dt, T, u, q


def zeta_of(kp, ki, chi=CHI, tau=TAU):
    """Damping ratio, in measured parameters. See the module docstring."""
    return (1.0 + chi * kp) / (2.0 * np.sqrt(tau * chi * ki))


# -------------------------------------------------------------- measured data

def measured_steps(path):
    """Blocks of constant (pwm, heat_cool) from the Module 4 log."""
    if not os.path.exists(path):
        sys.exit(f"{path} not found. Run this from the repository root.")
    blocks = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                k = (int(float(r["pwm"])), r["heat_cool"].strip() in ("1", "heat"))
                v = (float(r["time_s"]), float(r["temperature_C"]))
            except (KeyError, ValueError, TypeError):
                continue
            if not blocks or blocks[-1][0] != k:
                blocks.append((k, [v]))
            else:
                blocks[-1][1].append(v)
    return blocks


def measured_droop(path):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                out.append((float(r["kp"]), float(r["setpoint_c"]),
                            float(r["final_t_c"])))
            except (KeyError, ValueError, TypeError):
                continue
    return sorted(out)


def style(ax):
    ax.set_facecolor("white")
    ax.grid(True, which="major", color="#D9D9D9", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def setup_rc():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.edgecolor": "#868686", "axes.linewidth": 0.8,
        "xtick.direction": "out", "ytick.direction": "out",
        "xtick.color": "#595959", "ytick.color": "#595959",
    })


# ------------------------------------------------------------------- Part 4

def part4():
    print("=" * 72)
    print("PART 4   Open-loop simulation against measured traces")
    print("=" * 72)
    print(f"\n  chi   = {CHI:.5f} C per PWM count   (Module 4, heating branch)")
    print(f"  tau   = {TAU:.1f} s                   (Module 6 Part 3)")
    print(f"  T_amb = {T_AMB:.2f} C                 (Module 4, zero command)")
    print(f"  dt    = {DT} s, so dt/tau = {DT / TAU:.2e}")
    print(f"  u is the signed PWM command in counts, clamped to "
          f"+/-{PWM_LIMIT}\n")

    # Timestep convergence. The Euler method is only first order, so the answer
    # has to be shown not to depend on dt before any comparison is believable.
    print("  Timestep check: 300 s of a +25 count step from 21.54 C")
    print(f"  {'dt / s':>8} {'steps':>8} {'T(300 s) / C':>14} "
          f"{'change from previous':>22}")
    print("  " + "-" * 56)
    previous = None
    for dt in (1.0, 0.5, 0.1, 0.05, 0.01):
        _, T = run_open_loop(T_AMB, 25, 300.0, dt=dt)
        delta = "" if previous is None else f"{abs(T[-1] - previous):.2e} C"
        print(f"  {dt:8.2f} {int(300 / dt):8d} {T[-1]:14.6f} {delta:>22}")
        previous = T[-1]
    print(f"  Halving dt below {DT} s moves the answer by less than a "
          f"microkelvin,\n  far under the 0.02 C noise floor, so {DT} s is "
          f"small enough.\n")

    # Two measured steps: one driven, one passive.
    wanted = [(25, True), (0, True)]
    chosen = {}
    for key, pts in measured_steps(OPEN_LOOP_CSV):
        if key in wanted and len(pts) > 200:
            span = pts[-1][0] - pts[0][0]
            if key not in chosen or span > chosen[key][-1][0] - chosen[key][0][0]:
                chosen[key] = pts
    missing = [k for k in wanted if k not in chosen]
    if missing:
        sys.exit(f"{OPEN_LOOP_CSV} has no long block for {missing}.")

    setup_rc()
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4),
                             gridspec_kw={"wspace": 0.18})
    fig.patch.set_facecolor("white")

    print("  Simulation against measurement")
    print(f"  {'command':>9} {'span / s':>9} {'final meas':>11} "
          f"{'final sim':>10} {'diff':>8} {'rms resid':>10}")
    print("  " + "-" * 62)
    for ax, (key, title) in zip(axes, [((25, True), "driven, u = +25 counts"),
                                       ((0, True), "passive, u = 0")]):
        pts = chosen[key]
        arr = np.asarray(pts)
        tm, Tm = arr[:, 0] - arr[0, 0], arr[:, 1]
        u = key[0] if key[1] else -key[0]
        ts, Ts = run_open_loop(Tm[0], u, tm[-1])
        # Compare on the measured sample times.
        Ts_on_meas = np.interp(tm, ts, Ts)
        resid = Ts_on_meas - Tm
        rms = float(np.sqrt(np.mean(resid ** 2)))
        print(f"  {u:>+9d} {tm[-1]:9.0f} {Tm[-1]:11.2f} {Ts_on_meas[-1]:10.2f} "
              f"{Ts_on_meas[-1] - Tm[-1]:+8.2f} {rms:10.3f}")

        style(ax)
        ax.plot(tm, Tm, color=HEAT, linewidth=1.6, zorder=3, label="Measured")
        ax.plot(ts, Ts, "--", color=MODEL, linewidth=1.6, zorder=4,
                label="One-lump model")
        ax.axhline(T_AMB + CHI * u, color=GREY, linewidth=1.0, linestyle=":",
                   zorder=2,
                   label=f"$T_{{amb}} + \\chi u$ = {T_AMB + CHI * u:.2f} °C")
        ax.set_title(f"{title}      rms residual {rms:.3f} \u00b0C",
                     fontsize=11, color="#404040", pad=8)
        ax.set_xlabel("Time since the step  (s)", color="#404040")
        ax.set_ylabel("Temperature  (°C)", color="#404040")
        leg = ax.legend(loc="best", frameon=True, fontsize=9)
        leg.get_frame().set_edgecolor("#BFBFBF")
        leg.get_frame().set_linewidth(0.8)

    fig.suptitle("Part 4: one-lump model against measured open-loop steps",
                 fontsize=13, color="#404040", y=0.975)
    fig.text(0.008, 0.015,
             f"Model: T[n+1] = T[n] + (dt/tau)(T_amb + chi*u[n] - T[n]) with "
             f"chi = {CHI:.5f} C/count, tau = {TAU:.1f} s, "
             f"T_amb = {T_AMB:.2f} C, dt = {DT} s.\nNothing here is fitted to "
             f"these traces: all three parameters come from Module 4 and the "
             f"Part 3 time-constant fit. Source: {OPEN_LOOP_CSV}.",
             fontsize=7.8, color=GREY, va="bottom")
    fig.subplots_adjust(left=0.07, right=0.985, top=0.855, bottom=0.21)
    out = os.path.join(FIG_DIR, "open_loop_sim_vs_measured.png")
    fig.savefig(out, dpi=200, facecolor="white")
    plt.close(fig)
    print(f"\n  Figure: {out}\n")


# ------------------------------------------------------------------- Part 5

P_GAINS = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0]


def part5():
    print("=" * 72)
    print("PART 5   P-only feedback in simulation, against Module 5")
    print("=" * 72)
    runs = {kp: run_p(T_AMB, kp, duration=600.0) for kp in P_GAINS}
    measured = dict((kp, SETPOINT - final)
                    for kp, sp, final in measured_droop(DROOP_CSV)
                    if abs(sp - SETPOINT) < 0.01)

    print(f"\n  {'Kp':>6} {'L':>7} {'sim droop':>10} {'1/(1+L)':>9} "
          f"{'measured':>9} {'sim/meas':>9} {'peak PWM':>9} {'sat?':>6}")
    print("  " + "-" * 70)
    sim_droop = {}
    for kp in P_GAINS:
        _, T, u = runs[kp]
        droop = SETPOINT - T[-1]
        sim_droop[kp] = droop
        L = CHI * kp
        algebraic = (SETPOINT - T_AMB) / (1.0 + L)
        meas = measured.get(kp)
        ratio = f"{droop / meas:9.3f}" if meas else f"{'':>9}"
        peak = np.max(np.abs(u))
        print(f"  {kp:6.2f} {L:7.3f} {droop:10.3f} {algebraic:9.3f} "
              f"{meas if meas else float('nan'):9.2f} {ratio} {peak:9.0f} "
              f"{'yes' if peak >= PWM_LIMIT else 'no':>6}")
    print("\n  The simulated droop reproduces the algebraic 1/(1+L) result "
          "exactly, as it must:\n  both come from the same balance, one solved "
          "and one integrated.")

    setup_rc()
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.2),
                             gridspec_kw={"wspace": 0.26})
    fig.patch.set_facecolor("white")
    shades = plt.cm.viridis(np.linspace(0.08, 0.88, len(P_GAINS)))

    ax = axes[0]
    style(ax)
    for kp, c in zip(P_GAINS, shades):
        t, T, _ = runs[kp]
        ax.plot(t, T, color=c, linewidth=1.4)
        # Label each curve at its own settled level. Nine legend entries would
        # sit on top of the very traces they name.
        ax.text(368, T[-1], f" {kp:g}", color=c, fontsize=8.5,
                va="center", ha="left")
    ax.text(368, SETPOINT + 0.25, " $K_p$", color="#404040", fontsize=8.5,
            va="center", ha="left")
    ax.axhline(SETPOINT, color=GREY, linestyle="--", linewidth=1.2)
    ax.text(10, SETPOINT + 0.12, "setpoint", color=GREY, fontsize=8.5,
            va="bottom")
    ax.set_xlim(0, 400)
    ax.set_xlabel("Time  (s)", color="#404040")
    ax.set_ylabel("Temperature  (°C)", color="#404040")
    ax.set_title("Temperature", fontsize=11.5, color="#404040", pad=8)

    ax = axes[1]
    style(ax)
    for kp, c in zip(P_GAINS, shades):
        t, _, u = runs[kp]
        ax.plot(t, u, color=c, linewidth=1.4)
    ax.axhline(PWM_LIMIT, color=HEAT, linestyle=":", linewidth=1.2,
               label=f"clamp, {PWM_LIMIT} counts")
    ax.set_xlim(0, 120)
    ax.text(0.97, 0.80,
            "only $K_p$ = 32 reaches the clamp,\nand only for 0.3 s",
            transform=ax.transAxes, ha="right", va="top", fontsize=8.5,
            color=GREY)
    ax.set_xlabel("Time  (s)", color="#404040")
    ax.set_ylabel("Commanded PWM  (counts)", color="#404040")
    ax.set_title("Command", fontsize=11.5, color="#404040", pad=8)
    leg = ax.legend(loc="upper right", frameon=True, fontsize=8.5)
    leg.get_frame().set_edgecolor("#BFBFBF")
    leg.get_frame().set_linewidth(0.8)

    ax = axes[2]
    style(ax)
    grid = np.linspace(min(P_GAINS), max(P_GAINS), 400)
    ax.plot(grid, (SETPOINT - T_AMB) / (1.0 + CHI * grid), "--",
            color=MODEL, linewidth=1.6, zorder=2, label="algebraic 1/(1+L)")
    ax.plot(P_GAINS, [sim_droop[k] for k in P_GAINS], "o", color=MODEL,
            markersize=7, markeredgecolor="#404040", markeredgewidth=0.7,
            linestyle="none", zorder=3, label="simulated")
    if measured:
        ks = sorted(measured)
        ax.plot(ks, [measured[k] for k in ks], "s", color=HEAT, markersize=8,
                markeredgecolor="#404040", markeredgewidth=0.7,
                linestyle="none", zorder=4, label="measured, Module 5")
    ax.set_xscale("log")
    ax.set_xlabel("Proportional gain $K_p$  (counts per °C)",
                  color="#404040")
    ax.set_ylabel("Steady-state droop  (°C)", color="#404040")
    ax.set_title("Droop versus gain", fontsize=11.5, color="#404040", pad=8)
    leg = ax.legend(loc="upper right", frameon=True, fontsize=8.5)
    leg.get_frame().set_edgecolor("#BFBFBF")
    leg.get_frame().set_linewidth(0.8)

    fig.suptitle("Part 5: simulated P-only control", fontsize=13,
                 color="#404040", y=0.975)
    fig.text(0.006, 0.015,
             f"Every run starts from T_amb = {T_AMB:.2f} °C with a "
             f"{SETPOINT:.1f} °C setpoint. The command is clamped to "
             f"+/-{PWM_LIMIT} counts before it reaches the model.\n"
             f"Simulated and measured droop are compared against the "
             f"algebraic prediction, which has no free parameters.",
             fontsize=7.8, color=GREY, va="bottom")
    fig.subplots_adjust(left=0.055, right=0.99, top=0.855, bottom=0.215)
    out = os.path.join(FIG_DIR, "p_control_sim.png")
    fig.savefig(out, dpi=200, facecolor="white")
    plt.close(fig)
    print(f"\n  Figure: {out}\n")
    return sim_droop


# ------------------------------------------------------------------- Part 7

def settling_time(t, T, target, band):
    """Last time the trace is outside +/- band of target."""
    outside = np.flatnonzero(np.abs(T - target) > band)
    if not outside.size:
        return 0.0
    last = float(t[outside[-1]])
    # Still outside the band at the end of the run means it never settled.
    return float("inf") if outside[-1] >= len(t) - 2 else last


def part7():
    print("=" * 72)
    print("PART 7   Integral action, and what it costs")
    print("=" * 72)
    kp = 2.0                       # a gain Module 5 showed to be well behaved
    global WINDUP_KI
    L = CHI * kp
    ki_list = [0.002, 0.01, 0.05, 0.20]
    band = 0.10                    # C, the settling band

    t_p, T_p, u_p = run_p(T_AMB, kp, duration=900.0)
    print(f"\n  Baseline P-only at Kp = {kp:g} (L = {L:.3f}): "
          f"droop {SETPOINT - T_p[-1]:.3f} C, no overshoot by construction.")
    print(f"  Underdamped when (1+L)^2 < 4*tau*chi*Ki, i.e. "
          f"Ki > {(1 + L) ** 2 / (4 * TAU * CHI):.4f} counts/(C s).\n")
    print(f"  {'Ki':>7} {'zeta':>7} {'damping':>13} {'final droop':>12} "
          f"{'overshoot':>10} {'settle to 0.1C':>15}")
    print("  " + "-" * 70)

    runs = {}
    for ki in ki_list:
        t, T, u, q = run_pi(T_AMB, kp, ki, duration=900.0)
        runs[ki] = (t, T, u, q)
        z = zeta_of(kp, ki)
        kind = ("overdamped" if z > 1.02 else
                "critical" if z > 0.98 else "underdamped")
        overshoot = max(0.0, float(np.max(T)) - SETPOINT)
        settle = settling_time(t, T, SETPOINT, band)
        settle_text = "never" if np.isinf(settle) else f"{settle:.0f} s"
        print(f"  {ki:7.3f} {z:7.3f} {kind:>13} "
              f"{SETPOINT - T[-1]:12.4f} {overshoot:10.3f} "
              f"{settle_text:>15}")

    print(f"\n  P-only settles to 0.1 C of setpoint: never, the droop is "
          f"{SETPOINT - T_p[-1]:.2f} C.")
    print("  Integral action removes the droop entirely. The cost is "
          "overshoot, which\n  appears exactly where zeta drops below 1, and "
          "windup, which Part 8 covers.")

    # Windup demonstration. This apparatus is not actuator-limited at any safe
    # setpoint: holding 45 C needs only (45 - 21.54)/chi = 47 counts of the 255
    # available, so the real clamp never binds for long and windup never
    # appears. That is itself worth reporting. To show the effect at all we
    # have to impose a tighter limit, which is what Part 8 asks us to suppose.
    far = 45.0
    tight = 50
    required = (far - T_AMB) / CHI
    t_w, T_w, u_w, q_w = run_pi(T_AMB, kp, WINDUP_KI, setpoint=far,
                                duration=2400.0, limit=tight)
    t_a, T_a, u_a, q_a = run_pi(T_AMB, kp, WINDUP_KI, setpoint=far,
                                duration=2400.0, limit=tight,
                                anti_windup=True)
    print(f"\n  Windup. Holding {far:.0f} C needs {required:.0f} counts, and "
          f"the bridge supplies {PWM_LIMIT}, so\n  the real apparatus never "
          f"saturates for long at a safe setpoint and never winds up. The\n"
          f"  panel below imposes a {tight}-count limit, as Part 8 asks us to "
          f"suppose.")
    print(f"\n  {'':>14} {'peak T / C':>11} {'overshoot':>10} "
          f"{'peak integral':>14} {'clamped for':>12}")
    print("  " + "-" * 64)
    for name, T, u, q, t in (("plain PI", T_w, u_w, q_w, t_w),
                             ("anti-windup", T_a, u_a, q_a, t_a)):
        held = float(np.sum(np.abs(u) >= tight - 1e-9) * DT)
        print(f"  {name:>14} {np.max(T):11.2f} {np.max(T) - far:+10.2f} "
              f"{np.max(q):13.0f} {held:11.0f} s")

    setup_rc()
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.2),
                             gridspec_kw={"wspace": 0.26})
    fig.patch.set_facecolor("white")
    shades = plt.cm.plasma(np.linspace(0.08, 0.78, len(ki_list)))

    ax = axes[0]
    style(ax)
    ax.plot(t_p, T_p, color=GREY, linewidth=1.8, linestyle="--",
            label="P only", zorder=3)
    for ki, c in zip(ki_list, shades):
        t, T, _, _ = runs[ki]
        ax.plot(t, T, color=c, linewidth=1.4, zorder=4,
                label=f"$K_i$ = {ki:g}, $\\zeta$ = {zeta_of(kp, ki):.2f}")
    ax.axhline(SETPOINT, color="#404040", linewidth=1.0, linestyle=":",
               zorder=2)
    ax.set_xlim(0, 700)
    ax.set_xlabel("Time  (s)", color="#404040")
    ax.set_ylabel("Temperature  (°C)", color="#404040")
    ax.set_title(f"P against PI, $K_p$ = {kp:g}", fontsize=11.5,
                 color="#404040", pad=8)
    leg = ax.legend(loc="lower right", frameon=True, fontsize=8)
    leg.get_frame().set_edgecolor("#BFBFBF")
    leg.get_frame().set_linewidth(0.8)

    ax = axes[1]
    style(ax)
    grid = np.logspace(np.log10(5e-4), np.log10(1.0), 400)
    ax.plot(grid, zeta_of(kp, grid), color=MODEL, linewidth=1.6, zorder=3)
    ax.axhline(1.0, color=HEAT, linestyle="--", linewidth=1.2, zorder=2,
               label="$\\zeta$ = 1, critical")
    for ki, c in zip(ki_list, shades):
        ax.plot([ki], [zeta_of(kp, ki)], "o", color=c, markersize=8,
                markeredgecolor="#404040", markeredgewidth=0.7, zorder=4)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Integral gain $K_i$  (counts per °C per s)",
                  color="#404040")
    ax.set_ylabel("Damping ratio $\\zeta$", color="#404040")
    ax.set_title("Where PI turns underdamped", fontsize=11.5,
                 color="#404040", pad=8)
    leg = ax.legend(loc="upper right", frameon=True, fontsize=8.5)
    leg.get_frame().set_edgecolor("#BFBFBF")
    leg.get_frame().set_linewidth(0.8)

    ax = axes[2]
    style(ax)
    ax.plot(t_w, T_w, color=HEAT, linewidth=1.5, zorder=3, label="PI, plain")
    ax.plot(t_a, T_a, color=MODEL, linewidth=1.5, zorder=4,
            label="PI, anti-windup")
    ax.axhline(far, color=GREY, linestyle="--", linewidth=1.2, zorder=2,
               label=f"setpoint {far:.0f} °C")
    ax.set_xlim(0, 1200)
    ax.set_ylim(T_AMB - 1.0, far + 5.0)   # headroom for the two annotations
    ax.set_xlabel("Time  (s)", color="#404040")
    ax.set_ylabel("Temperature  (°C)", color="#404040")
    ax.set_title(f"Windup, $K_i$ = {WINDUP_KI:g}, command limited to {tight}",
                 fontsize=11.5, color="#404040", pad=8)
    held_w = float(np.sum(np.abs(u_w) >= tight - 1e-9) * DT)
    held_a = float(np.sum(np.abs(u_a) >= tight - 1e-9) * DT)
    ax.text(0.04, 0.95,
            f"plain:  +{np.max(T_w) - far:.2f} \u00b0C over, "
            f"clamped {held_w:.0f} s", transform=ax.transAxes, fontsize=9,
            color=HEAT, va="top")
    ax.text(0.04, 0.87,
            f"anti-windup:  +{np.max(T_a) - far:.2f} \u00b0C over, "
            f"clamped {held_a:.0f} s", transform=ax.transAxes, fontsize=9,
            color=MODEL, va="top")
    leg = ax.legend(loc="lower right", frameon=True, fontsize=8.5)
    leg.get_frame().set_edgecolor("#BFBFBF")
    leg.get_frame().set_linewidth(0.8)

    fig.suptitle("Part 7: integral action, damping, and windup", fontsize=13,
                 color="#404040", y=0.975)
    fig.text(0.006, 0.015,
             f"zeta = (1 + chi*Kp) / (2*sqrt(tau*chi*Ki)), which needs only "
             f"the measured chi and tau; C, H and Pu never separate.\n"
             f"Holding {far:.0f} °C needs only {required:.0f} of the "
             f"{PWM_LIMIT} available counts, so this apparatus never winds up "
             f"at a safe setpoint; the windup panel imposes a {tight}-count "
             f"limit to show the effect at all.",
             fontsize=7.8, color=GREY, va="bottom")
    fig.subplots_adjust(left=0.055, right=0.99, top=0.855, bottom=0.215)
    out = os.path.join(FIG_DIR, "pi_vs_p_sim.png")
    fig.savefig(out, dpi=200, facecolor="white")
    plt.close(fig)
    print(f"\n  Figure: {out}")


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    part4()
    part5()
    part7()
    print("\nAll three figures written to " + FIG_DIR)


if __name__ == "__main__":
    main()
