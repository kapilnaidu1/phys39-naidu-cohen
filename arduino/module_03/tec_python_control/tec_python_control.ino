/*
  Phys 39 Module 3, Part 6. Arduino serial-command control sketch.
  Naidu / Cohen

  Descended from the manual trim-pot sketch. The thermistor measurement and
  the H-bridge output behaviour are unchanged. What is replaced is the input:
  the trim pot and the physical direction switch are gone, and PWM and
  direction now arrive as commands from the Python GUI.

  PINS
    A0   thermistor divider midpoint (5V - 100k fixed - A0 - thermistor - GND)
    9    RPWM on the H-bridge
    10   LPWM on the H-bridge
    A1 and 11 are no longer read. Leaving the pot and switch physically wired
    is harmless; this sketch simply ignores them.

  COMMANDS ACCEPTED (one per line)
    SET PWM 120 DIR HEAT
    SET PWM 45 DIR COOL

  Anything else, including a malformed number, an unknown direction word, or
  a truncated line, sets PWM to zero. That is the assignment's rule and it is
  the right default for an actuator: when the instrument stops understanding
  its instructions, it should stop driving current, not keep the last value.

  MEASUREMENT LINE PRINTED (the format for the rest of the module)
    Temperature (C): 27.73, Time (s): 645.06, PWM: 120, Heat/Cool: 1

  Acknowledgements and errors are printed on separate lines beginning with
  "# ", so the Python parser can show them in the terminal without mistaking
  them for measurements.

  SET THIS FROM THE PART 2 AND 3 EXPERIMENT
    PIN9_IS_HEAT must carry the mapping you verified on the bench. HEAT must
    command the direction that was OBSERVED to raise the plate temperature.
    A pin number is not evidence.

  SAFETY
    PWM starts at zero on reset and stays there until a valid command
    arrives. There is no knob, so unlike the manual sketches there is nothing
    to arm: a fresh boot cannot be driving the TEC.
    Every scope probe ground clip goes to Arduino GND, never to M+ or M-.
    Do not run the TEC without its heat exchanger running.
*/

#include <math.h>

// ---- SET FROM THE BENCH EXPERIMENT -----------------------------------
// true  = PWM on pin 9 heats the plate, pin 10 cools it
// false = PWM on pin 9 cools the plate, pin 10 heats it
const bool PIN9_IS_HEAT = true;   // placeholder, confirm and record

// ---- thermistor, unchanged from Module 2 -----------------------------

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

const int rpwmPin = 9;
const int lpwmPin = 10;

// The command range is 0 to 255, as the assignment specifies. Lower this for
// a first power-on if the instructor wants the command ceiling reduced.
const int maxDuty = 255;

// Commanded state. Both start at the safe value.
int  commandedPwm     = 0;
bool commandedHeating = true;

// ---- serial command buffer -------------------------------------------
// Fixed-size buffer, no String objects. String on an Uno fragments the heap
// over a long run, and this sketch is meant to be left running.

const int  bufSize = 48;
char       buf[bufSize];
int        bufLen = 0;

const unsigned long reportIntervalMs = 500;
unsigned long lastReportMs = 0;

// ---- measurement chain -----------------------------------------------
// Average the raw counts first, then convert once. The resistance to
// temperature step is nonlinear, so the mean of the temperatures is not the
// temperature of the mean.

float averageAdcSamples() {
  unsigned long total = 0;              // 500 * 1023 overflows a 16-bit int
  for (int i = 0; i < sampleCount; i++) total += analogRead(thermistorPin);
  return (float)total / (float)sampleCount;
}

float adcToVoltage(float adcValue) { return adcValue * Vref / 1023.0; }

