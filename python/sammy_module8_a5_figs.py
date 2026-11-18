#!/usr/bin/env python3
"""
Phys 39 Module 8, Part I: the four figure groups of A5 (Samuel Cohen).  SAMMY.  Called by python/sammy_module8_a5_write.py.
"""

import math

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sammy_module8_angstrom_analysis as A
import sammy_module8_a5 as M
import sammy_module8_runs_summary as RS

plt.rcParams.update({"font.size": 8.5, "axes.grid": True, "grid.color": "#e4e4e4", "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})
RED, BLUE, GREY = "#c0392b", "#1f77b4", "#808080"


def fig1(path, rows, sims):
    """Boundary control: TEC against the requested 40 + 16 sin over three settled cycles, with T1, the PWM and (P, PI) the simulation."""
    order = [("raw0", "(a) RAW zero-centered, 100 s"), ("raw1", "(b) RAW positive-only, 100 s"), ("ff", "(c) feedforward (OL), 100 s"),
             ("p", "(d) P only, Kp 12, 100 s"), ("pi100", "(e) PI, Kp 12, Ki 0.2, 100 s"), ("pi300", "(f) PI, Kp 12, Ki 0.2, 300 s")]
    fig = plt.figure(figsize=(9.4, 4.6))
    outer = fig.add_gridspec(2, 3, hspace=0.62, wspace=0.2, left=0.055, right=0.995, top=0.87, bottom=0.085)
    for k, (key, title) in enumerate(order):
        r = next(x for x in rows if x["key"] == key)
        inner = outer[k // 3, k % 3].subgridspec(2, 1, height_ratios=[3.2, 1], hspace=0.12)
        ax = fig.add_subplot(inner[0])
        ax2 = fig.add_subplot(inner[1], sharex=ax)
        cols, data, t0, t1, P = r["cols"], r["data"], r["t0"], r["t1"], r["P"]
        t = cols["t"]
        sel = (t >= t0) & (t < t1)
        tt = t[sel] - t0
        pwm = cols["signed_pwm"].astype(float)
        if r["raw"]:
            fu = M.fit1(t, pwm, P, t0, t1)
            sp = M.TA + M.TB * np.cos(2 * math.pi / P * t[sel] + fu["phi"])
        else:
            sp = cols["setpoint_C"][sel]
        ax.plot(tt, sp, color=GREY, ls="--", lw=1.2, label="requested 40 + 16 sin")
        ax.plot(tt, data["T1_C"][sel], color=BLUE, lw=0.9, label="T1 (rod base)")
        ax.plot(tt, data["TEC_C"][sel], color="k", lw=1.5, label="TEC measured")
        if key in sims:
            ts, tp = sims[key][0], sims[key][1]
            m = (ts >= t0) & (ts < t1)
            ax.plot(ts[m] - t0, tp[m], color=RED, lw=1.2, ls=(0, (4, 2)), label="TEC simulated")
        ax2.step(tt, pwm[sel], where="post", color="#2a6f97", lw=0.9)
        for v in (-255, 255):
            ax2.axhline(v, color="k", lw=0.6, ls=":")
        ax.set_title(title, fontsize=8, loc="left")
        ax.set_ylim(18, 62)
        ax.set_xlim(0, 3 * P)
        ax2.set_ylim(-290, 290)
        ax2.set_yticks([-255, 0, 255])
        ax.tick_params(labelbottom=False)
        if k % 3 == 0:
            ax.set_ylabel("T (°C)")
            ax2.set_ylabel("PWM")
        if k >= 3:
            ax2.set_xlabel("t − t0 (s)")
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([], [], color=GREY, ls="--", lw=1.2, label="requested 40 + 16 sin"), Line2D([], [], color=BLUE, lw=1, label="T1 (rod base)"),
                        Line2D([], [], color="k", lw=1.5, label="TEC measured"), Line2D([], [], color=RED, lw=1.2, ls=(0, (4, 2)), label="TEC simulated"),
                        Line2D([], [], color="#2a6f97", lw=1, label="PWM (counts, ±255 dotted)")], loc="upper center", ncol=5, fontsize=7.5, frameon=False,
               bbox_to_anchor=(0.5, 1.0))
    fig.savefig(path, dpi=190, bbox_inches="tight")
    plt.close(fig)


def fig3(path, wins):
    """Spatial fits: ln amplitude, unwrapped phase and mean excess temperature against position, five periods, finite-rod curves."""
    fig, axs = plt.subplots(1, 3, figsize=(9.4, 3.5))
    xx = np.linspace(0, 0.106, 120)
    for w in wins:
        c = M.COLORS[w["P"]]
        wd, f, L = w["wd"], w["fin"], w["L"]
        x = w["x"] * 1000
        lab = f"{w['P']} s, {w['label']}, κ {f['kappa'] * 1e5:.2f}"
        axs[0].errorbar(x, np.log(wd["B"] / wd["B"][0]), yerr=wd["sB"] / wd["B"], fmt="o", ms=3.5, color=c, capsize=2, label=lab)
        lam = f["q"] + 1j * f["qp"]
        F = np.cosh(lam * (L - xx)) / np.cosh(lam * L)
        axs[0].plot(xx * 1000, np.log(np.abs(F)), color=c, lw=1.1)
        axs[1].errorbar(x, w["phi_u"] - w["phi_u"][0], yerr=wd["sphi"], fmt="o", ms=3.5, color=c, capsize=2)
        axs[1].plot(xx * 1000, np.angle(F), color=c, lw=1.1)
        pr = w["prof"]
        mu = pr["m"] * L
        axs[2].errorbar(x, (wd["a"] - w["t_room"]) / pr["theta0"], yerr=np.maximum(wd["sa"], 0.02) / pr["theta0"], fmt="o", ms=3.5, color=c, capsize=2)
        axs[2].plot(xx * 1000, np.cosh(mu * (1 - xx / L)) / np.cosh(mu), color=c, lw=1.1)
    axs[0].set_ylabel("ln [B(x) / B(0)]")
    axs[1].set_ylabel("φ(x) − φ(0) (rad)")
    axs[2].set_ylabel("[T̄(x) − T∞] / fitted value at x = 0")
    for a, t in zip(axs, ("(a) amplitude", "(b) unwrapped phase", "(c) mean profile")):
        a.set_xlabel("x from the T1 hole (mm)")
        a.set_title(t, fontsize=8.5, loc="left")
    axs[0].legend(fontsize=6.3, loc="lower left")
    fig.tight_layout()
    fig.savefig(path, dpi=190)
    plt.close(fig)


def fig2(path, wins, kw, nu):
    """Characteristic lengths of the five production windows with the curves of the shared kappa and nu."""
    rows = []
    for w in wins:
        f, pr = w["fin"], w["prof"]
        rows.append(dict(period=w["P"], q=f["q"], sq=f["sq"], qp=f["qp"], sqp=f["sqp"], color=M.COLORS[w["P"]], meets=0 if w["which"] == "last5" else 1, kapil=False,
                         m_mean=pr["m"], sm_mean=math.hypot(pr["sm_stat"], pr["sm_sys"]), source=f"{w['label']}, {w['P']} s"))
    RS.fig_length(path, rows, kw, nu, figsize=(9.4, 4.9), mean_label="1/m from each window's mean profile (triangles)")


def fig4(path, cp):
    """Matched 300 s run: boundary, downstream histories, and per-sensor amplitude ratio, phase difference and mean difference."""
    t, w, P = cp["t"], cp["w"], cp["P"]
    t1 = cp["win"][1]
    t0 = t1 - 3 * P
    sel = (t >= t0) & (t < t1)
    ss = (cp["t_sim"] >= t0) & (cp["t_sim"] < t1)
    cols, data = cp["cols"], cp["data"]
    fig = plt.figure(figsize=(9.4, 5.3))
    gs = fig.add_gridspec(2, 6, height_ratios=[1.25, 1], hspace=0.42, wspace=1.2)
    a = fig.add_subplot(gs[0, :3])
    a.plot(t[sel] - t0, cols["setpoint_C"][sel], color=GREY, ls="--", lw=1.1, label="requested")
    a.plot(t[sel] - t0, data["TEC_C"][sel], color="k", lw=1.4, label="TEC measured")
    a.plot(cp["t_sim"][ss] - t0, cp["tp"][ss], color=RED, ls=(0, (4, 2)), lw=1.1, label="TEC simulated")
    a.plot(t[sel] - t0, data["T1_C"][sel], color=BLUE, lw=1.1, label="T1 measured")
    a.plot(cp["t_sim"][ss] - t0, cp["rod"][ss, 0], color=RED, lw=1.1, label="T1 simulated")
    a.set_title("(a) boundary: simulation against measurement", fontsize=8.5, loc="left")
    a.set_ylabel("T (°C)")
    a.set_xlabel("t − t0 (s)")
    a.set_ylim(22, 68)
    a.legend(fontsize=6.5, ncol=3, loc="upper center")
    b = fig.add_subplot(gs[0, 3:])
    for i, c in ((2, "#2ca02c"), (4, "#8c564b")):
        ch = A.ROD[i]
        b.plot(t[sel] - t0, data[ch][sel], color=c, lw=1.5, label=f"T{i + 1} measured")
        b.plot(t[sel] - t0, cp["series"]["mean"][i] + cp["series"]["B"][i] * np.cos(w * t[sel] + cp["series"]["ph"][i]), color=BLUE, ls=(0, (1, 1.5)), lw=1.3,
               label="analytical" if i == 2 else None)
        b.plot(cp["t_sim"][ss] - t0, cp["rod"][ss, i], color=RED, ls=(0, (4, 2)), lw=1.1, label="simulated" if i == 2 else None)
    b.set_title("(b) downstream sensors T3 and T5", fontsize=8.5, loc="left")
    b.set_xlabel("t − t0 (s)")
    b.set_ylim(31, 43.5)
    b.legend(fontsize=6.5, ncol=2, loc="upper right")
    x = np.arange(5)
    for j, (key, ylabel, ref, title) in enumerate((("rB", "predicted / measured amplitude", 1.0, "(c) amplitude"), ("dphi", "predicted − measured phase (rad)", 0.0, "(d) phase"),
                                                   ("da", "predicted − measured mean (°C)", 0.0, "(e) mean"))):
        ax = fig.add_subplot(gs[1, 2 * j:2 * j + 2])
        ax.bar(x - 0.2, [s["ana"][key] for s in cp["sensors"]], 0.38, color=BLUE, label="analytical")
        ax.bar(x + 0.2, [s["num"][key] for s in cp["sensors"]], 0.38, color=RED, label="numerical")
        ax.axhline(ref, color="k", lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels([f"T{i + 1}" for i in x])
        ax.set_ylabel(ylabel, fontsize=7.5)
        ax.set_title(title, fontsize=8.5, loc="left")
        if key == "rB":
            ax.set_ylim(0.9, 1.05)
            ax.legend(fontsize=6.5, loc="upper right", ncol=2)
    fig.savefig(path, dpi=190, bbox_inches="tight")
    plt.close(fig)
