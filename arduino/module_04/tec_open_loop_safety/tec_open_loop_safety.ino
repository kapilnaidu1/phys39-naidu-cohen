/*
  Phys 39 Module 4, Part 1. Open-loop TEC calibration with software safety.
  Naidu / Cohen

  Descended from arduino/module_03/tec_python_control. The thermistor
  measurement, the command parser and the H-bridge output behaviour are
  unchanged. What is ADDED is a software temperature interlock.

  WHAT CHANGED FROM THE MODULE 3 SKETCH, for the assignment's "identify the
  lines that changed" requirement:

    1. temperatureLimitC = 60.0            the named software limit
    2. safetyLatched, safetyReason         the latch and why it tripped
    3. checkTemperatureLimit()             the new check, called every loop
    4. applyDrive()                        one early return honouring the latch
    5. loop()                              measures and checks EVERY pass,
                                           prints on the old 500 ms cadence
    6. parseCommand()                      TEST LIMIT and CLEAR SAFETY
    7. setup()                             announces the limit at boot

  HOW THE SAFETY LIMIT WORKS

    Every pass through loop(), the averaged thermistor reading is converted
    to a temperature and compared with temperatureLimitC. Above the limit,
    the sketch latches: commandedPwm is forced to 0, BOTH H-bridge inputs are
    driven LOW, and every subsequent report carries a SAFETY SHUTDOWN line.
    Serial reporting continues throughout, so the GUI keeps plotting and the
    operator can see exactly what the temperature did during and after the
    event.

    IT LATCHES RATHER THAN AUTO-RESUMING. If drive resumed the moment the
    plate fell back below the limit, an over-temperature condition would
    become an oscillation: heat to the limit, cut out, cool slightly, heat
    again. The apparatus would sit at its safety limit indefinitely and the
    operator might never notice. A latch requires a human to acknowledge that
    something went wrong before current flows again. Clear it with RESET or
    the CLEAR SAFETY command.

    The hardware thermal switch, which opens near 70 C, is the independent
    final protection and is unaffected by any of this. It interrupts TEC
    current in series, so it works whatever the software does, including if
    the sketch hangs. The software limit exists so that the hardware cutoff
    is not the NORMAL way a run stops.

  THE SECOND TRIP CONDITION, which the assignment does not require

    The sketch also latches if the thermistor reading is unusable for five
    consecutive measurements. An instrument that cannot measure temperature
    has no business driving a heater, and the plausibility window would
    otherwise let a disconnected sensor read a steady, comfortable "---"
    while full duty stayed applied.

    Five consecutive rather than one, because the A0 contact on this bench
    has been intermittent and glitches for a single sample. One bad reading
    is noise. Five in a row, about a quarter of a second, is a fault.

  TESTING THE LIMIT WITHOUT HEATING ANYTHING

    The assignment asks for the limit to be temporarily set below room
    temperature to prove the shutdown works. Rather than editing the
    constant and re-uploading, send

        TEST LIMIT 20

    which takes effect immediately. It can only ever LOWER the limit, never
    raise it above temperatureLimitC, so the test path cannot be used to make
    the instrument less safe than the compiled-in value. CLEAR SAFETY puts
    the limit back to temperatureLimitC and releases the latch.

  MEMORY, AND A BUG THIS SKETCH ALREADY HAD ONCE

    The first version of this file would not boot. It printed a few
    characters of its own banner and reset, over and over:

        #39 Mod
        # Phys 39 Mod

    Cause: the ATmega328P has 2048 bytes of SRAM, and by default every
    string literal in a Serial.print() call is copied into SRAM at startup.
    The safety code added enough new messages to push the total to about
    1491 bytes of literals alone, before any variables, the three 48-byte
    line buffers, or the stack. The stack collided with the globals and the
    board reset partway through printing.

    Worth recognising, because the symptom looks like a bad upload or a
    flaky board rather than a memory problem. A sketch that resets mid-print
    and always at roughly the same point is running out of RAM.

    Fixes applied:

      every Serial.print literal wrapped in F(), which keeps it in flash
        and streams it out rather than copying it to SRAM
      sensorName moved to PROGMEM for the same reason
      parseSafetyCommand() tokenizes in place instead of taking its own
        48-byte copy, since handleLine() already holds one and the two
        would be live at the same time

    Only the short reason strings passed to tripSafety() and failSafe()
    remain in SRAM, about 146 bytes, because they are handled as char* and
    moving them would complicate the code for little gain.

  Descended from the manual trim-pot sketch. PWM and direction arrive as
  commands from the Python GUI.

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

  DIRECTION CALIBRATION, MEASURED 16 SEPTEMBER 2026
    PIN9_IS_HEAT carries the mapping verified on the bench. HEAT commands the
    direction that was OBSERVED to raise the plate temperature. A pin number
    is not evidence.

      PWM on pin 10 raised the plate at +0.209 C/s at duty 40   -> HEAT
      PWM on pin 9  lowered the plate at -0.118 C/s at duty 40  -> COOL

    so PIN9_IS_HEAT = false. The cooling figure was taken at 24.4 C, only
    1.4 C above ambient, where passive decay contributes 0.009 C/s, so the
    plate was falling about 12x faster than it can unaided. The two signs are
    opposite in the two directions, which also rules out the thermistor being
    on the wrong face of the Peltier.

    Evidence: data/module_03/part3_direction_calibration.txt

  SAFETY
    PWM starts at zero on reset and stays there until a valid command
    arrives. There is no knob, so unlike the manual sketches there is nothing
    to arm: a fresh boot cannot be driving the TEC.
    Every scope probe ground clip goes to Arduino GND, never to M+ or M-.
    Do not run the TEC without its heat exchanger running.
*/

