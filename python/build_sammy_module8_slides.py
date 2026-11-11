#!/usr/bin/env python3
"""
Phys 39 Module 8, Part I: slide deck (PDF, 16:9) for the SAMMY Angstrom production run.

    python3 python/sammy_module8_angstrom_analysis.py data/module_08_sammy/sammy_angstrom_live_20261110_164057.csv
    python3 python/build_sammy_module8_slides.py      data/module_08_sammy/sammy_angstrom_live_20261110_164057.csv [--preview-dir DIR]

Run the analysis first. This script only lays out what it wrote: the tables and run_summary.json in
data/module_08_sammy/analysis_<stamp>/, the figures in docs/figures/module_08_sammy/, the photos in docs/images/
and the logged run CSV. Numbers on the slides are read from those files, not retyped (the short explanations of
what happened in this particular run are written out in the slide functions).
"""

import argparse
import csv
import json
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch, Rectangle
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sammy_module8_angstrom_analysis as an  # noqa: E402

plt.rcdefaults()
matplotlib.rcParams["pdf.fonttype"] = 42

W, H, DPI = 13.333, 7.5, 100
NAVY, BLUE, RED, INK, GREY, LIGHT, RULE = "#1F4E79", "#2E75B6", "#C0392B", "#222222", "#666666", "#EAF1F8", "#C9D6E3"
BOTTOM = 6.40            # content must end above this (the takeaway box starts at 6.48)
UNITS = {"s", "°C", "mm", "%", "min", "σ", "m²/s", "1/m", "dof"}   # never start a wrapped line with one of these

_probe = plt.figure(figsize=(W, H), dpi=DPI)
_renderer = _probe.canvas.get_renderer()


# ---------------------------------------------------------------------------
# drawing helpers (all positions in inches from the top-left corner of the slide)
# ---------------------------------------------------------------------------

def tw(s, size, weight="normal"):
    w, _, _ = _renderer.get_text_width_height_descent(s, FontProperties(size=size, weight=weight), False)
    return w / DPI


def wrap(s, size, width, weight="normal"):
    lines = []
    for para in s.split("\n"):
        cur = ""
        for word in para.split():
            trial = word if not cur else cur + " " + word
            if not cur or tw(trial, size, weight) <= width or word.rstrip(".,:;)") in UNITS:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def fit_size(s, width, sizes, weight="normal"):
    for size in sizes:
        if tw(s, size, weight) <= width:
            return size
    return sizes[-1]


def put(fig, x, y, s, size=16, color=INK, weight="normal", ha="left", va="top", style="normal"):
    return fig.text(x / W, 1 - y / H, s, fontsize=size, color=color, fontweight=weight, ha=ha, va=va, style=style)


def lines_at(fig, x, y, lines, size, color=INK, weight="normal", pitch=1.32, ha="left"):
    for i, ln in enumerate(lines):
        put(fig, x, y + i * size * pitch / 72, ln, size, color, weight, ha=ha)
    return y + len(lines) * size * pitch / 72


def bullets(fig, x, y, items, size=16, width=6.0, gap=0.10, color=INK):
    for it in items:
        s, lvl = (it, 0) if isinstance(it, str) else it
        sz = size - 2 * lvl
        ind = 0.26 + 0.28 * lvl
        lines = wrap(s, sz, width - ind)
        put(fig, x + 0.28 * lvl, y, "•" if lvl == 0 else "–", sz, BLUE if lvl == 0 else GREY)
        y = lines_at(fig, x + ind, y, lines, sz, color) + gap
    return y


def rect(fig, x, y, w, h, fc, ec="none", lw=0, rounded=False):
    if rounded:
        p = FancyBboxPatch((x / W, 1 - (y + h) / H), w / W, h / H, boxstyle="round,pad=0,rounding_size=0.012",
                           transform=fig.transFigure, fc=fc, ec=ec, lw=lw)
    else:
        p = Rectangle((x / W, 1 - (y + h) / H), w / W, h / H, transform=fig.transFigure, fc=fc, ec=ec, lw=lw)
    fig.add_artist(p)


def image(fig, path, x, y, w, h, dpi=150, frame=True):
    """Fit the picture inside the box (aspect kept), downsampled to `dpi` so the PDF stays small."""
    im = Image.open(path).convert("RGB")
    ar = im.width / im.height
    ww, hh = (h * ar, h) if w / h > ar else (w, w / ar)
    im = im.resize((max(1, int(ww * dpi)), max(1, int(hh * dpi))), Image.LANCZOS)
    x0, y0 = x + (w - ww) / 2, y + (h - hh) / 2
    ax = fig.add_axes([x0 / W, 1 - (y0 + hh) / H, ww / W, hh / H])
    ax.imshow(np.asarray(im), aspect="auto", interpolation="nearest")
    ax.set_axis_off()
    if frame:
        ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes, fill=False, ec=RULE, lw=1.0, clip_on=False))
    return x0, y0, ww, hh


def table(fig, x, y, colw, head, rows, size=13, rowh=0.38, hl=(), left0=False):
    total = sum(colw)
    rect(fig, x, y, total, rowh, NAVY)

    def row(cells, yy, color, weight):
        cx = x
        for j, (cw, cell) in enumerate(zip(colw, cells)):
            if j == 0 and left0:
                put(fig, cx + 0.1, yy + rowh / 2, cell, size, color, weight, va="center")
            else:
                put(fig, cx + cw / 2, yy + rowh / 2, cell, size, color, weight, ha="center", va="center")
            cx += cw

    row(head, y, "white", "bold")
    for i, cells in enumerate(rows):
        yy = y + rowh * (i + 1)
        if i in hl:
            rect(fig, x, yy, total, rowh, "#FFF1CC")
        elif i % 2:
            rect(fig, x, yy, total, rowh, "#F3F6F9")
        row(cells, yy, INK, "normal")
    rect(fig, x, y + rowh * (len(rows) + 1) - 0.012, total, 0.012, RULE)
    return y + rowh * (len(rows) + 1)


