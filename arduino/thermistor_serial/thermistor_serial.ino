/*
  Phys 39 Module 2, Part 1 and Part 2.
  Thermistor serial data and temperature conversion.

  Naidu / Cohen

  CIRCUIT
    5V --- 100 kOhm fixed resistor --- A0 --- NTC thermistor --- GND

    The thermistor is the LOWER leg, so A0 sits across the thermistor.
    An NTC falls in resistance as it warms, so the voltage at A0 FALLS
    as temperature rises. If warming the thermistor moves the reading
    the wrong way, the two legs are swapped.

  SENSOR
    TDK/EPCOS B57861S0104F040V24, R/T characteristic No. 2014
    R25 = 100.000 kOhm, B25/100 = 4540 K, tolerance +/-1%

  ACQUISITION ORDER (required by the assignment from this module onward)
    average many raw ADC readings -> one average voltage -> resistance
    -> temperature.  NOT temperature-per-reading then averaged.
    The resistance-to-temperature relation is nonlinear, so the mean of
    the temperatures is not the temperature of the mean.

  NOTE ON THE BETA MODEL
    B25/100 is fitted over 25 C to 100 C. Near room temperature we are
    extrapolating below that interval, so this model disagrees with the
    manufacturer's own R/T table by roughly 0.5 C at 15 C and 35 C. It is
    exact only at 25 C, where it is anchored. See docs/module_notes/
    module_02_preclass.md for the numbers.
*/

#include <math.h>

// ---- circuit and sensor constants -------------------------------------

const int   analogPin   = A0;
const float Vref        = 5.0;        // volts, Arduino analog reference
const float Rfixed      = 100000.0;   // ohms, precision resistor, upper leg
const float Rnominal    = 100000.0;   // ohms, thermistor resistance at 25 C
const float Tnominal    = 25.0;       // deg C, temperature where Rnominal applies
const float Beta        = 4540.0;     // kelvin, B25/100 from the data sheet

const int   sampleCount = 500;        // must be between 100 and 1000

const float KELVIN_OFFSET = 273.15;

// ---- output mode ------------------------------------------------------
// false = Part 1, one labeled human-readable line for Serial Monitor
// true  = Part 2, one bare number per line so Serial Plotter graphs it
const bool PLOTTER_MODE = false;

const unsigned long reportIntervalMs = 500;
unsigned long lastReportMs = 0;

// ---- measurement chain ------------------------------------------------

// Reads A0 sampleCount times and returns the mean ADC value.
// The accumulator is unsigned long, not int: 1000 * 1023 = 1,023,000
// overflows the 16-bit int on an Uno. Returns a float because the mean
// of many integers is not itself an integer.
float averageAdcSamples() {
  unsigned long total = 0;
  for (int i = 0; i < sampleCount; i++) {
    total += analogRead(analogPin);
  }
  return (float)total / (float)sampleCount;
}

// ADC count -> volts. 1023 is used, not 1024, because the assignment's
// conversion maps the top code to exactly Vref.
float adcToVoltage(float adcValue) {
  return adcValue * Vref / 1023.0;
}

// Volts at A0 -> thermistor resistance, by inverting the divider.
//   V = Vref * Rth / (Rth + Rfixed)
//   V * Rfixed = Rth * (Vref - V)
//   Rth = Rfixed * V / (Vref - V)
// Returns -1 for an impossible reading: V at 0 means the thermistor is
// shorted or A0 is disconnected, V at Vref means the thermistor is open.
// Both would otherwise divide by zero or blow up.
float voltageToResistance(float volts) {
  if (volts <= 0.0)  return -1.0;
  if (volts >= Vref) return -1.0;
  return Rfixed * volts / (Vref - volts);
}

// Thermistor resistance -> temperature, beta equation:
//   1/T = 1/T0 + (1/B) * ln(R/R0),  T and T0 in kelvin
// log() in Arduino is the natural logarithm.
float resistanceToCelsius(float ohms) {
  if (ohms <= 0.0) return NAN;
  float invT = 1.0 / (Tnominal + KELVIN_OFFSET)
             + (1.0 / Beta) * log(ohms / Rnominal);
  return 1.0 / invT - KELVIN_OFFSET;
}

// ---- output -----------------------------------------------------------

// Every printed number carries a label and a unit, so the line can be
// read without memorizing a column order. This is the only function to
// edit if the output should look different.
void printHumanReadable(float seconds, float adcValue, float volts,
                        float ohms, float celsius) {
  Serial.print("time = ");
  Serial.print(seconds, 2);
  Serial.print(" s");

  Serial.print("    average ADC = ");
  Serial.print(adcValue, 1);

  Serial.print("    voltage = ");
  Serial.print(volts, 3);
  Serial.print(" V");

  Serial.print("    resistance = ");
  if (ohms < 0.0) {
    Serial.print("out of range");
  } else {
    Serial.print(ohms / 1000.0, 2);
    Serial.print(" kOhm");
  }

  Serial.print("    temperature = ");
  if (isnan(celsius)) {
    Serial.print("---");
  } else {
    Serial.print(celsius, 1);
    Serial.print(" C");
  }

  Serial.print("    samples = ");
  Serial.println(sampleCount);
}

// ---- setup and loop ---------------------------------------------------

void setup() {
  Serial.begin(9600);
  delay(200);

  if (!PLOTTER_MODE) {
    Serial.println();
    Serial.println("Phys 39 Module 2 Part 1: thermistor divider, Naidu / Cohen");
    Serial.print("Rfixed = ");
    Serial.print(Rfixed / 1000.0, 1);
    Serial.print(" kOhm    R25 = ");
    Serial.print(Rnominal / 1000.0, 1);
    Serial.print(" kOhm    Beta = ");
    Serial.print(Beta, 0);
    Serial.print(" K    samples per report = ");
    Serial.println(sampleCount);
    Serial.println();
  }
}

void loop() {
  // Non-blocking report timer. Unsigned subtraction is wrap-safe, so this
  // keeps working after millis() rolls over at about 49 days.
  unsigned long now = millis();
  if (now - lastReportMs < reportIntervalMs) return;
  lastReportMs = now;

  // The required order: average first, then convert once.
  float adcValue = averageAdcSamples();
  float volts    = adcToVoltage(adcValue);
  float ohms     = voltageToResistance(volts);
  float celsius  = resistanceToCelsius(ohms);

  if (PLOTTER_MODE) {
    // Part 2: exactly one numeric value per line and nothing else, which
    // is what Serial Plotter needs to draw temperature versus read order.
    Serial.println(celsius, 2);
  } else {
    printHumanReadable(now / 1000.0, adcValue, volts, ohms, celsius);
  }
}
