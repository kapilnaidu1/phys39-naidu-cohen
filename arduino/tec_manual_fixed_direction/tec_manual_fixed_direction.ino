/*
  Phys 39 Module 3, Part 2. First manual sketch, fixed direction.
  Naidu / Cohen

  SIGNAL PATH (from the assignment)
    A0 thermistor    -> average -> temperature
    A1 trim pot      -> ADC value -> PWM command
    fixed direction  -> H-bridge -> TEC

  This version holds pin 9 LOW and sends the trim-pot PWM command to pin 10.
  Which way that drives heat is NOT assumed here. It is determined by
  experiment after the instructor approves power, and recorded in
  docs/module_notes/module_03_tec_gui.md.

  PINS
    A0   thermistor divider midpoint  (5V - 100k fixed - A0 - thermistor - GND)
    A1   trim pot wiper               (outer terminals to 5V and GND)
    9    RPWM on the H-bridge         held LOW for this sketch
    10   LPWM on the H-bridge         carries the PWM command

  SAFETY, and why this sketch is built the way it is

    1. PWM must start at zero. The trim pot is a physical knob, so nothing in
       software can guarantee where it is sitting when the board resets. This
       sketch therefore starts DISARMED: the output is forced to 0 until the
       pot has been seen at essentially zero at least once. Turn the knob to
       zero to arm it. This is what makes the "PWM starts at zero?" line of
       the pre-power checklist true rather than hopeful.

    2. Low power first. maxDuty caps the command well below full scale for the
       first TEC power-on. Raise it only with the instructor's approval.

    3. Pins 9 and 10 are logic-level H-bridge control inputs. They are not
       ground and they are not the power outputs M+ and M-.

    4. Every oscilloscope probe ground clip goes to Arduino GND. Never to M+
       or M-: a ground clip is earth-referenced and can short a driven output.

    5. Do not run the TEC without its heat exchanger. Confirm the pump and
       radiator fans are turning before any current flows.
*/

#include <math.h>

// ---- thermistor, unchanged from Module 2 ------------------------------

const int   thermistorPin = A0;
const float Vref          = 5.0;        // volts
const float Rfixed        = 100000.0;   // ohms, upper leg
const float Rnominal      = 100000.0;   // ohms at 25 C
const float Tnominal      = 25.0;       // deg C
const float Beta          = 4540.0;     // kelvin, B25/100, TDK B57861S0104F040V24
const float KELVIN_OFFSET = 273.15;

const int   sampleCount   = 500;        // assignment requires 100 to 1000

// ---- actuator --------------------------------------------------------

const int potPin  = A1;
const int rpwmPin = 9;     // held LOW in this sketch
const int lpwmPin = 10;    // carries PWM in this sketch

const int potSamples = 200;

// Low-power cap for the first TEC run. 64 of 255 is about 25%.
// Raise only after the instructor has checked the wiring and current limit.
const int maxDuty = 64;

// Arming threshold in ADC counts. The pot must be turned down to at least
// this before any output is allowed.
const int armBelowAdc = 10;
bool armed = false;

const unsigned long reportIntervalMs = 500;
unsigned long lastReportMs = 0;

// ---- measurement chain -----------------------------------------------
// The required order: average the raw ADC readings first, convert once.
// Converting each reading to temperature and then averaging would be wrong,
// because the resistance-to-temperature relation is nonlinear.

float averageAdcSamples() {
  unsigned long total = 0;              // 500 * 1023 overflows a 16-bit int
  for (int i = 0; i < sampleCount; i++) total += analogRead(thermistorPin);
  return (float)total / (float)sampleCount;
}

float adcToVoltage(float adcValue) {
  return adcValue * Vref / 1023.0;
}

float voltageToResistance(float volts) {
  if (volts <= 0.0)  return -1.0;       // shorted, or A0 disconnected
  if (volts >= Vref) return -1.0;       // thermistor open
  return Rfixed * volts / (Vref - volts);
}

float resistanceToCelsius(float ohms) {
  if (ohms <= 0.0) return NAN;
  float invT = 1.0 / (Tnominal + KELVIN_OFFSET)
             + (1.0 / Beta) * log(ohms / Rnominal);
  return 1.0 / invT - KELVIN_OFFSET;
}

float averagePot() {
  unsigned long total = 0;
  for (int i = 0; i < potSamples; i++) total += analogRead(potPin);
  return (float)total / (float)potSamples;
}

// ---- actuator output -------------------------------------------------

// Fixed direction: pin 9 is driven LOW first and stays LOW, pin 10 carries
// the command. The idle input is held at a hard LOW, never HIGH: on this
// driver, holding the idle input high while pulsing the other inverts the
// duty cycle, so a commanded zero would mean full drive.
void setDrive(int duty) {
  duty = constrain(duty, 0, maxDuty);
  digitalWrite(rpwmPin, LOW);
  if (duty == 0) {
    digitalWrite(lpwmPin, LOW);
    return;
  }
  analogWrite(lpwmPin, duty);
}

void setup() {
  // Both H-bridge inputs low before anything else, so the bridge is never
  // commanded during boot or reset.
  pinMode(rpwmPin, OUTPUT);
  pinMode(lpwmPin, OUTPUT);
  digitalWrite(rpwmPin, LOW);
  digitalWrite(lpwmPin, LOW);

  Serial.begin(9600);
  delay(200);
  Serial.println();
  Serial.println("Phys 39 Module 3 Part 2: manual TEC, fixed direction. Naidu / Cohen");
  Serial.print("PWM on pin 10, pin 9 held LOW. Max duty ");
  Serial.print(maxDuty);
  Serial.println(" of 255.");
  Serial.println("DISARMED. Turn the trim pot to zero to arm the output.");
  Serial.println();
}

void loop() {
  unsigned long now = millis();
  if (now - lastReportMs < reportIntervalMs) return;   // wrap-safe
  lastReportMs = now;

  float potAdc  = averagePot();
  float adcValue = averageAdcSamples();
  float volts    = adcToVoltage(adcValue);
  float ohms     = voltageToResistance(volts);
  float celsius  = resistanceToCelsius(ohms);

  // Arm once the knob has been turned down. It never disarms after that,
  // so the interlock protects the power-on transient, not later operation.
  if (!armed && potAdc < armBelowAdc) {
    armed = true;
    Serial.println("ARMED: trim pot seen at zero. Output now follows the knob.");
  }

  int duty = 0;
  if (armed) {
    duty = map((long)potAdc, 0, 1023, 0, maxDuty);
    duty = constrain(duty, 0, maxDuty);
  }
  setDrive(duty);

  // Measurement line format required by the assignment.
  Serial.print("Temperature (C): ");
  if (isnan(celsius)) Serial.print("---"); else Serial.print(celsius, 2);
  Serial.print(", Time (s): ");
  Serial.print(now / 1000.0, 2);
  Serial.print(", PWM: ");
  Serial.print(duty);
  Serial.print(", Active PWM pin: ");
  Serial.print(duty > 0 ? "10" : "none");
  if (!armed) Serial.print("   [DISARMED, turn trim pot to zero]");
  Serial.println();
}
