"""
Phys 39 Module 3, Part 5. Complete manual control GUI.
Naidu / Cohen

WHAT THIS PROGRAM DOES
    Everything tec_temperature_strip_chart.py does, plus controls:

      - a heat/cool switch,
      - a PWM slider from 0 to 255,
      - a PWM text box that accepts typed input and stays synchronized
        with the slider,
      - live displays of temperature, PWM, direction, and elapsed time,
      - a second strip chart of PWM against time, drawn as a solid red line
        while heating and a solid blue line while cooling.

    When a control changes, it sends one command line to the Arduino:

        SET PWM 120 DIR HEAT
        SET PWM 45 DIR COOL

    The temperature plot, the terminal echo of every received line, and the
    CSV logging all carry over from Part 4 unchanged.

THIS IS STILL MANUAL, OPEN-LOOP CONTROL
    Nothing here reads the temperature and decides what PWM to send. The
    operator does that. There is no setpoint, no error signal, and no
    feedback path. Python sets and displays PWM and direction, the Arduino
    applies the command and measures temperature, and the GUI plots and saves
    the instrument state. Closing that loop is a later module.

PAIR IT WITH
    arduino/module_03/tec_python_control/tec_python_control.ino

    The manual sketches will not obey these commands, which is expected:
    they take their orders from the trim pot and the slide switch.

ONE SERIAL PORT, ONE OWNER
    Close Arduino Serial Monitor and Serial Plotter completely before
    starting this program. "Port busy" on startup almost always means one of
    them is still open.

WHY THERE IS SOME DUPLICATION WITH PART 4
    The configuration block, the line parser, and the serial reader are
    repeated here rather than imported from the display-only program. The
    two programs are separate deliverables and each one should be readable
    on its own, without following an import into another file.

RUN IT
    pip install -r requirements.txt
    python python/tec_control_gui.py
"""

import csv
import re
import sys
import time
from collections import deque

import pyqtgraph as pg
import serial
import serial.tools.list_ports
from PySide6 import QtCore, QtWidgets

import demo_source

# =====================================================================
# CONFIGURATION
# =====================================================================

SERIAL_PORT = "/dev/cu.usbmodem1101"   # macOS; Windows looks like "COM5"
BAUD_RATE = 9600

WINDOW_SECONDS = 120.0       # visible history on both strip charts
UPDATE_INTERVAL_MS = 200     # plot redraw period

# Celsius axis limits, None for autoscale.
#
# Widened from 10 to 45 after the first full-drive run. At maxDuty 64 the
# plate stayed inside that window; at 255 it does not. A fixed axis that the
# trace runs off the top of does not just look wrong, it hides the part of
# the curve that matters, and the operator cannot tell a plate still climbing
# from one that has levelled off at the frame edge.
#
# -10 to 90 covers what this plate can reach in either direction at full
# command, with the thermal switch well inside the frame.
TEMP_MIN = -10.0
TEMP_MAX = 90.0

PWM_MIN = 0                  # the command range the Arduino accepts
PWM_MAX = 255

# How long to wait after the last slider movement before sending, in
# milliseconds. Dragging a slider emits a value for every pixel; without
# this the serial port would receive a hundred commands per drag.
SEND_DEBOUNCE_MS = 60

# Run from a synthetic thermal model instead of the Arduino, so the plot, the
# parser and the CSV writer can be developed while the bench is busy. Also
# settable from the command line with --demo. Demo output is written to a
# separate CSV so it can never be mistaken for measured data.
DEMO_MODE = False

CSV_FILENAME = "data/module_03/tec_control_run.csv"

HEAT_COLOR = "#d62728"       # solid red while heating
COOL_COLOR = "#1f77b4"       # solid blue while cooling


# =====================================================================
# PARSING
# =====================================================================

DEMO_CSV_FILENAME = CSV_FILENAME.replace(".csv", "_DEMO.csv")

