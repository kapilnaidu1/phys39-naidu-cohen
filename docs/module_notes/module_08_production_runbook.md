# Module 8 production run (S20, Monday 9 November): step by step

For whoever runs the bench. Everything below uses the code already on `main`.

**Total time about 2 hours:** 15 min setup, 101 min run, 5 min wrap-up. Start by
about 9:30 to finish well inside the lab block.

**Do not move any thermistor.** Stage 5 needs the same sensor map as the pilot
runs (T1 to T5 at 0, 25.4, 50.8, 76.2, 101.6 mm, ±1 mm).

## Before heating

1. In GitHub Desktop: **Fetch origin**, then **Pull origin**.
2. Upload `arduino/module_08/angstrom_tec/angstrom_tec.ino` (harmless if the
   board already has it), then close the Arduino IDE.
3. Open the GUI from the repository folder:
   ```bash
   cd ~/Documents/GitHub/phys39-naidu-cohen
   python3 python/angstrom_gui.py
   ```
4. **Caliper check (5 min, supply off, rod at room temperature).** Without moving
   any thermistor, measure centre to centre from the T1 hole to the T2, T3, T4
   and T5 holes. Type them as one note:
   `calipers T1-T2 __, T1-T3 __, T1-T4 __, T1-T5 __ mm`, filling in the readings.
5. Supply and pump **off**. Leave everything alone for 2 minutes and watch the six lines:
   - no spikes, no gaps (nan), all six flat;
   - they should agree within about 0.3 °C (T2 normally reads about 0.2 °C lower than the others).

   If a line jumps, reseat that thermistor's leads, its 100 kΩ resistor and its
   A-pin jumper on the breadboard (do not move wires to other pins), then wait
   another 2 minutes.
6. Type the note `room T baseline`. Room temperature = the mean of T1 to T5 over
   that flat stretch. Put the value in the **room T** box. (The fit scripts apply
   the offsets in `data/module_08/calibration_rod_run_20261026_112627.csv` later.)
7. Turn **on** the supply and the pump. Check that the pump and fans run.

## The run

8. Mode **PI**, Kp 12, Ki 0.2, χh 0.50127, χc 0.18091 (r = 2.771). Click
   **Send settings**, wait 3 s, click **GET** and check the terminal `# SETTINGS`
   line (including `Tamb=` matching the room T box).
9. Click **Production**. The box should read:
   ```
   300 40 0 100
   3360 40 16 480
   1680 40 16 240
   700 40 16 100
   ```

   | Step | What | Time |
   |---|---|---|
   | 1 | hold at 40 °C | 5 min |
   | 2 | 7 cycles at 480 s | 56 min |
   | 3 | 7 cycles at 240 s | 28 min |
   | 4 | 7 cycles at 100 s | 12 min |

10. Click **Send schedule**, wait 3 s, and check the terminal shows `# SCHEDULE 4 steps`.
11. Click **START schedule** and type the note `production run start`.
12. Hands off the rod, the wires and the breadboard until it ends. The status
    line shows the step number; the schedule turns the output off by itself at
    the end (`SCHEDULE DONE`).

Stop early (STOP) only if T1 nears 56 °C, a channel starts spiking, or the
safety latch trips. Type a note for anything unusual. If the run has to stop,
the 4 November data still meet the minimum, so stop safely rather than push on.

## After the run

13. Close the GUI. Turn off the supply and pump.
14. Show the professor the record (S20 data-readiness check): the live plot, or
    **Check a saved file** on the new CSV.
15. In GitHub Desktop, commit only the four new files
    `data/module_08/angstrom_live_20261109_<time>.csv`, `_events.txt`,
    `_notes.csv` and `_meta.json`, summary `S20 production run`, then
    **Push origin**.

## Why 7 cycles per period

The course asks for at least 5 complete settled cycles per period, counted only
after the settling criterion is met. Settled = every sensor's amplitude within
3 % and phase within 0.05 rad from one cycle to the next. Each period change
starts a new transient, and in our pilot runs the first 1 to 2 cycles did not
settle (2 Nov 480 s: cycle 1 dropped; 4 Nov 240 s and 180 s: cycles 1 and 2
dropped). Seven cycles leaves 5 settled ones even if 2 are lost.

## What the data are for

Each period gives q (amplitude decay), q′ (phase lag), κ = ω/(2qq′) and
ν = κ(q² − q′²). Agreement of κ across 480, 240 and 100 s in one record, under
one room temperature and one sensor seating, is the frequency-consistency test.
The caliper readings test whether the sensor spacing explains our κ being about
30 % above the handbook value for 6061-T6 (κ scales with spacing squared).
