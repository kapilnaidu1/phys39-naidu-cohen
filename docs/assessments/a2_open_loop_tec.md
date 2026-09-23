# A2: Open-Loop TEC Instrument Note

**Team:** Naidu / Cohen
**Due:** Monday 28 September 2026, 6:00 PM
**Working note:** [`docs/module_notes/module_04_open_loop_tec.md`](../module_notes/module_04_open_loop_tec.md)

*Draft. Sections marked TO WRITE need bench data from S7-S8.*

---

## 1. Wiring: the high-current path

TO WRITE. Diagram showing the 18 AWG path from supply through `B+`/`B-`,
the H-bridge, `M+`/`M-`, the **thermal switch in series** with the TEC, and
back. Include the spade crimps.

## 2. Power supply and software safety settings

| Setting | Value |
|---|---|
| Supply | ALITOVE ALT-1210T, 12 V, fixed output |
| Measured voltage at the barrier strip | TO RECORD |
| Current limit | none adjustable, supply's own 10 A / 120 W ceiling |
| Software temperature limit | **60.0 C**, `temperatureLimitC` |
| Hardware thermal switch | opens near 70 C, in series with the TEC |

## 3. Direction/PWM table and the steady-state criterion

TO WRITE from the module note. State the criterion before the table.

## 4. Raw data and labelled traces

TO WRITE. One heating trace, one cooling trace, both linked.

## 5. Steady-state temperature versus PWM

TO WRITE. Figure from `python/plot_open_loop_calibration.py`, red heating and
blue cooling, labelled axes with units, criterion in the caption.

## 6. Temperature susceptibility

| Direction | dT/dPWM (C per PWM count) |
|---|---|
| Heating | TO RECORD |
| Cooling | TO RECORD |

## 7. Heating/cooling asymmetry

TO WRITE. Argument sketched in the module note's pre-class question 3, backed
by the Module 3 measurements: +1.821 vs -0.269 C/s at full drive, a factor of
6.8, and 3.7 at duty 159. The ratio growing with drive is the evidence that
Joule heating, which goes as current squared, is the mechanism.

## 8. Code links

- Arduino safety limit: [`arduino/module_04/tec_open_loop_safety`](../../arduino/module_04/tec_open_loop_safety/tec_open_loop_safety.ino)
- Python GUI: [`python/tec_control_gui.py`](../../python/tec_control_gui.py)
- Plot and slopes: [`python/plot_open_loop_calibration.py`](../../python/plot_open_loop_calibration.py)

## 9. Safety test evidence

TO WRITE. Transcript showing both H-bridge outputs set to zero while serial
reporting continued. Procedure is in the module note; record it to
`data/module_04/part1_safety_shutdown_test.txt`.

## 10. Git checkpoint

TO RECORD. Commit hash and repository link.