LINE_PATTERN = re.compile(
    r"Temperature \(C\):\s*(-?\d+(?:\.\d+)?|-+)\s*,\s*"
    r"Time \(s\):\s*(-?\d+(?:\.\d+)?)\s*,\s*"
    r"PWM:\s*(\d+)\s*,\s*"
    r"Heat/Cool:\s*([01])"
)


def parse_measurement(line):
    """Return (time_s, temperature_C, pwm, heat_cool), or None."""
    match = LINE_PATTERN.search(line)
    if match is None:
        return None

    temperature_text = match.group(1)
    if set(temperature_text) == {"-"}:
        # "---" means the divider reading was impossible, so the thermistor
        # is open or shorted. Not a temperature, so not plotted or logged.
        return None

    return (
        float(match.group(2)),
        float(temperature_text),
        int(match.group(3)),
        int(match.group(4)),
    )

def is_measurement_line(line):
    """True if the line has the measurement format, usable reading or not."""
    return LINE_PATTERN.search(line) is not None


def resolve_port():
    """Return the serial port to open, preferring SERIAL_PORT above.

    Same logic as the Part 4 strip chart, and here for the same reason.
    macOS renames the Arduino's device node when the cable moves to a
    different physical USB socket, so /dev/cu.usbmodem1101 becomes
    usbmodem1201. Hard-coding one name means a working bench stops working
    because someone tidied a cable, and the error it raises, "No such file
    or directory", reads like a missing program rather than a moved plug.

    The configured name is therefore a preference, not a requirement. If it
    is present it is used. If it is absent but exactly one USB serial device
    is attached, that one is used and the substitution is ANNOUNCED. A
    program that silently drives a different instrument than the one it was
    told to drive is worse than one that refuses to start.
    """
    ports = list(serial.tools.list_ports.comports())
    names = [p.device for p in ports]

    if SERIAL_PORT in names:
        return SERIAL_PORT

    # Built-in Bluetooth and debug nodes are always present and are never the
    # Arduino, so match on USB serial adapter names instead.
    candidates = [n for n in names
                  if "usbmodem" in n or "usbserial" in n or n.startswith("COM")]

    if len(candidates) == 1:
        print(f"Note: {SERIAL_PORT} is not present. Using {candidates[0]} "
              f"instead, the only USB serial device attached.")
        return candidates[0]

    if not candidates:
        print(f"\nNo USB serial device found. {SERIAL_PORT} is not present "
              f"and neither is any other.", file=sys.stderr)
        print("The Arduino is not on the bus. Check the cable is seated at "
              "both ends and is a data cable, not charge-only.",
              file=sys.stderr)
    else:
        print(f"\n{SERIAL_PORT} is not present, and more than one USB serial "
              f"device is attached: {', '.join(candidates)}", file=sys.stderr)
        print("Set SERIAL_PORT to the right one rather than guessing.",
              file=sys.stderr)

    if ports:
        print("Ports this computer can see:", file=sys.stderr)
        for port in ports:
            print(f"    {port.device}    {port.description}", file=sys.stderr)
    sys.exit(1)


# =====================================================================
# SERIAL READER AND WRITER
# =====================================================================

class SerialLink(QtCore.QThread):
    """Owns the serial port. Reads lines on this thread, writes on demand.

    readline() blocks, so it must not run on the GUI thread or the window
    would freeze between measurements. Writes are issued from the GUI thread
    instead, and a mutex keeps a write from interleaving with the reader's
    use of the same port object.
    """

    line_received = QtCore.Signal(str)
    error = QtCore.Signal(str)

    def __init__(self, port, baud, parent=None):
        super().__init__(parent)
        self._port = port
        self._baud = baud
        self._running = True
        self._mutex = QtCore.QMutex()
        self.serial_port = None

    def run(self):
        try:
            self.serial_port = serial.Serial(self._port, self._baud, timeout=1)
        except serial.SerialException as exc:
            self.error.emit(str(exc))
            return

        # Opening the port toggles DTR, which resets an Uno. Wait for the
        # boot message rather than reading a torn first line.
        self.msleep(2000)
        self.serial_port.reset_input_buffer()

        while self._running:
            try:
                raw = self.serial_port.readline()
            except serial.SerialException as exc:
                self.error.emit(str(exc))
                break

            if not raw:
                continue

            text = raw.decode("utf-8", errors="replace").strip()
            if text:
                self.line_received.emit(text)

        with QtCore.QMutexLocker(self._mutex):
            if self.serial_port is not None and self.serial_port.is_open:
                self.serial_port.close()

    def send_command(self, text):
        """Send one command line. Safe to call from the GUI thread."""
        with QtCore.QMutexLocker(self._mutex):
            if self.serial_port is None or not self.serial_port.is_open:
                return False
            try:
                self.serial_port.write((text + "\n").encode("ascii"))
                self.serial_port.flush()
            except serial.SerialException as exc:
                self.error.emit(str(exc))
                return False
        print(f">>> {text}")      # show what we sent, alongside what we receive
        return True

    def stop(self):
        self._running = False
        self.wait(3000)


