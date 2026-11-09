/*
  Phys 39 Module 8, Part I: Angstrom method. SAMMY copy.

  Based on Kapil Naidu's arduino/module_08/angstrom_tec (commit ab5cb3f, 4 Nov),
  which stays unchanged. OL, P, PI, the frequency schedule, the record format
  and the safety limits behave exactly as in that sketch. ADDED here, for what
  the course page asks and that sketch does not do:

    1. RAW mode (S18.3 and S18.4): open-loop sinusoidal PWM, no temperature
       setpoint and no feedback,
           u(t) = U0 + U sin(phase)        PWM counts, + heats, - cools
       U0 = 0 is the zero-centered trial; U0 >= U keeps u >= 0 (positive
       only). SET MODE RAW, SET U <0..255>, SET U0 <-255..255>. The cooling
       multiplier is not applied. Ta_C, Tb_C, setpoint_C, feedforward_pwm and
       controller_pwm are nan in RAW; the applied command is signed_pwm.
    2. step marks the active run segment of a live run too: 1 at START, +1
       each time a setting that is in use actually changes during the run
       (mode, period, Ta, Tb, Kp, Ki, r, Tamb, U, U0). Idle is 0.

  Pair with python/sammy_module8_angstrom_gui.py.

  The Arduino computes the setpoint and the TEC command itself, in one of
  four control modes, and prints everything on one serial record that the
  Python GUI displays and saves.

      T_set(t) = Ta + Tb sin(phase),   phase advances by 2 pi dt / period

    OL  open loop, no feedback:
          u_ff = f^-1(T_set - T_amb), from the Module 4 steady-state curve
          (data/module_04/steady_state.csv), interpolated piecewise linearly.
          The curve has separate heating and cooling branches, so no extra
          multiplier is applied in this mode.
    P   u = Kp e,                     e = T_set - T_TEC
    PI  u = Kp e + Ki q,              q advances by e dt (conditional
                                      integration, as in Module 6)
        In P and PI the cooling side is boosted before the clamp:
          u_cmd = u if u >= 0, r u if u < 0,   r = chi_h / chi_c
    RAW u = U0 + U sin(phase), no setpoint, no feedback, no multiplier
    signed_pwm = command clamped to [-255, 255]; + heats, - cools

  Thermistor chain and H-bridge mapping are the Module 7 sketch
  (arduino/module_08/rod_tec_multichannel): TEC thermistor on A0 (1000
  readings per value), rod T1 to T5 on A1 to A5 (500 readings each, first 4
  after a channel switch thrown away), beta equation B = 4540 K,
  R25 = 100 kOhm. Raw values; calibration offsets are applied in analysis.

  ONE RECORD PER REPORT (every 500 ms), after a header line:

    time_ms,run_state,control_mode,step,Ta_C,Tb_C,period_s,setpoint_C,feedforward_pwm,TEC_C,T1_C,T2_C,T3_C,T4_C,T5_C,controller_pwm,heating_to_cooling_ratio,signed_pwm

    run_state        0 idle (output off), 1 running (live START),
                     2 running a frequency schedule, 9 safety latched
    control_mode     OL, P, PI or RAW (the selected mode, also while idle)
    step             active run segment: schedule step 1..n while a schedule
                     runs; 1, 2, ... for a live run (see 2. above); 0 idle
    Ta_C, Tb_C       nan (does not apply) in RAW
    setpoint_C       nan while idle and in RAW
    feedforward_pwm  u_ff in OL mode; nan (does not apply) in P, PI and RAW
    controller_pwm   raw P or PI command before the cooling multiplier and
                     the clamp; nan (does not apply) in OL and RAW
    signed_pwm       applied PWM; 0 while idle or latched
    nan              also marks a thermistor that could not be read

  Every other line starts with "# " (boot banner, settings, events, safety).
  Each boot prints "# BOOT n" (counter kept in EEPROM, written once per boot).

  COMMANDS (one per line, 9600 baud)
    SET TA 40   SET TB 16   SET PERIOD 100      setpoint, C and s
    SET KP 12   SET KI 0.2  SET R 2.771         gains and cooling multiplier
    SET TAMB 21.5                               room temperature for OL, C
    SET U 50    SET U0 0                        RAW amplitude and offset, counts
    SET MODE OL | P | PI | RAW
    START   STOP   GET   CLEAR SAFETY   TEST LIMIT <C>

  FREQUENCY SCHEDULE (Module 8 Stage 3). The GUI sends the steps, the
  Arduino runs them on its own clock while the laptop keeps recording:
    SCHED CLEAR
    SCHED ADD <duration_s> <Ta> <Tb> <period_s>     up to 8 steps
    SCHED LIST
    SCHED START      step 1 begins with phase 0; each later step keeps the
                     phase running, so a period change does not make the
                     setpoint jump. Every change prints "# EVENT ... STEP k"
                     and the record's step field shows the active step.
                     After the last step the output goes to 0 ("SCHEDULE
                     DONE"). STOP ends a schedule early.
  Periods are refused below 100 s (course minimum).
  A change during a run takes effect at the next report and is printed as
  "# EVENT". The phase carries on through a period change, so the setpoint
  does not jump. Changing the mode resets the integral.

  SAFETY
    Latch at 56 C on T1 (course limit for the measured rod base), at 65 C on
    the TEC thermistor (below the 70 C switch and the TEC's 80 C maximum),
    or after 5 unusable TEC readings in a row. Setpoints must stay within
    10 to 56 C (Ta + Tb <= 56, Ta - Tb >= 10). Output is 0 until START.
    The same latches apply in RAW, which has no feedback of its own.
*/