#include <math.h>
#include <avr/pgmspace.h>   // PROGMEM and the F() macro for sensorName

// ---- MEASURED ON THE BENCH, 16 SEPTEMBER 2026 ------------------------
// true  = PWM on pin 9 heats the plate, pin 10 cools it
// false = PWM on pin 9 cools the plate, pin 10 heats it
//
// Observed: PWM on pin 10 raised the plate, PWM on pin 9 lowered it.
const bool PIN9_IS_HEAT = false;

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
  const char  sensorName[] PROGMEM = "10 kOhm plate thermistor";
#else
  const float Rnominal = 100000.0;   // ohms at 25 C
  const float Beta     = 4540.0;     // TDK/EPCOS B57861S0104F040V24, B25/100
  const char  sensorName[] PROGMEM = "100 kOhm thermistor, TDK B57861S0104F040V24";
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

// The COMMAND range is 0 to 255, as the assignment specifies, and parsing
// accepts that whole range. maxDuty is a separate OUTPUT ceiling applied in
// applyDrive(), so the instrument can accept a legal command and still
// refuse to deliver more current than the bench has been proven safe at.
//
// RAISED TO FULL SCALE 23 SEPTEMBER 2026, and worth recording why.
//
// It was 64 for first power-on, the same ceiling both manual sketches used.
// That made the instrument safe and it also made it misleading. The GUI was
// commanded to 255 and the bridge received 64, so the plate reached only
// +27 C and -10 C from ambient and the run was read as a hardware fault. The
// supply, the bridge, the module and the heat exchanger were all fine. The
// ceiling was doing exactly what it was written to do, and the temperature
// curve was the honest response to a quarter of the commanded drive.
//
// A safety limit that the operator forgets is present will be mistaken for a
// broken instrument. The boot banner and the CAPPED notice both announced it
// and neither was enough, because nobody reads a banner they have seen
// twenty times.
//
// 255 is now the ceiling, so commanded and delivered duty are the same
// number and there is nothing left to misread. What keeps the plate safe is
// the thermal switch in series with the module, the temperature channel
// itself, and not leaving a full-drive heating run unattended. At full drive
// this plate rises fast, so watch it.
const int maxDuty = 255;

