/*
  Phys 39 Module 1, Part 3B: convert the ADC number to a voltage.

  V = Vref * n / 1023, as given in the assignment.

  The Uno's ADC is 10-bit, so it divides the input span into 2^10 = 1024
  levels and the nominal one-count resolution is

      dV_ADC = Vref / 2^10 = 5.00 / 1024 = 4.88 mV

  Naidu / Cohen
*/

const int   analogPin = A0;
const float Vref = 5.0;

void setup() {
  Serial.begin(9600);
}

void loop() {
  int   adcValue = analogRead(analogPin);
  float voltage  = adcValue * Vref / 1023.0;

  Serial.print("ADC:");
  Serial.print(adcValue);
  Serial.print("  Voltage_V:");
  Serial.println(voltage, 4);

  delay(100);
}