#include <math.h>
#include <EEPROM.h>

// ---- bench calibration, Module 3 (16 Sep): PWM on pin 10 heats -------
const bool PIN9_IS_HEAT = false;
const int  rpwmPin = 9;
const int  lpwmPin = 10;
const int  maxDuty = 255;

// ---- thermistors -----------------------------------------------------
const float Rnominal = 100000.0;
const float Beta     = 4540.0;
const float Tnominal = 25.0;
const float KELVIN   = 273.15;
const float Vref     = 5.0;

const int   tecPin     = A0;
const float tecRfixed  = 100000.0;
const int   tecSamples = 1000;

const int     NUM_ROD = 5;
const uint8_t rodPins[NUM_ROD]   = {A1, A2, A3, A4, A5};
const float   rodRfixed[NUM_ROD] = {100000.0, 100000.0, 100000.0,
                                    100000.0, 100000.0};
const int     rodSamples  = 500;
const int     ADC_DISCARD = 4;

// ---- Module 4 steady-state curve, data/module_04/steady_state.csv ----
// signed PWM (+ heat, - cool) and steady T - T0 with T0 = 21.54 C.
const int   FF_N = 9;
const float ffU[FF_N]  = {-65, -49, -32, -16, 0, 12, 25, 38, 50};
const float ffDT[FF_N] = {-11.79, -8.55, -5.71, -2.64, 0.0,
                           6.03, 12.53, 19.07, 25.06};

// ---- defaults: course first run, Module 6 gains, Module 4 ratio ------
// r = chi_h / chi_c = 0.50127 / 0.18091 = 2.771 (Module 4)
float Ta = 40.0, Tb = 16.0, periodS = 100.0;
float Kp = 12.0, Ki = 0.2, ratioR = 2.771;
float Tamb = 21.54;            // replace with today's measured room T
float rawU = 50.0, rawU0 = 0.0;  // RAW mode amplitude and offset, PWM counts
enum Mode { MODE_OL = 0, MODE_P = 1, MODE_PI = 2, MODE_RAW = 3 };
int   mode = MODE_PI;

// ---- limits ----------------------------------------------------------
const float T1_LIMIT_C  = 56.0;
const float TEC_LIMIT_C = 65.0;
const float SET_MAX_C   = 56.0;
const float SET_MIN_C   = 10.0;
float       t1Limit     = T1_LIMIT_C;
float       tecLimit    = TEC_LIMIT_C;

// ---- state -----------------------------------------------------------
int   runState = 0;          // 0 idle, 1 live run, 2 schedule, 9 latched
int   stepIdx  = 0;

