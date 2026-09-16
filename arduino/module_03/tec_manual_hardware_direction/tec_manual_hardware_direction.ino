/*
  Phys 39 Module 3, Part 3. Second manual sketch, hardware direction input.
  Naidu / Cohen

  Same measurement and actuator chain as tec_manual_fixed_direction, with the
  wire swap replaced by an SPDT slide switch on pin 11.

  PINS
    A0   thermistor divider midpoint
    A1   trim pot wiper
    9    RPWM on the H-bridge
    10   LPWM on the H-bridge
    11   SPDT direction switch, common terminal. Outer terminals to 5V and GND.

  SET THE DIRECTION CALIBRATION BEFORE USING THIS SKETCH

    PIN9_IS_HEAT below must be set from the Part 2 experiment, not from a pin
    number. The assignment is explicit: Heat/Cool: 1 must mean OBSERVED
    heating and Heat/Cool: 0 must mean OBSERVED cooling, at the thermistor
    embedded in the TEC plate.

    Procedure. Run tec_manual_fixed_direction (PWM on pin 10, pin 9 LOW), let
    the plate settle, apply low power, and watch the reported temperature for
    long enough to be sure of the sign. The TEC plate has real thermal mass
    and the thermistor has a time constant of roughly 15 s, so give it time.

      plate temperature RISES with PWM on pin 10  ->  pin 10 is heat
                                                  ->  set PIN9_IS_HEAT = false
      plate temperature FALLS with PWM on pin 10  ->  pin 10 is cool
                                                  ->  set PIN9_IS_HEAT = true

    Until that observation is made, the Heat/Cool field is unverified.
*/

#include <math.h>

// ---- SET THIS FROM THE PART 2 EXPERIMENT -----------------------------
// true  = PWM on pin 9 heats the plate, pin 10 cools it
// false = PWM on pin 9 cools the plate, pin 10 heats it
const bool PIN9_IS_HEAT = true;   // placeholder, confirm on the bench

// ---- thermistor ------------------------------------------------------

// ---- THERMISTOR CHANNEL ----------------------------------------------
//
// Wire it exactly as the assignment specifies, with the thermistor as the
// LOWER leg, because voltageToResistance() below inverts the divider on
// that assumption:
//
//     5V --- Rfixed --- A0 --- thermistor --- GND
//
// Expected at room temperature with the Module 2 100 kOhm parts:
//     ADC about 560, 2.75 V, 120 kOhm, 21 C
//
// If the plate thermistor turns out to be a 10 kOhm part rather than the
// 100 kOhm breadboard part, set SENSOR_IS_10K to 1 and take B from the part
// number rather than assuming it. Decide that by reading the values back,
// not in advance.
#define SENSOR_IS_10K 0

#if SENSOR_IS_10K
  const float Rnominal = 10000.0;    // ohms at 25 C
  const float Beta     = 3435.0;     // kelvin. CONFIRM against the part number.
  const char  sensorName[] = "10 kOhm plate thermistor";
#else
  const float Rnominal = 100000.0;   // ohms at 25 C
  const float Beta     = 4540.0;     // TDK/EPCOS B57861S0104F040V24, B25/100
  const char  sensorName[] = "100 kOhm thermistor, TDK B57861S0104F040V24";
#endif

// Rfixed is PHYSICAL. It must match the resistor actually in the upper leg.
// 100 kOhm is brown-black-yellow, 10 kOhm is brown-black-orange.
const float Rfixed = 100000.0;

// VALIDATING THE TEMPERATURE CHANNEL
//
// An unconnected analog input still returns numbers, and 500-sample
// averaging makes whatever it returns look steady. A plausible constant is
// harder to spot than an obviously broken one, so the channel is checked by
// its RESPONSE rather than by the value it reports.
//
// Warm the thermistor between finger and thumb and watch the ADC field:
//
//      ADC falls      -> correct. An NTC as the lower leg loses resistance
//      ADC rises      -> the two divider legs are swapped
//      ADC does not move -> the sensor is not in the circuit
//
// Run this check every time the divider is rebuilt. The plausibility window
// below catches a divider that is absent or shorted, but only the sign of
// the response confirms the sensor is the one being measured.

const int   thermistorPin = A0;
const float Vref          = 5.0;     // volts
const float Tnominal      = 25.0;    // deg C
const float KELVIN_OFFSET = 273.15;
const int   sampleCount   = 500;     // assignment requires 100 to 1000

// ---- actuator --------------------------------------------------------

const int potPin  = A1;
const int dirPin  = 11;
const int rpwmPin = 9;
const int lpwmPin = 10;

const int potSamples = 200;
const int maxDuty    = 64;    // low-power cap, about 25%. Raise only with approval.

const int armBelowAdc = 10;
bool armed = false;

const unsigned long reportIntervalMs = 500;
unsigned long lastReportMs = 0;

// ---- measurement chain -----------------------------------------------

float averageAdcSamples() {
  unsigned long total = 0;
  for (int i = 0; i < sampleCount; i++) total += analogRead(thermistorPin);
  return (float)total / (float)sampleCount;
}

float adcToVoltage(float adcValue) { return adcValue * Vref / 1023.0; }

float voltageToResistance(float volts) {
  if (volts <= 0.0)  return -1.0;
  if (volts >= Vref) return -1.0;
  return Rfixed * volts / (Vref - volts);
}

