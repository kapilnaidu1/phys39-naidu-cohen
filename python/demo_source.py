"""
Phys 39 Module 3: offline data source for developing Parts 4 and 5.

WHY THIS EXISTS

The Arduino has one USB serial connection and only one program can own it.
That makes the GUI work compete with the bench work: you cannot debug a plot
while someone else is putting a scope probe on pin 9.

This module synthesizes the same measurement line the Arduino prints, from a
simple thermal model, so the strip chart and the control GUI can be written
and tested on the laptop with no hardware attached. When the bench is free,
set DEMO_MODE back to False and nothing else changes: the demo source emits
text through the same signal, in the same format, so the parser, the plot,
and the CSV writer are exercised by the real code path.

It is a development aid. It is NOT data. Nothing produced here belongs in
data/module_03/ or in any figure submitted as a measurement.

THE MODEL

First-order plate response toward ambient, driven by the commanded duty:

    dT/dt = (T_ambient - T) / tau  +  rate_full * (duty / 255) * direction

with direction +1 for heating and -1 for cooling. Then the temperature is
pushed back through the real measurement chain, beta model to resistance to
divider voltage to a quantized ADC count, and converted back exactly as the
sketch does. That last step matters: it makes the demo show the same 0.08 C
quantization steps as the hardware, so the plot looks like the instrument
rather than like a smooth function.
"""

import math
import random

# ---- the same constants the sketches use -----------------------------
R_NOMINAL = 100000.0      # ohms at 25 C, TDK B57861S0104F040V24
BETA = 4540.0             # kelvin
T_NOMINAL = 25.0          # deg C
R_FIXED = 100000.0        # ohms, upper leg
V_REF = 5.0               # volts
KELVIN = 273.15

# ---- model parameters ------------------------------------------------
AMBIENT_C = 22.7          # room temperature seen on the bench
PLATE_TAU_S = 60.0        # plate time constant, minutes-scale not seconds
RATE_FULL_C_PER_S = 0.45  # dT/dt at duty 255 with no heat loss
ADC_NOISE_COUNTS = 0.15   # spread of a 500-sample average


def resistance_at(celsius):
    """Beta model, temperature to thermistor resistance."""
    kelvin = celsius + KELVIN
    return R_NOMINAL * math.exp(BETA * (1.0 / kelvin - 1.0 / (T_NOMINAL + KELVIN)))


def celsius_at(ohms):
    """Beta model inverted, exactly as resistanceToCelsius() in the sketch."""
    if ohms <= 0.0:
        return float("nan")
    inv_t = 1.0 / (T_NOMINAL + KELVIN) + math.log(ohms / R_NOMINAL) / BETA
    return 1.0 / inv_t - KELVIN


class PlantModel:
    """A TEC plate and its thermistor, good enough to develop a GUI against."""

    def __init__(self, ambient=AMBIENT_C, tau=PLATE_TAU_S,
                 rate_full=RATE_FULL_C_PER_S, seed=1):
        self.ambient = ambient
        self.tau = tau
        self.rate_full = rate_full
        self.true_c = ambient
        self.pwm = 0
        self.heating = True
        self._random = random.Random(seed)

    # ---- command interface, mirrors the Arduino ----------------------
    def set_command(self, pwm, heating):
        self.pwm = max(0, min(255, int(pwm)))
        self.heating = bool(heating)

    # ---- advance the model -------------------------------------------
    def step(self, dt_s):
        drive = self.rate_full * (self.pwm / 255.0) * (1.0 if self.heating else -1.0)
        decay = (self.ambient - self.true_c) / self.tau
        self.true_c += (decay + drive) * dt_s

    # ---- what the instrument would report ----------------------------
    def measured(self):
        """Push the true temperature through the real measurement chain.

        Returns (adc, volts, ohms, celsius) with the ADC quantization and
        noise that the hardware has, so the demo cannot look better than the
        instrument does.
        """
        ohms_true = resistance_at(self.true_c)
        volts_true = V_REF * ohms_true / (ohms_true + R_FIXED)
        adc_true = volts_true / V_REF * 1023.0

        adc = adc_true + self._random.gauss(0.0, ADC_NOISE_COUNTS)
        adc = round(adc, 1)                     # the sketch prints one decimal
        adc = max(0.0, min(1023.0, adc))

        volts = adc * V_REF / 1023.0
        ohms = R_FIXED * volts / (V_REF - volts) if 0.0 < volts < V_REF else -1.0
        return adc, volts, ohms, celsius_at(ohms)

    def line(self, elapsed_s):
        """Format one measurement line exactly as the Part 3 sketch does."""
        adc, volts, ohms, celsius = self.measured()
        ok = 20.0 < adc < 1000.0
        temperature_field = f"{celsius:.2f}" if ok else "---"
        resistance_field = f"{ohms / 1000.0:.2f} kOhm" if ohms > 0 else "out of range"
        active_pin = "none" if self.pwm == 0 else ("9" if self.heating else "10")
        return (
            f"Temperature (C): {temperature_field}, "
            f"Time (s): {elapsed_s:.2f}, "
            f"PWM: {self.pwm}, "
            f"Heat/Cool: {1 if self.heating else 0}"
            f"   [ADC = {adc:.1f}, V = {volts:.3f}, R = {resistance_field}, "
            f"pin 11 = {'5V' if self.heating else '0V'}, "
            f"PWM on pin {active_pin}, "
            f"{'heating' if self.heating else 'cooling'}]"
        )


# =====================================================================
# QT WRAPPER
# =====================================================================
# Imported lazily so the model above can be tested with plain Python and no
# Qt installed.

def make_demo_reader(qtcore):
    """Build a DemoReader class bound to the given QtCore module.

    The returned class is signal-compatible with SerialReader and SerialLink:
    same line_received and error signals, same start/stop, and a
    send_command() that steers the model instead of a serial port. The window
    code does not need to know which source it is talking to.
    """

    class DemoReader(qtcore.QThread):
        line_received = qtcore.Signal(str)
        error = qtcore.Signal(str)

        REPORT_INTERVAL_S = 0.5      # matches reportIntervalMs in the sketch

        def __init__(self, parent=None):
            super().__init__(parent)
            self.model = PlantModel()
            self._running = True
            self._elapsed = 0.0

        def run(self):
            self.line_received.emit(
                "Phys 39 Module 3 Part 3: manual TEC, hardware direction switch. "
                "Naidu / Cohen")
            self.line_received.emit(
                "# DEMO SOURCE. Synthetic data from a thermal model, not a "
                "measurement. Set DEMO_MODE = False to use the Arduino.")
            while self._running:
                self.model.step(self.REPORT_INTERVAL_S)
                self._elapsed += self.REPORT_INTERVAL_S
                self.line_received.emit(self.model.line(self._elapsed))
                self.msleep(int(self.REPORT_INTERVAL_S * 1000))

        def send_command(self, text):
            """Accept the same SET PWM n DIR HEAT|COOL line the Arduino takes."""
            parts = text.strip().split()
            try:
                pwm = int(parts[parts.index("PWM") + 1])
                heating = parts[parts.index("DIR") + 1].upper() == "HEAT"
            except (ValueError, IndexError):
                self.line_received.emit("# DEMO: command not understood, PWM set to 0")
                self.model.set_command(0, True)
                return
            self.model.set_command(pwm, heating)

        def stop(self):
            self._running = False
            self.wait(1000)

    return DemoReader