# =====================================================================
# THE WINDOW
# =====================================================================

class ControlWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phys 39 Module 3, TEC manual control (open loop)")
        self.resize(1000, 760)

        # ---- state ----------------------------------------------------
        self.commanded_pwm = 0
        self.commanded_heating = True

        # Set while a control is being updated in software, so that the
        # slider and the text box updating each other cannot recurse.
        self._syncing = False

        # Recent data. pwm_heat and pwm_cool hold the same series split in
        # two, with NaN wherever the other direction was active. Plotting
        # them as separate curves with connect="finite" gives a red line
        # while heating and a blue line while cooling, with no false
        # diagonal joining the two across a direction change.
        self.times = deque()
        self.temperatures = deque()
        self.pwm_heat = deque()
        self.pwm_cool = deque()

        self._build_ui()

        # ---- CSV ------------------------------------------------------
        # Set before the reader starts. See on_line() for why.
        self._closing = False

        self.csv_path = DEMO_CSV_FILENAME if DEMO_MODE else CSV_FILENAME
        self.csv_file = open(self.csv_path, "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(["time_s", "temperature_C", "pwm", "heat_cool"])
        self.csv_file.flush()
        print(f"Writing measurements to {self.csv_path}")

        # ---- serial ---------------------------------------------------
        if DEMO_MODE:
            print("DEMO MODE: synthetic data from a thermal model, "
                  "not a measurement.")
            self.link = demo_source.make_demo_reader(QtCore)()
        else:
            self.link = SerialLink(SERIAL_PORT, BAUD_RATE)
        self.link.line_received.connect(self.on_line)
        self.link.error.connect(self.on_serial_error)
        self.link.start()

        # ---- timers ---------------------------------------------------
        self.redraw_timer = QtCore.QTimer(self)
        self.redraw_timer.timeout.connect(self.update_plots)
        self.redraw_timer.start(UPDATE_INTERVAL_MS)

        # Single-shot, restarted on every control change. The command is
        # only sent once the controls have been still for a moment.
        self.send_timer = QtCore.QTimer(self)
        self.send_timer.setSingleShot(True)
        self.send_timer.timeout.connect(self.send_command)

        # Send the safe state once the board has finished booting, so the
        # GUI and the Arduino agree from the start.
        QtCore.QTimer.singleShot(2600, self.send_command)

    # -----------------------------------------------------------------
    # LAYOUT
    # -----------------------------------------------------------------
    def _build_ui(self):
        pg.setConfigOptions(antialias=True)

        # ---- live readouts -------------------------------------------
        self.temp_label = QtWidgets.QLabel("T = --- C")
        self.pwm_label = QtWidgets.QLabel("PWM = 0")
        self.dir_label = QtWidgets.QLabel("direction = HEAT")
        self.time_label = QtWidgets.QLabel("t = --- s")
        for label in (self.temp_label, self.pwm_label,
                      self.dir_label, self.time_label):
            font = label.font()
            font.setPointSize(15)
            label.setFont(font)

        # The sketch may refuse to deliver the duty it was commanded, and
        # when it does it says so on a "# " line. That notice previously went
        # only to the terminal, where it was missed, and a run at a quarter
        # of the commanded drive was read as a hardware fault for most of an
        # afternoon. A number on the GUI that does not describe what the
        # bridge is doing has to be contradicted on the GUI, not somewhere
        # the operator is not looking.
        self.cap_label = QtWidgets.QLabel("")
        cap_font = self.cap_label.font()
        cap_font.setPointSize(15)
        cap_font.setBold(True)
        self.cap_label.setFont(cap_font)
        self.cap_label.setStyleSheet("color: #ff8c00;")

        readout_row = QtWidgets.QHBoxLayout()
        for label in (self.temp_label, self.pwm_label,
                      self.dir_label, self.time_label, self.cap_label):
            readout_row.addWidget(label)
        readout_row.addStretch(1)

        # ---- heat / cool switch --------------------------------------
        # Two exclusive radio buttons. A single checkbox would work, but an
        # actuator direction should never be readable as "sort of on": two
        # labelled states make the commanded direction unambiguous.
        self.heat_button = QtWidgets.QRadioButton("HEAT")
        self.cool_button = QtWidgets.QRadioButton("COOL")
        self.heat_button.setChecked(True)
        self.heat_button.toggled.connect(self.on_direction_changed)

        direction_box = QtWidgets.QGroupBox("Direction")
        direction_layout = QtWidgets.QHBoxLayout()
        direction_layout.addWidget(self.heat_button)
        direction_layout.addWidget(self.cool_button)
        direction_box.setLayout(direction_layout)

        # ---- PWM slider and text box ---------------------------------
        self.pwm_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.pwm_slider.setMinimum(PWM_MIN)
        self.pwm_slider.setMaximum(PWM_MAX)
        self.pwm_slider.setValue(0)
        self.pwm_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.pwm_slider.setTickInterval(32)
        self.pwm_slider.valueChanged.connect(self.on_slider_moved)

        self.pwm_edit = QtWidgets.QLineEdit("0")
        self.pwm_edit.setFixedWidth(70)
        self.pwm_edit.setAlignment(QtCore.Qt.AlignRight)
        # editingFinished fires on Return and on losing focus, so a
        # half-typed number is never sent to the actuator.
        self.pwm_edit.editingFinished.connect(self.on_text_entered)

        self.stop_button = QtWidgets.QPushButton("PWM to 0")
        self.stop_button.clicked.connect(self.on_stop_clicked)

        pwm_box = QtWidgets.QGroupBox(f"PWM command ({PWM_MIN} to {PWM_MAX})")
        pwm_layout = QtWidgets.QHBoxLayout()
        pwm_layout.addWidget(self.pwm_slider, stretch=1)
        pwm_layout.addWidget(self.pwm_edit)
        pwm_layout.addWidget(self.stop_button)
        pwm_box.setLayout(pwm_layout)

        control_row = QtWidgets.QHBoxLayout()
        control_row.addWidget(direction_box)
        control_row.addWidget(pwm_box, stretch=1)

        # ---- temperature strip chart ---------------------------------
        self.temp_plot = pg.PlotWidget()
        self.temp_plot.setLabel("bottom", "Time", units="s")
        self.temp_plot.setLabel("left", "Temperature", units="C")
        self.temp_plot.showGrid(x=True, y=True, alpha=0.3)
        if TEMP_MIN is not None and TEMP_MAX is not None:
            self.temp_plot.setYRange(TEMP_MIN, TEMP_MAX)
        self.temp_curve = self.temp_plot.plot(pen=pg.mkPen("#2ca02c", width=2))

        # ---- PWM strip chart -----------------------------------------
        self.pwm_plot = pg.PlotWidget()
        self.pwm_plot.setLabel("bottom", "Time", units="s")
        self.pwm_plot.setLabel("left", "PWM command")
        self.pwm_plot.showGrid(x=True, y=True, alpha=0.3)
        self.pwm_plot.setYRange(PWM_MIN - 5, PWM_MAX + 5)
        self.pwm_plot.setXLink(self.temp_plot)   # the two charts share time
        self.pwm_heat_curve = self.pwm_plot.plot(
            pen=pg.mkPen(HEAT_COLOR, width=2), connect="finite", name="heating")
        self.pwm_cool_curve = self.pwm_plot.plot(
            pen=pg.mkPen(COOL_COLOR, width=2), connect="finite", name="cooling")

        legend = QtWidgets.QLabel(
            f"<span style='color:{HEAT_COLOR}'>&#9644; heating</span>"
            f"&nbsp;&nbsp;&nbsp;"
            f"<span style='color:{COOL_COLOR}'>&#9644; cooling</span>"
        )

        # ---- assemble -------------------------------------------------
        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(readout_row)
        layout.addLayout(control_row)
        layout.addWidget(self.temp_plot, stretch=3)
        layout.addWidget(legend)
        layout.addWidget(self.pwm_plot, stretch=2)

        container = QtWidgets.QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    # -----------------------------------------------------------------
    # CONTROLS
    # -----------------------------------------------------------------
    def on_slider_moved(self, value):
        if self._syncing:
            return
        self._syncing = True
        self.pwm_edit.setText(str(value))     # keep the text box in step
        self._syncing = False

        self.commanded_pwm = value
        self._refresh_command_labels()
        self.send_timer.start(SEND_DEBOUNCE_MS)

    def on_text_entered(self):
        text = self.pwm_edit.text().strip()

        # Clamp anything numeric into range; refuse anything that is not a
        # number by putting the current value back. Silently sending 0 for
        # unparseable text would hide a typing mistake.
        try:
            value = int(float(text))
        except ValueError:
            self._syncing = True
            self.pwm_edit.setText(str(self.commanded_pwm))
            self._syncing = False
            print(f"Ignored PWM entry {text!r}: not a number")
            return

        value = max(PWM_MIN, min(PWM_MAX, value))

        self._syncing = True
        self.pwm_edit.setText(str(value))
        self.pwm_slider.setValue(value)       # move the slider to match
        self._syncing = False

        self.commanded_pwm = value
        self._refresh_command_labels()
        self.send_timer.start(SEND_DEBOUNCE_MS)

    def on_direction_changed(self):
        self.commanded_heating = self.heat_button.isChecked()
        self._refresh_command_labels()
        self.send_timer.start(SEND_DEBOUNCE_MS)

    def on_stop_clicked(self):
        self.pwm_slider.setValue(0)           # this triggers on_slider_moved

    def _refresh_command_labels(self):
        self.pwm_label.setText(f"PWM = {self.commanded_pwm}")
        self.dir_label.setText(
            f"direction = {'HEAT' if self.commanded_heating else 'COOL'}")

    def send_command(self):
        direction = "HEAT" if self.commanded_heating else "COOL"
        self.link.send_command(f"SET PWM {self.commanded_pwm} DIR {direction}")

    # -----------------------------------------------------------------
    # INCOMING DATA
    # -----------------------------------------------------------------
    def on_line(self, line):
        # Late signal arriving after shutdown began. Qt delivers queued
        # line_received signals after closeEvent returns, so without this
        # the CSV write below raises on a closed file and prints a traceback
        # after the clean shutdown message.
        if self._closing:
            return

        measurement = parse_measurement(line)

        if measurement is None:
            # Not a usable measurement. Two different cases, and they must
            # not be treated the same way.
            if is_measurement_line(line):
                # The format matched but the temperature field was "---",
                # which the sketch prints when the divider reading is
                # impossible. Say so in one short line rather than echoing
                # the whole thing, and do not plot or log it.
                print("   (divider reading unusable, nothing logged)")
            else:
                # A heading, or one of the sketch's own notices such as
                # ARMED, POT JUMP or TEMPERATURE STEP. These are passed
                # through, because silently dropping a safety notice is
                # worse than a little extra text, and they are not
                # measurement lines.
                text = line.strip()
                if text:
                    print(text)

                # Two notices from the sketch mean the commanded duty is not
                # the delivered duty. Put them on the window, not just in the
                # terminal. Everything else passes through as before.
                if "CAPPED" in text:
                    self.cap_label.setText(
                        "OUTPUT CAPPED, commanded duty is not being delivered")
                elif "OUTPUT CEILING" in text:
                    self.cap_label.setText(
                        "OUTPUT CEILING SET, see the terminal for the value")
            return

        time_s, temperature_c, pwm, heat_cool = measurement
        direction = "heating" if heat_cool == 1 else "cooling"

        # The assignment asks for exactly these four values in the terminal,
        # extracted from the line rather than echoed with it.
        print(f"t = {time_s:8.2f} s    T = {temperature_c:6.2f} C    "
              f"PWM = {pwm:3d}    {direction}")

        self.times.append(time_s)
        self.temperatures.append(temperature_c)

        # Split the PWM series by direction. float("nan") leaves a gap in
        # the curve for the direction that was not active.
        if heat_cool == 1:
            self.pwm_heat.append(float(pwm))
            self.pwm_cool.append(float("nan"))
        else:
            self.pwm_heat.append(float("nan"))
            self.pwm_cool.append(float(pwm))

        while self.times and (time_s - self.times[0]) > WINDOW_SECONDS:
            self.times.popleft()
            self.temperatures.popleft()
            self.pwm_heat.popleft()
            self.pwm_cool.popleft()

        self.csv_writer.writerow([f"{time_s:.2f}", f"{temperature_c:.2f}",
                                  pwm, heat_cool])
        self.csv_file.flush()

        # These labels report what the Arduino says, not what we asked for.
        # If the two disagree, a command was refused or lost, and that is
        # worth seeing rather than hiding.
        self.temp_label.setText(f"T = {temperature_c:.2f} C")
        self.time_label.setText(f"t = {time_s:.1f} s")
        self.pwm_label.setText(f"PWM = {pwm}")
        self.dir_label.setText(
            f"direction = {'HEAT' if heat_cool == 1 else 'COOL'}")

    def on_serial_error(self, message):
        print(f"\nSerial error: {message}", file=sys.stderr)
        ports = list(serial.tools.list_ports.comports())
        if ports:
            print("Ports this computer can see:", file=sys.stderr)
            for port in ports:
                print(f"    {port.device}    {port.description}", file=sys.stderr)
        else:
            print("No serial ports found. Is the Arduino plugged in?",
                  file=sys.stderr)
        print("If the port looks right, close Arduino Serial Monitor and "
              "Serial Plotter and try again.", file=sys.stderr)
        QtWidgets.QApplication.quit()

    # -----------------------------------------------------------------
    def update_plots(self):
        if not self.times:
            return
        times = list(self.times)
        self.temp_curve.setData(times, list(self.temperatures))
        self.pwm_heat_curve.setData(times, list(self.pwm_heat))
        self.pwm_cool_curve.setData(times, list(self.pwm_cool))

    def closeEvent(self, event):
        # Command the actuator to zero before letting go of the port. A GUI
        # that exits leaving the TEC driven would be a bad instrument.
        self.commanded_pwm = 0
        self.send_command()
        time.sleep(0.15)      # let the bytes leave before the port closes

        # Flag AFTER the stop command is sent, so the zero command still goes
        # out, but before the file closes, so late lines are dropped.
        self._closing = True

        self.redraw_timer.stop()
        self.send_timer.stop()
        self.link.stop()
        self.csv_file.close()
        print(f"\nClosed. PWM commanded to 0. Data saved in {self.csv_path}")
        super().closeEvent(event)


def main():
    global DEMO_MODE, SERIAL_PORT
    if "--demo" in sys.argv:
        DEMO_MODE = True

    # Resolve the port BEFORE the window is built, because the window opens
    # the CSV in its constructor. Exiting after that point leaves a file
    # holding nothing but a header row, which looks like a run that recorded
    # no data rather than a run that never started.
    if not DEMO_MODE:
        SERIAL_PORT = resolve_port()

    app = QtWidgets.QApplication(sys.argv)
    window = ControlWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