// ---- frequency schedule (RAM; the GUI sends it before SCHED START) ----
const int MAX_STEPS = 8;
struct Step { float dur, ta, tb, period; };
Step sched[MAX_STEPS];
int  nSteps = 0;
unsigned long stepStartMs = 0;

bool running() { return runState == 1 || runState == 2; }
float phase    = 0.0;
float q        = 0.0;
float uCtrl    = NAN;        // raw P or PI command
float uFF      = NAN;        // open-loop command
int   signedPwm = 0;
float setpointC = NAN;

float tecC = NAN;  bool tecOk = false;
float rodC[NUM_ROD];
bool  rodOk[NUM_ROD];

bool latched  = false;
int  badTecRun = 0;

const unsigned long reportMs = 500;
unsigned long lastReport = 0;
unsigned long lastCtrl   = 0;
unsigned long bootId     = 0;

const int bufSize = 40;
char buf[bufSize];
int  bufLen = 0;

// =====================================================================
// measurement
// =====================================================================

float averageAdc(uint8_t pin, int n) {
  for (int i = 0; i < ADC_DISCARD; i++) analogRead(pin);
  unsigned long total = 0;
  for (int i = 0; i < n; i++) total += analogRead(pin);
  return (float)total / (float)n;
}

bool adcPlausible(float adc) { return adc > 20.0 && adc < 1000.0; }

float adcToCelsius(float adc, float rUpper) {
  float v = adc * Vref / 1023.0;
  if (v <= 0.0 || v >= Vref) return NAN;
  float ohms = rUpper * v / (Vref - v);
  float invT = 1.0 / (Tnominal + KELVIN) + log(ohms / Rnominal) / Beta;
  return 1.0 / invT - KELVIN;
}

void readTec() {
  float adc = averageAdc(tecPin, tecSamples);
  tecOk = adcPlausible(adc);
  tecC  = tecOk ? adcToCelsius(adc, tecRfixed) : NAN;
  if (isnan(tecC)) tecOk = false;
}

void readRod() {
  for (int i = 0; i < NUM_ROD; i++) {
    float adc = averageAdc(rodPins[i], rodSamples);
    rodOk[i] = adcPlausible(adc);
    rodC[i]  = rodOk[i] ? adcToCelsius(adc, rodRfixed[i]) : NAN;
    if (isnan(rodC[i])) rodOk[i] = false;
  }
}

// =====================================================================
// output
// =====================================================================

// One input carries PWM, the other is driven LOW first. Never both.
void applyDrive(int sp) {
  if (latched || !running()) sp = 0;
  sp = constrain(sp, -maxDuty, maxDuty);
  signedPwm = sp;
  if (sp == 0) {
    digitalWrite(rpwmPin, LOW);
    digitalWrite(lpwmPin, LOW);
    return;
  }
  bool heating = sp > 0;
  if (heating == PIN9_IS_HEAT) {
    digitalWrite(lpwmPin, LOW);
    analogWrite(rpwmPin, abs(sp));
  } else {
    digitalWrite(rpwmPin, LOW);
    analogWrite(lpwmPin, abs(sp));
  }
}

void trip(const __FlashStringHelper *why) {
  if (latched) return;
  latched  = true;
  runState = 9;
  q = 0.0;
  applyDrive(0);
  Serial.print(F("# SAFETY SHUTDOWN at t_ms="));
  Serial.print(millis());
  Serial.print(F(": "));
  Serial.println(why);
  Serial.println(F("# Outputs LOW. Send CLEAR SAFETY, then START."));
}

void checkSafety() {
  if (tecOk) {
    badTecRun = 0;
    if (tecC > tecLimit) trip(F("TEC thermistor above its limit"));
  } else if (++badTecRun >= 5) {
    trip(F("TEC thermistor unusable 5 times in a row"));
  }
  if (rodOk[0] && rodC[0] > t1Limit) trip(F("T1 (rod base) above its limit"));
}

// =====================================================================
// control, once per report
// =====================================================================

float compensate(float u) { return (u >= 0.0) ? u : ratioR * u; }

