# C1 checkoff prep, Session S4, Wednesday 9 September

Naidu / Cohen. Everything below is answerable from our own repo and our own measurements.
No AI agents allowed during the checkoff, so the point is to know this, not to read it off a screen.

Commit to cite: `2b97d31edaf758ee763cb0239e5bcbe5b9ed3947` on `main`.
If we commit anything before the demo, cite the new tip instead.

---

## Part 1: the five team demonstration items

### 1. Demonstrate a modified sketch running on the board

Open `code/module_01/averaging_compare.ino` in the Arduino IDE, upload, open Serial Monitor at **9600 baud**.

Output should read:

```
Ave1_Point_1 Voltage_V:4.222874
...
Ave1000_Point_1 Voltage_V:4.222527
...
Timing elapsed_us=112068 conversions_per_second=8923.2
```

To prove the board is running *this* version and not a stale upload, change `pointsPerBlock` from 100 to something obvious like 5, re-upload, and watch the block length change live in the Serial Monitor. Then change it back.

### 2. Show the organized repository and README

`README.md` at the repo root has a layout block and a table naming all five sketches and what each one measured. Point at the table, then open one of the linked sketches to show the link resolves.

Layout to say out loud: `code/module_01/` for sketches, `data/module_01/` for the raw capture, `docs/module_notes/` for the evidence note, `docs/images/` for the ten figures.

### 3. Show a meaningful commit pushed to GitHub

GitHub Desktop, History tab, top entry: **"Set final checkpoint hash and add exported A1 PDF"**. The absence of a "Push origin" badge in the toolbar is the proof it is already on GitHub. Confirm on github.com if asked.

"Meaningful" means the message says what changed and why, not "update". Ours do.

### 4. Locate the current and preceding commits

GitHub Desktop, History. Click `2b97d31` (top), then `8754dbc` directly below it. Select `module_01_evidence.md` in the file list to show the red/green line diff.

### 5. Individual oral questions

One workflow question each from 1 to 3, one measurement question each from 4 to 8. Answers below.

---

## Part 2: workflow questions

### Q1. Where is the sketch stored, what did you change, and how can you tell the board is running that version?

**Stored at** `code/module_01/averaging_compare.ino` in the team repo, opened in the Arduino IDE from that path.

**What we changed.** We started from the single-reading sketch and turned it into a comparison sketch:

- it now alternates a block of 100 single readings with a block of 100 thousand-reading averages, both printed under the same `Voltage_V` field name so the Serial Plotter draws one continuous curve and the drop in scatter is visible at the transition
- the accumulator is `unsigned long`, not `int`, because 1000 × 1023 = 1,023,000 overflows a 16-bit `int` on an Uno
- `micros()` wraps only the 1000-reading acquisition loop, with no `Serial` output inside the timed region, so printing cannot contaminate the timing
- there is a `HUNT_MODE` flag that prints raw integers instead, which is how we parked the potentiometer on an ADC code boundary

**How we know the board runs it.** The output format is specific to this sketch: the `Ave1_` / `Ave1000_` point labels and the `Timing elapsed_us=` line. Nothing else we wrote prints that. The stronger demonstration is to edit a constant, re-upload, and watch the output change.

### Q2. Difference between saving, committing, and pushing?

- **Save** writes the file to disk. Nothing outside the editor knows or cares. Git sees it as a modified working file.
- **Commit** records a snapshot of the staged changes in the local `.git` history, with a message, an author, a timestamp, and a hash. It is a permanent point you can return to, but it exists only on this laptop.
- **Push** uploads those local commits to the GitHub remote, so the server and any collaborator can see them.

Losing the laptop after a commit but before a push loses the work. That is why the assignment requires the commit to be *pushed* before the deadline.

Demonstration: edit README, save, GitHub Desktop shows it under Changes. Commit, and it moves from Changes into History. Push, and the "Push origin" badge clears.

### Q3. Locate the preceding committed version of a file. What protection does history provide?

In GitHub Desktop, History, select the cited commit `2b97d31`, then the one below it `8754dbc`, and click `docs/module_notes/module_01_evidence.md` to see exactly which lines changed.

**The protection:** every committed version is kept and individually addressable by hash, so no earlier state is ever overwritten. If a later edit breaks something we can compare versions to see precisely what changed and when, identify the commit that introduced the problem, and restore or revert to the known-good version. Without it the only record of a file is whatever it happens to contain right now.

---

## Part 3: measurement questions

### Q4. 10-bit ADC, 5.00 V reference. How many codes, min and max, one count?

- **1024 codes**, because 2^10 = 1024
- **Minimum 0, maximum 1023.** The count starts at zero, so the largest is 1024 − 1
- **One count** = V_ref / 2^10 = 5.00 / 1024 = 0.004883 V = **4.88 mV**

