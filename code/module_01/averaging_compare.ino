/*
  Phys 39 Module 1, Parts 3C and 3D.

  3C: repeatedly produce
        100 voltage values, each from ONE reading of A0
        100 voltage values, each the average of 1000 readings of A0
      then repeat forever.

      Exactly one plotted quantity per line (Voltage_V), with the same
      field name in both blocks so Serial Plotter draws a single curve
      and the drop in scatter is visible. The Ave1 / Ave1000 point label
      carries no colon, so the plotter ignores it while Serial Monitor
      still shows which block each point came from.

  3D: micros() wraps ONLY the 1000-reading acquisition loop. No Serial
      output sits inside the timed region, so the printing cannot
      contaminate the measurement.

  HUNT_MODE prints raw integers instead, which is how the potentiometer
  was set onto an ADC code boundary. Averaging only gains effective bits
  when noise dithers the readings across neighbouring codes, so a
  boundary setting is required for the 1/sqrt(N) comparison.

  Wiring: 100 kohm potentiometer, outer terminals to 5V and GND,
  wiper to A0.

  Naidu / Cohen
*/

const int analogPin = A0;
const float Vref = 5.0;

const int pointsPerBlock     = 100;
const int avgSamplesPerPoint = 1000;

const bool HUNT_MODE = false;   // true = print raw ADC codes to find a boundary

unsigned long lastElapsedUs = 0;
float lastConversionsPerSecond = 0.0;

void setup() {
  Serial.begin(9600);
  delay(3000);
}

float readSingleVoltage() {
  int adcValue = analogRead(analogPin);
  return adcValue * Vref / 1023.0;
}

float readAverageVoltage() {
  unsigned long total = 0;   // unsigned long, not int: 1000 * 1023 overflows an int

  // Part 3D: start timing immediately before the 1000 readings
  unsigned long startTime = micros();

  for (int i = 0; i < avgSamplesPerPoint; i++) {
    total += analogRead(analogPin);
  }

  // Part 3D: stop timing immediately after the 1000 readings
  lastElapsedUs = micros() - startTime;

  lastConversionsPerSecond =
      (1000000.0 * avgSamplesPerPoint) / lastElapsedUs;

  float averageAdc = total / float(avgSamplesPerPoint);
  return averageAdc * Vref / 1023.0;
}

void printPoint(int pointIndex, int mode, float voltageValue) {
  Serial.print("Ave");
  Serial.print(mode);
  Serial.print("_Point_");
  Serial.print(pointIndex + 1);
  Serial.print(" Voltage_V:");     // SPACE before Voltage_V, not an underscore
  Serial.println(voltageValue, 6);
}

void loop() {
  if (HUNT_MODE) {
    Serial.print("ADC:");
    Serial.println(analogRead(analogPin));
    delay(100);
    return;
  }

  // Part 3C block 1: 100 individual readings
  for (int i = 0; i < pointsPerBlock; i++) {
    printPoint(i, 1, readSingleVoltage());
    delay(20);
  }

  // Part 3C block 2: 100 averages, each of 1000 readings
  for (int i = 0; i < pointsPerBlock; i++) {
    printPoint(i, 1000, readAverageVoltage());
  }

  // Part 3D result for the most recent 1000-reading average.
  // Every token contains letters, so Serial Plotter parses none of them
  // as data and the Voltage_V curve is unaffected.
  Serial.print("Timing elapsed_us=");
  Serial.print(lastElapsedUs);
  Serial.print(" conversions_per_second=");
  Serial.println(lastConversionsPerSecond, 1);
}
