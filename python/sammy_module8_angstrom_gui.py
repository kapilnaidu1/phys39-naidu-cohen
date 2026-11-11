#!/usr/bin/env python3
"""
Phys 39 Module 8, Part I: live Angstrom GUI. SAMMY copy.

    python3 python/sammy_module8_angstrom_gui.py                 (from the repository root)
    python3 python/sammy_module8_angstrom_gui.py --check-file F  (saved-file report, no window)

Based on Kapil Naidu's python/angstrom_gui.py (commit 60500c8), which stays
unchanged. Pair with arduino/module_08_sammy/angstrom_tec_sammy. Everything
that file does is kept; the differences are:
  - data go to data/module_08_sammy/sammy_angstrom_live_YYYYMMDD_HHMMSS.csv
    (+ _events.txt, _notes.csv, _meta.json), sensor map from the same folder;
  - a fourth control mode, RAW (S18.3, S18.4): open-loop sinusoidal PWM
    u = U0 + U sin(wt), boxes U and U0 in PWM counts; U0 = 0 is the
    zero-centered trial, U0 >= U is positive only. RAW records carry nan in
    Ta_C, Tb_C, setpoint_C, feedforward_pwm and controller_pwm;
  - two more schedule presets (course periods 500-200-100 in PI; raw-PWM
    sweep 100-200-500);
  - "One long run": START PLAN sends the S18.3 raw-PWM schedule (U0 = 0, U and
    room T from the boxes) and, if the box is ticked, the PI re-run schedule
    once the Arduino reports SCHEDULE DONE (FULL_PLAN below). STOP, a safety
    shutdown, a refused command or an Arduino restart cancels what is left.

Long test (Kapil's S20 plan, about 101 min), after the room-temperature
baseline with supply and pump off: mode PI, Kp 12, Ki 0.2, chi_h 0.50127,
chi_c 0.18091 (r = 2.771), room T = the measured baseline; Send settings,
GET, check the # SETTINGS line; Production, Send schedule, START schedule.

The Arduino computes the sine setpoint and the TEC command in the selected
mode (OL open-loop feedforward from the Module 4 steady-state curve, P, or PI
with the cooling multiplier r = chi_h/chi_c, or RAW) and prints one CSV
record every 500 ms.

This program
  - sends settings (Ta, Tb, period, Kp, Ki, room temperature, r computed
    from chi_h and chi_c, control mode; U and U0 in RAW) and START / STOP,
  - shows the setpoint, the TEC thermistor and T1 to T5 live on one time
    axis, and the feedforward, controller and applied PWM below; plots on
    the left, live values and controls in two columns on the right (window
    and text size follow the screen; View menu or Cmd +, Cmd -, Cmd 0),
  - saves every valid record UNCHANGED, with every "#" line, malformed line
    and command sent in _events.txt (wall-clock time), typed notes in
    _notes.csv and the run description in _meta.json,
  - counts valid, malformed, duplicated and missing records,
  - "Check a saved file" reads a saved record file with the same parser and
    reports the same counts.
"""

import argparse
import csv
import json
import math
import os
import subprocess
import sys
from collections import deque
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO, "data", "module_08_sammy")
SENSOR_MAP = os.path.join(DATA_DIR, "sensor_map.csv")
SKETCH = "arduino/module_08_sammy/angstrom_tec_sammy/angstrom_tec_sammy.ino"
PROGRAM = "python/sammy_module8_angstrom_gui.py"
FILE_PREFIX = "sammy_angstrom_live_"

COLUMNS = ["time_ms", "run_state", "control_mode", "step", "Ta_C", "Tb_C",
           "period_s", "setpoint_C", "feedforward_pwm", "TEC_C", "T1_C",
           "T2_C", "T3_C", "T4_C", "T5_C", "controller_pwm",
           "heating_to_cooling_ratio", "signed_pwm"]
HEADER = ",".join(COLUMNS)
INT_COLS = {"time_ms", "run_state", "step", "signed_pwm"}
TEXT_COLS = {"control_mode"}
MODES = ("OL", "P", "PI", "RAW")
REPORT_MS = 500
# Frequency schedules (Module 8 Stage 3): one step per line,
# "duration_s Ta_C Tb_C period_s". Durations = about 2 cycles to settle + 5 kept.
SCHEDULE_PRESETS = {
    "Fast test": "# accelerated check: 3 steps, 2 automatic period changes, 10 min\n"
                 "200 40 16 100\n200 40 16 150\n200 40 16 200\n",
    "Production": "# S20 plan: 5 min hold at Ta (Tb 0) so the plate and integral start\n"
                  "# near the mean, then 7 cycles at each period, about 101 min\n"
                  "300 40 0 100\n3360 40 16 480\n1680 40 16 240\n700 40 16 100\n",
    "Course 500-200-100": "# PI at the course periods 500, 200, 100 s: 5 min hold, then 7 cycles each, about 98 min\n"
                          "300 40 0 100\n3500 40 16 500\n1400 40 16 200\n700 40 16 100\n",
    "Raw PWM sweep": "# RAW mode only (Ta, Tb ignored; U, U0 from the boxes): 6 cycles each, about 80 min\n"
                     "600 40 0 100\n1200 40 0 200\n3000 40 0 500\n",
}
# One click for a whole session. The mode is one setting for a whole Arduino schedule, so the GUI sends
# phase 2 itself when the Arduino reports "SCHEDULE DONE", but only if its box is ticked (default: phase 1
# only). STOP, a safety shutdown, a refused command or an Arduino restart cancels the rest. Phase 1 takes
# U and the room T from the boxes, U0 = 0.
FULL_PLAN = [
    {"name": "S18.3 raw PWM, U0 = 0", "mode": "RAW", "U0": 0.0,
     "schedule": "500 40 0 100\n800 40 0 200\n1500 40 0 500\n"},
    {"name": "PI re-run, 100 s then 480 s", "mode": "PI",
     "schedule": "300 40 0 100\n1200 40 16 100\n3840 40 16 480\n"},
]