// Commanded state. Both start at the safe value.
int  commandedPwm     = 0;
bool commandedHeating = true;

// ---- SOFTWARE TEMPERATURE LIMIT, MODULE 4 ----------------------------
//
// The compiled-in limit. The hardware thermal switch opens near 70 C and
// remains the independent final protection; this exists so that the hardware
// cutoff is not the normal way a run ends.
//
// 60 C is chosen to sit clearly below the switch and clearly above the
// 10 to 45 C operating band this module works in, so a normal calibration
// run never approaches it.
const float temperatureLimitC = 60.0;

// The limit actually in force. Equal to temperatureLimitC except during a
// deliberate TEST LIMIT, which can only lower it. Nothing can raise it above
// the compiled-in value.
float activeLimitC = temperatureLimitC;

// The latch. Once true, drive stays at zero until a human clears it.
bool        safetyLatched = false;
const char *safetyReason  = "";

// Consecutive unusable thermistor readings. One is noise on this bench,
// several in a row is a disconnected sensor. See the header.
int       badReadingRun      = 0;
const int badReadingsToTrip  = 5;

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
  // MODULE 4: the latch wins over any command. This is the single place
  // where PWM reaches the hardware, so putting the check here means no
  // command path, present or future, can drive the bridge while latched.
  if (safetyLatched) {
    digitalWrite(rpwmPin, LOW);
    digitalWrite(lpwmPin, LOW);
    return;
  }

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

// ---- MODULE 4: the software temperature interlock --------------------
//
// Called on EVERY pass through loop(), not on the reporting interval. A
// safety check gated by a print statement is a safety check that runs at
// whatever rate you happen to be printing.

void tripSafety(const char *why) {
  if (safetyLatched) return;          // already tripped, do not re-announce
  safetyLatched = true;
  safetyReason  = why;
  commandedPwm  = 0;                  // the command itself is zeroed too, so
                                      // the reported PWM matches the hardware
  applyDrive();                       // both inputs LOW, immediately

  Serial.println();
  Serial.print(F("# *** SAFETY SHUTDOWN: "));
  Serial.println(why);
  Serial.println(F("# Both H-bridge outputs driven LOW. PWM commands are refused."));
  Serial.println(F("# Reporting continues. Clear with RESET or: CLEAR SAFETY"));
  Serial.println();
}

void checkTemperatureLimit(float celsius, bool readingUsable) {
  if (readingUsable && !isnan(celsius)) {
    badReadingRun = 0;

    if (celsius > activeLimitC) {
      tripSafety("measured temperature above the software limit");
    }
    return;
  }

  // Unusable reading. Count it, and trip only on a sustained run of them.
  // See the header for why one bad sample is not enough.
  badReadingRun++;
  if (badReadingRun >= badReadingsToTrip) {
    tripSafety("thermistor reading unusable, cannot verify temperature");
  }
}

// Force the safe state and say why.
void failSafe(const char *why) {
  commandedPwm = 0;
  applyDrive();
  Serial.print(F("# PWM set to 0: "));
  Serial.println(why);
}

// ---- command parsing -------------------------------------------------
// Expected exactly: SET PWM <int> DIR <HEAT|COOL>
// Returns true only if the whole line was understood.

