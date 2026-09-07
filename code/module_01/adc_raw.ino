/*
  Phys 39 Module 1, Part 3A: observe the integer ADC readings.

  Reads A0 and prints the raw 10-bit result in the single labelled form
  that Serial Plotter recognises:

      ADC:512

  Used to find the minimum, maximum and midrange ADC values, and to
  observe that the readings occupy discrete integer levels.

  Wiring: 100 kohm potentiometer, one outer terminal to 5V, the other
  outer terminal to GND, wiper to A0.

  Naidu / Cohen
*/

const int analogPin = A0;

void setup() {
  Serial.begin(9600);
}

void loop() {
  Serial.print("ADC:");
  Serial.println(analogRead(analogPin));
  delay(100);
}
