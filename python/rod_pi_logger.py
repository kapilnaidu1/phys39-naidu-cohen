#!/usr/bin/env python3
"""
Phys 39 Module 7, Part III. Rod instrument: PI base control plus synchronized
multichannel logging. Naidu / Cohen

    python3 python/rod_pi_logger.py      (from the repository root)

Pair with arduino/module_08/rod_tec_multichannel. That sketch prints the
Module 6 measurement line with the rod temperatures appended:

    Temperature (C): 31.02, Time (s): 645.06, PWM: 40, Heat/Cool: 1, Rod (C): 28.41, 26.90, 25.77, 24.95, 24.31

This program is python/tec_pi_control_gui.py (the same window, the same
pi_step() controller and anti-windup, the same safety behaviour) with four
additions:

1. ROD COLUMNS. Every CSV row gets one column per rod channel, T_<name>_C,
   from the SAME serial line as the base temperature, so all channels share
   the Arduino's time stamp (time_s). Channel names and order come from
   data/module_08/sensor_map.csv; if that file is missing they are R1 ... R5.
2. NEW FILES, NEVER OVERWRITTEN. Each launch writes
       data/module_08/rod_run_YYYYMMDD_HHMMSS.csv        the data
       data/module_08/rod_run_YYYYMMDD_HHMMSS_meta.json  how it was taken
       data/module_08/rod_run_YYYYMMDD_HHMMSS_notes.csv  timed notes
   The metadata file records the start time, the Git commit, the serial port,
   the sketch, the units and a copy of the sensor map, so the data can be
   interpreted later without guessing.
3. TIMED NOTES. Type a note ("foam off", "base step to 40 C", "bumped the
   rod") and press Enter or "Log note". It is saved with the latest Arduino
   time and the wall-clock time.
4. ROD CURVES on the temperature plot, one colour per channel.

The rod values are raw beta-equation temperatures. Calibration offsets are
applied later in python/analysis/, never to the saved data.
"""

import csv
import json
import math
import os
import re
import subprocess
import sys
from collections import deque
from datetime import datetime

import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

import tec_control_gui as base
import tec_pi_control_gui as pig
from tec_control_gui import resolve_port

REPO = pig.REPO
DATA_DIR = os.path.join(REPO, "data", "module_08")
SENSOR_MAP = os.path.join(DATA_DIR, "sensor_map.csv")
SKETCH = "arduino/module_08/rod_tec_multichannel/rod_tec_multichannel.ino"
DEFAULT_NAMES = ["R1", "R2", "R3", "R4", "R5"]

ROD_PATTERN = re.compile(r"Rod \(C\):\s*(.*)$")
ROD_COLORS = ["#1f77b4", "#ff7f0e", "#9467bd", "#8c564b", "#e377c2",
              "#17becf", "#bcbd22", "#7f7f7f"]


def load_sensor_map(path=SENSOR_MAP):
    """Rows of the sensor map, or None if it does not exist yet."""
    if not os.path.exists(path):
        return None
    with open(path, newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("channel", "").strip()]
    return rows or None


def parse_rod(line):
    """Rod temperatures from a measurement line: list of floats (nan for
    "---"), or None if the line has no rod field."""
    m = ROD_PATTERN.search(line)
    if m is None:
        return None
    out = []
    for field in m.group(1).split(","):
        field = field.strip()
        try:
            out.append(float(field))
        except ValueError:
            out.append(float("nan"))
    return out


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO,
                                       text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


SENSOR_ROWS = load_sensor_map()
ROD_NAMES = ([r["channel"].strip() for r in SENSOR_ROWS] if SENSOR_ROWS
             else DEFAULT_NAMES)


