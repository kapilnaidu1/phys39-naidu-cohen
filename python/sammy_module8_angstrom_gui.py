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
    sweep 100-200-500).

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
    axis, and the feedforward, controller and applied PWM below,
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
    from PySide6 import QtCore, QtWidgets

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tec_control_gui as base

    CH_COLORS = {"TEC_C": "#000000", "T1_C": "#1f77b4", "T2_C": "#ff7f0e",
                 "T3_C": "#2ca02c", "T4_C": "#9467bd", "T5_C": "#8c564b"}

    def make_plots(layout_parent):
        temp = pg.PlotWidget()
        temp.setBackground("w")
        temp.showGrid(x=True, y=True, alpha=0.25)
        temp.setLabel("left", "Temperature (°C)")
        temp.addLegend(offset=(10, 10))
        curves = {"setpoint_C": temp.plot(
            pen=pg.mkPen("#7f7f7f", width=1.5, style=QtCore.Qt.DashLine),
            name="setpoint", connect="finite")}
        for ch, col in CH_COLORS.items():
            curves[ch] = temp.plot(pen=pg.mkPen(col, width=2 if ch == "TEC_C" else 1.6),
                                   name=ch.replace("_C", ""), connect="finite")
        pwm = pg.PlotWidget()
        pwm.setBackground("w")
        pwm.showGrid(x=True, y=True, alpha=0.25)
        pwm.setLabel("left", "PWM counts")
        pwm.setLabel("bottom", "Arduino time (s)")
        pwm.addLegend(offset=(10, 10))
        pwm.setXLink(temp)
        curves["feedforward_pwm"] = pwm.plot(pen=pg.mkPen("#d62728", width=1.4),
                                             name="feedforward (OL)", connect="finite")
        curves["controller_pwm"] = pwm.plot(pen=pg.mkPen("#aaaaaa", width=1.4),
                                            name="controller (P/PI, raw)", connect="finite")
        curves["signed_pwm"] = pwm.plot(pen=pg.mkPen("#202020", width=1.6),
                                        name="applied signed PWM")
        for y in (255, -255):
            pwm.addLine(y=y, pen=pg.mkPen("#C0392B", width=1, style=QtCore.Qt.DotLine))
        layout_parent.addWidget(temp, stretch=3)
        layout_parent.addWidget(pwm, stretch=2)
        return curves

    class ImportWindow(QtWidgets.QWidget):
        def __init__(self, path, segments, text):
            super().__init__()
            self.setWindowTitle(f"Saved file: {os.path.basename(path)}")
            self.resize(1100, 750)
            lay = QtWidgets.QVBoxLayout(self)
            lab = QtWidgets.QLabel(f"<pre>{text}</pre>")
            lab.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            lay.addWidget(lab)
            curves = make_plots(lay)
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
            self.resize(1250, 900)
            self.stats = StreamStats()
            self.buf = {k: deque() for k in ["t"] + COLUMNS}
            self.latest = None
            self.import_windows = []
            self._closing = False

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
            w = QtWidgets.QWidget()
            self.setCentralWidget(w)
            lay = QtWidgets.QVBoxLayout(w)

            row = QtWidgets.QHBoxLayout()
            self.spins = {}
            row.addWidget(QtWidgets.QLabel("mode"))
            self.mode_box = QtWidgets.QComboBox()
            self.mode_box.addItems(list(MODES))
            self.mode_box.setCurrentText("PI")
            row.addWidget(self.mode_box)
            specs = [("TA", "Ta (°C)", 10, 56, 2, 0.5), ("TB", "Tb (°C)", 0, 23, 2, 0.5),
                     ("PERIOD", "period (s)", 100, 3600, 1, 10), ("KP", "Kp", 0, 100, 3, 0.5),
                     ("KI", "Ki", 0, 5, 4, 0.01), ("TAMB", "room T (°C)", 10, 35, 2, 0.1),
                     ("CHIH", "χh", 0.01, 2, 5, 0.01), ("CHIC", "χc", 0.01, 2, 5, 0.01)]
            for key, label, lo, hi, dec, step in specs:
                row.addWidget(QtWidgets.QLabel(label))
                s = QtWidgets.QDoubleSpinBox()
                s.setRange(lo, hi)
                s.setDecimals(dec)
                s.setSingleStep(step)
                s.setValue(DEFAULTS[key])
                self.spins[key] = s
                row.addWidget(s)
            self.r_label = QtWidgets.QLabel()
            row.addWidget(self.r_label)
            self.spins["CHIH"].valueChanged.connect(self.update_r)
            self.spins["CHIC"].valueChanged.connect(self.update_r)
            self.update_r()
            send = QtWidgets.QPushButton("Send settings")
            send.clicked.connect(self.send_settings)
            row.addWidget(send)
            lay.addLayout(row)

            rowu = QtWidgets.QHBoxLayout()
            rowu.addWidget(QtWidgets.QLabel("RAW mode: u = U0 + U sin(ωt), PWM counts"))
            for key, lo, hi in (("U", 0, 255), ("U0", -255, 255)):
                rowu.addWidget(QtWidgets.QLabel(key))
                s = QtWidgets.QDoubleSpinBox()
                s.setRange(lo, hi)
                s.setDecimals(0)
                s.setSingleStep(5)
                s.setValue(DEFAULTS[key])
                self.spins[key] = s
                rowu.addWidget(s)
            rowu.addWidget(QtWidgets.QLabel("U0 = 0: zero-centered (S18.3); U0 ≥ U: positive only "
                                            "(S18.4). Use the course value of U."))
            rowu.addStretch(1)
            lay.addLayout(rowu)

            row2 = QtWidgets.QHBoxLayout()
            for text, cmd in [("START", "START"), ("STOP", "STOP"),
                              ("CLEAR SAFETY", "CLEAR SAFETY"), ("GET", "GET")]:
                b = QtWidgets.QPushButton(text)
                b.clicked.connect(lambda _=False, c=cmd: self.send(c))
                row2.addWidget(b)
            imp = QtWidgets.QPushButton("Check a saved file")
            imp.clicked.connect(self.check_saved_file)
            row2.addWidget(imp)
            row2.addWidget(QtWidgets.QLabel("window (s)"))
            self.win_spin = QtWidgets.QSpinBox()
            self.win_spin.setRange(60, 20000)
            self.win_spin.setValue(600)
            row2.addWidget(self.win_spin)
            self.note_edit = QtWidgets.QLineEdit()
            self.note_edit.setPlaceholderText("note, e.g. 'room T 21.4 C', then Enter")
            self.note_edit.returnPressed.connect(self.log_note)
            row2.addWidget(self.note_edit, stretch=2)
            lay.addLayout(row2)

            # frequency schedule
            row3 = QtWidgets.QHBoxLayout()
            self.sched_edit = QtWidgets.QPlainTextEdit(SCHEDULE_PRESETS["Fast test"])
            self.sched_edit.setFixedHeight(96)
            self.sched_edit.textChanged.connect(self.update_sched_label)
            row3.addWidget(QtWidgets.QLabel("schedule\n(duration Ta Tb period\nper line)"))
            row3.addWidget(self.sched_edit, stretch=2)
            for name in SCHEDULE_PRESETS:
                b = QtWidgets.QPushButton(name)
                b.clicked.connect(lambda _=False, n=name:
                                  self.sched_edit.setPlainText(SCHEDULE_PRESETS[n]))
                row3.addWidget(b)
            b = QtWidgets.QPushButton("Send schedule")
            b.clicked.connect(self.send_schedule)
            row3.addWidget(b)
            b = QtWidgets.QPushButton("START schedule")
            b.clicked.connect(lambda: self.send("SCHED START"))
            row3.addWidget(b)
            self.sched_label = QtWidgets.QLabel()
            row3.addWidget(self.sched_label)
            lay.addLayout(row3)
            self.update_sched_label()

            self.status = QtWidgets.QLabel("waiting for the Arduino ...")
            self.status.setTextFormat(QtCore.Qt.RichText)
            lay.addWidget(self.status)
            self.curves = make_plots(lay)

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
            t = "" if self.latest is None else self.latest["time_ms"]
            self.notes_w.writerow([datetime.now().isoformat(timespec="seconds"), t, text])
            self.notes.flush()
            print(f"--- NOTE at time_ms {t}: {text}")
            self.note_edit.clear()

        def on_line(self, line):
            if self._closing:
                return
            kind = classify(line)
            if kind in ("comment", "header", "blank"):
                if kind == "comment":
                    print(line)
                    self.log_event(line)
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
            r = self.latest
            state = {0: "idle", 1: "<b style='color:#1a7f37'>RUNNING</b>",
                     2: f"<b style='color:#1a7f37'>SCHEDULE step {r['step']}</b>",
                     9: "<b style='color:#C0392B'>SAFETY LATCHED</b>"}.get(
                         r["run_state"], str(r["run_state"]))

            def f(v):
                return "nan" if math.isnan(v) else f"{v:.2f}"
            self.status.setText(
                f"{state} &nbsp; t = {r['time_ms'] / 1000:.1f} s &nbsp; "
                f"set {f(r['setpoint_C'])} &nbsp; TEC {f(r['TEC_C'])} &nbsp; "
                + " ".join(f"T{i} {f(r[f'T{i}_C'])}" for i in range(1, 6))
                + f" &nbsp; ff {f(r['feedforward_pwm'])} &nbsp; ctrl "
                f"{f(r['controller_pwm'])} &nbsp; PWM {r['signed_pwm']}"
                f" &nbsp; | &nbsp; <b>{r['control_mode']}</b> Ta {r['Ta_C']:g} Tb {r['Tb_C']:g} "
                f"period {r['period_s']:g} s r {r['heating_to_cooling_ratio']:g}"
                f"<br>{self.stats.text()} &nbsp; file "
                f"{os.path.basename(self.csv_path)}")

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