// A healthy divider puts A0 near mid scale. This window is deliberately
// wide: with 100 kOhm against 100 kOhm, ADC 20 is about 118 C and ADC 1000
// is about -40 C, so a reading outside it indicates a wiring fault rather
// than a temperature.
bool adcPlausible(float adcValue) {
  return adcValue > 20.0 && adcValue < 1000.0;
}

const char *dividerHint(float adcValue) {
  if (adcValue <= 20.0)
    return "A0 near 0 V: no upper resistor from 5V, or the sensor is on another pin";
  if (adcValue >= 1000.0)
    return "A0 near 5 V: thermistor leg open or missing to GND";
  return "";
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

// Exactly one input carries PWM. The idle input is driven to a hard LOW
// BEFORE the active one is energized, so there is never an instant with both
// asserted, and the idle side is never held HIGH.
void setDrive(bool pwmOnPin9, int duty) {
  duty = constrain(duty, 0, maxDuty);

  if (duty == 0) {
    digitalWrite(rpwmPin, LOW);
    digitalWrite(lpwmPin, LOW);
    return;
  }
  if (pwmOnPin9) {
    digitalWrite(lpwmPin, LOW);
    analogWrite(rpwmPin, duty);
  } else {
    digitalWrite(rpwmPin, LOW);
    analogWrite(lpwmPin, duty);
  }
}

void setup() {
  pinMode(rpwmPin, OUTPUT);
  pinMode(lpwmPin, OUTPUT);
  digitalWrite(rpwmPin, LOW);
  digitalWrite(lpwmPin, LOW);

  // The SPDT switch drives pin 11 hard to 5V or GND, so a pull-up is not
  // needed to define the level. It is enabled anyway as a failure mode: if
  // the switch lead comes off, the pin reads HIGH instead of floating and
  // picking up noise. The assignment's rule is that pin 11 must never be
  // left unconnected.
  pinMode(dirPin, INPUT_PULLUP);

  Serial.begin(9600);
  delay(200);
  Serial.println();
  Serial.println("Phys 39 Module 3 Part 3: manual TEC, hardware direction switch. Naidu / Cohen");
  Serial.print("Sensor: ");
  Serial.print(sensorName);
  Serial.print(", R25 = ");
  Serial.print(Rnominal / 1000.0, 1);
  Serial.print(" kOhm, Beta = ");
  Serial.print(Beta, 0);
  Serial.print(" K, upper leg = ");
  Serial.print(Rfixed / 1000.0, 1);
  Serial.println(" kOhm");
  Serial.print("Calibration in use: PWM on pin 9 = ");
  Serial.println(PIN9_IS_HEAT ? "HEAT" : "COOL");
  Serial.print("Max duty ");
  Serial.print(maxDuty);
  Serial.println(" of 255.");
  Serial.println("DISARMED. Turn the trim pot to zero to arm the output.");
  Serial.println();
}

void loop() {
  unsigned long now = millis();
  if (now - lastReportMs < reportIntervalMs) return;
  lastReportMs = now;

  float potAdc   = averagePot();
  float adcValue = averageAdcSamples();
  float volts    = adcToVoltage(adcValue);
  float ohms     = voltageToResistance(volts);
  float celsius  = resistanceToCelsius(ohms);

  if (!armed && potAdc < armBelowAdc) {
    armed = true;
    Serial.println("ARMED: trim pot seen at zero. Output now follows the knob.");
  }

  int duty = 0;
  if (armed) {
    duty = map((long)potAdc, 0, 1023, 0, maxDuty);
    duty = constrain(duty, 0, maxDuty);
  }

  // Read the switch, then translate pin state into a PHYSICAL claim using
  // the calibration constant. dirHigh is what the pin says; heating is what
  // the plate actually does.
  bool dirHigh = (digitalRead(dirPin) == HIGH);
  bool pwmOnPin9 = dirHigh;                       // switch position -> which pin
  bool heating   = (pwmOnPin9 == PIN9_IS_HEAT);   // pin -> observed physics

  setDrive(pwmOnPin9, duty);

  // Measurement line format required for the rest of the module. Heat/Cool
  // is 1 for observed heating and 0 for observed cooling.
  bool ok = adcPlausible(adcValue);

  Serial.print("Temperature (C): ");
  if (!ok || isnan(celsius)) Serial.print("---"); else Serial.print(celsius, 2);
  Serial.print(", Time (s): ");
  Serial.print(now / 1000.0, 2);
  Serial.print(", PWM: ");
  Serial.print(duty);
  Serial.print(", Heat/Cool: ");
  Serial.print(heating ? 1 : 0);

  // Extra diagnostic fields, useful for the Part 3 oscilloscope table and
  // harmless to the Python parser, which reads the four labeled fields above.
  Serial.print("   [ADC = ");
  Serial.print(adcValue, 1);
  Serial.print(", V = ");
  Serial.print(volts, 3);
  Serial.print(", R = ");
  if (ohms < 0.0) Serial.print("out of range");
  else { Serial.print(ohms / 1000.0, 2); Serial.print(" kOhm"); }
  Serial.print(", pin 11 = ");
  Serial.print(dirHigh ? "5V" : "0V");
  Serial.print(", PWM on pin ");
  Serial.print(duty > 0 ? (pwmOnPin9 ? "9" : "10") : "none");
  Serial.print(", ");
  Serial.print(heating ? "heating" : "cooling");
  if (!armed) Serial.print(", DISARMED");
  if (!ok) { Serial.print(", "); Serial.print(dividerHint(adcValue)); }
  Serial.println("]");
}
