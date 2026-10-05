#!/usr/bin/env python3
"""
Phys 39 Module 4. Naidu / Cohen

Recompute the open-loop steady-state table directly from the raw log, so that
every number can be traced to measured samples by a documented method.

    python3 python/steady_state_from_raw.py     (run from the repository root)

INPUT   data/module_04/full_run.csv         the raw Module 4 log
        data/module_04/steady_state.csv     the table A2 was built from,
                                            read only, for comparison

OUTPUT  data/module_04/steady_state_from_raw.csv
        a comparison printed to the console

WHY THIS EXISTS

steady_state.csv was filled in during an earlier session. Eight of its ten
values are described as exponential-fit asymptotes, but the fitting window was
not recorded, and the heating values sit within 0.02 C of the fitted line. For
the runs that had not settled, the asymptote moves by up to about 1.3 C
depending on which window is fitted, so a single value per point hides a large
analysis choice. This script reports, for every step actually present in the
log:

  final_minute_C      mean of the last 60 s of the run, a measured reading
  drift_C_per_min     linear slope over that minute
  settled             whether that drift is within the 0.16 C noise criterion
                      the module specifies; if not, the run had not reached
                      steady state and final_minute_C is a lower bound in the
                      direction of travel
  asym_all/200/150/120_C
                      exponential-fit asymptote using the whole run, or only
                      its last 200, 150, 120 s: the spread across these is the
                      honest uncertainty of any single extrapolated value

It does not overwrite steady_state.csv.
"""

import csv
import importlib.util
import os
import sys

import numpy as np

RAW = "data/module_04/full_run.csv"
SUBMITTED = "data/module_04/steady_state.csv"
OUT = "data/module_04/steady_state_from_raw.csv"
NOISE_CRITERION = 0.16      # C per minute, the module's steady-state threshold
FINAL_WINDOW = 60.0         # s
FIT_WINDOWS = (None, 200.0, 150.0, 120.0)

# The exponential fit lives in estimate_tau.py; reuse it rather than copy it.
_spec = importlib.util.spec_from_file_location(
    "estimate_tau", os.path.join(os.path.dirname(__file__), "estimate_tau.py"))
_et = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_et)
fit_exponential = _et.fit_exponential


def load():
    if not os.path.exists(RAW):
        sys.exit(f"{RAW} not found. Run from the repository root.")
    rows = list(csv.DictReader(open(RAW, newline="")))
    t = np.array([float(r["time_s"]) for r in rows])
    T = np.array([float(r["temperature_C"]) for r in rows])
    p = np.array([int(float(r["pwm"])) for r in rows])
    h = np.array([int(r["heat_cool"]) for r in rows])
    return t, T, p, h


def longest_blocks(t, p, h, min_span=30.0):
    """{(pwm, heat): (i0, i1)} for the longest contiguous run of each command.
    Typing a new value logs a few one-sample intermediate commands; those are
    far shorter than min_span and are ignored."""
    out, i = {}, 0
    while i < len(t):
        j = i
        while j + 1 < len(t) and p[j + 1] == p[i] and h[j + 1] == h[i]:
            j += 1
        k = (int(p[i]), int(h[i]))
        if t[j] - t[i] >= min_span:
            if k not in out or (t[j] - t[i]) > (t[out[k][1]] - t[out[k][0]]):
                out[k] = (i, j)
        i = j + 1
    return out


def submitted_values():
    vals = {}
    if not os.path.exists(SUBMITTED):
        return vals
    for r in csv.DictReader(open(SUBMITTED, newline="")):
        pwm = int(float(r["pwm"]))
        heat = 1 if (r["direction"] == "heat" or pwm == 0) else 0
        vals[(pwm, heat)] = (float(r["steady_c"]), r.get("notes", ""))
    return vals


def line(points):
    x = np.array([q[0] for q in points], float)
    y = np.array([q[1] for q in points], float)
    m, b = np.polyfit(x, y, 1)
    r = y - (m * x + b)
    return m, b, float(np.sqrt(np.mean(r ** 2)))