def parse_schedule(text):
    """[(dur, Ta, Tb, period), ...] and a list of problems."""
    steps, problems = [], []
    for n, line in enumerate(text.splitlines(), 1):
        line = line.split("#")[0].strip()
        if not line:
            continue
        try:
            dur, ta, tb, per = (float(v) for v in line.replace(",", " ").split())
        except ValueError:
            problems.append(f"line {n}: need 4 numbers: duration Ta Tb period")
            continue
        if not 10 <= dur <= 36000:
            problems.append(f"line {n}: duration must be 10 to 36000 s")
        if not 100 <= per <= 3600:
            problems.append(f"line {n}: period must be 100 to 3600 s")
        if tb < 0 or ta + tb > 56 or ta - tb < 10:
            problems.append(f"line {n}: setpoint must stay within 10 to 56 C")
        steps.append((dur, ta, tb, per))
    if len(steps) > 8:
        problems.append("at most 8 steps")
    if not steps:
        problems.append("no steps")
    return steps, problems
# course first run (Ta 40, Tb 16, 100 s), Module 6 gains, Module 4 chi;
# U and U0 are the RAW-mode amplitude and offset in PWM counts
DEFAULTS = {"TA": 40.0, "TB": 16.0, "PERIOD": 100.0, "KP": 12.0, "KI": 0.2,
            "TAMB": 21.54, "CHIH": 0.50127, "CHIC": 0.18091,
            "U": 50.0, "U0": 0.0}


# =====================================================================
# parsing, shared by the live stream and the saved-file check
# =====================================================================

def parse_record(line):
    """dict of the 18 fields, or None if the line is not a valid record.
    'nan' is the placeholder for a field that does not apply or a channel
    that could not be read."""
    parts = line.strip().split(",")
    if len(parts) != len(COLUMNS):
        return None
    rec = {}
    try:
        for name, field in zip(COLUMNS, parts):
            if name in INT_COLS:
                rec[name] = int(field)
            elif name in TEXT_COLS:
                rec[name] = field
            else:
                rec[name] = float(field)
    except ValueError:
        return None
    if rec["time_ms"] < 0 or rec["run_state"] not in (0, 1, 2, 9) \
            or rec["control_mode"] not in MODES:
        return None
    return rec


def classify(line):
    """'comment', 'header', 'blank', 'record' or 'malformed'."""
    s = line.strip()
    if not s:
        return "blank"
    if s.startswith("#"):
        return "comment"
    if s == HEADER:
        return "header"
    return "record" if parse_record(s) is not None else "malformed"


class StreamStats:
    """Valid / malformed / duplicated / missing / restart counts."""

    def __init__(self):
        self.valid = self.malformed = self.duplicated = 0
        self.missing = self.restarts = 0
        self.last_ms = None

    def add(self, rec):
        t = rec["time_ms"]
        if self.last_ms is not None:
            if t == self.last_ms:
                self.duplicated += 1
                return "duplicate"
            if t < self.last_ms:
                self.restarts += 1
            else:
                gap = t - self.last_ms
                if gap > 1.5 * REPORT_MS:
                    self.missing += max(round(gap / REPORT_MS) - 1, 1)
        self.last_ms = t
        self.valid += 1
        return "ok"

    def text(self):
        return (f"valid {self.valid}  malformed {self.malformed}  "
                f"duplicated {self.duplicated}  missing ~{self.missing}  "
                f"restarts {self.restarts}")


def check_file(path):
    """Read a saved record file with the live parser. Returns
    (records, stats, segments, counts) where segments are lists of records
    between restarts."""
    stats = StreamStats()
    records, segments = [], [[]]
    counts = {"comment": 0, "header": 0, "blank": 0, "boot_lines": 0}
    with open(path, "r", errors="replace") as fh:
        for line in fh:
            kind = classify(line)
            if kind == "record":
                rec = parse_record(line)
                prev_restarts = stats.restarts
                if stats.add(rec) == "duplicate":
                    continue
                if stats.restarts > prev_restarts:
                    segments.append([])
                records.append(rec)
                segments[-1].append(rec)
            elif kind == "malformed":
                stats.malformed += 1
            else:
                counts[kind] += 1
                if line.startswith("# BOOT"):
                    counts["boot_lines"] += 1
    segments = [s for s in segments if s]
    return records, stats, segments, counts


def report_text(path, stats, segments, counts):
    out = [f"File: {path}", stats.text(),
           f"comment lines {counts['comment']}, header lines {counts['header']}, "
           f"BOOT lines {counts['boot_lines']}, segments {len(segments)}"]
    for i, seg in enumerate(segments, 1):
        t0, t1 = seg[0]["time_ms"] / 1000, seg[-1]["time_ms"] / 1000
        out.append(f"  segment {i}: {len(seg)} records, t = {t0:.1f} to "
                   f"{t1:.1f} s ({(t1 - t0) / 60:.1f} min)")
    return "\n".join(out)


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO,
                                       text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def sensor_map_rows():
    if not os.path.exists(SENSOR_MAP):
        return None
    with open(SENSOR_MAP, newline="") as fh:
        return list(csv.DictReader(fh))