We measured exactly this: A0 at ground gave 0, at 5 V gave 1023, midrange 512.

One subtlety worth knowing. Our sketches convert with V = V_ref × n / 1023, which is the form the assignment gives, and which maps code 1023 to exactly 5.000 V. The resolution uses 1024 because that is the number of levels the range is divided into. The two differ by 0.1% and we noted it rather than papering over it.

### Q5. Why does averaging improve precision? Derive the effective bits gained. Assumptions?

For N independent samples of a fluctuating quantity, the standard deviation of the mean falls as 1/√N. Halving the noise buys one extra bit of resolution, so gaining b bits means reducing noise by 2^b:

$$2^{b} = \sqrt{N} \quad\Longrightarrow\quad b = \tfrac{1}{2}\log_2 N$$

For **N = 1000**: b = ½ log₂(1000) = **4.98 bits**, so a 10-bit converter behaves like roughly a 15-bit one. Predicted ratio 1/√1000 = 0.0316.

**What we actually measured**, with the pot on the code 863/864 boundary:

| | s | ratio |
|---|---|---|
| Unaveraged, N = 1 | 2.035 mV | 1.000 |
| Averaged, N = 1000 | 0.0726 mV | **0.0357** |

Measured 0.0357 against a predicted 0.0316, so 13% high. Bits gained = log₂(2.035 / 0.0726) = **4.81** against the ideal 4.98.

**Assumptions required:**

1. **The noise samples must be independent.** Consecutive `analogRead()` calls are only about 112 µs apart, so 1000 of them span 0.112 s and sample only about seven cycles of 60 Hz mains. Any hum is heavily correlated within a single average and averages down more slowly than √N.
2. **The signal must be stationary.** Averaging removes random fluctuation, not drift. Our two block means differed by 0.68 mV, which is 0.14 of an ADC count, and that drift is the dominant reason our ratio came out above prediction.
3. **There must be dither.** This is the one people miss. Averaging only helps if noise makes the readings straddle a code boundary. Earlier in the session the pot sat inside a code window and all 100 unaveraged readings returned the identical value, so s₁ = 0 and the ratio was undefined. We had to move onto a boundary to get a real comparison.

Also worth saying: averaging improves **precision, not accuracy**. If the true reference is 4.93 V rather than 5.00 V, every averaged value is systematically high by 1.4% and no amount of averaging detects it.

### Q6. How fast is analogRead()? How long for 1000? How to measure? Why is averaging a low-pass filter?

**Nominal.** The Arduino reference gives roughly 100 µs per conversion, about 10,000 per second. That comes from the ADC clock: the prescaler divides 16 MHz down to 125 kHz and a conversion takes 13 ADC clock cycles, so 13 / 125 kHz ≈ 104 µs.

**So 1000 readings should take about 0.1 s.**

**Measured.** We wrapped `micros()` around the acquisition loop only:

```cpp
unsigned long startTime = micros();
for (int i = 0; i < 1000; i++) total += analogRead(analogPin);
unsigned long elapsed = micros() - startTime;
```

Eleven consecutive cycles gave 112,042 µs on average, so **112.0 µs per conversion and 8,925 conversions per second**. That is 12% slower than the reference figure, which is the function-call and loop overhead around each conversion. The spread across cycles was 0.1%, so the measurement is highly repeatable.

Keeping all `Serial` output outside the timed region matters: printing at 9600 baud is orders of magnitude slower than the ADC and would have swamped the result.

**Why it is a low-pass filter.** Averaging over a fixed 0.112 s window is a boxcar average in time. Fluctuations faster than roughly 1/0.112 ≈ 9 Hz get averaged toward zero, which is exactly what suppresses the noise. But the same mechanism flattens a genuine fast transient and delays it.

**The cost.** We can report fewer than nine averaged values per second. Anything real that happens inside a window is folded into the mean rather than resolved. Precision in voltage is bought directly with resolution in time, and the two cannot be improved independently.

Our own data shows both sides: averaging bought a factor of 28 in precision, and the 0.68 mV drift is precisely the slow change a 0.112 s window passes straight through.

### Q7. Measure the PWM waveform. What changes when you turn the pot?

Read off our two captures, Figures 8 and 9 in the evidence note:

| Quantity | 20% setting | 80% setting | Behaviour |
|---|---|---|---|
| Maximum | 5.36 V | 5.36 V | fixed |
| Minimum | −160 mV | −40.0 mV | fixed |
| Peak to peak | 5.52 V | 5.40 V | fixed |
| Period T | 2.036 ms | 2.040 ms | fixed |
| Frequency | 490.421 Hz | 490.421 Hz | fixed |
| Positive width | 408.1 µs | 1.632 ms | **changes** |
| Duty cycle | **20.0%** | **80.0%** | **changes** |

