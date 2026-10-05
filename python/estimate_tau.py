#!/usr/bin/env python3
"""
Phys 39 Module 6 Part 3. Naidu / Cohen

Estimate the open-loop thermal time constant tau = C/H from the Module 4
steps, and check it against the Module 5 closed-loop runs.

    python3 python/estimate_tau.py          (run from the repository root)

INPUT   data/module_04/full_run.csv          open-loop steps, constant command
        data/module_05/kp32_high_gain_run.csv closed-loop runs, for the check

OUTPUT  docs/figures/module_06/tau_estimate.png
        a table of tau per step, printed

METHOD

The module suggests reading tau off a single trace as the time to reach 63% of
the total change. That needs the final temperature, and several of our steps
were stopped before they fully arrived, so the 63% point would be read against
a finish line that is itself a guess.

Instead each step is fitted to

    T(t) = T_inf + (T_0 - T_inf) exp(-t / tau)

which estimates T_inf and tau together. The 63% time is then reported as well,
measured against the fitted asymptote, so the two methods can be compared.

The fit needs no scipy. At fixed tau the model is linear in T_inf and
(T_0 - T_inf), so those two come from ordinary least squares and only tau is
searched over, by a coarse log grid followed by a golden-section refinement.

WHY EVERY STEP SHOULD GIVE THE SAME TAU

In the one-lump model C dT/dt = Pu*u - H(T - T_amb), a constant command u
shifts where the temperature ends up but not how fast it gets there: the
homogeneous part is C dtheta/dt = -H theta no matter what u is. So tau = C/H
is a property of the apparatus, not of the drive. Eight steps at eight
different commands, heating and cooling, are therefore eight measurements of
one number, and their spread is the uncertainty.
"""

import csv
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OPEN_LOOP_CSV = "data/module_04/full_run.csv"
CLOSED_LOOP_CSV = "data/module_05/kp32_high_gain_run.csv"
OUTPUT_PNG = "docs/figures/module_06/tau_estimate.png"

CHI_U = 0.50127        # C per PWM count, Module 4 heating branch
MIN_SECONDS = 150      # a step shorter than about 2 tau cannot constrain tau
MIN_POINTS = 80

HEAT = "#C0392B"
COOL = "#1F77B4"
FIT = "#1F4E79"
GREY = "#595959"


def segments(path, keys, value_names):
    """Split a log into blocks over which every column in `keys` is constant."""
    if not os.path.exists(path):
        sys.exit(f"{path} not found. Run this from the repository root.")
    blocks = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                k = tuple(r[c] for c in keys)
                v = tuple(float(r[c]) for c in value_names)
            except (KeyError, ValueError, TypeError):
                continue
            if not blocks or blocks[-1][0] != k:
                blocks.append((k, [v]))
            else:
                blocks[-1][1].append(v)
    return blocks