// inverse of the steady-state curve: PWM that holds T - T_amb = dT
float feedforward(float dT) {
  int i = 1;
  while (i < FF_N - 1 && dT > ffDT[i]) i++;          // segment [i-1, i]
  float slope = (ffU[i] - ffU[i - 1]) / (ffDT[i] - ffDT[i - 1]);
  return ffU[i - 1] + slope * (dT - ffDT[i - 1]);   // extends the end segments
}

void printStep(int k) {
  Serial.print(F(" dur_s="));    Serial.print(sched[k].dur, 0);
  Serial.print(F(" Ta="));       Serial.print(sched[k].ta, 2);
  Serial.print(F(" Tb="));       Serial.print(sched[k].tb, 2);
  Serial.print(F(" period_s=")); Serial.println(sched[k].period, 1);
}

void stepEvent(const __FlashStringHelper *what, int k) {
  Serial.print(F("# EVENT t_ms="));
  Serial.print(millis());
  Serial.print(' ');
  Serial.print(what);
  Serial.print(F(" STEP "));
  Serial.print(k + 1);
  printStep(k);
}

void loadStep(int k, unsigned long now) {
  Ta = sched[k].ta;
  Tb = sched[k].tb;
  periodS = sched[k].period;     // phase carries on: no jump in the setpoint
  stepIdx = k + 1;
  stepStartMs = now;
}

// Move to the next step when the current one has run its duration.
void advanceSchedule(unsigned long now) {
  if (now - stepStartMs < (unsigned long)(sched[stepIdx - 1].dur * 1000.0)) return;
  if (stepIdx < nSteps) {
    loadStep(stepIdx, now);
    stepEvent(F("SCHEDULE"), stepIdx - 1);
  } else {
    runState = 0;
    stepIdx = 0;
    q = 0.0;
    applyDrive(0);
    event("SCHEDULE DONE, output 0", NULL);
  }
}

void controlStep(unsigned long now) {
  float dt = (now - lastCtrl) / 1000.0;
  lastCtrl = now;
  uCtrl = NAN;
  uFF   = NAN;
  if (runState == 2) advanceSchedule(now);
  if (!running()) {
    if (runState == 0) setpointC = NAN;
    applyDrive(0);
    return;
  }

  phase += 2.0 * PI * dt / periodS;
  if (phase >= 2.0 * PI) phase -= 2.0 * PI;

  if (mode == MODE_RAW) {   // no setpoint, no feedback, no cooling multiplier
    setpointC = NAN;
    float u = rawU0 + rawU * sin(phase);
    applyDrive((int)lround(constrain(u, -maxDuty, maxDuty)));
    return;
  }
  setpointC = Ta + Tb * sin(phase);

  if (mode == MODE_OL) {
    uFF = feedforward(setpointC - Tamb);
    applyDrive((int)lround(constrain(uFF, -maxDuty, maxDuty)));
    return;
  }

  if (!tecOk) {             // no feedback without a reading
    applyDrive(0);
    return;
  }
  float e = setpointC - tecC;
  if (mode == MODE_P) {
    q = 0.0;
    uCtrl = Kp * e;
  } else {
    float qTrial = q + e * dt;
    float uTrial = compensate(Kp * e + Ki * qTrial);
    bool pushesOut = (uTrial > maxDuty && e > 0) || (uTrial < -maxDuty && e < 0);
    if (!pushesOut) q = qTrial;
    uCtrl = Kp * e + Ki * q;
  }
  applyDrive((int)lround(constrain(compensate(uCtrl), -maxDuty, maxDuty)));
}

// =====================================================================
// reporting
// =====================================================================

void printNum(float v, int digits) {
  if (isnan(v)) Serial.print(F("nan"));
  else Serial.print(v, digits);
}

const char *modeName(int m) {
  return m == MODE_OL ? "OL" : (m == MODE_P ? "P" : (m == MODE_RAW ? "RAW" : "PI"));
}

void printHeader() {
  Serial.println(F("time_ms,run_state,control_mode,step,Ta_C,Tb_C,period_s,setpoint_C,"
                   "feedforward_pwm,TEC_C,T1_C,T2_C,T3_C,T4_C,T5_C,controller_pwm,"
                   "heating_to_cooling_ratio,signed_pwm"));
}

