"""
Phys 39 Module 3, Part 4. Python display-only temperature strip chart.
Naidu / Cohen

WHAT THIS PROGRAM DOES
    Reads the measurement line printed by the Arduino, prints every complete
    received line in the terminal, plots temperature in Celsius against the
    Arduino's own time, and saves every accepted measurement to a CSV file.

WHAT IT DELIBERATELY DOES NOT DO
    It never writes to the serial port. This version is display-only. The
    serial object is opened for reading and there is no call to .write()
    anywhere in this file. Sending commands is Part 5.

ONE SERIAL PORT, ONE OWNER
    The Arduino has a single USB serial connection and access to it is all or
    nothing. Close Arduino Serial Monitor AND Serial Plotter completely
    before starting this program, and close this program before reopening
    either of them. "Port busy" on startup almost always means Serial Monitor
    is still open.

    Because Serial Monitor cannot be open at the same time, this program
    prints each complete received line to the terminal. That gives you the
    same human-readable information you previously read in Serial Monitor.

EXPECTED INPUT LINE
    Temperature (C): 27.73, Time (s): 645.06, PWM: 120, Heat/Cool: 1

    Heat/Cool is 1 for observed heating and 0 for observed cooling, assigned
    from the bench experiment rather than from a pin number.

RUN IT
    pip install -r requirements.txt
    python python/tec_temperature_strip_chart.py
"""

import csv
import re
import sys
from collections import deque

import pyqtgraph as pg
import serial
import serial.tools.list_ports
from PySide6 import QtCore, QtWidgets

import demo_source

# =====================================================================
# CONFIGURATION. Everything you are likely to change lives here.
# =====================================================================

# The serial port the Arduino appears on.
#   macOS  looks like "/dev/cu.usbmodem1101"
#   Windows looks like "COM5"
# If this is wrong the program lists the ports it can see and exits.
SERIAL_PORT = "/dev/cu.usbmodem1101"

# Must match Serial.begin() in the sketch.
BAUD_RATE = 9600

# How many seconds of history the strip chart shows at once.
WINDOW_SECONDS = 120.0

# How often the plot redraws, in milliseconds. The Arduino only reports
# twice a second, so redrawing faster than this buys nothing.
UPDATE_INTERVAL_MS = 200

# Fixed temperature axis, in Celsius. Set to None for autoscale.
TEMP_MIN = 10.0
TEMP_MAX = 45.0

# The raw data file required for C3. Columns carry units in their names.
# Run from a synthetic thermal model instead of the Arduino, so the plot, the
# parser and the CSV writer can be developed while the bench is busy. Also
# settable from the command line with --demo. Demo output is written to a
# separate CSV so it can never be mistaken for measured data.
DEMO_MODE = False

CSV_FILENAME = "data/module_03/tec_run.csv"


# =====================================================================
# PARSING
# =====================================================================

# One regular expression per field, joined in order. Writing it this way
# means any extra text the Arduino adds after Heat/Cool, such as a
# diagnostic in brackets, is simply ignored instead of breaking the parse.
DEMO_CSV_FILENAME = CSV_FILENAME.replace(".csv", "_DEMO.csv")

LINE_PATTERN = re.compile(
    r"Temperature \(C\):\s*(-?\d+(?:\.\d+)?|-+)\s*,\s*"
    r"Time \(s\):\s*(-?\d+(?:\.\d+)?)\s*,\s*"
    r"PWM:\s*(\d+)\s*,\s*"
    r"Heat/Cool:\s*([01])"
)


def parse_measurement(line):
    """Turn one received line into (time_s, temperature_C, pwm, heat_cool).

    Returns None if the line is not a measurement. Lines beginning with "#"
    are the Arduino's own comments and headings, and anything else that does
    not match the pattern is ignored rather than guessed at.
    """
    match = LINE_PATTERN.search(line)
    if match is None:
        return None

    temperature_text = match.group(1)
    if temperature_text.startswith("-") and set(temperature_text) == {"-"}:
        # The sketch prints "---" when the divider reading is impossible,
        # meaning the thermistor is open or shorted. That is not a
        # temperature, so it is not plotted or logged.
        return None

    return (
        float(match.group(2)),   # time_s
        float(temperature_text),  # temperature_C
        int(match.group(3)),     # pwm
        int(match.group(4)),     # heat_cool
    )

def is_measurement_line(line):
    """True if the line has the measurement format, usable reading or not."""
    return LINE_PATTERN.search(line) is not None


# =====================================================================
# SERIAL READER
# =====================================================================