**Only the pulse width and therefore the duty cycle respond to the potentiometer.** That is the defining property of pulse-width modulation: the pin is either fully on or fully off and nothing else, so the only free parameter is the fraction of each cycle spent high. Frequency modulation and amplitude modulation would change the other rows; PWM does not.

**Frequency comparison.** Measured 490.421 Hz against the expected 490 Hz. Pin 9 is driven by Timer1 with a prescaler of 64 in phase-correct mode, counting up to 255 and back down, so it takes 510 timer ticks per cycle:

$$f = \frac{16{,}000{,}000}{64 \times 510} = 490.196 \text{ Hz}$$

Our measurement agrees to 0.05%.

**Duty cycle expected** = 100% × analogWrite value / 255, so the two settings correspond to analogWrite values of about 51 and 204.

**Overshoot.** Maximum reads 5.36 V and Minimum reads −40 to −160 mV rather than a clean 5.00 and 0. That is ringing on the fast switching edges caught by the scope's peak detectors, not a supply problem. The flat parts of the trace sit at the expected levels. A separate measurement gave a rise time of **3.238 µs**.

### Q8. How fast can the eye follow a flashing LED? Why does ours look steady?

**Flicker fusion** for ordinary viewing sits around **50 to 60 Hz**. Above that the flashes merge into steady light.

Our PWM runs at **490 Hz**, eight to ten times higher. The eye integrates over many complete cycles and perceives only the time-averaged brightness, so the LED looks continuously lit at a level set by the duty cycle. It really is switching fully on and fully off 490 times a second, which the oscilloscope resolves without difficulty. This is the direct answer to why a scope was necessary: the serial displays report 10 to 50 lines per second and cannot see a 490 Hz waveform at all.

**Why the threshold is not one universal number:**

- **Brightness.** Fusion frequency rises roughly with the logarithm of luminance (the Ferry-Porter law), so a bright source needs a higher frequency to appear steady than a dim one.
- **Contrast / modulation depth.** A source flicking between full on and full off is far easier to detect than one varying slightly about a mean.
- **Where in the visual field.** Peripheral vision is more sensitive to temporal change than the fovea, which is why a display that looks steady when viewed directly can visibly flicker in the corner of your eye.

---

## Part 4: the Moodle receipt

Due Wednesday 9 September, 5:00 PM. The Moodle page says one team member submits; the course page says each student submits separately. Both of us submitting satisfies either reading.

```
Milestone: C1
Student name(s): Kapil Naidu, Samuel Cohen
Repository URL: https://github.com/kapilnaidu1/phys39-naidu-cohen
Branch: main
Full commit hash: 2b97d31edaf758ee763cb0239e5bcbe5b9ed3947
README path: README.md
Arduino sketch path(s):
  code/module_01/adc_raw.ino
  code/module_01/adc_volts.ino
  code/module_01/averaging_compare.ino
  code/module_01/pwm_brightness.ino
  code/module_01/blink_ratio.ino
Brief description of what was demonstrated:
Module 1 instrumentation and repository milestone. Uploaded and ran a modified
sketch on the Arduino Uno, demonstrated the organized team repository and README
in VS Code and GitHub Desktop, and located the pushed commit and its predecessor
in the GitHub Desktop history. Repository contains the five Module 1 sketches,
the raw Serial Monitor capture from Parts 3C and 3D, the ten figures, and the A1
evidence note. Key measured results: ADC range 0 to 1023 with a one-count
resolution of 4.88 mV, s1000/s1 = 0.0357 against a 1/sqrt(1000) prediction of
0.0316, 112.0 us per analogRead conversion, and 490.42 Hz PWM on pin 9.
```

---

## Numbers worth having memorized

| | |
|---|---|
| ADC codes / range | 1024 codes, 0 to 1023 |
| One count | 4.88 mV (5.00 / 1024) |
| Working point | codes 863 / 864, 4.217986 V and 4.222874 V |
| s unaveraged | 2.035 mV |
| s averaged (N = 1000) | 0.0726 mV |
| Ratio measured / predicted | 0.0357 / 0.0316 |
| Bits gained measured / ideal | 4.81 / 4.98 |
| Time per conversion | 112.0 µs |
| Conversion rate | 8,925 per second |
| 1000-read acquisition | 0.112 s |
| PWM frequency | 490.421 Hz measured, 490.196 Hz predicted |
| PWM period | 2.04 ms |
| Rise time | 3.238 µs |
| Flicker fusion | 50 to 60 Hz |
