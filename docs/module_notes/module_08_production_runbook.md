# Module 8 production run (S20): step by step

For whoever runs the bench. Everything below uses the code already on `main`.

## Before heating

1. `git pull`. Upload `arduino/module_08/angstrom_tec/angstrom_tec.ino`, then close the Arduino IDE.
2. From the repository folder:
   ```bash
   cd ~/Documents/GitHub/phys39-naidu-cohen
   python3 python/angstrom_gui.py
   ```
3. Supply and pump **off**. Leave everything alone for 2 minutes and watch the six lines:
   - no spikes, no gaps (nan), all six flat;
   - after the known offsets they should agree within about 0.3 °C (T2 normally reads about 0.2 °C lower than the others).
   If a line jumps, reseat that thermistor's leads, its 100 kΩ resistor and its A-pin jumper on the breadboard (do not move wires to other pins), then wait another 2 minutes.
4. Type the note `room T baseline`. Room temperature = the mean of T1 to T5 over that flat stretch (the fit scripts use the offsets in `data/module_08/calibration_rod_run_20261026_112627.csv`). Put the value in the **room T** box.
5. Turn **on** the supply and the pump. Check that the pump and fans run.

## The run

6. Mode **PI**, Kp 12, Ki 0.2, χh 0.50127, χc 0.18091 (r = 2.771). Click **Send settings**, wait 3 s, click **GET** and check the terminal `# SETTINGS` line.
7. Click **Production**. The box should read:
   ```
   300 40 0 100
   3360 40 16 480
   1680 40 16 240
   700 40 16 100
   ```
   (5 min hold at 40 °C, then 7 cycles each at 480, 240 and 100 s; about 101 min.)
8. Click **Send schedule**, wait 3 s, and check the terminal shows `# SCHEDULE 4 steps`.
9. Click **START schedule** and type the note `production run start`.
10. Hands off the rod, the wires and the breadboard until it ends. The status line shows the step number; the schedule turns the output off by itself at the end (`SCHEDULE DONE`).

Stop early (STOP) only if T1 nears 56 °C, a channel starts spiking, or the safety latch trips. Type a note for anything unusual.

## After the run

11. Close the GUI. Turn off the supply and pump.
12. If possible, measure room temperature again (a separate thermometer, or the rod channels once everything is back at room) and add it as a note in the next GUI session.
13. Commit and push `data/module_08/angstrom_live_<date_time>.csv` and its `_events.txt`, `_notes.csv`, `_meta.json`.

## What the data are for

Each period gives q (amplitude decay), q′ (phase lag) and κ = ω/(2qq′). Agreement of κ across 480, 240 and 100 s is the frequency-consistency test. Settled = every sensor's amplitude within 3 % and phase within 0.05 rad from one cycle to the next; at least 5 settled cycles kept per period.