class SerialReader(QtCore.QThread):
    """Reads complete lines from the serial port on a background thread.

    The read is done off the GUI thread because serial.readline() blocks
    until a line arrives or the timeout expires. Doing that on the GUI
    thread would freeze the window between measurements.

    Communication back to the GUI is by Qt signal, which is the safe way to
    cross threads in Qt.
    """

    line_received = QtCore.Signal(str)
    error = QtCore.Signal(str)

    def __init__(self, port, baud, parent=None):
        super().__init__(parent)
        self._port = port
        self._baud = baud
        self._running = True
        self.serial_port = None

    def run(self):
        try:
            # timeout=1 means readline() gives up after a second and returns
            # whatever it has, so the loop can notice self._running changing.
            self.serial_port = serial.Serial(self._port, self._baud, timeout=1)
        except serial.SerialException as exc:
            self.error.emit(str(exc))
            return

        # Give the board time to finish resetting. Opening the port toggles
        # DTR on an Uno, which reboots it, and the first fragment of output
        # is usually a partial line.
        self.msleep(2000)
        self.serial_port.reset_input_buffer()

        while self._running:
            try:
                raw = self.serial_port.readline()
            except serial.SerialException as exc:
                self.error.emit(str(exc))
                break

            if not raw:
                continue    # timed out with nothing to read, loop again

            # errors="replace" so one corrupted byte cannot crash the reader.
            text = raw.decode("utf-8", errors="replace").strip()
            if text:
                self.line_received.emit(text)

        if self.serial_port is not None and self.serial_port.is_open:
            self.serial_port.close()

    def stop(self):
        self._running = False
        self.wait(3000)


# =====================================================================
# THE WINDOW
# =====================================================================

class StripChartWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phys 39 Module 3, TEC temperature strip chart (display only)")
        self.resize(900, 520)

        # ---- recent data, for the plot --------------------------------
        # deques so that old points fall off the left-hand end cheaply.
        self.times = deque()
        self.temperatures = deque()

        # ---- the plot -------------------------------------------------
        pg.setConfigOptions(antialias=True)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel("bottom", "Time", units="s")
        self.plot_widget.setLabel("left", "Temperature", units="C")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        if TEMP_MIN is not None and TEMP_MAX is not None:
            self.plot_widget.setYRange(TEMP_MIN, TEMP_MAX)
        self.temperature_curve = self.plot_widget.plot(pen=pg.mkPen(width=2))

        # ---- a one-line readout above the plot ------------------------
        self.readout = QtWidgets.QLabel("waiting for the first measurement...")
        font = self.readout.font()
        font.setPointSize(14)
        self.readout.setFont(font)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.readout)
        layout.addWidget(self.plot_widget)
        container = QtWidgets.QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # ---- the CSV file --------------------------------------------
        # Opened once and flushed after every row, so a crash or an
        # unplugged cable cannot cost more than the last measurement.
        self.csv_path = DEMO_CSV_FILENAME if DEMO_MODE else CSV_FILENAME
        self.csv_file = open(self.csv_path, "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(["time_s", "temperature_C", "pwm", "heat_cool"])
        self.csv_file.flush()
        print(f"Writing measurements to {self.csv_path}")

        # ---- the serial reader ---------------------------------------
        if DEMO_MODE:
            print("DEMO MODE: synthetic data from a thermal model, "
                  "not a measurement.")
            self.reader = demo_source.make_demo_reader(QtCore)()
        else:
            self.reader = SerialReader(SERIAL_PORT, BAUD_RATE)
        self.reader.line_received.connect(self.on_line)
        self.reader.error.connect(self.on_serial_error)
        self.reader.start()

        # ---- the redraw timer ----------------------------------------
        # The plot is redrawn on a timer rather than on every arriving line,
        # so a burst of data cannot flood the GUI with redraws.
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(UPDATE_INTERVAL_MS)

    # ---- one line has arrived from the Arduino ------------------------
    def on_line(self, line):
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
            return

        time_s, temperature_c, pwm, heat_cool = measurement
        direction = "heating" if heat_cool == 1 else "cooling"

        # The assignment asks for exactly these four values in the terminal,
        # extracted from the line rather than echoed with it.
        print(f"t = {time_s:8.2f} s    T = {temperature_c:6.2f} C    "
              f"PWM = {pwm:3d}    {direction}")

        # Store for plotting, then drop anything older than the window.
        self.times.append(time_s)
        self.temperatures.append(temperature_c)
        while self.times and (time_s - self.times[0]) > WINDOW_SECONDS:
            self.times.popleft()
            self.temperatures.popleft()

        # Save every accepted measurement.
        self.csv_writer.writerow([f"{time_s:.2f}", f"{temperature_c:.2f}",
                                  pwm, heat_cool])
        self.csv_file.flush()

        direction = "heating" if heat_cool == 1 else "cooling"
        self.readout.setText(
            f"T = {temperature_c:.2f} C     "
            f"t = {time_s:.1f} s     "
            f"PWM = {pwm}     "
            f"{direction}"
        )

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

    # ---- redraw ------------------------------------------------------
    def update_plot(self):
        if not self.times:
            return
        self.temperature_curve.setData(list(self.times), list(self.temperatures))

    # ---- shutdown ----------------------------------------------------
    def closeEvent(self, event):
        self.timer.stop()
        self.reader.stop()
        self.csv_file.close()
        print(f"\nClosed. Data saved in {self.csv_path}")
        super().closeEvent(event)


def main():
    global DEMO_MODE
    if "--demo" in sys.argv:
        DEMO_MODE = True

    app = QtWidgets.QApplication(sys.argv)
    window = StripChartWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
