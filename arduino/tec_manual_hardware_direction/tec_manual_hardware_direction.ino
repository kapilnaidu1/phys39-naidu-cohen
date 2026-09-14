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

  THE ONE THING TO SET BEFORE THIS SKETCH IS HONEST

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

    Until that observation is made and recorded, leave the placeholder value
    and treat the Heat/Cool field as unverified.
*/

#include <math.h>

// ---- SET THIS FROM THE PART 2 EXPERIMENT -----------------------------
// true  = PWM on pin 9 heats the plate, pin 10 cools it
// false = PWM on pin 9 cools the plate, pin 10 heats it
const bool PIN9_IS_HEAT = true;   // placeholder, confirm on the bench

// ---- thermistor ------------------------------------------------------

const int   thermistorPin = A0;
const float Vref          = 5.0;
const float Rfixed        = 100000.0;
const float Rnominal      = 100000.0;
const float Tnominal      = 25.0;
const float Beta          = 4540.0;
const float KELVIN_OFFSET = 273.15;
const int   sampleCount   = 500;

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
  Serial.print("Temperature (C): ");
  if (isnan(celsius)) Serial.print("---"); else Serial.print(celsius, 2);
  Serial.print(", Time (s): ");
  Serial.print(now / 1000.0, 2);
  Serial.print(", PWM: ");
  Serial.print(duty);
  Serial.print(", Heat/Cool: ");
  Serial.print(heating ? 1 : 0);

  // Extra diagnostic fields, useful for the Part 3 oscilloscope table and
  // harmless to the Python parser, which reads the four labeled fields above.
  Serial.print("   [pin 11 = ");
  Serial.print(dirHigh ? "5V" : "0V");
  Serial.print(", PWM on pin ");
  Serial.print(duty > 0 ? (pwmOnPin9 ? "9" : "10") : "none");
  Serial.print(", ");
  Serial.print(heating ? "heating" : "cooling");
  if (!armed) Serial.print(", DISARMED");
  Serial.println("]");
}
