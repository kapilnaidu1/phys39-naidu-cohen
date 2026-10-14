#!/usr/bin/env python3
"""
Phys 39 Module 6, Part 7. PI temperature control. Naidu / Cohen

Built on the Module 5 P controller, tec_p_control_gui.py. The serial thread,
the measurement parser and the port resolver are imported from
tec_control_gui, as before.

    python3 python/tec_pi_control_gui.py      (from the repository root)

THE CONTROL LAW, all of it in pi_step() below

    e          = T_set - T
    q[n+1]     = q[n] + e[n] dt        dt = time between accepted readings
    u_P        = Kp e
    u_I        = Ki q[n+1]
    u_req      = u_P + u_I
    u_applied  = clamp(u_req, -limit, +limit)

    The sign of u_applied picks HEAT or COOL and |u_applied|, rounded to the
    nearest count, is the PWM sent to the Arduino.

ANTI-WINDUP, conditional integration

    The new q is worked out first. If the command it would give is past the
    PWM limit and the error has the sign that pushes it farther out, the step
    is refused and q keeps its old value. An error of the other sign is always
    integrated, so q can unwind. This is the same test as controller_command()
    in the course simulator Lab_6_7_modeling_tec.py. In P mode q is held at 0
    and u_I is 0, also as in that simulator.

WHAT THE WINDOW ENFORCES

    Mode, Zero integral, PWM limit, anti-windup and the run label can only be
    changed with control OFF, which means the PWM has already been set to 0
    (Part 7, step 3). Setpoint and gains stay live.

    The PWM limit clamp here and the Arduino's temperature shutdown are both
    active in every mode. A SAFETY SHUTDOWN line from the Arduino switches
    control OFF.

    Spin boxes apply a typed value on Enter or when the box loses focus, so a
    half-typed number is never used.

DATA

    Every launch writes a new file, data/module_06/pi_run_YYYYMMDD_HHMMSS.csv,
    so restarting can never overwrite an earlier run.

    time_s, temperature_C   from the Arduino line
    pwm, heat_cool          from the Arduino line: the drive in force when
                            that line was printed, before this update
    setpoint_C, error_C
    dt_s                    time since the previous accepted reading
    q_Cs                    integral state after this update, C s
    u_P, u_I, u_req, u_applied
                            PWM counts, signed, + heats and - cools.
                            With control OFF these are what the controller
                            would ask for; u_applied is then 0.
    pwm_sent                signed integer actually commanded
    saturated               1 if u_req was clipped to the limit
    q_held                  1 if anti-windup refused the integral step
    mode, kp, ki, pwm_limit, anti_windup, control_on, run
                            ki is the value in effect, so 0 in P mode.
                            run is the label set in the window, 0 for
                            anything that is not one of the six retained runs.
"""

import csv
import math
import os
import sys
import time
from collections import deque
from datetime import datetime

import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

import tec_control_gui as base
from tec_control_gui import (SerialLink, parse_measurement,
                             is_measurement_line, resolve_port)

# =====================================================================
# CONFIGURATION
# =====================================================================

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO, "data", "module_06")

WINDOW_SECONDS = 600.0          # an up step and a down step fit on screen
UPDATE_INTERVAL_MS = 200
PWM_FULL_SCALE = 255
GAP_WARNING_S = 2.0             # readings normally arrive about 0.5 s apart

# Used only for the prediction line on screen. Nothing here changes the
# command sent to the TEC.
CHI_HEAT = 0.50127              # C per PWM count, Module 4 heating branch
CHI_COOL = 0.18091              # C per PWM count, Module 4 cooling magnitude
T_AMBIENT = 22.38               # C, plate at PWM 0 on 13 October before
                                # the runs (Module 4 measured 21.54)
TAU_S = 62.9                    # s, Module 6 fit to the Module 5 steps,
                                # which used 500-sample averaging