void printSettings() {
  Serial.print(F("# SETTINGS mode="));  Serial.print(modeName(mode));
  Serial.print(F(" Ta="));              Serial.print(Ta, 2);
  Serial.print(F(" Tb="));              Serial.print(Tb, 2);
  Serial.print(F(" period_s="));        Serial.print(periodS, 1);
  Serial.print(F(" Kp="));              Serial.print(Kp, 3);
  Serial.print(F(" Ki="));              Serial.print(Ki, 4);
  Serial.print(F(" r="));               Serial.print(ratioR, 3);
  Serial.print(F(" Tamb="));            Serial.print(Tamb, 2);
  Serial.print(F(" U="));               Serial.print(rawU, 1);
  Serial.print(F(" U0="));              Serial.print(rawU0, 1);
  Serial.print(F(" T1_limit="));        Serial.print(t1Limit, 1);
  Serial.print(F(" TEC_limit="));       Serial.print(tecLimit, 1);
  Serial.print(F(" run_state="));       Serial.print(runState);
  Serial.print(F(" sched_steps="));     Serial.println(nSteps);
}

void report(unsigned long now) {
  Serial.print(now);                 Serial.print(',');
  Serial.print(runState);            Serial.print(',');
  Serial.print(modeName(mode));      Serial.print(',');
  Serial.print(stepIdx);             Serial.print(',');
  printNum(mode == MODE_RAW ? NAN : Ta, 2);  Serial.print(',');
  printNum(mode == MODE_RAW ? NAN : Tb, 2);  Serial.print(',');
  Serial.print(periodS, 1);          Serial.print(',');
  printNum(setpointC, 3);            Serial.print(',');
  printNum(uFF, 2);                  Serial.print(',');
  printNum(tecOk ? tecC : NAN, 2);   Serial.print(',');
  for (int i = 0; i < NUM_ROD; i++) {
    printNum(rodOk[i] ? rodC[i] : NAN, 2);
    Serial.print(',');
  }
  printNum(uCtrl, 2);                Serial.print(',');
  Serial.print(ratioR, 3);           Serial.print(',');
  Serial.println(signedPwm);
}

// =====================================================================
// commands
// =====================================================================

bool parseFloat(const char *s, float &out) {
  if (!s || !*s) return false;
  char *end;
  double v = strtod(s, &end);
  if (*end != '\0') return false;
  out = (float)v;
  return true;
}

void event(const char *a, const char *b) {
  Serial.print(F("# EVENT t_ms="));
  Serial.print(millis());
  Serial.print(' ');
  Serial.print(a);
  if (b) { Serial.print(' '); Serial.print(b); }
  Serial.println();
}

void refuse(const __FlashStringHelper *why) {
  Serial.print(F("# REFUSED: "));
  Serial.println(why);
}

// A setting that is in use changed during a live run: next run segment.
void newSegment() {
  if (runState == 1) stepIdx++;
}

