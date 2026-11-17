#!/usr/bin/env python3
"""
Phys 39 Module 8, Part I: cut a GUI plan run (one CSV, several phases) into one file per phase.  SAMMY copy.

    python3 python/sammy_module8_plan_slices.py data/module_08_sammy/sammy_angstrom_live_<stamp>.csv [--out-dir DIR] [--dry-run]

When START PLAN starts a phase the GUI writes the note "PLAN phase k of n start: <name> (<mode>)" with the time_ms of the last record
received. Phase k runs from that time_ms up to, not including, the next phase's note (the last phase to the end of the file); the
idle lead-in before the first note belongs to no phase. The rows are copied byte for byte with the header to

    sammy_angstrom_live_<stamp>_phase<k>_<slug of the phase name>.csv

next to the run file (or in --out-dir), so every analysis script reads a slice as a run file (the analysis stamp becomes
<stamp>_phase<k>_<slug>). Prints one line per phase.
"""

import argparse
import csv
import os
import re
import sys

NOTE = re.compile(r"^PLAN phase (\d+) of (\d+) start: (.*) \((OL|P|PI|RAW)\)$")
PREFIX = "sammy_angstrom_live_"


def slug(name):
    s = re.sub(r"(\d)\s+s\b", r"\1s", name.lower())          # "300 s" -> "300s"
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def read_phases(notes_path):
    out = []
    with open(notes_path, newline="") as fh:
        for r in csv.DictReader(fh):
            m = NOTE.match(" ".join(r["note"].split()))
            if m:
                out.append(dict(k=int(m.group(1)), n=int(m.group(2)), name=m.group(3), mode=m.group(4), t_ms=int(r["time_ms"])))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--out-dir")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    run = os.path.abspath(a.run)
    stamp = os.path.basename(run)[len(PREFIX):-len(".csv")]
    phases = read_phases(run.replace(".csv", "_notes.csv"))
    if not phases:
        sys.exit("no 'PLAN phase k of n start' notes in " + run.replace(".csv", "_notes.csv"))
    out_dir = a.out_dir or os.path.dirname(run)
    os.makedirs(out_dir, exist_ok=True)

    with open(run, "rb") as fh:
        lines = fh.read().splitlines(keepends=True)
    header, rows = lines[0], lines[1:]
    t_ms = [int(r.split(b",", 1)[0]) for r in rows]

    print(f"{os.path.basename(run)}: {len(rows)} records, {len(phases)} phase notes")
    for i, ph in enumerate(phases):
        t0 = ph["t_ms"]
        t1 = phases[i + 1]["t_ms"] if i + 1 < len(phases) else float("inf")
        idx = [j for j, t in enumerate(t_ms) if t0 <= t < t1]
        name = f"{PREFIX}{stamp}_phase{ph['k']}_{slug(ph['name'])}.csv"
        if not idx:
            print(f"  phase {ph['k']} of {ph['n']}: {ph['name']} ({ph['mode']}): no records")
            continue
        sel = rows[idx[0]:idx[-1] + 1]
        print(f"  phase {ph['k']} of {ph['n']}: {ph['name']} ({ph['mode']}): {len(sel)} records, t = {t_ms[idx[0]] / 1000:.1f} to "
              f"{t_ms[idx[-1]] / 1000:.1f} s ({(t_ms[idx[-1]] - t_ms[idx[0]]) / 60000:.1f} min) -> {name}")
        if not a.dry_run:
            with open(os.path.join(out_dir, name), "wb") as fh:
                fh.write(header + b"".join(sel))
    if ph["n"] != len(phases):
        print(f"  note: the plan had {ph['n']} phases but only {len(phases)} start notes were written (cancelled or stopped early)")


if __name__ == "__main__":
    main()