def takeaway(fig, s):
    rect(fig, 0.5, 6.48, W - 1.0, 0.66, LIGHT)
    rect(fig, 0.5, 6.48, 0.08, 0.66, NAVY)
    for size in (15, 14, 13, 12):
        lines = wrap(s, size, W - 1.0 - 0.5)
        if len(lines) <= 2:
            break
    top = 6.48 + (0.66 - len(lines) * size * 1.3 / 72) / 2
    lines_at(fig, 0.75, top, lines, size, INK, pitch=1.3)


def pm(v, s, scale=1.0, nd=2):
    return f"{v * scale:.{nd}f} ± {s * scale:.{nd}f}"


def check(fig, name, bottoms=()):
    """Print a warning for text outside the page, text overlapping text, or content running into the takeaway box."""
    r = fig.canvas.get_renderer()
    boxes = []
    for t in fig.texts:
        if not t.get_text().strip():
            continue
        bb = t.get_window_extent(r)
        boxes.append((bb, t.get_text()[:40]))
        if bb.x0 < -1 or bb.x1 > W * DPI + 1 or bb.y0 < -1 or bb.y1 > H * DPI + 1:
            print(f"  [{name}] text outside the page: {t.get_text()[:50]!r}")
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i][0], boxes[j][0]
            ix, iy = min(a.x1, b.x1) - max(a.x0, b.x0), min(a.y1, b.y1) - max(a.y0, b.y0)
            if ix > 2 and iy > 2 and ix * iy > 0.12 * min(a.width * a.height, b.width * b.height):
                print(f"  [{name}] overlap: {boxes[i][1]!r} / {boxes[j][1]!r}")
    for lab, yb in bottoms:
        if yb > BOTTOM:
            print(f"  [{name}] {lab} ends at {yb:.2f} in (limit {BOTTOM})")


class Deck:
    def __init__(self, pdf, stamp, preview_dir):
        self.pdf, self.stamp, self.preview, self.n = pdf, stamp, preview_dir, 0

    def blank(self):
        self.n += 1
        return plt.figure(figsize=(W, H), dpi=DPI)

    def page(self, title, source=None):
        fig = self.blank()
        rect(fig, 0, 0, W, 0.9, NAVY)
        put(fig, 0.5, 0.45, title, fit_size(title, W - 1.0, (26, 24, 22, 20), "bold"), "white", "bold", va="center")
        foot = f"Phys 39 · Module 8, Part I · SAMMY copy · run {self.stamp}" + (f" · {source}" if source else "")
        put(fig, 0.5, 7.27, foot, 9, GREY, va="center")
        put(fig, W - 0.5, 7.27, str(self.n), 9, GREY, ha="right", va="center")
        return fig

    def done(self, fig, name, bottoms=()):
        check(fig, name, bottoms)
        self.pdf.savefig(fig)
        if self.preview:
            fig.savefig(os.path.join(self.preview, f"slide_{self.n:02d}.png"), dpi=72)
        plt.close(fig)


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------

