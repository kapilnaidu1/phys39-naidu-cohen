/*
  Phys 39 Module 3: input channel bench check. Naidu / Cohen

  Not part of the assignment. A deliberately minimal sketch for testing the
  two analog inputs with everything else removed: no PWM, no arming, no
  direction logic, no averaging, no temperature conversion. When a channel
  misbehaves in the real sketch there are half a dozen candidate causes. Here
  there are two wires and a print statement.

  SAFE BY CONSTRUCTION
    Both H-bridge inputs are held LOW for the life of the sketch, so the TEC
    cannot be driven while you are handling the board. The 12 V supply may
    stay on but does not need to be.

  WHAT TO LOOK FOR

    Trim pot on A1. Turn it end to end. potMin must reach 0 and potMax must
    reach 1023. Anything short of that is a bad contact, not a knob with
    limited travel.

    Thermistor on A0. Leave it alone. At steady room temperature the span
    should stay within a few counts. A span of tens of counts with nobody
    touching it is an intermittent contact.

  WHY MIN AND MAX RATHER THAN THE LIVE VALUE

    A bad contact glitches for a fraction of a second and recovers. Watching
    a number scroll past you will miss it. The extremes are held since reset,
    so a single glitch anywhere in the test is still on screen a minute later.

    Press RESET on the Arduino to clear the extremes and begin a new test.

  Read it in Arduino Serial Monitor at 9600. No Python needed, which also
  avoids the serial-monitor-versus-Python port contention entirely.
*/

const int potPin        = A1;
const int thermistorPin = A0;

const int rpwmPin = 9;
const int lpwmPin = 10;

int potMin = 1023, potMax = 0;
int thMin  = 1023, thMax  = 0;

void setup() {
  // Bridge inputs low before anything else, so nothing can drive the TEC
  // while the board is being poked at.
  pinMode(rpwmPin, OUTPUT);
  pinMode(lpwmPin, OUTPUT);
  digitalWrite(rpwmPin, LOW);
  digitalWrite(lpwmPin, LOW);

  Serial.begin(9600);
  delay(200);
  Serial.println();
  Serial.println("Input channel bench check. Both PWM pins held LOW.");
  Serial.println("Turn the trim pot end to end. Want potMin 0 and potMax 1023.");
  Serial.println("Leave the thermistor alone. Want a small A0 span.");
  Serial.println("Press RESET to clear the extremes.");
  Serial.println();
}

void loop() {
  int pot = analogRead(potPin);
  int th  = analogRead(thermistorPin);

  if (pot < potMin) potMin = pot;
  if (pot > potMax) potMax = pot;
  if (th  < thMin)  thMin  = th;
  if (th  > thMax)  thMax  = th;

  Serial.print("pot A1 = ");
  Serial.print(pot);
  Serial.print("  [min ");
  Serial.print(potMin);
  Serial.print(", max ");
  Serial.print(potMax);
  Serial.print(", span ");
  Serial.print(potMax - potMin);
  Serial.print("]     therm A0 = ");
  Serial.print(th);
  Serial.print("  [min ");
  Serial.print(thMin);
  Serial.print(", max ");
  Serial.print(thMax);
  Serial.print(", span ");
  Serial.print(thMax - thMin);
  Serial.print("]");

  // A verdict, so the numbers do not have to be interpreted at the bench.
  if (potMin <= 5 && potMax >= 1018) {
    Serial.print("   POT OK");
  } else if (potMax - potMin < 50) {
    Serial.print("   POT NOT MOVING");
  } else {
    Serial.print("   POT PARTIAL");
  }

  // 15 counts is about 1.2 C on this divider. Anything larger at rest is a
  // contact, not the room. This will also trip if you touch the sensor,
  // which is why the instruction is to leave it alone.
  if (thMax - thMin > 15) {
    Serial.print("   A0 UNSTABLE");
  }

  Serial.println();
  delay(200);
}