class RodWindow(pig.PIControlWindow):
    window_title = "Phys 39 Module 7, rod instrument (PI base control)"
    data_dir = DATA_DIR
    csv_prefix = "rod_run"
    columns = pig.COLUMNS + [f"T_{n}_C" for n in ROD_NAMES]

    def __init__(self):
        self.rod_names = ROD_NAMES
        self.latest_rod = [float("nan")] * len(self.rod_names)
        self.latest_time = float("nan")
        self.rod_buf = [deque() for _ in self.rod_names]
        self.rod_t = deque()
        self._count_warned = False
        super().__init__()

        stem = self.csv_path[:-4]
        self.notes_path = stem + "_notes.csv"
        self.notes_file = open(self.notes_path, "x", newline="")
        self.notes_writer = csv.writer(self.notes_file)
        self.notes_writer.writerow(["wall_clock", "time_s", "note"])
        self.notes_file.flush()

        meta = {
            "file": os.path.relpath(self.csv_path, REPO),
            "started": datetime.now().isoformat(timespec="seconds"),
            "git_commit_at_start": git_commit(),
            "program": "python/rod_pi_logger.py",
            "sketch": SKETCH,
            "serial_port": base.SERIAL_PORT,
            "baud": base.BAUD_RATE,
            "time_column": "time_s = Arduino millis()/1000 at the report; "
                           "base and rod values of a row share it",
            "units": {"time_s": "s", "temperature_C": "degC (base, A0)",
                      "T_<channel>_C": "degC, raw beta-equation value",
                      "pwm": "counts 0-255", "u_*": "signed PWM counts",
                      "q_Cs": "degC s"},
            "rod_channels": self.rod_names,
            "sensor_map_file": os.path.relpath(SENSOR_MAP, REPO),
            "sensor_map": SENSOR_ROWS or "sensor_map.csv not filled in yet",
            "notes_file": os.path.relpath(self.notes_path, REPO),
        }
        with open(stem + "_meta.json", "x") as fh:
            json.dump(meta, fh, indent=2)
        print(f"Metadata in {stem}_meta.json, notes in {self.notes_path}")
        if SENSOR_ROWS is None:
            print("!!! data/module_08/sensor_map.csv not found: channels are "
                  "named R1 ... R5. Fill in the sensor map. !!!")

    # ---- UI additions ----------------------------------------------------
    def _build_ui(self):
        super()._build_ui()
        self.rod_curves = []
        parts = []
        for i, name in enumerate(self.rod_names):
            c = ROD_COLORS[i % len(ROD_COLORS)]
            self.rod_curves.append(self.temp_plot.plot(
                pen=pg.mkPen(c, width=1.6), connect="finite"))
            parts.append(f"<span style='color:{c}'><b>&#9644; {name}</b></span>")
        legend = QtWidgets.QLabel(
            f"<span style='color:{pig.TEMP_COLOR}'><b>&#9644; base (A0)</b>"
            f"</span>&nbsp;&nbsp;&nbsp;" + "&nbsp;&nbsp;&nbsp;".join(parts))

        self.note_edit = QtWidgets.QLineEdit()
        self.note_edit.setPlaceholderText(
            "note, e.g. 'foam off' or 'base step to 40 C', then Enter")
        self.note_edit.returnPressed.connect(self.on_log_note)
        note_btn = QtWidgets.QPushButton("Log note")
        note_btn.setObjectName("plain")
        note_btn.clicked.connect(self.on_log_note)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(legend, stretch=1)
        row.addWidget(self.note_edit, stretch=2)
        row.addWidget(note_btn)

        layout = self.centralWidget().layout()
        layout.insertLayout(layout.indexOf(self.temp_plot), row)

    def on_log_note(self):
        text = self.note_edit.text().strip()
        if not text:
            return
        wall = datetime.now().isoformat(timespec="seconds")
        t = "" if math.isnan(self.latest_time) else f"{self.latest_time:.2f}"
        self.notes_writer.writerow([wall, t, text])
        self.notes_file.flush()
        print(f"\n--- NOTE at t = {t} s: {text} ---")
        self.note_edit.clear()

    # ---- data ------------------------------------------------------------
    def extra_row(self):
        return [("" if math.isnan(v) else f"{v:.2f}") for v in self.latest_rod]

    def on_line(self, line):
        if self._closing:
            return
        rod = parse_rod(line)
        m = pig.parse_measurement(line)
        if m is not None:
            n = len(self.rod_names)
            if rod is None:
                rod = [float("nan")] * n
            elif len(rod) != n and not self._count_warned:
                print(f"!!! the Arduino sends {len(rod)} rod values but the "
                      f"sensor map names {n}. Check rodPins[] and "
                      f"sensor_map.csv. !!!")
                self._count_warned = True
            rod = (rod + [float("nan")] * n)[:n]
            self.latest_rod = rod
            self.latest_time = m[0]
            self.rod_t.append(m[0])
            for d, v in zip(self.rod_buf, rod):
                d.append(v)
            while self.rod_t and (m[0] - self.rod_t[0]) > pig.WINDOW_SECONDS:
                self.rod_t.popleft()
                for d in self.rod_buf:
                    d.popleft()
        super().on_line(line)

    # ---- plots -----------------------------------------------------------
    def update_plots(self):
        super().update_plots()
        if not self.rod_t:
            return
        t = list(self.rod_t)
        vals = [v for d in self.rod_buf for v in d if not math.isnan(v)]
        for curve, d in zip(self.rod_curves, self.rod_buf):
            curve.setData(t, list(d))
        if vals and self.buf["T"]:
            temps = list(self.buf["T"]) + list(self.buf["set"]) + vals
            lo, hi = min(temps) - 1.0, max(temps) + 1.0
            if hi - lo < 6.0:
                c = 0.5 * (lo + hi)
                lo, hi = c - 3.0, c + 3.0
            self.temp_plot.setYRange(lo, hi, padding=0)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.notes_file.close()


def main():
    base.SERIAL_PORT = resolve_port()
    app = QtWidgets.QApplication(sys.argv)
    w = RodWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