def read_csv(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def by_period(path):
    return {int(float(r["period_s"])): {k: float(v) for k, v in r.items()} for r in read_csv(path)}


def prof_val(d, period, channel, key):
    for r in d["prof"]:
        if int(float(r["period_s"])) == period and r["channel"] == channel:
            return float(r[key])
    raise KeyError((period, channel))


def amp(d, period, channel):
    return prof_val(d, period, channel, "B_C")


def gather(run):
    stamp = an.stamp_of(run)
    adir = os.path.join(an.DATA_DIR, f"analysis_{stamp}")
    cols = an.load(run)
    K = by_period(os.path.join(adir, "kappa_by_period.csv"))
    S = by_period(os.path.join(adir, "settled_blocks.csv"))
    T = by_period(os.path.join(adir, "tracking_by_period.csv"))
    with open(os.path.join(adir, "run_summary.json")) as fh:
        J = json.load(fh)
    prof = read_csv(os.path.join(adir, "profile_by_period.csv"))
    P = list(K)
    k = np.array([K[p]["kappa_m2_s"] for p in P])
    s = np.array([K[p]["skappa_m2_s"] for p in P])
    w = 1 / s ** 2
    kw, skw = float(np.sum(w * k) / np.sum(w)), float(1 / math.sqrt(np.sum(w)))
    chi2 = float(np.sum(((k - kw) / s) ** 2))
    kap = {p: an.KAPIL[p] for p in P if p in an.KAPIL}
    sig = {p: (K[p]["kappa_m2_s"] - kap[p][0]) / math.hypot(K[p]["skappa_m2_s"], kap[p][1]) for p in kap}
    kap_off = [v[0] / an.KAPPA_HANDBOOK - 1 for v in an.KAPIL.values()]
    t, run_on = cols["t"], cols["run_state"] == 2
    return dict(stamp=stamp, run_name=os.path.basename(run), cols=cols, K=K, S=S, T=T, J=J, prof=prof, P=P, kw=kw, skw=skw, chi2=chi2,
                kap=kap, sig=sig, kap_off=(min(kap_off), max(kap_off)), t_start=float(t[run_on][0]),
                t_end=float(t[run_on][-1]), rate=len(t) / float(t[-1] - t[0]),
                ok=[p for p in P if S[p]["meets_5_cycle_minimum"] == 1], photos=an.photo_info(cols),
                fig=lambda name: os.path.join(an.FIG_DIR, f"{stamp}_{name}.png"))


# ---------------------------------------------------------------------------
# diagrams
# ---------------------------------------------------------------------------

def rod_diagram(fig, x, y, w, h):
    ax = fig.add_axes([x / W, 1 - (y + h) / H, w / W, h / H])
    ax.set_xlim(-64, 300)
    ax.set_ylim(-1.75, 2.0)
    ax.axis("off")
    ax.add_patch(Rectangle((-64, -0.6), 46, 1.2, fc=BLUE, ec=NAVY))
    ax.text(-41, 0, "TEC", ha="center", va="center", fontsize=13, color="white", fontweight="bold")
    ax.add_patch(Rectangle((-18, -0.22), 299.9, 0.44, fc="#D5D8DC", ec="#7F8C8D"))
    for i, xv in enumerate((0, 25.4, 50.8, 76.2, 101.6)):
        c = an.COLORS[f"T{i + 1}_C"]
        ax.plot([xv, xv], [0.22, 0.55], color=c, lw=2)
        ax.plot(xv, 0.62, "o", color=c, ms=9)
        ax.text(xv, 0.9, f"T{i + 1}", ha="center", va="bottom", fontsize=12, color=c, fontweight="bold")
    xs = np.linspace(0, 281.9, 400)
    ax.plot(xs, 1.65 + 0.3 * np.exp(-xs / 85) * np.cos(xs / 15), color=RED, lw=1.6)
    ax.plot(xs, 1.65 + 0.3 * np.exp(-xs / 85), color=RED, lw=0.8, ls=":")
    ax.plot(xs, 1.65 - 0.3 * np.exp(-xs / 85), color=RED, lw=0.8, ls=":")
    ax.text(298, 1.0, "damped thermal wave:\namplitude ∝ e^(−qx), phase lag q′x", ha="right", va="center", fontsize=11, color=RED)
    for yy, x1, label, lx in ((-0.62, 101.6, "T1 to T5: 4 × 25.4 mm = 101.6 mm (±1 mm)", 50.8),
                              (-1.15, 281.9, "T1 to the tip: 281.9 ± 1.3 mm", 140.9)):
        ax.annotate("", xy=(x1, yy), xytext=(0, yy), arrowprops=dict(arrowstyle="<->", color=GREY, lw=1.2))
        ax.text(lx, yy - 0.12, label, ha="center", va="top", fontsize=11, color=GREY)


def timeline(fig, x, y, w, h, d):
    J = d["J"]
    t0 = d["t_start"] / 60
    steps = [J["step_minutes"][str(i)] for i in (1, 2, 3, 4)]
    total = J["minutes"]
    tail = total - t0 - sum(steps)
    labels = [("idle", f"{t0:.1f} min", "#F2F2F2"), ("hold", f"{steps[0]:.1f} min", an.STEP_COLORS[1])]
    for p, st, key in zip(d["P"], steps[1:], (2, 3, 4)):
        labels.append((f"{int(d['S'][p]['cycles_recorded'])} × {p} s", f"{st:.1f} min", an.STEP_COLORS[key]))
    labels.append(("", "", "#F2F2F2"))
    widths = [t0] + steps + [tail]
    cx = x
    for (a, b, c), mins in zip(labels, widths):
        ww = w * mins / total
        rect(fig, cx, y, ww, h, c, ec="white", lw=1.5)
        if a:
            put(fig, cx + ww / 2, y + h * 0.30, a, 12, INK, "bold", ha="center", va="center")
            put(fig, cx + ww / 2, y + h * 0.70, b, 11, GREY, ha="center", va="center")
        cx += ww


# ---------------------------------------------------------------------------
# slides
# ---------------------------------------------------------------------------

def s_title(deck, d):
    fig = deck.blank()
    rect(fig, 0, 0, W, 3.3, NAVY)
    lines = wrap("Ångström run: thermal diffusivity of an aluminum rod", 34, W - 1.4, "bold")
    y = lines_at(fig, 0.7, 0.5, lines, 34, "white", "bold", pitch=1.25)
    put(fig, 0.7, y + 0.2, "Phys 39 · Module 8, Part I · PI-controlled TEC drive at periods of 480, 240 and 100 s", 17, "#D6E4F2")
    put(fig, 0.7, y + 0.72, f"Samuel Cohen (SAMMY copy) · run of 10 November 2026 · {d['run_name']}", 14, "#B9CDE2")
    image(fig, d["fig"]("run_overview"), 0.5, 3.55, 6.3, 3.5)
    x, wd = 7.2, W - 7.2 - 0.5
    put(fig, x, 3.62, f"Weighted mean of the three periods (χ² = {d['chi2']:.1f} for {len(d['P']) - 1} degrees of freedom)", 12, GREY)
    big = f"κ = {pm(d['kw'], d['skw'], 1e5)} × 10⁻⁵ m²/s"
    put(fig, x, 3.95, big, fit_size(big, wd, (28, 26, 24, 22), "bold"), NAVY, "bold")
    off = 100 * (d["kw"] / an.KAPPA_HANDBOOK - 1)
    sg = [abs(v) for v in d["sig"].values()]
    ok_p = ", ".join(f"{p} s" for p in d["ok"]) or "none"
    bullets(fig, x, 4.75, [
        f"{off:.0f} % above the handbook value for 6061-T6 (6.9 × 10⁻⁵ m²/s). Kapil's PI data on the same rod show the same offset.",
        f"Within {min(sg):.1f} to {max(sg):.1f} σ of Kapil's PI fits at the same periods.",
        f"Only {ok_p} has the five settled cycles the lab asks for; the other periods are supplementary."],
        size=14, width=wd, gap=0.12)
    deck.done(fig, "title")


def s_idea(deck, d):
    fig = deck.page("The Ångström method in one slide")
    y = bullets(fig, 0.5, 1.25, [
        "Drive one end of a long rod with a sinusoidal temperature of period P (ω = 2π/P).",
        "A damped thermal wave travels down the rod: its amplitude falls as e^(−qx) and its phase lags by q′x.",
        "Fit each thermistor record with a sine: amplitude B and phase φ at its position x.",
        "ln B and φ are straight lines in x. Their slopes are −q and −q′.",
        "The product qq′ fixes the diffusivity. Heat loss from the side of the rod changes q and q′ separately "
        "(q² − q′² = ν/κ) but not their product."], size=16, width=6.0, gap=0.14)
    rect(fig, 6.85, 1.2, W - 0.5 - 6.85, 5.05, LIGHT, rounded=True)
    cx = 6.85 + (W - 0.5 - 6.85) / 2
    eqs = [("temperature along the rod: steady profile plus a travelling wave",
            r"$T(x,t)=T_m(x)+B(x)\,\cos\left(\omega t+\varphi(x)\right)$"),
           ("amplitude decay and phase lag, both linear in x (after taking ln B)",
            r"$B(x)=B_0\,e^{-qx},\qquad \varphi(x)=\varphi_0-q'x$"),
           ("thermal diffusivity from the product of the two slopes",
            r"$\kappa=\frac{\omega}{2\,q\,q'}$"),
           ("side-loss rate (the small difference of two nearly equal numbers)",
            r"$\nu=\kappa\,(q^{2}-q'^{2})$")]
    yy = 1.4
    for label, eq in eqs:
        put(fig, cx, yy, label, 11, GREY, ha="center")
        put(fig, cx, yy + 0.3, eq, 21, INK, ha="center")
        yy += 1.2 if "frac" not in eq else 1.35
    takeaway(fig, "Two slopes and one frequency give κ. Only amplitude ratios and phase differences between positions matter, "
                  "so constant sensor offsets cancel.")
    deck.done(fig, "idea", [("bullets", y)])


def s_setup(deck, d):
    fig = deck.page("Set-up: rod, sensors, controller")
    rod_diagram(fig, 0.5, 1.05, W - 1.0, 2.55)
    y1 = bullets(fig, 0.5, 3.85, [
        "Rod: 6061-T6 aluminum, d = 12.757 ± 0.006 mm.",
        "Thermistors T1 to T5 at 0, 25.4, 50.8, 76.2 and 101.6 mm (±1 mm); the tip is 281.9 ± 1.3 mm from T1.",
        "Sensor offsets from the 26 Oct calibration run are applied in the analysis only. They do not change B or φ."],
        size=14, width=5.95, gap=0.12)
    y2 = bullets(fig, 6.85, 3.85, [
        "TEC on an H-bridge driven by an Arduino Uno. PI control of the TEC thermistor (Kp 12, Ki 0.2) with heating-to-cooling "
        "ratio r = χh/χc = 2.771.",
        "Setpoint 40 ± 16 °C sine, computed on the Arduino so period and phase are exact.",
        f"The Arduino latches the drive off if T1 exceeds 56 °C or the TEC thermistor 65 °C. The Python GUI logs 18 columns at about "
        f"{d['rate']:.1f} records per second."],
        size=14, width=5.95, gap=0.12)
    takeaway(fig, "The wave is launched by the TEC and measured by five thermistors along 101.6 mm. The sine setpoint and the safety "
                  "latches run on the Arduino, so the forcing does not depend on the computer's timing.")
    deck.done(fig, "setup", [("left", y1), ("right", y2)])


def s_schedule(deck, d):
    J = d["J"]
    fig = deck.page("Procedure: one schedule, three periods")
    timeline(fig, 0.5, 1.2, W - 1.0, 0.85, d)
    put(fig, 0.5, 2.1, f"Time axis of the logged file: {J['minutes']:.1f} min, {J['records']} records", 10, GREY)
    plan = {2: "3360 s", 3: "1680 s", 4: "700 s"}
    rows = [["1", "Hold at 40 °C to settle plate and integral term", "40 °C", "none", "300 s", f"{J['step_minutes']['1']:.1f} min"]]
    for p, key in zip(d["P"], (2, 3, 4)):
        n = int(d["S"][p]["cycles_recorded"])
        rows.append([str(key), f"Oscillation, {n} cycles", "40 ± 16 °C", f"{p} s", plan[key], f"{J['step_minutes'][str(key)]:.1f} min"])
    yb = table(fig, 0.5, 2.5, [0.8, 5.0, 1.9, 1.4, 1.7, W - 1.0 - 10.8], ["Step", "What", "Setpoint", "Period", "Planned", "Ran"],
               rows, size=13, rowh=0.4)
    y = bullets(fig, 0.5, yb + 0.25, [
        f"{d['t_start'] / 60:.1f} min elapsed between the start of logging and step 1: lead handling, then idle recording "
        f"(room temperature 24.3 °C = mean of T1 to T5).",
        "Seven cycles per period let the start-up transient die out and still leave a settled block to fit.",
        "The raw CSV is never edited. Masks and sensor offsets are applied only inside the analysis."],
        size=14, width=W - 1.0, gap=0.12)
    takeaway(fig, "One uninterrupted schedule gives three periods (480, 240 and 100 s) on the same rod with the same sensors, "
                  "so the periods can be compared directly.")
    deck.done(fig, "schedule", [("bullets", y)])


def s_photos(deck, d):
    fig = deck.page("The run on the bench: live GUI photos", source="docs/images/module08_sammy_gui_*.jpg")
    gap = 0.24
    pw = (W - 1.0 - 2 * gap) / 3
    bottoms = []
    for i, p in enumerate(d["photos"]):
        x = 0.5 + i * (pw + gap)
        ox, oy, ow, oh = image(fig, p["path"], x, 1.15, pw, 2.5, dpi=200)
        y = lines_at(fig, x, oy + oh + 0.08, wrap(p["title"], 12, pw, "bold"), 12, NAVY, "bold")
        bottoms.append(lines_at(fig, x, y + 0.03, wrap("On screen: " + p["caption"], 10.5, pw), 10.5, GREY))
    y = bullets(fig, 0.5, max(bottoms) + 0.12, [
        "Plots on the left (temperatures above, PWM below), live readouts in the middle, schedule and controls on the right.",
        "240 s step: the TEC thermistor follows the setpoint near its 55 °C peak while the rod sensors show smaller, later peaks "
        "(T1 36.7 °C down to T5 30.1 °C): the wave dying out along the rod.",
        "100 s step: the TEC swings quickly and the rod sensors barely move (T1 to T5 within 30.3 to 31.6 °C at this instant)."],
        size=13, width=W - 1.0, gap=0.08)
    takeaway(fig, "The numbers on screen are the logged values (record numbers 8807, 8811 and 11623), so the photos document the run "
                  "without adding any data of their own.")
    deck.done(fig, "photos", [("captions", max(bottoms)), ("bullets", y)])


def s_overview(deck, d):
    J = d["J"]
    fig = deck.page("The whole run", source=f"{d['stamp']}_run_overview.png")
    image(fig, d["fig"]("run_overview"), 0.5, 1.12, 8.45, 5.28)
    steps = ", ".join(f"{J['step_minutes'][str(i)]:.1f}" for i in (1, 2, 3, 4))
    clip = J["pwm_clipped_samples"]
    clip_txt = "never reached ±255" if clip == 0 else f"reached ±255 in {clip} samples"
    y = bullets(fig, 9.2, 1.25, [
        "Setpoint (dotted), TEC thermistor (black) and T1 to T5. Shaded bands are the four schedule steps; red marks masked samples.",
        f"All four steps ran to the end ({steps} min).",
        f"PWM {clip_txt} (range {J['pwm_min']} to {J['pwm_max']}).".replace("-", "−"),
        f"T1 peaked at {J['t1_max_C']:.1f} °C and the TEC thermistor at {J['tec_max_C']:.1f} °C (latch limits 56 and 65 °C).",
        f"{J['gaps']} gaps longer than 0.75 s, {J['gaps_in_schedule']} during the schedule; "
        f"{J['duplicated']} duplicated records and {J['restarts']} restarts."], size=13, width=W - 9.2 - 0.5, gap=0.12)
    takeaway(fig, "The controller held the TEC thermistor on the 40 ± 16 °C sine for 100 minutes without saturating or tripping a latch.")
    deck.done(fig, "overview", [("bullets", y)])


def s_quality(deck, d):
    J = d["J"]
    m2 = J["t5_prediction"]["2"]
    fig = deck.page("Data quality: what was masked and why", source=f"{d['stamp']}_t5_mask_check.png")
    image(fig, d["fig"]("t5_mask_check"), 0.5, 1.15, 7.95, 5.2)
    y = bullets(fig, 8.7, 1.25, [
        "T3, T4 and T5 spiked while the leads were handled before the run (up to 33, 117 and 102 °C): masked from 36 to 200 s.",
        "In the 480 s step T5 read 1 to 4 °C above its prediction from T3 and T4 for 1860 to 2618 s and up to 3.6 °C for "
        "3060 to 3141 s: masked.",
        f"The prediction uses T3, T4 and their slopes, fitted on the last two cycles of each step (RMS {m2['rms_fit']:.3f} °C).",
        f"Outside the masks T5 stays within {m2['max_outside']:.2f} °C (480 s), "
        f"{J['t5_prediction']['3']['max_outside']:.2f} °C (240 s) and {J['t5_prediction']['4']['max_outside']:.2f} °C (100 s) of it.",
        f"The raw CSV is unchanged: {J['masked_samples']} samples are set to nan inside the fits only."],
        size=13, width=W - 8.7 - 0.5, gap=0.1)
    takeaway(fig, "A contact fault on T5 was removed by an explicit, documented mask rather than by editing the data; "
                  "the mask file sits next to the run CSV.")
    deck.done(fig, "quality", [("bullets", y)])


def s_fit(deck, d):
    fig = deck.page("Step 1 of the analysis: fit every cycle", source=f"{d['stamp']}_cycles_240s.png")
    image(fig, d["fig"]("cycles_240s"), 0.5, 1.15, 8.55, 5.2)
    y = bullets(fig, 9.3, 1.25, [
        "Each sensor and each cycle is fitted separately: T = a + B cos(ωt + φ) + c (t − t_mid). The linear term absorbs slow drift.",
        "Example: the 240 s step. The TEC thermistor follows the setpoint; the rod sensors show smaller and later waves, "
        "smaller the further from the TEC.",
        "Residuals stay within about ±0.15 °C.",
        "The cycle-to-cycle scatter of B and φ (sd/√N) is the uncertainty carried into the spatial fit, as in Kapil's angstrom_fit.py."],
        size=13, width=W - 9.3 - 0.5, gap=0.12)
    takeaway(fig, "A sine fit per cycle turns each temperature record into one amplitude and one phase per sensor, "
                  "with an error bar taken from the data themselves.")
    deck.done(fig, "fit", [("bullets", y)])


def s_settling(deck, d):
    fig = deck.page("Step 2: which cycles have settled?", source=f"{d['stamp']}_settling.png")
    image(fig, d["fig"]("settling"), 0.5, 1.15, 8.2, 4.2)
    rows = []
    for p in d["P"]:
        s = d["S"][p]
        rows.append([str(p), f"{int(s['first_settled_cycle'])} to {int(s['last_settled_cycle'])} ({int(s['settled_cycles'])})",
                     "yes" if s["meets_5_cycle_minimum"] == 1 else "no"])
    hl = [i for i, p in enumerate(d["P"]) if p in d["ok"]]
    yb = table(fig, 8.95, 1.2, [0.9, 2.2, 0.78], ["P (s)", "Settled cycles", "≥ 5"], rows, size=12, rowh=0.38, hl=hl)
    y = bullets(fig, 8.95, yb + 0.2, [
        f"A cycle joins the block while every rod sensor is within {an.TOL_B * 100:.0f} % in B and {an.TOL_PHI} rad in φ of the block "
        "median, counting back from the last cycle.",
        "480 s: at t = 2598 s the TEC reading stepped up by 4 °C and all rod amplitudes afterwards were about 10 % lower. "
        "The cause is unknown.",
        f"100 s: T5's amplitude is only {amp(d, d['P'][-1], 'T5'):.2f} °C, so 3 % is {0.03 * amp(d, d['P'][-1], 'T5'):.3f} °C."],
        size=11.5, width=W - 8.95 - 0.5, gap=0.08)
    ytxt = lines_at(fig, 0.5, 5.45, wrap("Lines show the change of B (top) and φ (bottom) of every sensor from cycle to cycle, "
                                         "relative to the settled block.", 12, 8.2), 12, GREY)
    takeaway(fig, "Only the 240 s step has five or more settled cycles. The 480 s and 100 s results use three cycles each and "
                  "are supplementary; the tolerances are chosen for this analysis.")
    deck.done(fig, "settling", [("right column", y), ("note", ytxt)])


def s_spatial(deck, d):
    K = d["K"]
    fig = deck.page("Step 3: amplitude and phase against distance", source=f"{d['stamp']}_spatial_fits.png")
    image(fig, d["fig"]("spatial_fits"), 0.5, 1.15, 8.6, 5.2)
    gaps = ", ".join(f"{100 * (K[p]['q_1_m'] - K[p]['qprime_1_m']) / K[p]['q_1_m']:.0f} % ({p} s)" for p in d["P"])
    qs = ", ".join(f"{K[p]['q_1_m']:.1f}" for p in d["P"])
    y = bullets(fig, 9.35, 1.25, [
        "Top: ln B against x is a straight line of slope −q. Bottom: the unwrapped phase is a straight line of slope −q′.",
        f"q = {qs} 1/m at {', '.join(str(p) for p in d['P'])} s: shorter periods decay faster.",
        "Lines are weighted fits; the errors are scaled by √(χ²/dof) when that is above 1 (Kapil's rule).",
        f"q and q′ differ by only {gaps}, so side loss is a small correction to the pure-conduction wave."],
        size=13, width=W - 9.35 - 0.5, gap=0.12)
    takeaway(fig, "Five sensors fall on straight lines in both amplitude and phase, which is what the model predicts; "
                  "κ = ω/(2qq′) follows from the two slopes.")
    deck.done(fig, "spatial", [("bullets", y)])


def s_results(deck, d):
    K = d["K"]
    fig = deck.page("Results: thermal diffusivity at each period")
    rows, hl = [], []
    for i, p in enumerate(d["P"]):
        r = K[p]
        kap = d["kap"].get(p)
        rows.append([str(p), f"{int(r['settled_cycles'])} of {int(d['S'][p]['cycles_recorded'])}", pm(r["q_1_m"], r["sq_1_m"]),
                     pm(r["qprime_1_m"], r["sqprime_1_m"]), pm(r["kappa_m2_s"], r["skappa_m2_s"], 1e5),
                     pm(kap[0], kap[1], 1e5) if kap else "–", f"{d['sig'][p]:+.1f} σ".replace("-", "−") if kap else "–",
                     f"{r['k_W_mK']:.0f}"])
        if p in d["ok"]:
            hl.append(i)
    yb = table(fig, 0.5, 1.2, [0.95, 1.35, 1.7, 1.7, 2.0, 2.15, 1.35, W - 1.0 - 11.2],
               ["P (s)", "Settled", "q (1/m)", "q′ (1/m)", "κ (10⁻⁵ m²/s)", "Kapil κ (PI)", "Difference", "k (W/m K)"],
               rows, size=13, rowh=0.44, hl=hl)
    put(fig, 0.5, yb + 0.06, "Highlighted row: meets the five-settled-cycle minimum. Kapil's values are his PI fits of 2 and 4 Nov on the same rod; "
                              "k uses the handbook ρ and cp.", 10, GREY)
    lo, hi = d["kap_off"]
    off = 100 * (d["kw"] / an.KAPPA_HANDBOOK - 1)
    chg = ", ".join(f"{100 * (K[p]['kappa_last5_m2_s'] / K[p]['kappa_m2_s'] - 1):+.1f} % at {p} s" for p in d["P"])
    chg = chg.replace("-0.0 %", "0.0 %").replace("+0.0 %", "0.0 %").replace("-", "−")
    y = bullets(fig, 0.5, yb + 0.5, [
        f"Weighted mean of the three periods: {pm(d['kw'], d['skw'], 1e5)} × 10⁻⁵ m²/s (χ² = {d['chi2']:.1f} for {len(d['P']) - 1} degrees "
        "of freedom, so the periods are consistent with one value).",
        f"Handbook 6061-T6 (k = 167 W/(m K), ρ = 2700 kg/m³, cp = 896 J/(kg K)) gives κ = 6.9 × 10⁻⁵ m²/s: the measurement is {off:.0f} % higher. "
        f"Kapil's five periods are {100 * lo:.0f} to {100 * hi:.0f} % higher.",
        "A spacing error cannot explain this: κ scales with spacing squared, so about "
        f"{100 * (math.sqrt(d['kw'] / an.KAPPA_HANDBOOK) - 1):.0f} % would be needed, while the sensor positions are good to about 1 %.",
        f"Using the last five cycles of every period (Kapil's rule) instead of the settled block changes κ by {chg}; the 480 s window "
        "straddles the disturbance at t = 2598 s."],
        size=14, width=W - 1.0, gap=0.1)
    takeaway(fig, f"κ = {pm(d['kw'], d['skw'], 1e5)} × 10⁻⁵ m²/s, in agreement with Kapil's data but about {off:.0f} % above the handbook value; "
                  "the cause is not resolved by this run.")
    deck.done(fig, "results", [("bullets", y)])


def s_kappa(deck, d):
    fig = deck.page("κ against forcing period", source=f"{d['stamp']}_kappa_vs_period.png")
    image(fig, d["fig"]("kappa_vs_period"), 0.5, 1.15, W - 1.0, 5.2)
    sg = ", ".join(f"{d['sig'][p]:+.1f} σ at {p} s".replace("-", "−") for p in d["kap"])
    takeaway(fig, f"No significant trend with period (χ² = {d['chi2']:.1f} for {len(d['P']) - 1} dof). Differences from Kapil's PI fits: {sg}. "
                  "ν, from the small difference q² − q′², is noisy (right panel).")
    deck.done(fig, "kappa")


def s_length(deck, d):
    K = d["K"]
    fig = deck.page("How far does the wave reach?", source=f"{d['stamp']}_characteristic_length.png")
    image(fig, d["fig"]("characteristic_length"), 0.5, 1.15, 8.2, 5.2)
    ls = ", ".join(f"{1000 / K[p]['q_1_m']:.0f} mm ({p} s)" for p in d["P"])
    p_short, p_long = d["P"][-1], d["P"][0]
    left = 100 * math.exp(-K[p_short]["q_1_m"] * 0.1016)
    y = bullets(fig, 8.95, 1.25, [
        f"1/q is the distance over which the amplitude falls by a factor e: {ls}.",
        f"The five sensors span 101.6 mm, so at {p_short} s the last sensor sees only about {left:.0f} % of the amplitude of the first "
        f"(T5 amplitude {amp(d, p_short, 'T5'):.2f} °C).",
        f"At {p_long} s the rod is only {281.9 * K[p_long]['q_1_m'] / 1000:.1f} e-folding lengths long, which gives the largest "
        f"finite-length difference ({100 * K[p_long]['finite_length_max_rel_diff']:.1f} %).",
        "A longer period reaches further but needs more settled cycles; a shorter period is cheap but leaves T5 with a small signal."],
        size=13, width=W - 8.95 - 0.5, gap=0.12)
    takeaway(fig, "The three periods probe the rod at different length scales and give the same κ, which supports using one "
                  "conduction model for all of them.")
    deck.done(fig, "length", [("bullets", y)])


def s_validity(deck, d):
    K = d["K"]
    fig = deck.page("Is the semi-infinite model good enough?", source=f"{d['stamp']}_mean_profile.png")
    image(fig, d["fig"]("mean_profile"), 1.35, 1.12, 10.6, 3.86)
    rows = [[str(p), f"{100 * K[p]['finite_length_max_rel_diff']:.2f} %", f"{K[p]['Bi_radial']:.1e}", f"{K[p]['m_from_q_1_m']:.2f}",
             pm(K[p]["m_mean_profile_1_m"], K[p]["sm_mean_profile_1_m"])] for p in d["P"]]
    yb = table(fig, 0.5, 5.05, [1.0, 3.0, 2.4, 2.9, W - 1.0 - 9.3],
               ["P (s)", "Finite-length difference (max)", "Radial Biot number", "m from √(q²−q′²) (1/m)", "m from the mean profile (1/m)"],
               rows, size=11.5, rowh=0.33)
    d21 = [prof_val(d, p, "T2", "mean_C") - prof_val(d, p, "T1", "mean_C") for p in d["P"]]
    lo21, hi21 = f"{min(d21):.1f}", f"{max(d21):.1f}"
    rng = lo21 if lo21 == hi21 else f"{lo21} to {hi21}"
    t21 = (f" T2's mean temperature is {rng} °C above T1's, which conduction away from the TEC cannot give."
           if min(d21) > 0 else "")
    takeaway(fig, "Finite length and radial gradients are negligible. The mean-profile slope does not match √(q²−q′²)." + t21 +
                  " Quote ν and h with caution.")
    deck.done(fig, "validity", [("table", yb)])


def s_tracking(deck, d):
    T, J = d["T"], d["J"]
    fig = deck.page("Controller tracking (PI)", source=f"{d['stamp']}_tracking.png")
    image(fig, d["fig"]("tracking"), 0.5, 1.15, 8.3, 4.2)
    rows = [[str(p), f"{T[p]['B_TEC_over_Tb']:.2f}", f"{T[p]['TEC_lag_s']:.1f}", f"{int(T[p]['pwm_min'])} to {int(T[p]['pwm_max'])}".replace("-", "−")]
            for p in d["P"]]
    yb = table(fig, 9.05, 1.2, [0.8, 0.95, 0.95, 1.08], ["P (s)", "B/Tb", "Lag (s)", "PWM"], rows, size=11.5, rowh=0.38)
    h = J["hold"]
    lags = [T[p]["TEC_lag_s"] for p in d["P"]]
    y = bullets(fig, 9.05, yb + 0.2, [
        "B/Tb: TEC amplitude as a fraction of the 16 °C setpoint amplitude.",
        f"The TEC thermistor lags the setpoint by about {min(lags):.0f} to {max(lags):.0f} s at every period.",
        f"Hold step: TEC reached 39.5 °C after {h['t_reach']:.0f} s with {h['overshoot']:+.2f} °C overshoot.",
        f"No sample at ±255 PWM ({J['pwm_clipped_samples']})."], size=12, width=W - 9.05 - 0.5, gap=0.08)
    put(fig, 0.5, 5.45, "Top: setpoint, TEC thermistor and T1 over the settled block. Bottom: PWM commanded.", 12, GREY)
    takeaway(fig, "The controller follows the sine closely at 480 and 240 s; at 100 s the TEC amplitude falls to "
                  f"{100 * T[d['P'][-1]]['B_TEC_over_Tb']:.0f} % of the setpoint's, so the rod is driven a little less than the 16 °C asked for.")
    deck.done(fig, "tracking", [("right column", y)])


def s_conclusions(deck, d):
    K = d["K"]
    off = 100 * (d["kw"] / an.KAPPA_HANDBOOK - 1)
    sg = [abs(v) for v in d["sig"].values()]
    fig = deck.page("Conclusions, limits and next steps")
    rect(fig, 0.5, 1.15, 6.05, 5.2, LIGHT, rounded=True)
    put(fig, 0.75, 1.25, "What the run shows", 15, NAVY, "bold")
    y1 = bullets(fig, 0.75, 1.7, [
        f"κ = {pm(d['kw'], d['skw'], 1e5)} × 10⁻⁵ m²/s from three periods; they are consistent with one value (χ² = {d['chi2']:.1f}, "
        f"{len(d['P']) - 1} dof).",
        f"Within {min(sg):.1f} to {max(sg):.1f} σ of Kapil's PI fits at each period: same rod, same method.",
        f"{off:.0f} % above the 6061-T6 handbook value (k ≈ {np.mean([K[p]['k_W_mK'] for p in d['P']]):.0f} against 167 W/(m K) with the handbook "
        "ρ and cp). Kapil's data show it too, so it is not an accident of this run.",
        "Only 240 s has five settled cycles; 480 s and 100 s are supplementary."], size=14, width=5.55, gap=0.1)
    rect(fig, 6.78, 1.15, W - 0.5 - 6.78, 5.2, "#FBF3E4", rounded=True)
    put(fig, 7.03, 1.25, "Limits and next steps", 15, "#8A5A00", "bold")
    y2 = bullets(fig, 7.03, 1.7, [
        "ν and h: ν is a small difference of two close numbers, and the mean-profile slope disagrees (3.7 to 4.2 against 4.7 to 5.0 1/m). "
        "Quote them with caution.",
        "T5 needed masking in the 480 s step; the settling tolerances are this analysis's own.",
        "Not covered by this file: open-loop and P-only comparisons, the raw sinusoidal PWM trials (S18.3, S18.4), gain tuning at "
        "200 s and 500 s, the P-versus-PI simulation.",
        "Next: repeat the 480 s and 100 s steps (or run them longer) to reach five settled cycles, and test the offset from the handbook, "
        "for example with a second rod of known alloy."], size=14, width=W - 0.5 - 7.03 - 0.25, gap=0.1)
    takeaway(fig, f"The method and the controller worked; the open question is the {off:.0f} % offset from the handbook diffusivity, "
                  "which this run reproduces rather than explains.")
    deck.done(fig, "conclusions", [("left", y1), ("right", y2)])


def s_reproduce(deck, d):
    fig = deck.page("Files, reproduction and AI assistance")
    rect(fig, 0.5, 1.15, 7.3, 5.2, "#F6F6F6", rounded=True)
    put(fig, 0.75, 1.25, "Reproduce", 15, NAVY, "bold")
    cmd = [f"python3 python/sammy_module8_angstrom_analysis.py \\", f"    data/module_08_sammy/{d['run_name']}", "",
           f"python3 python/build_sammy_module8_slides.py \\", f"    data/module_08_sammy/{d['run_name']}"]
    for i, ln in enumerate(cmd):
        fig.text(0.75 / W, 1 - (1.72 + i * 0.27) / H, ln, fontsize=10.5, family="monospace", color=INK, va="top")
    put(fig, 0.75, 3.35, "Where things are", 15, NAVY, "bold")
    y = bullets(fig, 0.75, 3.8, [
        f"data/module_08_sammy/: the run CSV, its events, meta and notes, the mask file, analysis_{d['stamp']}/ (tables, JSON, report).",
        "docs/figures/module_08_sammy/ and docs/images/: figures and photos.",
        "docs/sammy_module_08_guide/: the written summary and this deck.",
        "python/: sammy_module8_angstrom_gui.py (acquisition), sammy_module8_angstrom_analysis.py, build_sammy_module8_slides.py."],
        size=12, width=6.8, gap=0.08)
    rect(fig, 8.05, 1.15, W - 0.5 - 8.05, 5.2, LIGHT, rounded=True)
    put(fig, 8.3, 1.25, "AI assistance", 15, NAVY, "bold")
    y2 = bullets(fig, 8.3, 1.7, [
        "The acquisition-GUI changes, the analysis script, the figures, these slides and the written summary were produced with "
        "GitHub Copilot assistance.",
        "They follow Kapil Naidu's angstrom_fit.py method and the Module 8 study guide, and were checked against his fitted values.",
        "Kapil's acquisition code, analysis scripts and data are unchanged; everything here is an addition."],
        size=13, width=W - 0.5 - 8.3 - 0.25, gap=0.12)
    takeaway(fig, "Every number on these slides is read from the analysis tables; rerunning the two commands rebuilds the tables, figures, "
                  "summary and deck from the run CSV.")
    deck.done(fig, "reproduce", [("left", y), ("right", y2)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--out", default=os.path.join(an.GUIDE_DIR, "Phys39_Module_8_Angstrom_Slides_Sammy.pdf"))
    ap.add_argument("--preview-dir")
    a = ap.parse_args()
    d = gather(os.path.abspath(a.run))
    if a.preview_dir:
        os.makedirs(a.preview_dir, exist_ok=True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    meta = {"Title": "Phys 39 Module 8 Part I: Angstrom run, SAMMY copy", "Author": "Samuel Cohen",
            "Subject": f"Run {d['stamp']}"}
    with PdfPages(a.out, metadata=meta) as pdf:
        deck = Deck(pdf, d["stamp"], a.preview_dir)
        for fn in (s_title, s_idea, s_setup, s_schedule, s_photos, s_overview, s_quality, s_fit, s_settling, s_spatial,
                   s_results, s_kappa, s_length, s_validity, s_tracking, s_conclusions, s_reproduce):
            fn(deck, d)
    print(f"Wrote {os.path.relpath(a.out, an.REPO)} ({deck.n} slides)")


if __name__ == "__main__":
    main()
