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

// Safety cap on the command, out of 255. This was 80 (about 31%) while the
// H-bridge inputs were being checked on the scope with no load attached.
// Raised to 255 for Part 3C, the DC motor run, with the instructor present
// and the TEC module and thermal switch unplugged from the load terminals.
// This is the value that produced data/module_02/part3_hbridge_motor.txt.
const int maxDuty    = 255;

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

  // 10-bit input (0..1023) to 8-bit PWM. Map onto 0..maxDuty rather than
  // 0..255 then clipping, so the whole knob travel stays useful while the
  // cap is in place. With maxDuty = 255 this is the full range.
  //
  // Note the double quantization: potAdc is a float average, but map()
  // takes (long)potAdc, so the average is truncated to a whole ADC count
  // before the scaling. That is why the printed duty can flip between two
  // adjacent counts while the printed ADC average looks steady. See
  // section 4 of data/module_02/part3_hbridge_motor.txt.
  int duty = map((long)potAdc, 0, 1023, 0, maxDuty);
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
  // Known cosmetic limitation, left as it ran so the archived capture and
  // this sketch agree: these two fields report which pin WOULD carry PWM
  // for the current direction. At duty 0 both pins are in fact held LOW by
  // setDrive(), so the line still prints "pin 9 = PWM" while pin 9 is low.
  Serial.print("%)    pin 9 = ");
  Serial.print(heat ? "PWM" : "0V ");
  Serial.print("    pin 10 = ");
  Serial.println(heat ? "0V " : "PWM");
}
