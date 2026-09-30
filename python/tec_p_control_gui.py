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

# Measured zero-PWM temperature, Module 4. Used only to predict where the
# loop should settle, so the readout can be checked against the run.
T_AMBIENT = 21.54             # C


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

        # Force a light window. Without this the app inherits macOS dark
        # mode while the plots are white, which is what made the first
        # version hard to read.
        self.setStyleSheet("""
            QWidget { background: #FFFFFF; color: #202020;
                      font-family: -apple-system, Helvetica, Arial; }
            QLabel#big   { font-size: 19px; font-weight: 600; }
            QLabel#unit  { font-size: 11px; color: #777777; }
            QLabel#loop  { font-size: 12px; color: #1F4E79;
                           background: #EEF4FA; padding: 6px 9px;
                           border: 1px solid #C9DCEC; border-radius: 4px; }
            QDoubleSpinBox { font-size: 15px; padding: 3px 6px;
                             border: 1px solid #BBBBBB; border-radius: 3px;
                             min-width: 96px; }
            QCheckBox { font-size: 15px; font-weight: 600; }
            QPushButton { font-size: 14px; padding: 6px 14px;
                          border: 1px solid #C0392B; border-radius: 4px;
                          background: #FDEDEC; color: #C0392B;
                          font-weight: 600; }
            QPushButton:hover { background: #F9D9D6; }
            QPushButton#plain { border: 1px solid #BBBBBB; background: #F4F4F4;
                                color: #333333; font-weight: 500; }
            QPushButton#plain:hover { background: #E8E8E8; }
            QGroupBox { font-size: 11px; color: #666666;
                        border: 1px solid #DDDDDD; border-radius: 4px;
                        margin-top: 8px; padding-top: 8px; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px;
                               padding: 0 4px; }
        """)

        # ---- readouts, as a row of labelled tiles ---------------------
        def tile(caption):
            """One big number over a small grey caption."""
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
        row1.setSpacing(26)
        b, self.temp_label = tile("measured T  (\u00b0C)");   row1.addLayout(b)
        b, self.set_label = tile("setpoint  (\u00b0C)");      row1.addLayout(b)
        b, self.err_label = tile("error e = Tset \u2212 T");  row1.addLayout(b)
        b, self.pwm_label = tile("PWM magnitude");             row1.addLayout(b)
        b, self.dir_label = tile("direction");                 row1.addLayout(b)
        row1.addStretch(1)

        self.set_label.setText(f"{self.setpoint:.1f}")
        self.pwm_label.setText("0")

        # The error is the quantity this module is about, so colour it:
        # red when the plate is below setpoint, blue when above.
        self.err_label.setStyleSheet("color: #C0392B;")

        self.loop_label = QtWidgets.QLabel("")
        self.loop_label.setObjectName("loop")
        self.loop_label.setWordWrap(True)

        # ---- controls -------------------------------------------------
        self.set_spin = QtWidgets.QDoubleSpinBox()
        self.set_spin.setRange(5.0, 55.0)
        self.set_spin.setSingleStep(0.5)
        self.set_spin.setDecimals(1)
        self.set_spin.setSuffix(" \u00b0C")
        self.set_spin.setValue(self.setpoint)
        self.set_spin.valueChanged.connect(self.on_setpoint_changed)

        self.kp_spin = QtWidgets.QDoubleSpinBox()
        self.kp_spin.setRange(0.0, 200.0)
        self.kp_spin.setSingleStep(0.25)
        self.kp_spin.setDecimals(3)
        self.kp_spin.setValue(self.kp)
        self.kp_spin.valueChanged.connect(self.on_kp_changed)

        self.enable_box = QtWidgets.QCheckBox("P control ON")
        self.enable_box.toggled.connect(self.on_enable_toggled)

        self.stop_btn = QtWidgets.QPushButton("STOP  \u2014  PWM to 0")
        self.stop_btn.clicked.connect(self.on_stop)

        # pyqtgraph turns auto-ranging OFF the moment you scroll or drag a
        # plot, so one stray trackpad gesture strands the view somewhere with
        # no data and the axis label goes to something like "Time (e27s)".
        # This puts it back.
        self.rescale_btn = QtWidgets.QPushButton("Rescale plots")
        self.rescale_btn.setObjectName("plain")
        self.rescale_btn.clicked.connect(self.rescale_plots)

        ctl = QtWidgets.QGroupBox("controller")
        row2 = QtWidgets.QHBoxLayout()
        row2.setSpacing(10)
        row2.addWidget(QtWidgets.QLabel("Setpoint"))
        row2.addWidget(self.set_spin)
        row2.addSpacing(10)
        row2.addWidget(QtWidgets.QLabel("Kp  (PWM/\u00b0C)"))
        row2.addWidget(self.kp_spin)
        row2.addSpacing(16)
        row2.addWidget(self.enable_box)
        row2.addStretch(1)
        row2.addWidget(self.rescale_btn)
        row2.addWidget(self.stop_btn)
        ctl.setLayout(row2)

        # ---- plots ----------------------------------------------------
        self.temp_plot = pg.PlotWidget()
        self.temp_plot.setLabel("bottom", "Time", units="s")
        self.temp_plot.setLabel("left", "Temperature", units="C")
        self.temp_plot.showGrid(x=True, y=True, alpha=0.3)
        self.temp_curve = self.temp_plot.plot(
            pen=pg.mkPen("#2ca02c", width=2))
        self.set_line = pg.InfiniteLine(
            pos=self.setpoint, angle=0,
            pen=pg.mkPen(SET_COLOR, width=1.6, style=QtCore.Qt.DashLine))
        self.temp_plot.addItem(self.set_line)

        self.err_plot = pg.PlotWidget()
        self.err_plot.setLabel("bottom", "Time", units="s")
        self.err_plot.setLabel("left", "Error", units="C")
        self.err_plot.showGrid(x=True, y=True, alpha=0.3)
        self.err_plot.addItem(pg.InfiniteLine(
            pos=0, angle=0, pen=pg.mkPen("#999999", width=1.2,
                                         style=QtCore.Qt.DashLine)))
        self.err_curve = self.err_plot.plot(pen=pg.mkPen(ERR_COLOR, width=2))
        self.err_plot.setXLink(self.temp_plot)

        self.pwm_plot = pg.PlotWidget()
        self.pwm_plot.setLabel("bottom", "Time", units="s")
        self.pwm_plot.setLabel("left", "PWM")
        self.pwm_plot.showGrid(x=True, y=True, alpha=0.3)
        self.pwm_plot.setYRange(PWM_MIN - 5, PWM_MAX + 5)
        self.pwm_heat_curve = self.pwm_plot.plot(
            pen=pg.mkPen(HEAT_COLOR, width=2), connect="finite")
        self.pwm_cool_curve = self.pwm_plot.plot(
            pen=pg.mkPen(COOL_COLOR, width=2), connect="finite")
        self.pwm_plot.setXLink(self.temp_plot)

        legend = QtWidgets.QLabel(
            "<span style='color:#d62728'><b>&#9644; heating</b></span>"
            "&nbsp;&nbsp;&nbsp;<span style='color:#1f77b4'><b>&#9644; cooling"
            "</b></span>&nbsp;&nbsp;&nbsp;<span style='color:#7f7f7f'>"
            "&#9476;&#9476; setpoint</span>")

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(14, 12, 14, 10)
        layout.setSpacing(9)
        layout.addLayout(row1)
        layout.addWidget(self.loop_label)
        layout.addWidget(ctl)
        layout.addWidget(self.temp_plot, stretch=4)
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
        fractional droop 1/(1+L) and the droop in degrees are printed beside
        it so the prediction can be checked against the run as it happens.
        """
        chi = CHI_HEAT if self.commanded_heating else CHI_COOL
        which = "heating" if self.commanded_heating else "cooling"
        L = self.kp * chi
        frac = 1.0 / (1.0 + L) if L > -1 else float("nan")

        if L < 0.3:
            verdict = "weak feedback"
        elif L < 3.0:
            verdict = "comparable feedback"
        else:
            verdict = "strong feedback"

        # Predicted settling point, which is the thing to watch for.
        e0 = self.setpoint - T_AMBIENT
        droop = e0 * frac
        Tss = self.setpoint - droop

        self.loop_label.setText(
            f"<b>L = Kp \u00d7 \u03c7 = {self.kp:.3f} \u00d7 {chi:.5f} = "
            f"{L:.3f}</b>  ({verdict}, \u03c7 for {which})"
            f" &nbsp;&nbsp;|&nbsp;&nbsp; predicted droop "
            f"1/(1+L) = {frac:.3f} of e\u2080 = {droop:+.2f} \u00b0C"
            f" &nbsp;&nbsp;|&nbsp;&nbsp; <b>expect to settle near "
            f"{Tss:.2f} \u00b0C</b>, not {self.setpoint:.1f}"
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
        self.set_label.setText(f"{self.setpoint:.1f}")
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

        self.temp_label.setText(f"{temperature_c:.2f}")
        self.err_label.setText(f"{e:+.2f}")
        self.err_label.setStyleSheet(
            "color: #C0392B;" if e >= 0 else "color: #1F77B4;")
        self.pwm_label.setText(f"{pwm}")
        self.dir_label.setText('HEAT' if heat_cool == 1 else 'COOL')
        self.dir_label.setStyleSheet(
            'color: #d62728;' if heat_cool == 1 else 'color: #1f77b4;')

    def on_serial_error(self, message):
        print(f"\nSerial error: {message}", file=sys.stderr)

    # -----------------------------------------------------------------
    def rescale_plots(self):
        """Put every view back on the data.

        Re-enables auto-ranging on all three plots and snaps the shared time
        axis to the rolling window. Safe to press at any time; it changes
        only the view, never the data or the controller.
        """
        for plot in (self.temp_plot, self.err_plot, self.pwm_plot):
            plot.enableAutoRange(axis="x", enable=True)
            plot.enableAutoRange(axis="y", enable=True)
        self.pwm_plot.setYRange(PWM_MIN - 5, PWM_MAX + 5)
        if self.times:
            t = list(self.times)
            self.temp_plot.setXRange(t[0], t[-1], padding=0.02)
        print("Plots rescaled.")

    def update_plots(self):
        if not self.times:
            return
        t = list(self.times)
        # Keep the time axis pinned to the rolling window every redraw, so a
        # stray scroll corrects itself on the next sample instead of leaving
        # the operator staring at an empty plot.
        self.temp_plot.setXRange(t[0], t[-1], padding=0.02)
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