DEFAULT_SETPOINT = 30.0
DEFAULT_KP = 2.0                # stable in Module 5
DEFAULT_KI = 0.0

COLUMNS = ["time_s", "temperature_C", "pwm", "heat_cool", "setpoint_C",
           "error_C", "dt_s", "q_Cs", "u_P", "u_I", "u_req", "u_applied",
           "pwm_sent", "saturated", "q_held", "mode", "kp", "ki",
           "pwm_limit", "anti_windup", "control_on", "run"]

TEMP_COLOR = "#2ca02c"
SET_COLOR = "#7f7f7f"
ERR_COLOR = "#2ca02c"
UP_COLOR = "#ff7f0e"
UI_COLOR = "#9467bd"
UREQ_COLOR = "#aaaaaa"
UAPP_COLOR = "#202020"
LIMIT_COLOR = "#C0392B"


# =====================================================================
# THE CONTROLLER
# =====================================================================

def pi_step(q, e, dt, kp, ki, limit, mode, anti_windup):
    """One controller update.

    q is the integral state before this reading, e = T_set - T now, dt the
    time since the last accepted reading. Returns
    (q_new, u_P, u_I, u_req, u_applied, q_held).
    """
    u_P = kp * e                                    # proportional part

    if mode == "P":
        q_new, q_held = 0.0, False                  # no integral in P mode
        u_I = 0.0
    else:
        q_trial = q + e * dt                        # q[n+1] = q[n] + e dt
        u_trial = u_P + ki * q_trial
        # conditional integration: refuse the step if the command would be
        # past the limit and this error pushes it farther out
        pushes_out = ((u_trial > limit and e > 0) or
                      (u_trial < -limit and e < 0))
        q_held = anti_windup and pushes_out
        q_new = q if q_held else q_trial
        u_I = ki * q_new                            # integral part

    u_req = u_P + u_I                               # requested command
    u_applied = max(-limit, min(limit, u_req))      # clamped command
    return q_new, u_P, u_I, u_req, u_applied, q_held


def prediction_text(mode, kp, ki, setpoint):
    """One-lump model prediction for the current settings.

    The real plate lags in a way this model does not (Module 6 notes), so
    this is a starting point for choosing gains, not a forecast.
    """
    heating = setpoint >= T_AMBIENT
    chi = CHI_HEAT if heating else CHI_COOL
    side = "heating" if heating else "cooling"
    L = kp * chi
    head = (f"<b>one-lump model, {side} side:</b> L = Kp·χ = "
            f"{kp:.3f} × {chi:.5f} = <b>{L:.3f}</b>")

    if mode == "P":
        droop = (setpoint - T_AMBIENT) / (1.0 + L)
        return (f"{head} &nbsp;|&nbsp; P droop (T<sub>set</sub>"
                f"−T<sub>amb</sub>)/(1+L) = {droop:+.2f} °C, "
                f"settles near <b>{setpoint - droop:.2f} °C</b>")

    ki_crit = (1.0 + L) ** 2 / (4.0 * TAU_S * chi)
    if ki <= 0:
        return (f"{head} &nbsp;|&nbsp; PI with Ki = 0 is P control. "
                f"ζ = 1 at Ki = {ki_crit:.4f}")
    zeta = (1.0 + L) / (2.0 * math.sqrt(TAU_S * chi * ki))
    return (f"{head} &nbsp;|&nbsp; ζ = (1+L)/(2√(τχKi)) "
            f"= <b>{zeta:.2f}</b> with τ = {TAU_S} s &nbsp;|&nbsp; "
            f"ζ = 1 at Ki = {ki_crit:.4f}")


# =====================================================================
# THE WINDOW
# =====================================================================

class PIControlWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phys 39 Module 6, PI temperature control")
        self.resize(1120, 920)

        # ---- controller state ----------------------------------------
        self.control_on = False
        self.mode = "P"
        self.setpoint = DEFAULT_SETPOINT
        self.kp = DEFAULT_KP
        self.ki = DEFAULT_KI
        self.limit = PWM_FULL_SCALE
        self.anti_windup = True
        self.run_label = 0
        self.q = 0.0
        self.t_prev = None
        self.sent_pwm = 0
        self.sent_heating = True

        self.buf = {k: deque() for k in
                    ("t", "T", "set", "e", "uP", "uI", "ureq", "uapp")}

        self._build_ui()

        # ---- CSV, a new file every launch ----------------------------
        self._closing = False
        os.makedirs(DATA_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_path = os.path.join(DATA_DIR, f"pi_run_{stamp}.csv")
        k = 1
        while os.path.exists(self.csv_path):
            self.csv_path = os.path.join(DATA_DIR, f"pi_run_{stamp}_{k}.csv")
            k += 1
        self.csv_file = open(self.csv_path, "x", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(COLUMNS)
        self.csv_file.flush()
        print(f"Writing to {self.csv_path}")

        # ---- serial ---------------------------------------------------
        self.link = SerialLink(base.SERIAL_PORT, base.BAUD_RATE)
        self.link.line_received.connect(self.on_line)
        self.link.error.connect(self.on_serial_error)
        self.link.start()

        self.redraw_timer = QtCore.QTimer(self)
        self.redraw_timer.timeout.connect(self.update_plots)
        self.redraw_timer.start(UPDATE_INTERVAL_MS)

        # PWM 0 once the Arduino has finished its reset.
        QtCore.QTimer.singleShot(2600, lambda: self.send_pwm(0, True))

    # -----------------------------------------------------------------
    def _build_ui(self):
        pg.setConfigOptions(antialias=True)
        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")

        self.setStyleSheet("""
            QWidget { background: #FFFFFF; color: #202020;
                      font-family: -apple-system, Helvetica, Arial; }
            QLabel#big   { font-size: 18px; font-weight: 600; }
            QLabel#unit  { font-size: 11px; color: #777777; }
            QLabel#loop  { font-size: 12px; color: #1F4E79;
                           background: #EEF4FA; padding: 6px 9px;
                           border: 1px solid #C9DCEC; border-radius: 4px; }
            QDoubleSpinBox, QSpinBox { font-size: 15px; padding: 3px 6px;
                             border: 1px solid #BBBBBB; border-radius: 3px;
                             min-width: 80px; }
            QCheckBox, QRadioButton { font-size: 14px; }
            QCheckBox#enable { font-size: 15px; font-weight: 600; }
            QPushButton { font-size: 14px; padding: 6px 14px;
                          border: 1px solid #C0392B; border-radius: 4px;
                          background: #FDEDEC; color: #C0392B;
                          font-weight: 600; }
            QPushButton:hover { background: #F9D9D6; }
            QPushButton#plain { border: 1px solid #BBBBBB; background: #F4F4F4;
                                color: #333333; font-weight: 500; }
            QPushButton#plain:hover { background: #E8E8E8; }
            QPushButton:disabled { color: #AAAAAA; border-color: #DDDDDD;
                                   background: #F8F8F8; }
            QGroupBox { font-size: 11px; color: #666666;
                        border: 1px solid #DDDDDD; border-radius: 4px;
                        margin-top: 8px; padding-top: 8px; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px;
                               padding: 0 4px; }
        """)

        # ---- readouts -------------------------------------------------
        def tile(caption):
            box = QtWidgets.QVBoxLayout()
            box.setSpacing(0)
            value = QtWidgets.QLabel("---")
            value.setObjectName("big")
            unit = QtWidgets.QLabel(caption)
            unit.setObjectName("unit")
            box.addWidget(value)
            box.addWidget(unit)
            return box, value

        row1 = QtWidgets.QHBoxLayout()
        row1.setSpacing(22)
        b, self.temp_label = tile("T  (°C)");                 row1.addLayout(b)
        b, self.set_label = tile("setpoint  (°C)");           row1.addLayout(b)
        b, self.err_label = tile("e = Tset − T  (°C)");  row1.addLayout(b)
        b, self.q_label = tile("q  (°C s)");                  row1.addLayout(b)
        b, self.up_label = tile("u_P = Kp e");                      row1.addLayout(b)
        b, self.ui_label = tile("u_I = Ki q");                      row1.addLayout(b)
        b, self.ureq_label = tile("u requested");                   row1.addLayout(b)
        b, self.uapp_label = tile("u applied (sent)");              row1.addLayout(b)
        b, self.state_label = tile("status");                       row1.addLayout(b)
        row1.addStretch(1)
        self.set_label.setText(f"{self.setpoint:.1f}")
        self.q_label.setText("0.00")
        self.state_label.setText("OFF")

        self.pred_label = QtWidgets.QLabel("")
        self.pred_label.setObjectName("loop")
        self.pred_label.setWordWrap(True)

        # ---- controls -------------------------------------------------
        def dspin(lo, hi, step, decimals, value, suffix=""):
            s = QtWidgets.QDoubleSpinBox()
            s.setRange(lo, hi)
            s.setSingleStep(step)
            s.setDecimals(decimals)
            s.setKeyboardTracking(False)
            if suffix:
                s.setSuffix(suffix)
            s.setValue(value)
            return s

        self.set_spin = dspin(5.0, 55.0, 0.5, 1, self.setpoint, " °C")
        self.set_spin.valueChanged.connect(self.on_setpoint_changed)
        self.kp_spin = dspin(0.0, 500.0, 0.25, 3, self.kp)
        self.kp_spin.valueChanged.connect(self.on_kp_changed)
        self.ki_spin = dspin(0.0, 50.0, 0.005, 4, self.ki)
        self.ki_spin.valueChanged.connect(self.on_ki_changed)

        self.limit_spin = QtWidgets.QSpinBox()
        self.limit_spin.setRange(1, PWM_FULL_SCALE)
        self.limit_spin.setKeyboardTracking(False)
        self.limit_spin.setValue(self.limit)
        self.limit_spin.valueChanged.connect(self.on_limit_changed)

        self.run_spin = QtWidgets.QSpinBox()
        self.run_spin.setRange(0, 6)
        self.run_spin.setKeyboardTracking(False)
        self.run_spin.setValue(self.run_label)
        self.run_spin.valueChanged.connect(self.on_run_changed)

        self.p_radio = QtWidgets.QRadioButton("P")
        self.pi_radio = QtWidgets.QRadioButton("PI")
        self.p_radio.setChecked(True)
        self.pi_radio.toggled.connect(self.on_mode_toggled)

        self.aw_box = QtWidgets.QCheckBox("anti-windup")
        self.aw_box.setChecked(self.anti_windup)
        self.aw_box.toggled.connect(self.on_anti_windup_toggled)

        self.zero_btn = QtWidgets.QPushButton("Zero integral")
        self.zero_btn.setObjectName("plain")
        self.zero_btn.clicked.connect(self.on_zero_integral)

        self.enable_box = QtWidgets.QCheckBox("Control ON")
        self.enable_box.setObjectName("enable")
        self.enable_box.toggled.connect(self.on_enable_toggled)

        self.stop_btn = QtWidgets.QPushButton("STOP, PWM to 0")
        self.stop_btn.clicked.connect(self.on_stop)

        self.rescale_btn = QtWidgets.QPushButton("Rescale plots")
        self.rescale_btn.setObjectName("plain")
        self.rescale_btn.clicked.connect(self.rescale_plots)

        def labelled(text, widget):
            box = QtWidgets.QHBoxLayout()
            box.setSpacing(5)
            box.addWidget(QtWidgets.QLabel(text))
            box.addWidget(widget)
            return box

        live = QtWidgets.QGroupBox("live: can change while running")
        r2 = QtWidgets.QHBoxLayout()
        r2.setSpacing(14)
        r2.addLayout(labelled("Setpoint", self.set_spin))
        r2.addLayout(labelled("Kp (PWM/°C)", self.kp_spin))
        r2.addLayout(labelled("Ki (PWM/°C s)", self.ki_spin))
        r2.addStretch(1)
        r2.addWidget(self.enable_box)
        r2.addWidget(self.stop_btn)
        live.setLayout(r2)

        fixed = QtWidgets.QGroupBox("per run: only with control OFF")
        r3 = QtWidgets.QHBoxLayout()
        r3.setSpacing(14)
        r3.addWidget(QtWidgets.QLabel("Mode"))
        r3.addWidget(self.p_radio)
        r3.addWidget(self.pi_radio)
        r3.addSpacing(8)
        r3.addLayout(labelled("PWM limit", self.limit_spin))
        r3.addWidget(self.aw_box)
        r3.addLayout(labelled("Run", self.run_spin))
        r3.addWidget(self.zero_btn)
        r3.addStretch(1)
        r3.addWidget(self.rescale_btn)
        fixed.setLayout(r3)
        self.per_run_widgets = (self.p_radio, self.pi_radio, self.limit_spin,
                                self.aw_box, self.run_spin, self.zero_btn)

        # ---- plots ----------------------------------------------------
        # Axis labels are plain text, not pyqtgraph units, so the axes never
        # rescale to ks or "mC" on their own.
        self.temp_plot = pg.PlotWidget()
        self.temp_plot.setLabel("left", "Temperature (°C)")
        self.temp_plot.showGrid(x=True, y=True, alpha=0.3)
        self.set_curve = self.temp_plot.plot(
            pen=pg.mkPen(SET_COLOR, width=1.6, style=QtCore.Qt.DashLine))
        self.temp_curve = self.temp_plot.plot(pen=pg.mkPen(TEMP_COLOR, width=2))

        self.err_plot = pg.PlotWidget()
        self.err_plot.setLabel("left", "Error e (°C)")
        self.err_plot.showGrid(x=True, y=True, alpha=0.3)
        self.err_plot.addItem(pg.InfiniteLine(
            pos=0, angle=0, pen=pg.mkPen("#999999", width=1.2,
                                         style=QtCore.Qt.DashLine)))
        self.err_curve = self.err_plot.plot(pen=pg.mkPen(ERR_COLOR, width=2))
        self.err_plot.setXLink(self.temp_plot)

        self.u_plot = pg.PlotWidget()
        self.u_plot.setLabel("bottom", "Time (s)")
        self.u_plot.setLabel("left", "Command (PWM counts)")
        self.u_plot.showGrid(x=True, y=True, alpha=0.3)
        # The limit lines do not set the y range, otherwise a 255 limit would
        # squash a 20-count command flat. They come into view when u nears them.
        lim_pen = pg.mkPen(LIMIT_COLOR, width=1.2, style=QtCore.Qt.DashLine)
        self.lim_hi = pg.InfiniteLine(pos=self.limit, angle=0, pen=lim_pen)
        self.lim_lo = pg.InfiniteLine(pos=-self.limit, angle=0, pen=lim_pen)
        self.u_plot.addItem(self.lim_hi, ignoreBounds=True)
        self.u_plot.addItem(self.lim_lo, ignoreBounds=True)
        self.ureq_curve = self.u_plot.plot(
            pen=pg.mkPen(UREQ_COLOR, width=1.5, style=QtCore.Qt.DotLine),
            connect="finite")
        self.up_curve = self.u_plot.plot(pen=pg.mkPen(UP_COLOR, width=1.6),
                                         connect="finite")
        self.ui_curve = self.u_plot.plot(pen=pg.mkPen(UI_COLOR, width=1.6),
                                         connect="finite")
        self.uapp_curve = self.u_plot.plot(pen=pg.mkPen(UAPP_COLOR, width=2))
        self.u_plot.setXLink(self.temp_plot)

        legend = QtWidgets.QLabel(
            f"<span style='color:{UAPP_COLOR}'><b>&#9644; u applied</b></span>"
            f"&nbsp;&nbsp;&nbsp;<span style='color:{UP_COLOR}'><b>&#9644; u_P"
            f"</b></span>&nbsp;&nbsp;&nbsp;<span style='color:{UI_COLOR}'><b>"
            f"&#9644; u_I</b></span>&nbsp;&nbsp;&nbsp;<span style='color:"
            f"#888888'>&middot;&middot;&middot; u requested</span>&nbsp;&nbsp;"
            f"&nbsp;<span style='color:{LIMIT_COLOR}'>&#9476;&#9476; PWM limit"
            f"</span>&nbsp;&nbsp;&nbsp;+ heats, &minus; cools")

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(14, 12, 14, 10)
        layout.setSpacing(8)
        layout.addLayout(row1)
        layout.addWidget(self.pred_label)
        layout.addWidget(live)
        layout.addWidget(fixed)
        layout.addWidget(self.temp_plot, stretch=4)
        layout.addWidget(self.err_plot, stretch=2)
        layout.addWidget(legend)
        layout.addWidget(self.u_plot, stretch=3)

        central = QtWidgets.QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self._sync_widgets()

    # -----------------------------------------------------------------
    # HELPERS
    # -----------------------------------------------------------------
    def _effective_ki(self):
        return self.ki if self.mode == "PI" else 0.0

    def _sync_widgets(self):
        # On macOS a disabled radio button or check box is drawn as if it
        # were unticked, which made P and anti-windup look switched off
        # during the 13 October runs. Those three are locked by ignoring the
        # mouse and keyboard instead, so they keep showing their real state.
        for w in self.per_run_widgets:
            if w in (self.p_radio, self.pi_radio, self.aw_box):
                w.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents,
                               self.control_on)
                w.setFocusPolicy(QtCore.Qt.NoFocus if self.control_on
                                 else QtCore.Qt.StrongFocus)
            else:
                w.setEnabled(not self.control_on)
        self.ki_spin.setEnabled(self.mode == "PI")
        self.pred_label.setText(prediction_text(
            self.mode, self.kp, self._effective_ki(), self.setpoint))

    def send_pwm(self, n, heating):
        d = "HEAT" if heating else "COOL"
        self.link.send_command(f"SET PWM {n} DIR {d}")
        self.sent_pwm = n
        if n > 0:
            self.sent_heating = heating

    def _settings(self):
        return (f"mode {self.mode}, Kp {self.kp:.3f}, Ki "
                f"{self._effective_ki():.4f}, limit {self.limit}, "
                f"anti-windup {'on' if self.anti_windup else 'off'}, "
                f"run {self.run_label}")

    # -----------------------------------------------------------------
    # UI EVENTS
    # -----------------------------------------------------------------
    def on_setpoint_changed(self, value):
        self.setpoint = float(value)
        self.set_label.setText(f"{self.setpoint:.1f}")
        self._sync_widgets()
        T = self.buf["T"][-1] if self.buf["T"] else float("nan")
        print(f"\n--- setpoint {self.setpoint:.1f} C, T = {T:.2f} C, "
              f"control {'ON' if self.control_on else 'OFF'} ---")

    def on_kp_changed(self, value):
        self.kp = float(value)
        self._sync_widgets()
        print(f"\n--- Kp {self.kp:.3f} ---")

    def on_ki_changed(self, value):
        self.ki = float(value)
        self._sync_widgets()
        print(f"\n--- Ki {self.ki:.4f} ---")

    def on_limit_changed(self, value):
        self.limit = int(value)
        self.lim_hi.setPos(self.limit)
        self.lim_lo.setPos(-self.limit)

    def on_run_changed(self, value):
        self.run_label = int(value)

    def _show_locked_settings(self):
        """Put the mode and anti-windup boxes back to the values in force."""
        for w, state in ((self.pi_radio, self.mode == "PI"),
                         (self.p_radio, self.mode == "P"),
                         (self.aw_box, self.anti_windup)):
            w.blockSignals(True)
            w.setChecked(state)
            w.blockSignals(False)

    def on_mode_toggled(self, pi_checked):
        if self.control_on:             # locked while running
            self._show_locked_settings()
            return
        self.mode = "PI" if pi_checked else "P"
        if self.mode == "P":
            self.q = 0.0                # P mode carries no integral state
            self.q_label.setText("0.00")
        self._sync_widgets()

    def on_anti_windup_toggled(self, on):
        if self.control_on:             # locked while running
            self._show_locked_settings()
            return
        self.anti_windup = bool(on)

    def on_zero_integral(self):
        # Only reachable with control OFF, so the PWM is already 0.
        self.q = 0.0
        self.q_label.setText("0.00")
        print("\n--- integral state q set to 0 ---")

    def on_enable_toggled(self, on):
        self.control_on = bool(on)
        if not on:
            self.send_pwm(0, self.sent_heating)
            self.state_label.setText("OFF")
            print("\n--- control OFF, PWM commanded to 0 ---")
        else:
            T = self.buf["T"][-1] if self.buf["T"] else float("nan")
            print(f"\n--- control ON: setpoint {self.setpoint:.1f} C, "
                  f"T = {T:.2f} C, q = {self.q:.2f} C s, {self._settings()} ---")
        self._sync_widgets()

    def on_stop(self):
        self.enable_box.setChecked(False)
        self.send_pwm(0, self.sent_heating)

    # -----------------------------------------------------------------
    # DATA
    # -----------------------------------------------------------------
    def on_line(self, line):
        if self._closing:
            return

        m = parse_measurement(line)
        if m is None:
            if is_measurement_line(line):
                print("   (divider reading unusable, nothing logged)")
            else:
                text = line.strip()
                if text:
                    print(text)
                if "SAFETY SHUTDOWN" in text and self.control_on:
                    self.enable_box.setChecked(False)
                    print("!!! Arduino latched a safety shutdown. "
                          "Control switched OFF. !!!")
            return

        time_s, T, pwm, heat_cool = m

        # dt from the actual spacing of accepted readings
        dt = 0.0 if self.t_prev is None else time_s - self.t_prev
        self.t_prev = time_s
        if dt < 0:
            print("!!! Arduino clock went backwards, it has probably reset. "
                  "dt set to 0 for this reading. !!!")
            dt = 0.0

        e = self.setpoint - T
        ki = self._effective_ki()

        if self.control_on:
            if dt > GAP_WARNING_S:
                print(f"!!! {dt:.1f} s since the last good reading. "
                      f"Stop if this repeats. !!!")
            (self.q, u_P, u_I, u_req,
             u_app, held) = pi_step(self.q, e, dt, self.kp, ki, self.limit,
                                    self.mode, self.anti_windup)
            n = int(abs(u_app) + 0.5)           # nearest count, half up
            heating = u_app >= 0
            if n != self.sent_pwm or (n > 0 and heating != self.sent_heating):
                self.send_pwm(n, heating)
            sent = n if heating else -n
        else:
            u_P, u_I = self.kp * e, ki * self.q
            u_req, u_app, held, sent = u_P + u_I, 0.0, False, 0

        saturated = not math.isclose(u_req, u_app) and self.control_on

        state = "OFF"
        if self.control_on:
            state = self.mode
            if saturated:
                state += " SAT"
            if held:
                state += " q held"
        print(f"t = {time_s:8.2f}  T = {T:6.2f}  e = {e:+6.2f}  q = "
              f"{self.q:+8.2f}  uP = {u_P:+7.1f}  uI = {u_I:+7.1f}  "
              f"u = {sent:+4d}  [{state}]")

        # Plot only: with control OFF nothing is sent, so u_P, u_I and u_req
        # are left blank on screen rather than drawn as if they were driving
        # the TEC. The CSV row below still records them.
        nan = float("nan")
        on = self.control_on
        b = self.buf
        for k, v in (("t", time_s), ("T", T), ("set", self.setpoint),
                     ("e", e), ("uP", u_P if on else nan),
                     ("uI", u_I if on else nan), ("ureq", u_req if on else nan),
                     ("uapp", u_app if on else 0.0)):
            b[k].append(v)
        while b["t"] and (time_s - b["t"][0]) > WINDOW_SECONDS:
            for d in b.values():
                d.popleft()

        self.csv_writer.writerow([
            f"{time_s:.2f}", f"{T:.2f}", pwm, heat_cool,
            f"{self.setpoint:.2f}", f"{e:.3f}", f"{dt:.3f}",
            f"{self.q:.3f}", f"{u_P:.3f}", f"{u_I:.3f}", f"{u_req:.3f}",
            f"{u_app:.3f}", sent, int(saturated), int(held), self.mode,
            f"{self.kp:.4f}", f"{ki:.5f}", self.limit,
            int(self.anti_windup), int(self.control_on), self.run_label])
        self.csv_file.flush()

        self.temp_label.setText(f"{T:.2f}")
        self.err_label.setText(f"{e:+.2f}")
        self.q_label.setText(f"{self.q:+.2f}")
        self.up_label.setText(f"{u_P:+.1f}")
        self.ui_label.setText(f"{u_I:+.1f}")
        self.ureq_label.setText(f"{u_req:+.1f}")
        self.uapp_label.setText(f"{sent:+d}")
        self.state_label.setText(state)
        self.state_label.setStyleSheet(
            "color: #C0392B;" if ("SAT" in state or "held" in state) else "")

    def on_serial_error(self, message):
        print(f"\nSerial error: {message}", file=sys.stderr)

    # -----------------------------------------------------------------
    # PLOTS
    # -----------------------------------------------------------------
    def rescale_plots(self):
        """Put every view back on the data. Changes nothing but the view."""
        for plot in (self.temp_plot, self.err_plot, self.u_plot):
            plot.enableAutoRange(axis="x", enable=True)
            plot.enableAutoRange(axis="y", enable=True)
        if self.buf["t"]:
            self.temp_plot.setXRange(self.buf["t"][0], self.buf["t"][-1],
                                     padding=0.02)

    def update_plots(self):
        b = self.buf
        if not b["t"]:
            return
        t = list(b["t"])
        self.temp_plot.setXRange(t[0], t[-1], padding=0.02)
        temps, sets = list(b["T"]), list(b["set"])
        self.temp_curve.setData(t, temps)
        self.set_curve.setData(t, sets)
        self.err_curve.setData(t, list(b["e"]))
        self.up_curve.setData(t, list(b["uP"]))
        self.ui_curve.setData(t, list(b["uI"]))
        self.ureq_curve.setData(t, list(b["ureq"]))
        self.uapp_curve.setData(t, list(b["uapp"]))

        lo = min(min(temps), min(sets)) - 1.0
        hi = max(max(temps), max(sets)) + 1.0
        if hi - lo < 6.0:
            c = 0.5 * (lo + hi)
            lo, hi = c - 3.0, c + 3.0
        self.temp_plot.setYRange(lo, hi, padding=0)

    def closeEvent(self, event):
        self.control_on = False
        self.send_pwm(0, self.sent_heating)
        time.sleep(0.15)
        self._closing = True
        self.redraw_timer.stop()
        self.link.stop()
        self.csv_file.close()
        print(f"\nClosed. PWM commanded to 0. Data in {self.csv_path}")
        super().closeEvent(event)


def main():
    base.SERIAL_PORT = resolve_port()
    app = QtWidgets.QApplication(sys.argv)
    w = PIControlWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