void handleSet(char *name, char *val) {
  if (!strcmp(name, "MODE")) {
    int m;
    if      (!strcmp(val, "OL"))  m = MODE_OL;
    else if (!strcmp(val, "P"))   m = MODE_P;
    else if (!strcmp(val, "PI"))  m = MODE_PI;
    else if (!strcmp(val, "RAW")) m = MODE_RAW;
    else { refuse(F("mode must be OL, P, PI or RAW")); return; }
    if (m != mode) newSegment();
    mode = m;
    q = 0.0;
    event("SET MODE", val);
    printSettings();
    return;
  }
  float v;
  if (!parseFloat(val, v)) { refuse(F("not a number")); return; }
  float newTa = Ta, newTb = Tb;
  bool changed = false;
  if      (!strcmp(name, "TA")) { changed = (v != Ta); newTa = v; }
  else if (!strcmp(name, "TB")) { changed = (v != Tb); newTb = v; }
  else if (!strcmp(name, "PERIOD")) {
    if (v < 100.0 || v > 3600.0) { refuse(F("period must be 100 to 3600 s")); return; }
    changed = (v != periodS);
    periodS = v;
  } else if (!strcmp(name, "KP")) {
    if (v < 0.0 || v > 100.0) { refuse(F("Kp must be 0 to 100")); return; }
    changed = (v != Kp);
    Kp = v;
  } else if (!strcmp(name, "KI")) {
    if (v < 0.0 || v > 5.0) { refuse(F("Ki must be 0 to 5")); return; }
    changed = (v != Ki);
    Ki = v;
  } else if (!strcmp(name, "R")) {
    if (v < 0.5 || v > 5.0) { refuse(F("r must be 0.5 to 5")); return; }
    changed = (v != ratioR);
    ratioR = v;
  } else if (!strcmp(name, "TAMB")) {
    if (v < 10.0 || v > 35.0) { refuse(F("room temperature must be 10 to 35 C")); return; }
    changed = (v != Tamb);
    Tamb = v;
  } else if (!strcmp(name, "U")) {
    if (v < 0.0 || v > 255.0) { refuse(F("U must be 0 to 255 counts")); return; }
    changed = (v != rawU);
    rawU = v;
  } else if (!strcmp(name, "U0")) {
    if (v < -255.0 || v > 255.0) { refuse(F("U0 must be -255 to 255 counts")); return; }
    changed = (v != rawU0);
    rawU0 = v;
  } else { refuse(F("unknown setting")); return; }

  if (newTb < 0.0 || newTa + newTb > SET_MAX_C || newTa - newTb < SET_MIN_C) {
    refuse(F("setpoint must stay within 10 to 56 C"));
    return;
  }
  Ta = newTa;
  Tb = newTb;
  if (changed) newSegment();
  char msg[16];
  snprintf(msg, sizeof(msg), "SET %s", name);
  event(msg, val);
  printSettings();
}

void handleSched(char *b, char *c, char *d, char *e, char *f) {
  if (!strcmp(b, "CLEAR")) {
    if (runState == 2) { refuse(F("schedule running, STOP first")); return; }
    nSteps = 0;
    event("SCHED CLEAR", NULL);
    return;
  }
  if (!strcmp(b, "ADD")) {
    float dur, ta, tb, per;
    if (!parseFloat(c, dur) || !parseFloat(d, ta) || !parseFloat(e, tb) || !parseFloat(f, per)) {
      refuse(F("SCHED ADD <duration_s> <Ta> <Tb> <period_s>"));
      return;
    }
    if (runState == 2)               { refuse(F("schedule running, STOP first")); return; }
    if (nSteps >= MAX_STEPS)         { refuse(F("at most 8 steps")); return; }
    if (dur < 10.0 || dur > 36000.0) { refuse(F("duration must be 10 to 36000 s")); return; }
    if (per < 100.0 || per > 3600.0) { refuse(F("period must be 100 to 3600 s")); return; }
    if (tb < 0.0 || ta + tb > SET_MAX_C || ta - tb < SET_MIN_C) {
      refuse(F("setpoint must stay within 10 to 56 C"));
      return;
    }
    sched[nSteps].dur = dur;
    sched[nSteps].ta = ta;
    sched[nSteps].tb = tb;
    sched[nSteps].period = per;
    nSteps++;
    stepEvent(F("SCHED ADD"), nSteps - 1);
    return;
  }
  if (!strcmp(b, "LIST")) {
    Serial.print(F("# SCHEDULE "));
    Serial.print(nSteps);
    Serial.println(F(" steps"));
    for (int k = 0; k < nSteps; k++) {
      Serial.print(F("#   step "));
      Serial.print(k + 1);
      printStep(k);
    }
    return;
  }
  if (!strcmp(b, "START")) {
    if (nSteps == 0) { refuse(F("no schedule loaded")); return; }
    if (latched)     { refuse(F("safety latched, send CLEAR SAFETY")); return; }
    if (!tecOk)      { refuse(F("TEC thermistor not readable")); return; }
    unsigned long now = millis();
    phase = 0.0;
    q = 0.0;
    lastCtrl = now;
    loadStep(0, now);
    runState = 2;
    event("SCHEDULE START", modeName(mode));
    stepEvent(F("SCHEDULE"), 0);
    return;
  }
  refuse(F("SCHED CLEAR | ADD | LIST | START"));
}