# =====================================================================
# the window (Qt imported here so --check-file works without a display)
# =====================================================================

def run_gui():
    import pyqtgraph as pg
    from PySide6 import QtCore, QtGui, QtWidgets

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tec_control_gui as base

    CH_COLORS = {"TEC_C": "#000000", "T1_C": "#1f77b4", "T2_C": "#ff7f0e",
                 "T3_C": "#2ca02c", "T4_C": "#9467bd", "T5_C": "#8c564b"}
    BASE_PT = 13.0      # text size on a screen 1000 logical px tall

    def screen_scale():
        """Text scale for this screen: 1 at 1000 px of height, 1.8 at most."""
        scr = QtWidgets.QApplication.primaryScreen()
        return max(1.0, min(1.8, scr.availableGeometry().height() / 1000.0))

    def fit_to_screen(win, frac):
        geo = QtWidgets.QApplication.primaryScreen().availableGeometry()
        win.resize(int(geo.width() * frac), int(geo.height() * frac))
        win.move(geo.center() - win.rect().center())

    def style_plot(plot, pt):
        font = QtGui.QFont()
        font.setPointSizeF(pt)
        for name, text in plot.axis_labels.items():
            plot.setLabel(name, text, **{"font-size": f"{pt}pt", "color": "#303030"})
        for name in ("left", "bottom"):
            plot.getAxis(name).setStyle(tickFont=font)
            plot.getAxis(name).setTextPen("#505050")
        plot.legend_item.setScale(pt / 12.0)     # the legend text is 12 px at scale 1

    def make_plots(layout_parent):
        temp = pg.PlotWidget()
        temp.setBackground("w")
        temp.showGrid(x=True, y=True, alpha=0.25)
        temp.axis_labels = {"left": "Temperature (°C)"}
        temp.legend_item = temp.addLegend(offset=(10, 10), labelTextColor="#303030")
        curves = {"setpoint_C": temp.plot(
            pen=pg.mkPen("#7f7f7f", width=1.5, style=QtCore.Qt.DashLine),
            name="setpoint", connect="finite")}
        for ch, col in CH_COLORS.items():
            curves[ch] = temp.plot(pen=pg.mkPen(col, width=2 if ch == "TEC_C" else 1.6),
                                   name=ch.replace("_C", ""), connect="finite")
        pwm = pg.PlotWidget()
        pwm.setBackground("w")
        pwm.showGrid(x=True, y=True, alpha=0.25)
        pwm.axis_labels = {"left": "PWM counts", "bottom": "Arduino time (s)"}
        pwm.legend_item = pwm.addLegend(offset=(10, 10), labelTextColor="#303030")
        pwm.setXLink(temp)
        curves["feedforward_pwm"] = pwm.plot(pen=pg.mkPen("#d62728", width=1.4),
                                             name="feedforward (OL)", connect="finite")
        curves["controller_pwm"] = pwm.plot(pen=pg.mkPen("#aaaaaa", width=1.4),
                                            name="controller (P/PI, raw)", connect="finite")
        curves["signed_pwm"] = pwm.plot(pen=pg.mkPen("#202020", width=1.6),
                                        name="applied signed PWM")
        for y in (255, -255):
            pwm.addLine(y=y, pen=pg.mkPen("#C0392B", width=1, style=QtCore.Qt.DotLine))
        for plot in (temp, pwm):          # wheel and drag move time only, y follows the visible data
            plot.getViewBox().setMouseEnabled(x=True, y=False)
            plot.getViewBox().setAutoVisible(y=True)
            plot.enableAutoRange(axis="y", enable=True)
        layout_parent.addWidget(temp, stretch=3)
        layout_parent.addWidget(pwm, stretch=2)
        return curves, temp, pwm

    class ImportWindow(QtWidgets.QWidget):
        def __init__(self, path, segments, text):
            super().__init__()
            self.setWindowTitle(f"Saved file: {os.path.basename(path)}")
            fit_to_screen(self, 0.85)
            lay = QtWidgets.QVBoxLayout(self)
            lab = QtWidgets.QLabel(f"<pre>{text}</pre>")
            lab.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            lay.addWidget(lab)
            curves, temp, pwm = make_plots(lay)
            for plot in (temp, pwm):
                style_plot(plot, QtWidgets.QApplication.font().pointSizeF())
            # segments laid end to end; each restart starts after the last
            data = {k: [] for k in curves}
            t_all, offset = [], 0.0
            for seg in segments:
                t0 = seg[0]["time_ms"] / 1000.0
                for r in seg:
                    t_all.append(offset + r["time_ms"] / 1000.0 - t0)
                    for k in curves:
                        data[k].append(r[k])
                offset = t_all[-1] + 1.0
                t_all.append(float("nan"))       # break the line
                for k in curves:
                    data[k].append(float("nan"))
            for k, c in curves.items():
                c.setData(t_all, data[k], connect="finite")

    class Window(QtWidgets.QMainWindow):
        def __init__(self, port):
            super().__init__()
            self.setWindowTitle("Phys 39 Module 8 SAMMY: Angstrom live run")
            self.ui_scale = screen_scale()
            self.stats = StreamStats()
            self.buf = {k: deque() for k in ["t"] + COLUMNS}
            self.latest = None
            self.import_windows = []
            self._closing = False
            self.plan = None

            os.makedirs(DATA_DIR, exist_ok=True)
            self.stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = os.path.join(DATA_DIR, f"{FILE_PREFIX}{self.stamp}")
            self.csv_path = stem + ".csv"
            self.csv_file = open(self.csv_path, "x", newline="")
            self.csv_file.write(HEADER + "\n")
            self.csv_file.flush()
            self.events = open(stem + "_events.txt", "x")
            self.notes = open(stem + "_notes.csv", "x", newline="")
            self.notes_w = csv.writer(self.notes)
            self.notes_w.writerow(["wall_clock", "time_ms", "note"])
            self.notes.flush()
            meta = {
                "file": os.path.relpath(self.csv_path, REPO),
                "started": datetime.now().isoformat(timespec="seconds"),
                "git_commit_at_start": git_commit(),
                "program": PROGRAM,
                "derived_from": "python/angstrom_gui.py at commit 60500c8 (Kapil Naidu)",
                "sketch": SKETCH,
                "serial_port": port, "baud": base.BAUD_RATE,
                "columns": COLUMNS,
                "units": {"time_ms": "ms, Arduino millis() at the report",
                          "Ta_C, Tb_C, setpoint_C, TEC_C, T1_C..T5_C":
                              "degC, raw beta-equation values (no offsets); "
                              "Ta_C, Tb_C and setpoint_C are nan in RAW",
                          "period_s": "s",
                          "step": "active run segment: schedule step, or for a "
                          "live run 1 at START and +1 at every change of a "
                          "setting in use; 0 idle",
                          "feedforward_pwm": "OL command from the Module 4 "
                          "steady-state curve; nan in P, PI and RAW",
                          "controller_pwm": "raw P or PI command before the "
                          "cooling multiplier and clamp; nan in OL and RAW",
                          "signed_pwm": "applied PWM, + heat, - cool (RAW: "
                          "U0 + U sin(phase), no multiplier)",
                          "heating_to_cooling_ratio": "r = chi_h/chi_c"},
                "control_mode": {"OL": "open-loop feedforward",
                                 "P": "proportional only", "PI": "PI",
                                 "RAW": "open-loop sinusoidal PWM, no feedback"},
                "placeholder": "nan = does not apply in this mode, or "
                               "channel unreadable",
                "run_state": {"0": "idle", "1": "running (live START)",
                              "2": "running a frequency schedule",
                              "9": "safety latched"},
                "sensor_map_file": os.path.relpath(SENSOR_MAP, REPO),
                "sensor_map": sensor_map_rows(),
                "events_file": os.path.relpath(stem + "_events.txt", REPO),
                "notes_file": os.path.relpath(stem + "_notes.csv", REPO),
            }
            with open(stem + "_meta.json", "x") as fh:
                json.dump(meta, fh, indent=2)
            print(f"Saving to {self.csv_path}")

            self._build_ui()
            fit_to_screen(self, 0.92)
            self.link = base.SerialLink(port, base.BAUD_RATE)
            self.link.line_received.connect(self.on_line)
            self.link.error.connect(lambda m: self.log_event(f"SERIAL ERROR {m}"))
            self.link.start()
            self.timer = QtCore.QTimer(self)
            self.timer.timeout.connect(self.redraw)
            self.timer.start(300)
            self.cmd_queue = deque()
            self.cmd_timer = QtCore.QTimer(self)
            self.cmd_timer.timeout.connect(self._send_next)
            self.cmd_timer.start(300)

        # ---- UI -----------------------------------------------------------
        def _build_ui(self):
            self.spins = {}
            self.split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
            self.split.setHandleWidth(6)
            self.setCentralWidget(self.split)

            plots = QtWidgets.QWidget()
            plot_lay = QtWidgets.QVBoxLayout(plots)
            plot_lay.setContentsMargins(0, 0, 0, 0)
            self.curves, temp, pwm = make_plots(plot_lay)
            self.plots = (temp, pwm)
            self.split.addWidget(plots)
            self.split.setStretchFactor(0, 1)
            self.split.setCollapsible(0, False)

            self.side_panes = []
            for panel in (self._data_panel(), self._controls_panel()):
                scroll = QtWidgets.QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
                scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
                scroll.setWidget(panel)
                self.split.addWidget(scroll)
                self.side_panes.append(scroll)
            self.split.setStretchFactor(1, 0)
            self.split.setStretchFactor(2, 0)

            self.view_menu = self.menuBar().addMenu("View")
            for text, keys, factor in (("Larger text", ("Ctrl++", "Ctrl+="), 1.1),
                                       ("Smaller text", ("Ctrl+-",), 1 / 1.1),
                                       ("Reset text size", ("Ctrl+0",), None)):
                act = QtGui.QAction(text, self)
                act.setShortcuts([QtGui.QKeySequence(k) for k in keys])
                act.triggered.connect(lambda _=False, f=factor: self.set_scale(
                    screen_scale() if f is None else self.ui_scale * f))
                self.view_menu.addAction(act)
                self.addAction(act)
            self.set_scale(self.ui_scale)

        def _data_panel(self):
            panel = QtWidgets.QWidget()
            lay = QtWidgets.QVBoxLayout(panel)

            box = QtWidgets.QGroupBox("State")
            vbox = QtWidgets.QVBoxLayout(box)
            self.state_label = QtWidgets.QLabel("waiting for the Arduino ...")
            self.state_label.setTextFormat(QtCore.Qt.RichText)
            self.state_label.setWordWrap(True)
            self.time_label = QtWidgets.QLabel("t = -")
            self.mode_label = QtWidgets.QLabel("-")
            self.mode_label.setWordWrap(True)
            for lab in (self.state_label, self.time_label, self.mode_label):
                vbox.addWidget(lab)
            lay.addWidget(box)

            self.value_labels = {}
            groups = (
                ("Temperatures (°C)",
                 [("setpoint_C", "setpoint", "#7f7f7f")]
                 + [(ch, ch.replace("_C", ""), color) for ch, color in CH_COLORS.items()]),
                ("PWM counts",
                 [("feedforward_pwm", "feedforward (OL)", "#d62728"),
                  ("controller_pwm", "controller (P/PI)", "#aaaaaa"),
                  ("signed_pwm", "applied", "#202020")]))
            for title, rows in groups:
                box = QtWidgets.QGroupBox(title)
                grid = QtWidgets.QGridLayout(box)
                for i, (key, name, color) in enumerate(rows):
                    grid.addWidget(QtWidgets.QLabel(
                        f"<span style='color:{color}'>&#9632;</span> {name}"), i, 0)
                    val = QtWidgets.QLabel("-")
                    val.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                    grid.addWidget(val, i, 1)
                    self.value_labels[key] = val
                grid.setColumnStretch(1, 1)
                lay.addWidget(box)

            box = QtWidgets.QGroupBox("Stream")
            grid = QtWidgets.QGridLayout(box)
            self.stat_labels = {}
            for i, (key, name) in enumerate((
                    ("valid", "valid"), ("malformed", "malformed"),
                    ("duplicated", "duplicated"), ("missing", "missing (approx.)"),
                    ("restarts", "restarts"))):
                grid.addWidget(QtWidgets.QLabel(name), i, 0)
                val = QtWidgets.QLabel("0")
                val.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                grid.addWidget(val, i, 1)
                self.stat_labels[key] = val
            stamp = QtWidgets.QLabel(f"run file stamp {self.stamp}")
            stamp.setWordWrap(True)
            grid.addWidget(stamp, 5, 0, 1, 2)
            grid.setColumnStretch(1, 1)
            lay.addWidget(box)
            lay.addStretch(1)
            return panel

        def _controls_panel(self):
            panel = QtWidgets.QWidget()
            lay = QtWidgets.QVBoxLayout(panel)

            box = QtWidgets.QGroupBox("Run")
            grid = QtWidgets.QGridLayout(box)
            for i, text in enumerate(("START", "STOP", "CLEAR SAFETY", "GET")):
                b = QtWidgets.QPushButton(text)
                b.clicked.connect(lambda _=False, c=text: self.send(c))
                grid.addWidget(b, i // 2, i % 2)
            lay.addWidget(box)

            box = QtWidgets.QGroupBox("One long run")
            vbox = QtWidgets.QVBoxLayout(box)
            self.plan_pi = QtWidgets.QCheckBox(f"then the PI re-run (+ {self.phase_minutes(FULL_PLAN[1]):.0f} min)")
            hint = QtWidgets.QLabel()
            hint.setTextFormat(QtCore.Qt.RichText)
            hint.setWordWrap(True)
            self.plan_pi.toggled.connect(lambda _=False: hint.setText(self.plan_summary()))
            hint.setText(self.plan_summary())
            vbox.addWidget(hint)
            vbox.addWidget(self.plan_pi)
            b = QtWidgets.QPushButton("START PLAN")
            b.clicked.connect(self.start_plan)
            vbox.addWidget(b)
            self.plan_label = QtWidgets.QLabel("plan not started")
            self.plan_label.setTextFormat(QtCore.Qt.RichText)
            self.plan_label.setWordWrap(True)
            vbox.addWidget(self.plan_label)
            lay.addWidget(box)

            box = QtWidgets.QGroupBox("Note")
            vbox = QtWidgets.QVBoxLayout(box)
            self.note_edit = QtWidgets.QLineEdit()
            self.note_edit.setPlaceholderText("note, e.g. 'room T 21.4 C', then Enter")
            self.note_edit.returnPressed.connect(self.log_note)
            vbox.addWidget(self.note_edit)
            lay.addWidget(box)

            box = QtWidgets.QGroupBox("Settings")
            grid = QtWidgets.QGridLayout(box)
            self.mode_box = QtWidgets.QComboBox()
            self.mode_box.addItems(list(MODES))
            self.mode_box.setCurrentText("PI")
            grid.addWidget(QtWidgets.QLabel("mode"), 0, 0)
            grid.addWidget(self.mode_box, 0, 1, 1, 3)
            specs = [("TA", "Ta (°C)", 10, 56, 2, 0.5), ("TB", "Tb (°C)", 0, 23, 2, 0.5),
                     ("PERIOD", "period (s)", 100, 3600, 1, 10), ("KP", "Kp", 0, 100, 3, 0.5),
                     ("KI", "Ki", 0, 5, 4, 0.01), ("TAMB", "room T (°C)", 10, 35, 2, 0.1),
                     ("CHIH", "χh", 0.01, 2, 5, 0.01), ("CHIC", "χc", 0.01, 2, 5, 0.01)]
            for i, (key, label, lo, hi, dec, step) in enumerate(specs):
                s = QtWidgets.QDoubleSpinBox()
                s.setRange(lo, hi)
                s.setDecimals(dec)
                s.setSingleStep(step)
                s.setValue(DEFAULTS[key])
                self.spins[key] = s
                grid.addWidget(QtWidgets.QLabel(label), 1 + i // 2, 2 * (i % 2))
                grid.addWidget(s, 1 + i // 2, 2 * (i % 2) + 1)
            self.r_label = QtWidgets.QLabel()
            self.spins["CHIH"].valueChanged.connect(self.update_r)
            self.spins["CHIC"].valueChanged.connect(self.update_r)
            self.update_r()
            grid.addWidget(self.r_label, 5, 0, 1, 4)
            send = QtWidgets.QPushButton("Send settings")
            send.clicked.connect(self.send_settings)
            grid.addWidget(send, 6, 0, 1, 4)
            grid.setColumnStretch(1, 1)
            grid.setColumnStretch(3, 1)
            lay.addWidget(box)

            box = QtWidgets.QGroupBox("Schedule")
            vbox = QtWidgets.QVBoxLayout(box)
            hint = QtWidgets.QLabel("one step per line: duration (s), Ta, Tb, period (s)")
            hint.setWordWrap(True)
            vbox.addWidget(hint)
            self.sched_edit = QtWidgets.QPlainTextEdit(SCHEDULE_PRESETS["Fast test"])
            self.sched_edit.textChanged.connect(self.update_sched_label)
            vbox.addWidget(self.sched_edit)
            grid = QtWidgets.QGridLayout()
            for i, name in enumerate(SCHEDULE_PRESETS):
                b = QtWidgets.QPushButton(name)
                b.clicked.connect(lambda _=False, n=name:
                                  self.sched_edit.setPlainText(SCHEDULE_PRESETS[n]))
                grid.addWidget(b, i // 2, i % 2)
            vbox.addLayout(grid)
            row = QtWidgets.QHBoxLayout()
            b = QtWidgets.QPushButton("Send schedule")
            b.clicked.connect(self.send_schedule)
            row.addWidget(b)
            b = QtWidgets.QPushButton("START schedule")
            b.clicked.connect(lambda: self.send("SCHED START"))
            row.addWidget(b)
            vbox.addLayout(row)
            self.sched_label = QtWidgets.QLabel()
            self.sched_label.setWordWrap(True)
            vbox.addWidget(self.sched_label)
            self.update_sched_label()
            lay.addWidget(box)

            box = QtWidgets.QGroupBox("RAW mode")
            grid = QtWidgets.QGridLayout(box)
            hint = QtWidgets.QLabel("u = U0 + U sin(ωt), PWM counts. U0 = 0: zero-centered (S18.3); "
                                    "U0 ≥ U: positive only (S18.4). Use the course value of U.")
            hint.setWordWrap(True)
            grid.addWidget(hint, 0, 0, 1, 4)
            for i, (key, lo, hi) in enumerate((("U", 0, 255), ("U0", -255, 255))):
                s = QtWidgets.QDoubleSpinBox()
                s.setRange(lo, hi)
                s.setDecimals(0)
                s.setSingleStep(5)
                s.setValue(DEFAULTS[key])
                self.spins[key] = s
                grid.addWidget(QtWidgets.QLabel(key), 1, 2 * i)
                grid.addWidget(s, 1, 2 * i + 1)
            grid.setColumnStretch(1, 1)
            grid.setColumnStretch(3, 1)
            lay.addWidget(box)

            box = QtWidgets.QGroupBox("Plots and files")
            grid = QtWidgets.QGridLayout(box)
            grid.addWidget(QtWidgets.QLabel("window (s)"), 0, 0)
            self.win_spin = QtWidgets.QSpinBox()
            self.win_spin.setRange(60, 20000)
            self.win_spin.setValue(600)
            grid.addWidget(self.win_spin, 0, 1)
            b = QtWidgets.QPushButton("Autoscale plots")
            b.clicked.connect(self.autoscale_plots)
            grid.addWidget(b, 1, 0, 1, 2)
            imp = QtWidgets.QPushButton("Check a saved file")
            imp.clicked.connect(self.check_saved_file)
            grid.addWidget(imp, 2, 0, 1, 2)
            grid.setColumnStretch(1, 1)
            lay.addWidget(box)
            lay.addStretch(1)
            return panel

        def set_scale(self, scale):
            self.ui_scale = max(0.7, min(2.6, scale))
            pt = BASE_PT * self.ui_scale
            font = QtWidgets.QApplication.font()
            font.setPointSizeF(pt)
            QtWidgets.QApplication.setFont(font)
            for box in self.findChildren(QtWidgets.QGroupBox):    # titles keep the old size otherwise
                box.setFont(font)
            mono = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
            mono.setPointSizeF(pt * 1.15)
            metrics = QtGui.QFontMetrics(mono)
            for lab in self.value_labels.values():
                lab.setFont(mono)
                lab.setMinimumWidth(metrics.horizontalAdvance("-000.00"))
            self.sched_edit.setFont(mono)
            self.sched_edit.setMinimumHeight(metrics.lineSpacing() * 8 + 12)
            big = QtGui.QFont(font)
            big.setPointSizeF(pt * 1.4)
            big.setBold(True)
            self.state_label.setFont(big)
            for plot in self.plots:
                style_plot(plot, pt)
            QtCore.QTimer.singleShot(0, self._fit_panes)   # after the font change has reached every widget

        def _fit_panes(self):
            bar = self.side_panes[0].verticalScrollBar().sizeHint().width() + 4
            for scroll in self.side_panes:
                scroll.setMinimumWidth(scroll.widget().minimumSizeHint().width() + bar)
            widths = [scroll.widget().sizeHint().width() + bar for scroll in self.side_panes]
            self.split.setSizes([max(300, self.split.width() - sum(widths))] + widths)

        def autoscale_plots(self):
            for plot in self.plots:
                plot.enableAutoRange(axis="xy", enable=True)

        # ---- I/O ----------------------------------------------------------
        def log_event(self, text):
            if self._closing:
                return
            wall = datetime.now().isoformat(timespec="seconds")
            self.events.write(f"{wall}\t{text}\n")
            self.events.flush()

        # The Uno's serial input buffer is 64 bytes and the sketch only
        # reads it between ~0.1 s measurement passes, so a burst of commands
        # can overflow it (on 2 Nov the 7th of 7 settings was lost and the
        # next START arrived garbled). Commands therefore go out one at a
        # time, 0.3 s apart.
        def send(self, cmd):
            if cmd == "STOP":
                self.cancel_plan("STOP pressed", warn=False)
            self.cmd_queue.append(cmd)

        def _send_next(self):
            if self.cmd_queue:
                cmd = self.cmd_queue.popleft()
                if self.link.send_command(cmd):
                    self.log_event(f"SENT {cmd}")

        def r_value(self):
            return self.spins["CHIH"].value() / self.spins["CHIC"].value()

        def update_r(self):
            self.r_label.setText(f"r = χh/χc = {self.r_value():.3f}")

        def send_settings(self):
            mode = self.mode_box.currentText()
            self.send(f"SET MODE {mode}")
            if mode == "RAW":
                for key in ("U", "U0"):
                    self.send(f"SET {key} {self.spins[key].value():g}")
            for key in ("TA", "TB", "PERIOD", "KP", "KI", "TAMB"):
                self.send(f"SET {key} {self.spins[key].value():g}")
            self.send(f"SET R {self.r_value():.3f}")
            self.log_event(f"chi_h {self.spins['CHIH'].value():g} chi_c "
                           f"{self.spins['CHIC'].value():g} -> r {self.r_value():.4f}")

        def update_sched_label(self):
            steps, problems = parse_schedule(self.sched_edit.toPlainText())
            if problems:
                self.sched_label.setText("<span style='color:#C0392B'>"
                                         + "; ".join(problems) + "</span>")
            else:
                total = sum(st[0] for st in steps)
                self.sched_label.setText(f"{len(steps)} steps, {total / 60:.1f} min")

        def send_schedule(self):
            steps, problems = parse_schedule(self.sched_edit.toPlainText())
            if problems:
                QtWidgets.QMessageBox.warning(self, "Schedule", "\n".join(problems))
                return
            self.send("SCHED CLEAR")
            for dur, ta, tb, per in steps:
                self.send(f"SCHED ADD {dur:g} {ta:g} {tb:g} {per:g}")
            self.send("SCHED LIST")
            self.log_event("schedule sent: " + " | ".join(
                f"{d:g} s, Ta {a:g}, Tb {b:g}, period {p:g} s" for d, a, b, p in steps))

        def log_note(self):
            text = self.note_edit.text().strip()
            if not text:
                return
            self._write_note(text)
            self.note_edit.clear()

        def _write_note(self, text):
            t = "" if self.latest is None else self.latest["time_ms"]
            self.notes_w.writerow([datetime.now().isoformat(timespec="seconds"), t, text])
            self.notes.flush()
            print(f"--- NOTE at time_ms {t}: {text}")

        # ---- one long run -------------------------------------------------
        def phase_minutes(self, ph):
            steps, _ = parse_schedule(ph["schedule"])
            return sum(s[0] for s in steps) / 60

        def plan_phases(self):
            return FULL_PLAN if self.plan_pi.isChecked() else FULL_PLAN[:1]

        def plan_summary(self):
            parts, total = [], 0.0
            for i, ph in enumerate(self.plan_phases(), 1):
                steps, _ = parse_schedule(ph["schedule"])
                mins = self.phase_minutes(ph)
                total += mins
                parts.append(f"{i}. {ph['name']} ({ph['mode']}): {len(steps)} steps, {mins:.1f} min")
            return "<br>".join(parts) + f"<br>Total {total:.0f} min from one click. STOP cancels the rest."

        def plan_text(self):
            if self.plan is None:
                return "plan not running"
            i, r = self.plan["phase"], self.latest
            phases = self.plan["phases"]
            mins = (r["time_ms"] - self.plan["t_ms"]) / 60000.0
            return (f"<b>phase {i + 1} of {len(phases)}</b>: {phases[i]['name']}<br>"
                    f"schedule step {r['step']}, {mins:.1f} min into this phase")

        def start_plan(self):
            r = self.latest
            if self.plan is not None:
                QtWidgets.QMessageBox.warning(self, "Full plan", "The plan is already running.")
                return
            if r is None or r["run_state"] != 0 or math.isnan(r["TEC_C"]):
                QtWidgets.QMessageBox.warning(
                    self, "Full plan", "Start only when the Arduino is idle (not latched, not running) "
                    "and the TEC thermistor shows a number.")
                return
            text = (self.plan_summary().replace("<br>", "\n")
                    + f"\n\nRAW phase: U = {self.spins['U'].value():g}, U0 = 0, room T = "
                    f"{self.spins['TAMB'].value():g} C.\nRoom-temperature baseline done, TEC supply and pump on?")
            ans = QtWidgets.QMessageBox.question(self, "Full plan", text,
                                                 QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                 QtWidgets.QMessageBox.No)
            if ans != QtWidgets.QMessageBox.Yes:
                return
            self.plan = {"phase": 0, "t_ms": r["time_ms"], "phases": self.plan_phases()}
            self.log_event("PLAN start")
            self._plan_phase(0)

        def _plan_phase(self, i):
            phases = self.plan["phases"]
            ph = phases[i]
            self.plan.update(phase=i, t_ms=self.latest["time_ms"])
            self.mode_box.setCurrentText(ph["mode"])
            if "U0" in ph:
                self.spins["U0"].setValue(ph["U0"])
            self.sched_edit.setPlainText(ph["schedule"])
            self.send_settings()
            self.send_schedule()
            self.send("SCHED START")
            note = f"PLAN phase {i + 1} of {len(phases)} start: {ph['name']} ({ph['mode']})"
            self.log_event(note)
            self._write_note(note)

        def _plan_continue(self, i):
            if self.plan is None or self.plan["phase"] != i - 1 or self._closing:
                return
            self._plan_phase(i)

        def _plan_comment(self, line):
            if self.plan is None:
                return
            if "SCHEDULE DONE" in line:
                i = self.plan["phase"]
                if i + 1 < len(self.plan["phases"]):
                    QtCore.QTimer.singleShot(1500, lambda: self._plan_continue(i + 1))
                else:
                    self.log_event("PLAN finished")
                    self._write_note("PLAN finished")
                    self.plan = None
                    self.plan_label.setText("plan finished")
            elif "SAFETY SHUTDOWN" in line or "REFUSED" in line:
                self.cancel_plan(line.lstrip("# ").strip())

        def cancel_plan(self, reason, warn=True):
            if self.plan is None:
                return
            i = self.plan["phase"]
            self.plan = None
            self.cmd_queue.clear()
            msg = f"PLAN cancelled in phase {i + 1}: {reason}"
            self.log_event(msg)
            self._write_note(msg)
            self.plan_label.setText(f"<span style='color:#C0392B'>{msg}</span>")
            if warn and not self._closing:
                QtWidgets.QMessageBox.warning(self, "Full plan", msg + "\nNothing further is sent.")

        def on_line(self, line):
            if self._closing:
                return
            kind = classify(line)
            if kind in ("comment", "header", "blank"):
                if kind == "comment":
                    print(line)
                    self.log_event(line)
                    self._plan_comment(line)
                return
            if kind == "malformed":
                self.stats.malformed += 1
                self.log_event(f"MALFORMED {line}")
                print(f"!!! malformed: {line}")
                return
            rec = parse_record(line)
            restarted = (self.latest is not None
                         and rec["time_ms"] < self.latest["time_ms"])
            if self.stats.add(rec) == "duplicate":
                self.log_event(f"DUPLICATE {line}")
                return
            if restarted:
                for d in self.buf.values():      # Arduino restarted
                    d.clear()
                self.log_event("RESTART detected (time_ms went backwards)")
                self.cancel_plan("Arduino restarted")
            self.csv_file.write(line.strip() + "\n")    # unchanged
            self.csv_file.flush()
            self.latest = rec
            self.buf["t"].append(rec["time_ms"] / 1000.0)
            for k in COLUMNS:
                self.buf[k].append(rec[k])
            span = self.win_spin.value()
            while self.buf["t"] and self.buf["t"][-1] - self.buf["t"][0] > span:
                for d in self.buf.values():
                    d.popleft()

        def redraw(self):
            if not self.buf["t"]:
                return
            t = list(self.buf["t"])
            for k, c in self.curves.items():
                c.setData(t, list(self.buf[k]), connect="finite")
            for plot in self.plots:
                plot.enableAutoRange(axis="y", enable=True)
            r = self.latest
            state = {0: "idle", 1: "<b style='color:#1a7f37'>RUNNING</b>",
                     2: f"<b style='color:#1a7f37'>SCHEDULE step {r['step']}</b>",
                     9: "<b style='color:#C0392B'>SAFETY LATCHED</b>"}.get(
                         r["run_state"], str(r["run_state"]))

            def f(v):
                return "nan" if math.isnan(v) else f"{v:.2f}"
            self.state_label.setText(state)
            self.time_label.setText(f"t = {r['time_ms'] / 1000:.1f} s")
            self.mode_label.setText(
                f"<b>{r['control_mode']}</b> &nbsp; Ta {r['Ta_C']:g} &nbsp; Tb {r['Tb_C']:g}"
                f"<br>period {r['period_s']:g} s &nbsp; r {r['heating_to_cooling_ratio']:g}")
            for key, lab in self.value_labels.items():
                lab.setText(f"{r[key]:+d}" if key == "signed_pwm" else f(r[key]))
            for key, lab in self.stat_labels.items():
                lab.setText(str(getattr(self.stats, key)))
            if self.plan is not None:
                self.plan_label.setText(self.plan_text())

        def check_saved_file(self):
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Saved record file", DATA_DIR,
                "Text or CSV (*.txt *.csv *.TXT *.CSV);;All files (*)")
            if not path:
                return
            records, stats, segments, counts = check_file(path)
            text = report_text(path, stats, segments, counts)
            print(text)
            self.log_event("IMPORT " + text.replace("\n", " | "))
            if not records:
                QtWidgets.QMessageBox.warning(self, "Saved record file", text)
                return
            win = ImportWindow(path, segments, text)
            win.show()
            self.import_windows.append(win)

        def closeEvent(self, event):
            self.cmd_queue.clear()
            if self.link.send_command("STOP"):
                self.log_event("SENT STOP")
            QtCore.QThread.msleep(300)
            self._closing = True
            self.timer.stop()
            self.link.stop()
            for fh in (self.csv_file, self.events, self.notes):
                fh.close()
            print(f"Closed. {self.stats.text()}")
            super().closeEvent(event)

    base.SERIAL_PORT = base.resolve_port()
    app = QtWidgets.QApplication(sys.argv)
    w = Window(base.SERIAL_PORT)
    w.show()
    sys.exit(app.exec())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-file", help="report on a saved record file and exit")
    a = ap.parse_args()
    if a.check_file:
        _, stats, segments, counts = check_file(a.check_file)
        print(report_text(a.check_file, stats, segments, counts))
        return
    run_gui()


if __name__ == "__main__":
    main()