def main():
    t, T, p, h = load()
    blocks = longest_blocks(t, p, h)
    sub = submitted_values()

    records = []
    for (pwm, heat), (a, b) in sorted(blocks.items(),
                                      key=lambda kv: (kv[0][1], kv[0][0])):
        if pwm in (110,):       # the opening 98 s drive to 4.9 C, not a point
            continue
        ts, Ts = t[a:b + 1], T[a:b + 1]
        u = pwm if heat else -pwm
        f = ts >= ts[-1] - FINAL_WINDOW
        final = float(Ts[f].mean())
        drift = float(np.polyfit(ts[f], Ts[f], 1)[0] * 60.0)
        asym = []
        for w in FIT_WINDOWS:
            m = np.ones_like(ts, bool) if w is None else ts >= ts[-1] - w
            _, tinf, _ = fit_exponential(ts[m] - ts[m][0], Ts[m])
            asym.append(float(tinf))
        records.append({
            "u": u, "pwm": pwm, "heat": heat,
            "span_s": float(ts[-1] - ts[0]),
            "final": final, "drift": drift,
            "settled": abs(drift) <= NOISE_CRITERION,
            "asym": asym,
            "submitted": sub.get((pwm, heat), (None, ""))[0],
        })

    print(f"Steady-state table recomputed from {RAW}\n")
    hdr = (f"{'u':>5} {'span':>5} {'final 60 s':>10} {'drift/min':>9} "
           f"{'settled':>7} | {'fit all':>7} {'200 s':>6} {'150 s':>6} "
           f"{'120 s':>6} {'spread':>6} | {'submitted':>9}")
    print(hdr)
    print("-" * len(hdr))
    for r in sorted(records, key=lambda r: r["u"]):
        spread = max(r["asym"]) - min(r["asym"])
        s = "" if r["submitted"] is None else f"{r['submitted']:9.2f}"
        print(f"{r['u']:+5d} {r['span_s']:5.0f} {r['final']:10.2f} "
              f"{r['drift']:+9.3f} {'yes' if r['settled'] else 'NO':>7} | "
              + " ".join(f"{x:{7 if i == 0 else 6}.2f}"
                         for i, x in enumerate(r["asym"]))
              + f" {spread:6.2f} | {s}")

    missing = [k for k in sub if k not in blocks]
    if missing:
        print("\nIn steady_state.csv but with no run in the raw log:")
        for k in missing:
            print(f"   {'heat' if k[1] else 'cool'} {k[0]}: {sub[k][0]:.2f} C  "
                  f"({sub[k][1]})")

    heat = [r for r in records if r["heat"] or r["pwm"] == 0]
    cool = [r for r in records if not r["heat"] or r["pwm"] == 0]
    print("\nSlopes, using only points present in the raw log:")
    for label, key in (("final 60 s, measured", "final"),
                       ("asymptote, last 200 s", 1),
                       ("asymptote, whole run", 0)):
        get = (lambda r: r["final"]) if key == "final" else \
              (lambda r, k=key: r["asym"][k])
        mh, bh, rh = line([(r["u"], get(r)) for r in heat])
        mc, bc, rc = line([(r["u"], get(r)) for r in cool])
        ratio = mh / mc
        print(f"   {label:>24}: m_h {mh:.4f} (rms {rh:.3f}), m_c {mc:.4f} "
              f"(rms {rc:.3f}), r {ratio:.3f}, Qj/Qp {(ratio-1)/(ratio+1):.3f}")
    print(f"   {'as submitted in A2':>24}: m_h 0.5013 (rms 0.010), m_c 0.1809 "
          f"(rms 0.138), r 2.771, Qj/Qp 0.470")

    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["u", "span_s", "final_minute_C", "drift_C_per_min",
                    "settled", "asym_all_C", "asym_200s_C", "asym_150s_C",
                    "asym_120s_C", "submitted_C"])
        for r in sorted(records, key=lambda r: r["u"]):
            w.writerow([r["u"], f"{r['span_s']:.0f}", f"{r['final']:.3f}",
                        f"{r['drift']:+.3f}", "yes" if r["settled"] else "no"]
                       + [f"{x:.3f}" for x in r["asym"]]
                       + ["" if r["submitted"] is None
                          else f"{r['submitted']:.2f}"])
    print(f"\nWritten {OUT}")


if __name__ == "__main__":
    main()
