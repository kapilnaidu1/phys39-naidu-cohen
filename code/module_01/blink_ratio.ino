/*
  Phys 39 Module 1, Part 1: Blink and digital output.

  Blinks the external LED and the built-in LED together. Change ON_MS and
  OFF_MS, re-upload, and measure the pin with the oscilloscope.

  The total period is held at 1000 ms in all three cases so that only the
  HIGH:LOW ratio changes:

      1:1    500 / 500 ms    expected duty 50.0 %
     10:1    909 /  91 ms    expected duty 90.9 %
      1:10    91 / 909 ms    expected duty  9.1 %

  Wiring: pin 9 -> 3.25 kohm resistor -> LED anode, LED cathode -> GND.
  The same LED and probe position as Part 4, so no rewiring is needed
  between the two.

  Per the instructor, this part was a short familiarisation exercise and
  no oscilloscope data needed to be recorded for it.

  Naidu / Cohen
*/

const int LED_PIN = 9;

const unsigned long ON_MS  = 500;   // then 909, then 91
const unsigned long OFF_MS = 500;   // then  91, then 909

void setup() {
  pinMode(LED_PIN, OUTPUT);
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  digitalWrite(LED_PIN, HIGH);
  digitalWrite(LED_BUILTIN, HIGH);
  delay(ON_MS);

  digitalWrite(LED_PIN, LOW);
  digitalWrite(LED_BUILTIN, LOW);
  delay(OFF_MS);
}
