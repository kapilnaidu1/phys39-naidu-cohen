/*
  Phys 39 Module 8, Part I: Angstrom method. Naidu / Cohen

  The Arduino now runs the whole control loop itself:

      T_set(t) = Ta + Tb sin(phase),   phase advances by 2 pi dt / period
      e        = T_set - T_TEC
      u_PI     = Kp e + Ki q,          q advances by e dt (conditional integration)
      u_cmd    = u_PI        if u_PI >= 0   (heating)
               = r * u_PI    if u_PI <  0   (cooling, r = chi_h / chi_c)
      signed_pwm = u_cmd clamped to [-255, 255]

  so the same serial line carries the setpoint, the six temperatures and the
  controller output, and the Fermion logger (listening on TX, pin 1) records
  exactly what the laptop sees. The Python GUI only sends settings and START /
  STOP; it does not compute the control.

  Thermistor chain, H-bridge mapping and the latch are the Module 7 sketch
  (arduino/module_08/rod_tec_multichannel): base on A0 (1000 readings per
  value), rod T1 to T5 on A1 to A5 (500 readings each, first 4 after a
  channel switch thrown away), beta equation B = 4540 K, R25 = 100 kOhm.

  ONE RECORD PER REPORT (every 500 ms), comma separated, after a header line:

    time_ms,run_state,step,Ta_C,Tb_C,period_s,setpoint_C,TEC_C,T1_C,T2_C,T3_C,T4_C,T5_C,uPI_pwm,heating_to_cooling_ratio,signed_pwm

    run_state  0 idle (output off), 1 running, 9 safety latched
    step       schedule step; 0 for a live run started from the GUI
    uPI_pwm    raw PI command before the cooling multiplier and the clamp
    signed_pwm what the H-bridge gets: + heating, - cooling
    nan        a channel that could not be read

  Every other line starts with "# ", including the boot header, so a parser
  can skip it. Each boot prints "# BOOT n" with n kept in EEPROM, so a
  restart is easy to find in a logger file. EEPROM is written once per boot,
  never in the loop.

  COMMANDS (one per line, from the GUI or Serial Monitor at 9600 baud)
    SET TA 40        mean setpoint, C
    SET TB 8         setpoint amplitude, C (0 gives a constant hold at Ta)
    SET PERIOD 100   forcing period, s
    SET KP 12        SET KI 0.2        SET R 2.771
    START            phase = 0, q = 0, control on
    STOP             control off, output 0
    GET              print the settings
    CLEAR SAFETY     release the latch (output stays 0 until START)
    TEST LIMIT 20    lower the limit, for the shutdown test
  A setting changed during a run takes effect at the next report and is
  printed as an "# EVENT" line. The phase carries on through a period
  change, so the setpoint does not jump.

  SAFETY
    Latch at 55 C on the TEC thermistor or on T1 (the course limit for the
    rod base), or after 5 unusable TEC readings in a row. Setpoints are kept
    inside 10 to 50 C: Ta + Tb above 50 or Ta - Tb below 10 is refused.
    The 70 C thermal switch stays the independent hardware protection.
    Output starts at 0 and only START turns control on.
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

const int   tecPin        = A0;
const float tecRfixed     = 100000.0;
const int   tecSamples    = 1000;

const int     NUM_ROD = 5;
const uint8_t rodPins[NUM_ROD]   = {A1, A2, A3, A4, A5};
const float   rodRfixed[NUM_ROD] = {100000.0, 100000.0, 100000.0,
                                    100000.0, 100000.0};
const int     rodSamples  = 500;
const int     ADC_DISCARD = 4;

// ---- defaults: course first run, Module 6 gains, Module 4 ratio ------
// r = chi_h / chi_c = 0.50127 / 0.18091 = 2.771 (Module 4 open-loop steps)
float Ta = 40.0, Tb = 8.0, periodS = 100.0;
float Kp = 12.0, Ki = 0.2, ratioR = 2.771;

// ---- limits ----------------------------------------------------------
const float LIMIT_C      = 55.0;
const float SET_MAX_C    = 50.0;
const float SET_MIN_C    = 10.0;
float       activeLimitC = LIMIT_C;

// ---- state -----------------------------------------------------------
int   runState = 0;          // 0 idle, 1 running, 9 latched
int   stepIdx  = 0;
float phase    = 0.0;        // rad
float q        = 0.0;        // C s
float uPI      = 0.0;
int   signedPwm = 0;
float setpointC = NAN;

float tecC = NAN;  bool tecOk = false;
float rodC[NUM_ROD];
bool  rodOk[NUM_ROD];

bool        latched = false;
const char *latchWhy = "";
int         badTecRun = 0;

const unsigned long reportMs = 500;
unsigned long lastReport = 0;
unsigned long lastCtrl   = 0;
unsigned long bootId     = 0;

// ---- serial input ----------------------------------------------------
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
  if (latched || runState != 1) sp = 0;
  sp = constrain(sp, -maxDuty, maxDuty);
  signedPwm = sp;
  if (sp == 0) {
    digitalWrite(rpwmPin, LOW);
    digitalWrite(lpwmPin, LOW);
    return;
  }
  bool heating = sp > 0;
  int  duty    = abs(sp);
  if (heating == PIN9_IS_HEAT) {
    digitalWrite(lpwmPin, LOW);
    analogWrite(rpwmPin, duty);
  } else {
    digitalWrite(rpwmPin, LOW);
    analogWrite(lpwmPin, duty);
  }
}

void trip(const char *why) {
  if (latched) return;
  latched  = true;
  latchWhy = why;
  runState = 9;
  q = 0.0;
  uPI = 0.0;
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
    if (tecC > activeLimitC) trip("TEC thermistor above the limit");
  } else if (++badTecRun >= 5) {
    trip("TEC thermistor unusable 5 times in a row");
  }
  if (rodOk[0] && rodC[0] > activeLimitC) trip("T1 (rod base) above the limit");
}

// =====================================================================
// control, called once per report
// =====================================================================

float compensate(float u) { return (u >= 0.0) ? u : ratioR * u; }

void controlStep(unsigned long now) {
  float dt = (now - lastCtrl) / 1000.0;
  lastCtrl = now;
  if (runState != 1) {
    setpointC = (runState == 0) ? NAN : setpointC;
    uPI = 0.0;
    applyDrive(0);
    return;
  }

  phase += 2.0 * PI * dt / periodS;
  if (phase >= 2.0 * PI) phase -= 2.0 * PI;
  setpointC = Ta + Tb * sin(phase);

  if (!tecOk) {             // hold the integral, drive nothing
    uPI = 0.0;
    applyDrive(0);
    return;
  }

  float e = setpointC - tecC;
  float qTrial = q + e * dt;
  float uTrial = compensate(Kp * e + Ki * qTrial);
  // conditional integration on the compensated command (Module 6)
  bool pushesOut = (uTrial > maxDuty && e > 0) || (uTrial < -maxDuty && e < 0);
  if (!pushesOut) q = qTrial;
  uPI = Kp * e + Ki * q;
  float uCmd = compensate(uPI);
  applyDrive((int)lround(constrain(uCmd, -maxDuty, maxDuty)));
}

// =====================================================================
// reporting
// =====================================================================

void printNum(float v, int digits) {
  if (isnan(v)) Serial.print(F("nan"));
  else Serial.print(v, digits);
}

void printHeader() {
  Serial.println(F("time_ms,run_state,step,Ta_C,Tb_C,period_s,setpoint_C,TEC_C,"
                   "T1_C,T2_C,T3_C,T4_C,T5_C,uPI_pwm,heating_to_cooling_ratio,signed_pwm"));
}

void printSettings() {
  Serial.print(F("# SETTINGS Ta="));  Serial.print(Ta, 2);
  Serial.print(F(" Tb="));            Serial.print(Tb, 2);
  Serial.print(F(" period_s="));      Serial.print(periodS, 1);
  Serial.print(F(" Kp="));            Serial.print(Kp, 3);
  Serial.print(F(" Ki="));            Serial.print(Ki, 4);
  Serial.print(F(" r="));             Serial.print(ratioR, 3);
  Serial.print(F(" limit_C="));       Serial.print(activeLimitC, 1);
  Serial.print(F(" run_state="));     Serial.println(runState);
}

void report(unsigned long now) {
  Serial.print(now);                 Serial.print(',');
  Serial.print(runState);            Serial.print(',');
  Serial.print(stepIdx);             Serial.print(',');
  Serial.print(Ta, 2);               Serial.print(',');
  Serial.print(Tb, 2);               Serial.print(',');
  Serial.print(periodS, 1);          Serial.print(',');
  printNum(setpointC, 3);            Serial.print(',');
  printNum(tecOk ? tecC : NAN, 2);   Serial.print(',');
  for (int i = 0; i < NUM_ROD; i++) {
    printNum(rodOk[i] ? rodC[i] : NAN, 2);
    Serial.print(',');
  }
  printNum(uPI, 2);                  Serial.print(',');
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

void event(const char *what) {
  Serial.print(F("# EVENT t_ms="));
  Serial.print(millis());
  Serial.print(' ');
  Serial.println(what);
}

void refuse(const __FlashStringHelper *why) {
  Serial.print(F("# REFUSED: "));
  Serial.println(why);
}

void handleSet(char *name, char *val) {
  float v;
  if (!parseFloat(val, v)) { refuse(F("not a number")); return; }
  float newTa = Ta, newTb = Tb;
  if      (!strcmp(name, "TA"))     newTa = v;
  else if (!strcmp(name, "TB"))     newTb = v;
  else if (!strcmp(name, "PERIOD")) {
    if (v < 20.0 || v > 3600.0) { refuse(F("period must be 20 to 3600 s")); return; }
    periodS = v;
  }
  else if (!strcmp(name, "KP")) {
    if (v < 0.0 || v > 100.0) { refuse(F("Kp must be 0 to 100")); return; }
    Kp = v;
  }
  else if (!strcmp(name, "KI")) {
    if (v < 0.0 || v > 5.0) { refuse(F("Ki must be 0 to 5")); return; }
    Ki = v;
  }
  else if (!strcmp(name, "R")) {
    if (v < 0.5 || v > 5.0) { refuse(F("r must be 0.5 to 5")); return; }
    ratioR = v;
  }
  else { refuse(F("unknown setting")); return; }

  if (newTb < 0.0 || newTa + newTb > SET_MAX_C || newTa - newTb < SET_MIN_C) {
    refuse(F("setpoint range must stay inside 10 to 50 C"));
    return;
  }
  Ta = newTa;
  Tb = newTb;
  char msg[32];
  snprintf(msg, sizeof(msg), "SET %s %s", name, val);
  event(msg);
  printSettings();
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
  if (!a) return;

  if (!strcmp(a, "SET") && b && c) { handleSet(b, c); return; }
  if (!strcmp(a, "GET"))            { printSettings(); return; }
  if (!strcmp(a, "START")) {
    if (latched) { refuse(F("safety latched, send CLEAR SAFETY")); return; }
    if (!tecOk)  { refuse(F("TEC thermistor not readable")); return; }
    phase = 0.0;
    q = 0.0;
    lastCtrl = millis();
    runState = 1;
    stepIdx = 0;
    event("START");
    printSettings();
    return;
  }
  if (!strcmp(a, "STOP")) {
    if (runState == 1) runState = 0;
    q = 0.0;
    uPI = 0.0;
    applyDrive(0);
    event("STOP");
    return;
  }
  if (!strcmp(a, "CLEAR") && b && !strcmp(b, "SAFETY")) {
    latched = false;
    latchWhy = "";
    badTecRun = 0;
    activeLimitC = LIMIT_C;
    runState = 0;
    applyDrive(0);
    event("CLEAR SAFETY");
    return;
  }
  if (!strcmp(a, "TEST") && b && !strcmp(b, "LIMIT") && c) {
    float v;
    if (!parseFloat(c, v) || v > LIMIT_C) { refuse(F("TEST LIMIT can only lower the limit")); return; }
    activeLimitC = v;
    event("TEST LIMIT");
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
    else {                                  // too long: drop the line
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

  // boot counter, written once per boot
  EEPROM.get(0, bootId);
  if (bootId == 0xFFFFFFFFUL) bootId = 0;
  bootId++;
  EEPROM.put(0, bootId);

  Serial.begin(9600);
  delay(2500);              // the Fermion logger needs about 2 s to start

  Serial.println();
  Serial.println(F("# Phys 39 Module 8 Angstrom, arduino/module_08/angstrom_tec. Naidu / Cohen"));
  Serial.print(F("# BOOT "));
  Serial.println(bootId);
  Serial.println(F("# TEC on A0 (1000 readings), T1-T5 on A1-A5 (500 readings, 4 discarded), report every 500 ms"));
  Serial.println(F("# setpoint = Ta + Tb sin(phase); PI on the TEC thermistor; cooling command x r; clamp +-255"));
  Serial.print(F("# Safety latch at "));
  Serial.print(LIMIT_C, 1);
  Serial.println(F(" C on TEC or T1. Output is 0 until START."));
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
