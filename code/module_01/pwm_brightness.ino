/*
  Phys 39 Module 1, Part 4: LED brightness from averaged analog input.

  Signal chain:
    pot voltage -> averaged ADC number -> voltage -> map to PWM
                -> analogWrite -> oscilloscope -> LED brightness

  Pin 9 is driven by Timer1 with a prescaler of 64 in phase-correct mode,
  counting to 255 and back down, so the PWM frequency is
      16 MHz / 64 / 510 = 490.2 Hz
  which is what the oscilloscope measured (490.42 Hz).

  Wiring:
    pot : outer terminals to 5V and GND, wiper to A0
    LED : pin 9 -> 2.25 kohm resistor -> LED anode, LED cathode -> GND

  Naidu / Cohen
*/

const int   analogPin  = A0;
const int   ledPin     = 9;      // must be a PWM pin; 9 gives ~490 Hz
const float Vref       = 5.0;
const int   avgSamples = 200;    // small enough that the knob stays responsive

void setup() {
  Serial.begin(9600);
  pinMode(ledPin, OUTPUT);
}

void loop() {
  unsigned long total = 0;
  for (int i = 0; i < avgSamples; i++) {
    total += analogRead(analogPin);
  }

  float averageADC = total / float(avgSamples);
  float voltage    = averageADC * Vref / 1023.0;

  // linear map so that duty cycle tracks pot voltage directly
  int brightness = map((int)(averageADC + 0.5), 0, 1023, 0, 255);
  analogWrite(ledPin, brightness);

  Serial.print("Average_Voltage:");
  Serial.print(voltage, 4);
  Serial.print(" Brightness:");
  Serial.print(brightness);
  Serial.print(" Duty_percent:");
  Serial.println(100.0 * brightness / 255.0, 1);

  delay(100);
}