void handleLine() {
  while (bufLen > 0 && (buf[bufLen - 1] == '\r' || buf[bufLen - 1] == ' '))
    bufLen--;
  buf[bufLen] = '\0';
  bufLen = 0;
  for (char *p = buf; *p; p++) *p = toupper(*p);

  char *a = strtok(buf, " \t");
  char *b = strtok(NULL, " \t");
  char *c = strtok(NULL, " \t");
  char *d = strtok(NULL, " \t");
  char *e = strtok(NULL, " \t");
  char *f = strtok(NULL, " \t");
  if (!a) return;

  if (!strcmp(a, "SCHED") && b) { handleSched(b, c, d, e, f); return; }

  if (!strcmp(a, "SET") && b && c) { handleSet(b, c); return; }
  if (!strcmp(a, "GET"))            { printSettings(); return; }
  if (!strcmp(a, "START")) {
    if (latched) { refuse(F("safety latched, send CLEAR SAFETY")); return; }
    if (!tecOk)  { refuse(F("TEC thermistor not readable")); return; }
    phase = 0.0;
    q = 0.0;
    lastCtrl = millis();
    runState = 1;
    stepIdx = 1;
    event("START", modeName(mode));
    printSettings();
    return;
  }
  if (!strcmp(a, "STOP")) {
    if (running()) runState = 0;
    stepIdx = 0;
    q = 0.0;
    applyDrive(0);
    event("STOP", NULL);
    return;
  }
  if (!strcmp(a, "CLEAR") && b && !strcmp(b, "SAFETY")) {
    latched = false;
    badTecRun = 0;
    t1Limit = T1_LIMIT_C;
    tecLimit = TEC_LIMIT_C;
    runState = 0;
    stepIdx = 0;
    applyDrive(0);
    event("CLEAR SAFETY", NULL);
    return;
  }
  if (!strcmp(a, "TEST") && b && !strcmp(b, "LIMIT") && c) {
    float v;
    if (!parseFloat(c, v) || v > T1_LIMIT_C) { refuse(F("TEST LIMIT can only lower the limits")); return; }
    t1Limit = v;
    tecLimit = v;
    event("TEST LIMIT", c);
    printSettings();
    return;
  }
  refuse(F("unknown command"));
}

void readSerial() {
  while (Serial.available() > 0) {
    char ch = Serial.read();
    if (ch == '\n') { handleLine(); continue; }
    if (bufLen < bufSize - 1) buf[bufLen++] = ch;
    else {
      bufLen = 0;
      while (Serial.available() > 0 && Serial.read() != '\n') { }
      refuse(F("command too long"));
    }
  }
}

// =====================================================================

void setup() {
  pinMode(rpwmPin, OUTPUT);
  pinMode(lpwmPin, OUTPUT);
  digitalWrite(rpwmPin, LOW);
  digitalWrite(lpwmPin, LOW);

  EEPROM.get(0, bootId);
  if (bootId == 0xFFFFFFFFUL) bootId = 0;
  bootId++;
  EEPROM.put(0, bootId);

  Serial.begin(9600);
  delay(2500);              // the GUI resets the board when it opens the port

  Serial.println();
  Serial.println(F("# Phys 39 Module 8 Angstrom SAMMY copy, arduino/module_08_sammy/angstrom_tec_sammy (based on Naidu / Cohen)"));
  Serial.print(F("# BOOT "));
  Serial.println(bootId);
  Serial.println(F("# TEC on A0 (1000 readings), T1-T5 on A1-A5 (500 readings, 4 discarded), report every 500 ms"));
  Serial.println(F("# modes: OL u_ff from the Module 4 curve; P and PI on the TEC thermistor, cooling x r; RAW u = U0 + U sin(phase), no feedback; clamp +-255"));
  Serial.println(F("# placeholders: nan = does not apply in this mode, or channel unreadable"));
  Serial.println(F("# latch: T1 > 56 C, TEC > 65 C, or 5 bad TEC readings. Output is 0 until START."));
  printSettings();
  printHeader();
  lastCtrl = millis();
}

void loop() {
  readSerial();
  readTec();
  checkSafety();

  unsigned long now = millis();
  if (now - lastReport < reportMs) return;
  lastReport = now;

  readRod();
  checkSafety();
  controlStep(now);
  report(now);
}
