#!/usr/bin/env python3
"""
Phys 39 Module 5. P-only temperature control. Naidu / Cohen

Closes the loop the Module 4 GUI left open:

    e = T_set - T          error, degrees C
    u = Kp * e             signed PWM command
    sign(u) -> direction,  P = |u| clamped to 0..255 -> Arduino

Run from the repository root:

    python3 python/tec_p_control_gui.py

WHAT THIS FILE DOES AND DOES NOT OWN

    The serial thread, the measurement-line parser and the port resolver are
    imported from tec_control_gui rather than copied. Those took a long time
    to get right (a Qt shutdown race, a device node that changes when the
    cable moves) and having two copies would mean fixing each bug twice.

    What is new here is the control law, the setpoint and gain controls, the
    error plot, and two extra CSV columns.

DIVISION OF AUTHORITY, which is the safety argument

    Python decides what to ask for. The Arduino decides what to do. The
    software temperature limit from Module 4 lives in the sketch and is not
    reachable from here: if the plate passes temperatureLimitC the sketch
    latches both bridge inputs LOW and refuses further drive whatever this
    program sends. A runaway gain can therefore make the loop oscillate or
    saturate, but it cannot defeat the interlock.

THE ONE THING WORTH UNDERSTANDING BEFORE TOUCHING Kp

    Kp has units of PWM counts per degree C, so its bare numerical value
    means nothing on its own. What decides whether feedback is weak or
    strong is the DIMENSIONLESS loop gain

        L = Kp * chi_T,u

    with chi_T,u the open-loop susceptibility in C per PWM count measured in
    Module 4. The fraction of the initial error that survives at steady state
    is 1/(1+L), so L is the number to reason with and Kp is only how you dial
    it in. The readout shows both.
"""

import csv
import sys
import time
from collections import deque

import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

# Shared with the Module 4 manual GUI. Importing rather than copying keeps
# the serial layer and the parser in one place.
import tec_control_gui as base
from tec_control_gui import (SerialLink, parse_measurement,
                             is_measurement_line, resolve_port)

# =====================================================================
# CONFIGURATION
# =====================================================================

SERIAL_PORT = base.SERIAL_PORT
BAUD_RATE = base.BAUD_RATE

WINDOW_SECONDS = 400.0        # wider than Module 4: a droop run is long
UPDATE_INTERVAL_MS = 200

PWM_MIN, PWM_MAX = 0, 255

CSV_FILENAME = "data/module_05/p_control_run.csv"

HEAT_COLOR = "#d62728"
COOL_COLOR = "#1f77b4"
SET_COLOR = "#7f7f7f"
ERR_COLOR = "#2ca02c"

# Measured in Module 4 and used only to display L. Changing it changes no
# control action, just the number on screen.
CHI_HEAT = 0.50127            # C per PWM count, heating branch
CHI_COOL = 0.18091            # C per PWM count, cooling magnitude

DEFAULT_SETPOINT = 30.0       # C, inside the 30 to 35 band the module asks for
DEFAULT_KP = 0.25             # PWM counts per C. Deliberately small: L = 0.13


class PControlWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phys 39 Module 5, P-only temperature control")
        self.resize(1040, 820)

        # ---- controller state ----------------------------------------
        self.p_enabled = False
        self.setpoint = DEFAULT_SETPOINT
        self.kp = DEFAULT_KP
        self.commanded_pwm = 0
        self.commanded_heating = True
        self.last_error = float("nan")

        self.times = deque()
        self.temperatures = deque()
        self.errors = deque()
        self.pwm_heat = deque()
        self.pwm_cool = deque()

        self._build_ui()

        # ---- CSV ------------------------------------------------------
        self._closing = False
        self.csv_path = CSV_FILENAME
        self.csv_file = open(self.csv_path, "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        # Two columns beyond Module 4's: without setpoint and error stored
        # alongside, a droop run cannot be re-analysed later.
        self.csv_writer.writerow(["time_s", "temperature_C", "pwm",
                                  "heat_cool", "setpoint_C", "error_C",
                                  "kp", "p_enabled"])
        self.csv_file.flush()
        print(f"Writing to {self.csv_path}")

        # ---- serial ---------------------------------------------------
        self.link = SerialLink(SERIAL_PORT, BAUD_RATE)
        self.link.line_received.connect(self.on_line)
        self.link.error.connect(self.on_serial_error)
        self.link.start()

        self.redraw_timer = QtCore.QTimer(self)
        self.redraw_timer.timeout.connect(self.update_plots)
        self.redraw_timer.start(UPDATE_INTERVAL_MS)

        QtCore.QTimer.singleShot(2600, self.send_command)

    # -----------------------------------------------------------------
    def _build_ui(self):
        pg.setConfigOptions(antialias=True)
        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")

        big = lambda w: (w.setFont(self._f(15)) or w)

        self.temp_label = QtWidgets.QLabel("T = --- C")
        self.set_label = QtWidgets.QLabel(f"set = {self.setpoint:.1f} C")
        self.err_label = QtWidgets.QLabel("e = --- C")
        self.pwm_label = QtWidgets.QLabel("PWM = 0")
        self.dir_label = QtWidgets.QLabel("dir = ---")
        self.loop_label = QtWidgets.QLabel("")
        for w in (self.temp_label, self.set_label, self.err_label,
                  self.pwm_label, self.dir_label, self.loop_label):
            big(w)
        self.loop_label.setStyleSheet("color: #1f4e79;")

        row1 = QtWidgets.QHBoxLayout()
        for w in (self.temp_label, self.set_label, self.err_label,
                  self.pwm_label, self.dir_label):
            row1.addWidget(w)
        row1.addStretch(1)

        # ---- controls -------------------------------------------------
        self.set_spin = QtWidgets.QDoubleSpinBox()
        self.set_spin.setRange(5.0, 55.0)
        self.set_spin.setSingleStep(0.5)
        self.set_spin.setDecimals(1)
        self.set_spin.setSuffix(" C")
        self.set_spin.setValue(self.setpoint)
        self.set_spin.valueChanged.connect(self.on_setpoint_changed)

        self.kp_spin = QtWidgets.QDoubleSpinBox()
        self.kp_spin.setRange(0.0, 200.0)
        self.kp_spin.setSingleStep(0.25)
        self.kp_spin.setDecimals(3)
        self.kp_spin.setSuffix(" PWM/C")
        self.kp_spin.setValue(self.kp)
        self.kp_spin.valueChanged.connect(self.on_kp_changed)

        self.enable_box = QtWidgets.QCheckBox("P control ON")
        self.enable_box.toggled.connect(self.on_enable_toggled)

        self.stop_btn = QtWidgets.QPushButton("STOP, PWM to 0")
        self.stop_btn.clicked.connect(self.on_stop)

        row2 = QtWidgets.QHBoxLayout()
        row2.addWidget(QtWidgets.QLabel("Setpoint"))
        row2.addWidget(self.set_spin)
        row2.addSpacing(14)
        row2.addWidget(QtWidgets.QLabel("Kp"))
        row2.addWidget(self.kp_spin)
        row2.addSpacing(14)
        row2.addWidget(self.enable_box)
        row2.addSpacing(14)
        row2.addWidget(self.stop_btn)
        row2.addStretch(1)

        # ---- plots ----------------------------------------------------
        self.temp_plot = pg.PlotWidget()
        self.temp_plot.setLabel("bottom", "Time", units="s")
        self.temp_plot.setLabel("left", "Temperature", units="C")
        self.temp_plot.showGrid(x=True, y=True, alpha=0.3)
        self.temp_curve = self.temp_plot.plot(
            pen=pg.mkPen("#2ca02c", width=2))
        # The setpoint drawn as a line is what makes droop visible: the gap
        # between the trace and this line IS the thing being measured.
        self.set_line = pg.InfiniteLine(
            pos=self.setpoint, angle=0,
            pen=pg.mkPen(SET_COLOR, width=1.4, style=QtCore.Qt.DashLine))
        self.temp_plot.addItem(self.set_line)

        self.err_plot = pg.PlotWidget()
        self.err_plot.setLabel("bottom", "Time", units="s")
        self.err_plot.setLabel("left", "Error e = Tset - T", units="C")
        self.err_plot.showGrid(x=True, y=True, alpha=0.3)
        self.err_plot.addItem(pg.InfiniteLine(
            pos=0, angle=0, pen=pg.mkPen("#999999", width=1.2,
                                         style=QtCore.Qt.DashLine)))
        self.err_curve = self.err_plot.plot(pen=pg.mkPen(ERR_COLOR, width=2))
        self.err_plot.setXLink(self.temp_plot)

        self.pwm_plot = pg.PlotWidget()
        self.pwm_plot.setLabel("bottom", "Time", units="s")
        self.pwm_plot.setLabel("left", "PWM magnitude")
        self.pwm_plot.showGrid(x=True, y=True, alpha=0.3)
        self.pwm_plot.setYRange(PWM_MIN - 5, PWM_MAX + 5)
        self.pwm_heat_curve = self.pwm_plot.plot(
            pen=pg.mkPen(HEAT_COLOR, width=2), connect="finite")
        self.pwm_cool_curve = self.pwm_plot.plot(
            pen=pg.mkPen(COOL_COLOR, width=2), connect="finite")
        self.pwm_plot.setXLink(self.temp_plot)

        legend = QtWidgets.QLabel(
            "<span style='color:#d62728'><b>&#9644; heating</b></span>"
            "&nbsp;&nbsp;<span style='color:#1f77b4'><b>&#9644; cooling</b>"
            "</span>&nbsp;&nbsp;<span style='color:#7f7f7f'>- - setpoint"
            "</span>")

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(row1)
        layout.addWidget(self.loop_label)
        layout.addLayout(row2)
        layout.addWidget(self.temp_plot, stretch=3)
        layout.addWidget(self.err_plot, stretch=2)
        layout.addWidget(legend)
        layout.addWidget(self.pwm_plot, stretch=2)

        central = QtWidgets.QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self._refresh_loop_label()

    @staticmethod
    def _f(pt):
        f = QtWidgets.QApplication.font()
        f.setPointSize(pt)
        return f

    # -----------------------------------------------------------------
    # CONTROL
    # -----------------------------------------------------------------
    def _refresh_loop_label(self):
        """Show the dimensionless loop gain, not just Kp.

        Kp on its own is uninterpretable because it carries units. L tells
        you where you are: L << 1 is weak feedback with most of the error
        surviving, L ~ 1 is comparable, L >> 1 is strong. The predicted
        fractional droop 1/(1+L) is printed beside it so the number can be
        checked against the run as it happens.
        """
        chi = CHI_HEAT if self.commanded_heating else CHI_COOL
        L = self.kp * chi
        frac = 1.0 / (1.0 + L) if L > -1 else float("nan")
        self.loop_label.setText(
            f"L = Kp × χ = {self.kp:.3f} × {chi:.5f} = "
            f"{L:.3f}      predicted fractional droop 1/(1+L) = {frac:.3f}"
            f"      χ used: {'heating' if self.commanded_heating else 'cooling'}"
        )

    def compute_command(self, temperature_c):
        """The entire control law. Returns (pwm_magnitude, heating)."""
        e = self.setpoint - temperature_c
        self.last_error = e

        u = self.kp * e                 # signed PWM, counts
        heating = u >= 0.0              # sign selects direction
        p = int(round(abs(u)))          # magnitude, then clamp
        p = max(PWM_MIN, min(PWM_MAX, p))
        return p, heating

    def send_command(self):
        d = "HEAT" if self.commanded_heating else "COOL"
        self.link.send_command(f"SET PWM {self.commanded_pwm} DIR {d}")

    # -----------------------------------------------------------------
    # UI EVENTS
    # -----------------------------------------------------------------
    def on_setpoint_changed(self, value):
        self.setpoint = float(value)
        self.set_line.setPos(self.setpoint)
        self.set_label.setText(f"set = {self.setpoint:.1f} C")
        self._refresh_loop_label()

    def on_kp_changed(self, value):
        self.kp = float(value)
        self._refresh_loop_label()

    def on_enable_toggled(self, on):
        self.p_enabled = bool(on)
        if not on:
            # Leaving the loop open must not leave the actuator driven.
            self.commanded_pwm = 0
            self.send_command()
            print("\n--- P control OFF, PWM commanded to 0 ---")
        else:
            print(f"\n--- P control ON: setpoint {self.setpoint:.1f} C, "
                  f"Kp {self.kp:.3f} PWM/C, L "
                  f"{self.kp * (CHI_HEAT if self.commanded_heating else CHI_COOL):.3f} ---")

    def on_stop(self):
        self.enable_box.setChecked(False)
        self.commanded_pwm = 0
        self.send_command()

    # -----------------------------------------------------------------
    # DATA
    # -----------------------------------------------------------------
    def on_line(self, line):
        if self._closing:
            return

        measurement = parse_measurement(line)
        if measurement is None:
            if is_measurement_line(line):
                print("   (divider reading unusable, nothing logged)")
            else:
                text = line.strip()
                if text:
                    print(text)
                if "SAFETY SHUTDOWN" in text and self.p_enabled:
                    # The sketch has latched. Open the loop so the GUI stops
                    # asking for drive that is being refused, and so the
                    # operator is not left thinking control is still running.
                    self.enable_box.setChecked(False)
                    print("!!! Arduino latched a safety shutdown. "
                          "P control switched OFF. !!!")
            return

        time_s, temperature_c, pwm, heat_cool = measurement

        # ---- the loop closes here -------------------------------------
        # One control update per measurement. The Arduino reports about once
        # a second after averaging 1000 samples, so that sets the loop rate;
        # there is no point computing a new command more often than the
        # measurement it is based on.
        if self.p_enabled:
            p, heating = self.compute_command(temperature_c)
            if p != self.commanded_pwm or heating != self.commanded_heating:
                self.commanded_pwm = p
                self.commanded_heating = heating
                self.send_command()
                self._refresh_loop_label()
        else:
            self.last_error = self.setpoint - temperature_c

        e = self.last_error
        direction = "heating" if heat_cool == 1 else "cooling"
        mode = "P" if self.p_enabled else "open"
        print(f"t = {time_s:8.2f} s   T = {temperature_c:6.2f} C   "
              f"e = {e:+6.2f} C   PWM = {pwm:3d} {direction:7s} [{mode}]")

        self.times.append(time_s)
        self.temperatures.append(temperature_c)
        self.errors.append(e)
        if heat_cool == 1:
            self.pwm_heat.append(float(pwm))
            self.pwm_cool.append(float("nan"))
        else:
            self.pwm_heat.append(float("nan"))
            self.pwm_cool.append(float(pwm))

        while self.times and (time_s - self.times[0]) > WINDOW_SECONDS:
            for d in (self.times, self.temperatures, self.errors,
                      self.pwm_heat, self.pwm_cool):
                d.popleft()

        self.csv_writer.writerow([f"{time_s:.2f}", f"{temperature_c:.2f}",
                                  pwm, heat_cool, f"{self.setpoint:.2f}",
                                  f"{e:.2f}", f"{self.kp:.3f}",
                                  1 if self.p_enabled else 0])
        self.csv_file.flush()

        self.temp_label.setText(f"T = {temperature_c:.2f} C")
        self.err_label.setText(f"e = {e:+.2f} C")
        self.pwm_label.setText(f"PWM = {pwm}")
        self.dir_label.setText(f"dir = {'HEAT' if heat_cool == 1 else 'COOL'}")

    def on_serial_error(self, message):
        print(f"\nSerial error: {message}", file=sys.stderr)

    # -----------------------------------------------------------------
    def update_plots(self):
        if not self.times:
            return
        t = list(self.times)
        temps = list(self.temperatures)
        self.temp_curve.setData(t, temps)
        self.err_curve.setData(t, list(self.errors))
        self.pwm_heat_curve.setData(t, list(self.pwm_heat))
        self.pwm_cool_curve.setData(t, list(self.pwm_cool))

        # Keep the setpoint inside the view even before the plate gets near
        # it, otherwise the dashed line vanishes off-screen and the droop
        # gap is invisible, which is the one thing this window is for.
        lo = min(min(temps), self.setpoint)
        hi = max(max(temps), self.setpoint)
        pad = 1.0
        if (hi + pad) - (lo - pad) < 6.0:
            c = 0.5 * (lo + hi)
            lo, hi = c - 3.0, c + 3.0
        else:
            lo, hi = lo - pad, hi + pad
        self.temp_plot.setYRange(lo, hi, padding=0)

    def closeEvent(self, event):
        self.p_enabled = False
        self.commanded_pwm = 0
        self.send_command()
        time.sleep(0.15)
        self._closing = True
        self.redraw_timer.stop()
        self.link.stop()
        self.csv_file.close()
        print(f"\nClosed. PWM commanded to 0. Data in {self.csv_path}")
        super().closeEvent(event)


def main():
    base.SERIAL_PORT = resolve_port()
    globals()["SERIAL_PORT"] = base.SERIAL_PORT

    app = QtWidgets.QApplication(sys.argv)
    w = PControlWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
