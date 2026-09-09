/*
  Phys 39 Module 2, Part 3A.
  Trim-pot PWM and heat/cool direction for the BTS7960 H-bridge.

  Naidu / Cohen

  SIGNAL PATH
    trim-pot voltage -> analogRead average -> map to PWM -> analogWrite
                     -> H-bridge input

  PINS
    A1   trim pot wiper   (outer terminals to 5V and GND)
    11   direction input  (5V = heat/clockwise, 0V = cool/counterclockwise)
    9    RPWM  on the H-bridge
    10   LPWM  on the H-bridge

  DIRECTION LOGIC, from the assignment table

    direction input | mode                    | pin 9 | pin 10
    ----------------|-------------------------|-------|-------
    5V (HIGH)       | heat / clockwise        | PWM   | 0V
    0V (LOW)        | cool / counterclockwise | 0V    | PWM

  Exactly one input carries PWM at any moment. The other is held at a hard
  LOW, never HIGH: on this driver, holding the idle input high while pulsing
  the other inverts the duty cycle, so a commanded 0 would mean full drive.
  The idle pin is driven low BEFORE the active pin is energized, so there is
  never an instant with both inputs asserted.

  Pin 11 is configured INPUT_PULLUP so it can never float. Unconnected reads
  HIGH, which is heat. Jumper it to GND for cool.

  SAFETY
    Keep actuator power OFF and the TEC disconnected while verifying these
    signals on the oscilloscope. maxDuty caps the command for the low-power
    motor test; raise it only when the instructor has checked the wiring.
    Every scope ground clip goes to Arduino GND, never to M+ or M-.
*/

const int potPin  = A1;
const int dirPin  = 11;
const int rpwmPin = 9;    // heat / clockwise
const int lpwmPin = 10;   // cool / counterclockwise

const int avgSamples = 200;   // small enough that the knob stays responsive
const int maxDuty    = 80;    // safety cap out of 255; 80 is about 31%

const unsigned long reportIntervalMs = 300;
unsigned long lastReportMs = 0;

// Average the trim pot. unsigned long accumulator: 200 * 1023 still fits in
// a long comfortably and the habit is worth keeping.
float averagePot() {
  unsigned long total = 0;
  for (int i = 0; i < avgSamples; i++) total += analogRead(potPin);
  return (float)total / (float)avgSamples;
}

// Drive exactly one H-bridge input. Idle pin is forced low first.
void setDrive(bool heat, int duty) {
  duty = constrain(duty, 0, maxDuty);

  if (duty == 0) {                 // commanded off: both inputs low
    digitalWrite(rpwmPin, LOW);
    digitalWrite(lpwmPin, LOW);
    return;
  }
  if (heat) {
    digitalWrite(lpwmPin, LOW);    // idle side off first
    analogWrite(rpwmPin, duty);
  } else {
    digitalWrite(rpwmPin, LOW);    // idle side off first
    analogWrite(lpwmPin, duty);
  }
}

void setup() {
  // Outputs low before anything else, so the bridge is never commanded
  // during boot.
  pinMode(rpwmPin, OUTPUT);
  pinMode(lpwmPin, OUTPUT);
  digitalWrite(rpwmPin, LOW);
  digitalWrite(lpwmPin, LOW);

  pinMode(dirPin, INPUT_PULLUP);

  Serial.begin(9600);
  delay(200);
  Serial.println();
  Serial.println("Phys 39 Module 2 Part 3A: trim pot -> PWM -> H-bridge, Naidu / Cohen");
  Serial.print("max duty = ");
  Serial.print(maxDuty);
  Serial.println(" of 255");
  Serial.println();
}

void loop() {
  unsigned long now = millis();
  if (now - lastReportMs < reportIntervalMs) return;
  lastReportMs = now;

  float potAdc = averagePot();

  // 10-bit input (0..1023) to 8-bit PWM (0..255).
  int duty = map((long)potAdc, 0, 1023, 0, 255);
  duty = constrain(duty, 0, maxDuty);

  bool heat = (digitalRead(dirPin) == HIGH);
  setDrive(heat, duty);

  Serial.print("pot ADC = ");
  Serial.print(potAdc, 1);
  Serial.print("    direction = ");
  Serial.print(heat ? "HEAT / clockwise " : "COOL / counter-cw");
  Serial.print("    duty = ");
  Serial.print(duty);
  Serial.print(" of 255 (");
  Serial.print(100.0 * duty / 255.0, 1);
  Serial.print("%)    pin 9 = ");
  Serial.print(heat ? "PWM" : "0V ");
  Serial.print("    pin 10 = ");
  Serial.println(heat ? "0V " : "PWM");
}
