# Module 8, Part I: Angstrom method

Naidu / Cohen. Course page: Module 8, Part I (S18 to S22). Data in
`data/module_08/`, figures in `docs/figures/module_08/`.

## 1. Acquisition (new for Module 8)

| Part | File |
|---|---|
| Arduino | `arduino/module_08/angstrom_tec/angstrom_tec.ino` |
| GUI | `python/angstrom_gui.py` |
| Logger check without the GUI | `python3 python/angstrom_gui.py --check-file <file>` |

The Arduino now computes everything that goes into a record: the setpoint
T_set = Ta + Tb sin(phase), the PI command on the TEC thermistor (Kp, Ki,
conditional integration as in Module 6), the cooling multiplier r and the
clamped signed PWM. So the laptop and the Fermion logger, which both listen
to the same TX line, record identical lines. The GUI only sends settings and
START / STOP.

One record every 500 ms:

```text
time_ms,run_state,step,Ta_C,Tb_C,period_s,setpoint_C,TEC_C,T1_C,T2_C,T3_C,T4_C,T5_C,uPI_pwm,heating_to_cooling_ratio,signed_pwm
```

run_state: 0 idle, 1 running, 9 safety latched. step is 0 for a live run.
Temperatures are raw beta-equation values; calibration offsets are applied
in analysis only. Lines starting with `#` are boot headers and events; each
boot prints `# BOOT n` (counter in EEPROM) so a restart is visible in the
logger file.

Cooling multiplier: r = χ_h/χ_c = 0.50127/0.18091 = **2.771** (Module 4
open-loop steps). A negative PI command is multiplied by r before the clamp.

Safety: latch at 55 °C on the TEC thermistor or on T1, or after 5 unusable
TEC readings; setpoints must stay within 10 to 50 °C (Ta + Tb ≤ 50,
Ta − Tb ≥ 10). Output is 0 until START.

Check on the Module 6 one-lump plate model (no rod), Kp 12, Ki 0.2,
r 2.771, Ta 40, Tb 8, period 100 s: the TEC follows with amplitude 6.8 °C and
a lag of 0.55 rad, PWM between −53 and +91, no saturation. The rod adds heat
load and lag, so the real numbers will differ; this only says the gains are a
sensible start.

## 2. Logger wiring and setup

- Arduino 5V → logger VCC, GND → GND, Arduino TX (pin 1) → logger RX.
  Logger TX not connected.
- `CONFIG.TXT` on the card: baud 9600, to match `Serial.begin(9600)`.
- The sketch waits 2.5 s after boot before printing, for the logger to start.
- Logger USB-C stays unplugged while recording (plugged in, it is a USB drive
  and does not log).

## 3. Running the live session (S18)

1. Upload `angstrom_tec.ino`, close the Arduino IDE.
2. `python3 python/angstrom_gui.py` from the repository root.
3. Type the room temperature as a note (`room T ... C`, and how measured).
4. Check that all six temperatures read sensibly with output off.
5. Send settings (defaults: Ta 40, Tb 8, period 100 s, Kp 12, Ki 0.2,
   r 2.771), then START.
6. Every change of settings goes through the GUI, so the Arduino prints an
   `# EVENT` line and the GUI saves it in `_events.txt`.
7. At the end: STOP, close the GUI, wait a few seconds, power off, then read
   the logger card. "Import logger file" checks it with the same parser and
   copies it unchanged into `data/module_08/`.

## 4. P3: predictions and pilot plan

**Qualitative.** Every sensor oscillates at the drive period. Farther from
T1 the oscillation is smaller (amplitude falls as e^(−qx)) and later (phase
lag q′x). The mean temperature also falls along the rod, with a different
decay length (the stationary profile of Module 7). A shorter period gives
stronger attenuation and more phase lag per metre.

**Numbers, for planning only.** κ from handbook values for 6061-T6 (k = 167
W/(m K), ρ = 2700 kg/m³, c = 896 J/(kg K)): κ = 6.9 × 10⁻⁵ m²/s. ν = κm² with
our Module 7 m = 4.12 m⁻¹: ν = 1.2 × 10⁻³ s⁻¹. Then
q = √((ν + √(ν² + ω²))/(2κ)) and q′ = √((−ν + √(ν² + ω²))/(2κ)), semi-infinite rod:

| Period (s) | q (1/m) | q′ (1/m) | B/B1 at 4 in | phase lag at 4 in (rad) | B/B1 at 8 in | phase lag at 8 in (rad) |
|---|---|---|---|---|---|---|
| 100 | 21.5 | 21.1 | 0.11 | 2.2 | 0.013 | 4.3 |
| 180 | 16.2 | 15.6 | 0.19 | 1.6 | 0.037 | 3.2 |
| 240 | 14.1 | 13.5 | 0.24 | 1.4 | 0.057 | 2.7 |
| 300 | 12.7 | 12.0 | 0.28 | 1.2 | 0.076 | 2.4 |
| 480 | 10.2 | 9.3 | 0.36 | 0.95 | 0.13 | 1.9 |

The course targets are a farthest retained sensor at 10 to 20 % of the x = 0
amplitude and 0.5 to 2 rad of phase lag. At 100 s the 1-inch layout (sensors
at 0 to 4 in) meets both; the 2-inch layout (0 to 8 in) only keeps T1 to T3.

**Pilot settings.** Ta 40 °C, Tb 8 °C (setpoint 32 to 48 °C), period 100 s,
Kp 12, Ki 0.2, r 2.771, report every 0.5 s (200 samples per period). Limits:
55 °C latch on TEC and T1, 70 °C thermal switch. Settling test: fit
consecutive groups of complete cycles; settled when B and φ of each sensor
agree between groups within their uncertainties and there is no drift in the
residuals.