// MODULE 4: the two safety commands, handled before the SET PWM grammar
// because they have a different shape. Returns true if the line was one of
// them and has been dealt with.
//
// NOTE ON MEMORY: this deliberately tokenizes `line` in place rather than
// taking its own copy. handleLine() already holds a 48-byte `echo` buffer on
// the stack, and this function is called from inside it, so a local copy here
// would be a third 48-byte buffer live at the same time. On a 2 KB Uno that
// matters. handleLine() restores `line` from `echo` if this returns false.
bool parseSafetyCommand(char *line) {
  char *a = strtok(line, " \t");
  char *b = strtok(NULL, " \t");
  char *c = strtok(NULL, " \t");
  char *d = strtok(NULL, " \t");
  if (!a || !b || d) return false;

  // CLEAR SAFETY: release the latch and restore the compiled-in limit.
  if (strcmp(a, "CLEAR") == 0 && strcmp(b, "SAFETY") == 0 && !c) {
    safetyLatched = false;
    safetyReason  = "";
    badReadingRun = 0;
    activeLimitC  = temperatureLimitC;
    commandedPwm  = 0;              // never resume drive on a clear. The
    applyDrive();                   // operator re-commands deliberately.
    Serial.print(F("# SAFETY CLEARED. Limit restored to "));
    Serial.print(temperatureLimitC, 1);
    Serial.println(F(" C. PWM is 0; re-command drive when ready."));
    return true;
  }

  // TEST LIMIT <value>: lower the limit for the shutdown demonstration.
  // It can only ever move the limit DOWN. A test path that could raise the
  // safety limit would be a way to defeat the interlock, so it is refused.
  if (strcmp(a, "TEST") == 0 && strcmp(b, "LIMIT") == 0 && c) {
    float requested = atof(c);
    if (requested > temperatureLimitC) {
      Serial.print(F("# REFUSED: "));
      Serial.print(requested, 1);
      Serial.print(F(" C is above the compiled limit of "));
      Serial.print(temperatureLimitC, 1);
      Serial.println(F(" C. TEST LIMIT can only lower it."));
      return true;
    }
    activeLimitC = requested;
    Serial.print(F("# TEST LIMIT IN FORCE: "));
    Serial.print(activeLimitC, 1);
    Serial.println(F(" C. This is a test setting, not the real limit."));
    Serial.println(F("# Send CLEAR SAFETY to restore it."));
    return true;
  }

  return false;
}

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

  // MODULE 4: safety commands first, they have their own grammar.
  // parseSafetyCommand() tokenizes in place to save RAM, so if it does not
  // recognise the line we restore it from `echo` before parseCommand() sees
  // it. Without this, strtok's inserted NULs would leave parseCommand
  // looking at only the first word.
  if (parseSafetyCommand(line)) {
    bufLen = 0;
    return;
  }
  strncpy(buf, echo, bufSize - 1);
  buf[bufSize - 1] = '\0';
  line = buf;

  if (parseCommand(line)) {
    // MODULE 4: a drive command while latched is refused, loudly. Silently
    // accepting it would leave the GUI showing a PWM the hardware is not
    // delivering, which is the exact failure this instrument already made
    // once with the output ceiling.
    if (safetyLatched && commandedPwm > 0) {
      commandedPwm = 0;
      applyDrive();
      Serial.print(F("# REFUSED, safety shutdown is latched: "));
      Serial.println(safetyReason);
      Serial.println(F("# Send CLEAR SAFETY first. PWM stays at 0."));
      bufLen = 0;
      return;
    }

    applyDrive();
    Serial.print(F("# OK: PWM "));
    Serial.print(commandedPwm);
    Serial.print(F(" DIR "));
    Serial.print(commandedHeating ? "HEAT" : "COOL");
    Serial.print(F("  (PWM on pin "));
    if (commandedPwm == 0) Serial.print(F("none"));
    else Serial.print((commandedHeating == PIN9_IS_HEAT) ? "9" : "10");
    Serial.print(F(")"));

    // Never cap silently. If the GUI says 200 and the plate behaves like 64,
    // the operator has to be told, or the instrument is lying about what it
    // is doing.
    if (commandedPwm > maxDuty) {
      Serial.print(F("  CAPPED: driving "));
      Serial.print(maxDuty);
      Serial.print(F(", the maxDuty output ceiling"));
    }
    Serial.println();
  } else {
    Serial.print(F("# malformed command: \""));
    Serial.print(echo);
    Serial.println(F("\""));
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
  Serial.println(F("# Phys 39 Module 3 Part 6: TEC serial-command control. Naidu / Cohen"));
  Serial.print(F("# Sensor: "));
  Serial.print((const __FlashStringHelper *)sensorName);
  Serial.print(F(", R25 = "));
  Serial.print(Rnominal / 1000.0, 1);
  Serial.print(F(" kOhm, Beta = "));
  Serial.print(Beta, 0);
  Serial.print(F(" K, upper leg = "));
  Serial.print(Rfixed / 1000.0, 1);
  Serial.println(F(" kOhm"));
  Serial.print(F("# Calibration in use: PWM on pin 9 = "));
  Serial.println(PIN9_IS_HEAT ? "HEAT" : "COOL");
  Serial.println(F("# Commands: SET PWM <0-255> DIR <HEAT|COOL>"));
  Serial.println(F("#           TEST LIMIT <degC>   (lowers the limit, for the shutdown test)"));
  Serial.println(F("#           CLEAR SAFETY        (releases the latch, restores the limit)"));
  Serial.println(F("# PWM starts at 0 and stays there until a valid command arrives."));
  Serial.print(F("# SOFTWARE TEMPERATURE LIMIT: "));
  Serial.print(temperatureLimitC, 1);
  Serial.println(F(" C. Above it, both H-bridge outputs are driven LOW and latched."));
  Serial.println(F("# Hardware thermal switch near 70 C remains the independent final protection."));
  if (maxDuty < 255) {
    Serial.print(F("# OUTPUT CEILING: commands above "));
    Serial.print(maxDuty);
    Serial.print(F(" are accepted but driven at "));
    Serial.print(maxDuty);
    Serial.println(F(". Raise maxDuty for the graded run."));
  }
  Serial.println();

  applyDrive();     // explicitly assert the zero-PWM state
}