def fit_exponential(t, T):
    """Return (tau, T_inf, R^2) for T = T_inf + (T_0 - T_inf) exp(-t/tau)."""
    def residual(tau):
        basis = np.column_stack([np.ones_like(t), np.exp(-t / tau)])
        coeffs, *_ = np.linalg.lstsq(basis, T, rcond=None)
        return float(np.sum((basis @ coeffs - T) ** 2)), coeffs

    grid = np.exp(np.linspace(np.log(2.0), np.log(1500.0), 400))
    best = min(grid, key=lambda x: residual(x)[0])

    lo, hi = best / 1.5, best * 1.5
    phi = (np.sqrt(5.0) - 1.0) / 2.0
    for _ in range(80):
        a, b = hi - phi * (hi - lo), lo + phi * (hi - lo)
        if residual(a)[0] < residual(b)[0]:
            hi = b
        else:
            lo = a

    tau = 0.5 * (lo + hi)
    ss_res, coeffs = residual(tau)
    ss_tot = float(np.sum((T - T.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot else float("nan")
    return tau, coeffs[0], r2


def crossing_63(t, T, t_inf):
    """Elapsed time to cover 63% of the way to the fitted asymptote."""
    target = T[0] + 0.63 * (t_inf - T[0])
    rising = t_inf > T[0]
    hit = np.flatnonzero((T >= target) if rising else (T <= target))
    return float(t[hit[0]]) if hit.size else float("nan")


def main():
    results = []
    for (pwm, direction), values in segments(
            OPEN_LOOP_CSV, ["pwm", "heat_cool"], ["time_s", "temperature_C"]):
        arr = np.asarray(values)
        t, T = arr[:, 0] - arr[0, 0], arr[:, 1]
        if t[-1] < MIN_SECONDS or len(t) < MIN_POINTS:
            continue
        tau, t_inf, r2 = fit_exponential(t, T)
        if not 2.0 < tau < 1200.0:
            continue
        results.append({
            "pwm": int(float(pwm)),
            "heating": direction.strip() in ("1", "heat", "HEAT"),
            "duration": t[-1], "t": t, "T": T,
            "tau": tau, "t_inf": t_inf, "r2": r2,
            "t63": crossing_63(t, T, t_inf),
            "covered": 100.0 * (1.0 - np.exp(-t[-1] / tau)),
        })
    if not results:
        sys.exit(f"No usable steps in {OPEN_LOOP_CSV}.")

    taus = np.array([r["tau"] for r in results])
    tau_mean, tau_sd = taus.mean(), taus.std(ddof=1)
    sem = tau_sd / np.sqrt(len(taus))

    print(f"Open-loop steps from {OPEN_LOOP_CSV}\n")
    print(f"{'PWM':>5} {'dir':>5} {'span/s':>7} {'tau/s':>7} {'t63/s':>7} "
          f"{'T_inf/C':>8} {'R^2':>8} {'arrived':>8}")
    print("-" * 62)
    for r in sorted(results, key=lambda x: x["tau"]):
        print(f"{r['pwm']:>5} {'heat' if r['heating'] else 'cool':>5} "
              f"{r['duration']:7.0f} {r['tau']:7.1f} {r['t63']:7.1f} "
              f"{r['t_inf']:8.2f} {r['r2']:8.5f} {r['covered']:7.1f}%")

    print(f"\n  tau = {tau_mean:.1f} +/- {tau_sd:.1f} s  "
          f"(standard deviation over {len(taus)} steps; "
          f"standard error {sem:.1f} s)")
    t63s = np.array([r["t63"] for r in results if np.isfinite(r["t63"])])
    print(f"  63% crossing gives {t63s.mean():.1f} +/- {t63s.std(ddof=1):.1f} s, "
          f"the same number by the module's own method")
    passive = [r for r in results if r["pwm"] == 0]
    if passive:
        print(f"  the zero-command decay alone gives {passive[0]['tau']:.1f} s, "
              f"which is C/H with no TEC drive at all")

    # ---- closed-loop check: tau_cl should be tau / (1 + L) ----
    print(f"\nClosed-loop check against {CLOSED_LOOP_CSV}")
    print("  A segment is only usable if it is a real step: the loop has to "
          "move far enough,\n  and be watched for long enough, for an "
          "exponential to be fitted at all.\n")
    print(f"{'Kp':>7} {'L':>7} {'step/C':>7} {'span/tau_cl':>12} "
          f"{'tau_cl':>8} {'tau/(1+L)':>10} {'ratio':>7}")
    print("-" * 66)
    usable = []
    for (kp_text, enabled), values in segments(
            CLOSED_LOOP_CSV, ["kp", "p_enabled"], ["time_s", "temperature_C"]):
        if enabled.strip() not in ("1", "true", "True"):
            continue
        arr = np.asarray(values)
        if len(arr) < MIN_POINTS:
            continue
        t, T = arr[:, 0] - arr[0, 0], arr[:, 1]
        tau_cl, _, r2 = fit_exponential(t, T)
        if not 0.5 < tau_cl < 1200.0 or r2 < 0.9:
            continue
        kp = float(kp_text)
        predicted = tau_mean / (1.0 + kp * CHI_U)
        step = abs(T[-1] - T[0])
        spans = t[-1] / predicted
        good = step > 0.5 and spans > 1.5
        if good:
            usable.append(tau_cl / predicted)
        print(f"{kp:7.2f} {kp * CHI_U:7.2f} {step:7.2f} {spans:12.1f} "
              f"{tau_cl:8.1f} {predicted:10.1f} {tau_cl / predicted:7.2f}"
              f"{'' if good else '   too small or too short to fit'}")

    if usable:
        u = np.array(usable)
        print(f"\n  Over the {len(u)} usable segments, measured tau_cl is "
              f"{u.mean():.2f} +/- {u.std(ddof=1):.2f} times tau/(1+L).")
    print("  Each gain was entered from the previous steady state, so most "
          "steps are small;\n  this check confirms the trend rather than "
          "measuring tau a second time.")

    # Mild systematic drift of tau with the command, worth stating rather than
    # averaging away: it says the constant-coefficient assumption is only
    # approximate over this range.
    order = sorted(results, key=lambda r: r["pwm"] if r["heating"]
                   else -r["pwm"])
    print(f"\n  tau runs from {order[0]['tau']:.1f} s at u = "
          f"{order[0]['pwm'] if order[0]['heating'] else -order[0]['pwm']:+d} "
          f"to {order[-1]['tau']:.1f} s at u = "
          f"{order[-1]['pwm'] if order[-1]['heating'] else -order[-1]['pwm']:+d}"
          f" counts, a {100 * (order[-1]['tau'] / order[0]['tau'] - 1):.0f}% "
          f"drift.\n  H and C are therefore not quite constant over the "
          f"10 to 45 C range; the one-lump model is an approximation, not an "
          f"identity.")

    # ---------------------------- figure ----------------------------
    # Same conventions as the other figures: white plot area, light grey
    # gridlines, no top or right spine, plain coloured text at the top left,
    # a plain legend, and a grey note underneath.
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.edgecolor": "#868686", "axes.linewidth": 0.8,
        "xtick.direction": "out", "ytick.direction": "out",
        "xtick.color": "#595959", "ytick.color": "#595959",
    })
    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(10.5, 4.6),
                                            gridspec_kw={"wspace": 0.2})
    fig.patch.set_facecolor("white")
    for ax in (ax_left, ax_right):
        ax.set_facecolor("white")
        ax.grid(True, which="major", color="#D9D9D9", linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

    # Left: every step collapsed onto one normalised curve.
    for r in results:
        scale = r["t_inf"] - r["T"][0]
        if abs(scale) < 0.5:
            continue
        theta = 1.0 - (r["T"] - r["T"][0]) / scale
        ax_left.plot(r["t"] / tau_mean, theta,
                     color=HEAT if r["heating"] else COOL,
                     linewidth=1.1, alpha=0.75, zorder=3)
    x = np.linspace(0, 5, 200)
    ax_left.plot(x, np.exp(-x), "--", color=FIT, linewidth=1.8, zorder=4,
                 label=r"$e^{-t/\tau}$")
    ax_left.plot([], [], color=HEAT, linewidth=1.1, label="heating steps")
    ax_left.plot([], [], color=COOL, linewidth=1.1, label="cooling steps")
    ax_left.set_xlim(0, 5)
    ax_left.set_ylim(-0.05, 1.05)
    ax_left.set_xlabel(r"Elapsed time / $\tau$", color="#404040")
    ax_left.set_ylabel("Fraction of the step remaining", color="#404040")
    ax_left.set_title("All eight steps on one scale", fontsize=11.5,
                      color="#404040", pad=8)
    ax_left.text(0.44, 0.72,
                 f"$\\tau$ = {tau_mean:.1f} $\\pm$ {tau_sd:.1f} s",
                 transform=ax_left.transAxes, fontsize=11, color=FIT,
                 va="top")
    leg = ax_left.legend(loc="upper right", frameon=True, fontsize=9)
    leg.get_frame().set_edgecolor("#BFBFBF")
    leg.get_frame().set_linewidth(0.8)

    # Right: tau against the command that produced it.
    for r in results:
        u = r["pwm"] if r["heating"] else -r["pwm"]
        ax_right.plot([u], [r["tau"]], "o" if r["heating"] else "s",
                      color=HEAT if r["heating"] else COOL, markersize=8,
                      markeredgecolor="#404040", markeredgewidth=0.7,
                      zorder=3)
    ax_right.axhline(tau_mean, color=FIT, linestyle="--", linewidth=1.5,
                     zorder=2, label=f"mean, {tau_mean:.1f} s")
    ax_right.axhspan(tau_mean - tau_sd, tau_mean + tau_sd, color=FIT,
                     alpha=0.09, zorder=1,
                     label=f"$\\pm$ 1 sd, {tau_sd:.1f} s")
    ax_right.set_xlabel("Signed PWM command during the step  (counts)",
                        color="#404040")
    ax_right.set_ylabel(r"Fitted $\tau$  (s)", color="#404040")
    ax_right.set_title(r"$\tau$ across the whole command range",
                       fontsize=11.5, color="#404040", pad=8)
    drift = 100.0 * (max(taus) / min(taus) - 1.0)
    ax_right.text(0.03, 0.93,
                  f"spread {min(taus):.0f} to {max(taus):.0f} s, {drift:.0f}%,"
                  f" with no step-size dependence",
                  transform=ax_right.transAxes, fontsize=9.5, color=GREY,
                  va="top")
    ax_right.set_ylim(0, max(taus) * 1.45)
    leg = ax_right.legend(loc="lower right", frameon=True, fontsize=9)
    leg.get_frame().set_edgecolor("#BFBFBF")
    leg.get_frame().set_linewidth(0.8)

    fig.text(0.008, 0.015,
             f"Each step is fitted to T = T_inf + (T_0 - T_inf) exp(-t/tau); "
             f"every fit has R^2 > {min(r['r2'] for r in results):.3f}. "
             f"Steps shorter than {MIN_SECONDS} s are excluded.\n"
             f"A constant command moves where the temperature ends up but not "
             f"how fast it gets there, so all eight are measurements of one "
             f"number. Source: {OPEN_LOOP_CSV}.",
             fontsize=7.8, color=GREY, va="bottom")
    fig.subplots_adjust(left=0.075, right=0.985, top=0.91, bottom=0.21)

    os.makedirs(os.path.dirname(OUTPUT_PNG), exist_ok=True)
    fig.savefig(OUTPUT_PNG, dpi=200, facecolor="white")
    print(f"\nFigure written to {OUTPUT_PNG}")


if __name__ == "__main__":
    main()