float voltageToResistance(float volts) {
  if (volts <= 0.0)  return -1.0;       // shorted, or A0 disconnected
  if (volts >= Vref) return -1.0;       // thermistor open
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

// ---- actuator output -------------------------------------------------

// Exactly one input carries PWM. The idle input is driven to a hard LOW
// BEFORE the active one is energized, so there is never an instant with both
// asserted, and the idle side is never held HIGH. Holding the idle input
// high on this driver inverts the duty cycle, which would turn a commanded
// zero into full drive.
void applyDrive() {
  int duty = constrain(commandedPwm, 0, maxDuty);

  if (duty == 0) {
    digitalWrite(rpwmPin, LOW);
    digitalWrite(lpwmPin, LOW);
    return;
  }

  bool pwmOnPin9 = (commandedHeating == PIN9_IS_HEAT);

  if (pwmOnPin9) {
    digitalWrite(lpwmPin, LOW);
    analogWrite(rpwmPin, duty);
  } else {
    digitalWrite(rpwmPin, LOW);
    analogWrite(lpwmPin, duty);
  }
}

// Force the safe state and say why.
void failSafe(const char *why) {
  commandedPwm = 0;
  applyDrive();
  Serial.print("# PWM set to 0: ");
  Serial.println(why);
}

// ---- command parsing -------------------------------------------------
// Expected exactly: SET PWM <int> DIR <HEAT|COOL>
// Returns true only if the whole line was understood.

bool parseCommand(char *line) {
  // Tokenize on spaces and tabs. strtok writes into the buffer, which is
  // fine because the buffer is discarded after this call.
  char *t1 = strtok(line, " \t");   // SET
  char *t2 = strtok(NULL, " \t");   // PWM
  char *t3 = strtok(NULL, " \t");   // the number
  char *t4 = strtok(NULL, " \t");   // DIR
  char *t5 = strtok(NULL, " \t");   // HEAT or COOL
  char *t6 = strtok(NULL, " \t");   // must be nothing

  if (!t1 || !t2 || !t3 || !t4 || !t5) return false;
  if (t6) return false;                          // trailing junk
  if (strcmp(t1, "SET") != 0) return false;
  if (strcmp(t2, "PWM") != 0) return false;
  if (strcmp(t4, "DIR") != 0) return false;

  // The number must be entirely digits, with an optional leading sign.
  // atoi() alone would silently turn "12x" into 12 and "abc" into 0, which
  // would let a malformed command through as a valid zero.
  char *p = t3;
  if (*p == '+' || *p == '-') p++;
  if (*p == '\0') return false;
  for (char *q = p; *q; q++) {
    if (!isdigit((unsigned char)*q)) return false;
  }
  long value = atol(t3);

  bool heating;
  if      (strcmp(t5, "HEAT") == 0) heating = true;
  else if (strcmp(t5, "COOL") == 0) heating = false;
  else return false;

  // Out-of-range numbers are clamped rather than rejected, which is what
  // the assignment asks for. A value of 300 is a legal command for full
  // scale; only a value that is not a number is malformed.
  if (value < 0)   value = 0;
  if (value > 255) value = 255;

  commandedPwm     = (int)value;
  commandedHeating = heating;
  return true;
}

void handleLine() {
  // Trim trailing whitespace and carriage returns. Serial Monitor may send
  // CR, LF, or both depending on its line-ending setting, and a stray CR
  // would otherwise make "COOL\r" fail to match "COOL".
  while (bufLen > 0 &&
         (buf[bufLen - 1] == '\r' || buf[bufLen - 1] == ' ' ||
          buf[bufLen - 1] == '\t')) {
    bufLen--;
  }
  buf[bufLen] = '\0';

  // Skip leading whitespace.
  char *line = buf;
  while (*line == ' ' || *line == '\t') line++;

  if (*line == '\0') {          // a bare newline is not a command
    bufLen = 0;
    return;
  }

  // Keep a copy for the echo, because strtok will chop the original up.
  char echo[bufSize];
  strncpy(echo, line, bufSize - 1);
  echo[bufSize - 1] = '\0';

  if (parseCommand(line)) {
    applyDrive();
    Serial.print("# OK: PWM ");
    Serial.print(commandedPwm);
    Serial.print(" DIR ");
    Serial.print(commandedHeating ? "HEAT" : "COOL");
    Serial.print("  (PWM on pin ");
    if (commandedPwm == 0) Serial.print("none");
    else Serial.print((commandedHeating == PIN9_IS_HEAT) ? "9" : "10");
    Serial.println(")");
  } else {
    Serial.print("# malformed command: \"");
    Serial.print(echo);
    Serial.println("\"");
    failSafe("command not understood");
  }

  bufLen = 0;
}

void readSerial() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\n') {
      handleLine();
      continue;
    }

    if (bufLen < bufSize - 1) {
      buf[bufLen++] = c;
    } else {
      // Overrun. Discard the line rather than acting on a fragment, and go
      // to the safe state, because a truncated command is a malformed one.
      bufLen = 0;
      failSafe("command line too long");
      // Swallow the rest of the offending line.
      while (Serial.available() > 0 && Serial.read() != '\n') { }
    }
  }
}

void setup() {
  // Outputs low before anything else, so the bridge is never commanded
  // during boot or reset.
  pinMode(rpwmPin, OUTPUT);
  pinMode(lpwmPin, OUTPUT);
  digitalWrite(rpwmPin, LOW);
  digitalWrite(lpwmPin, LOW);

  Serial.begin(9600);
  delay(200);
  Serial.println();
  Serial.println("# Phys 39 Module 3 Part 6: TEC serial-command control. Naidu / Cohen");
  Serial.print("# Sensor: ");
  Serial.print(sensorName);
  Serial.print(", R25 = ");
  Serial.print(Rnominal / 1000.0, 1);
  Serial.print(" kOhm, Beta = ");
  Serial.print(Beta, 0);
  Serial.print(" K, upper leg = ");
  Serial.print(Rfixed / 1000.0, 1);
  Serial.println(" kOhm");
  Serial.print("# Calibration in use: PWM on pin 9 = ");
  Serial.println(PIN9_IS_HEAT ? "HEAT" : "COOL");
  Serial.println("# Commands: SET PWM <0-255> DIR <HEAT|COOL>");
  Serial.println("# PWM starts at 0 and stays there until a valid command arrives.");
  Serial.println();

  applyDrive();     // explicitly assert the zero-PWM state
}

void loop() {
  readSerial();     // commands are handled the moment they arrive

  unsigned long now = millis();
  if (now - lastReportMs < reportIntervalMs) return;   // wrap-safe
  lastReportMs = now;

  float adcValue = averageAdcSamples();
  float volts    = adcToVoltage(adcValue);
  float ohms     = voltageToResistance(volts);
  float celsius  = resistanceToCelsius(ohms);

  bool ok = adcPlausible(adcValue);

  Serial.print("Temperature (C): ");
  if (!ok || isnan(celsius)) Serial.print("---"); else Serial.print(celsius, 2);
  Serial.print(", Time (s): ");
  Serial.print(now / 1000.0, 2);
  Serial.print(", PWM: ");
  Serial.print(commandedPwm);
  Serial.print(", Heat/Cool: ");
  Serial.println(commandedHeating ? 1 : 0);

  // A wiring fault is reported on its own comment line rather than folded
  // into the measurement line, so the Python parser never has to guess
  // whether a temperature field it cannot read means hot or means broken.
  if (!ok) {
    Serial.print("# temperature channel not usable, ADC = ");
    Serial.print(adcValue, 1);
    Serial.print(": ");
    Serial.println(dividerHint(adcValue));
  }
}