void loop() {
  readSerial();     // commands are handled the moment they arrive

  // MODULE 4: measure and check on EVERY pass. The measurement used to sit
  // below the reporting gate, which meant the temperature was only looked at
  // twice a second because that is how often the sketch printed. Reporting
  // cadence and safety cadence are different things and should not share a
  // condition. Averaging 500 samples takes about 50 ms, so the limit is now
  // checked roughly 20 times a second.
  float adcValue = averageAdcSamples();
  float volts    = adcToVoltage(adcValue);
  float ohms     = voltageToResistance(volts);
  float celsius  = resistanceToCelsius(ohms);

  bool ok = adcPlausible(adcValue);

  checkTemperatureLimit(celsius, ok);

  // Everything below here is reporting, on the original 500 ms cadence.
  unsigned long now = millis();
  if (now - lastReportMs < reportIntervalMs) return;   // wrap-safe
  lastReportMs = now;

  Serial.print(F("Temperature (C): "));
  if (!ok || isnan(celsius)) Serial.print(F("---")); else Serial.print(celsius, 2);
  Serial.print(F(", Time (s): "));
  Serial.print(now / 1000.0, 2);
  Serial.print(F(", PWM: "));
  Serial.print(commandedPwm);
  Serial.print(F(", Heat/Cool: "));
  Serial.println(commandedHeating ? 1 : 0);

  // MODULE 4: while latched, say so on every report. An operator who looks
  // at the screen at any moment during a shutdown sees the shutdown, not
  // just a PWM that happens to read zero.
  if (safetyLatched) {
    Serial.print(F("# SAFETY SHUTDOWN ACTIVE: "));
    Serial.print(safetyReason);
    Serial.print(F(". Limit "));
    Serial.print(activeLimitC, 1);
    Serial.println(F(" C. Outputs LOW. Send: CLEAR SAFETY"));
  }

  // A wiring fault is reported on its own comment line rather than folded
  // into the measurement line, so the Python parser never has to guess
  // whether a temperature field it cannot read means hot or means broken.
  if (!ok) {
    Serial.print(F("# temperature channel not usable, ADC = "));
    Serial.print(adcValue, 1);
    Serial.print(F(": "));
    Serial.println(dividerHint(adcValue));
  }
}