# Module 8, Part I: bench plan for Wednesday 18 November 2026

One session that repeats what the 16 and 17 Nov runs left weak or open. The GUI runs the six runs from one click (START PLAN; `FULL_PLAN` in
`python/sammy_module8_angstrom_gui.py`, tested offline against a fake Arduino, 40 checks); the rest is setup before and analysis after.
Kapil Naidu's acquisition code and data are unchanged.

## 1. What is repeated and why

| Run | Fixes | Pass criterion | Priority |
|---|---|---|---|
| PI 400 s | 17 Nov: the strict settling test kept 2 of 7 cycles (5 needed); the rod mean was still creeping (T5 31.2 to 31.6 °C) after a 300 s hold | at least 5 settled cycles by the same test (3 % amplitude, 0.05 rad, counting back from the last cycle) and at least 3 measurable rod sensors | must |
| RAW zero-centered 300 s (S18.3) | the page asks for 300, 200 and 100 s; SAMMY has 100, 200 and 500 s with 3, 3 and 2 settled cycles (the page wants 3) | at least 3 settled cycles | could |
| RAW feedforward 100 s (S18.5, S18.6) | the page now asks for the heating-only line u_a = (T_a − T_room)/χh, u_b = T_b/χh; the 2 Nov feedforward inverted the steady-state curve but drove 3 to 67 counts, the same as this formula (3.2 to 67), so this run only repeats it in your session | at least 3 settled cycles; mean, amplitude and lag against the prediction | optional (15 min that can be dropped) |
| P only, PI Ki 0.5, PI Kp 20 (S18.7) | SAMMY has only PI at Kp 12, Ki 0.2; the page wants P and PI at the same Kp, then one gain changed per trial, every trial kept | at least 3 settled cycles each; note saturation and the PWM range | could |

Not repeated: the plate-only tests of Modules 2 to 6 (the rod is attached now; their limits stay stated limits), PI 300 s (Kapil's 4 Nov run qualifies),
PI 100 s and 200 s (the 16 Nov runs qualify), PI 500 s (480 s is accepted for 500 s, which saves the 58 min step), sensor T2 (above the fit by 2 to 5 % in amplitude, but dropping it moves κ by under 1 %).

## 2. The plan START PLAN runs

PI and P runs use Ta 40, Tb 16, χh 0.50127, χc 0.18091 (r = 2.771). Each phase starts 1.5 s after the previous `SCHEDULE DONE`; every phase sends its own settings.

| # | Run | Mode and settings | Schedule (duration Ta Tb period) | Length | Ends | Clock if START PLAN is at 09:30 |
|---|---|---|---|---|---|---|
| 1 | RAW zero-centered 300 s | RAW, U 50, U0 0 | `1800 40 0 300` | 30 min | T+0:30 | 10:00 |
| 2 | PI production 400 s | PI, Kp 12, Ki 0.2 | `1200 40 0 100`, `4000 40 16 400` | 86.7 min | T+1:57 | 11:27 |
| 3 | RAW feedforward 100 s | RAW, U 32, U0 35 | `900 40 0 100` | 15 min | T+2:12 | 11:42 |
| 4 | P only 100 s | P, Kp 12, Ki 0 | `300 40 0 100`, `700 40 16 100` | 16.7 min | T+2:28 | 11:58 |
| 5 | PI Ki 0.5, 100 s | PI, Kp 12, Ki 0.5 | `300 40 0 100`, `700 40 16 100` | 16.7 min | T+2:45 | 12:15 |
| 6 | PI Kp 20, 100 s | PI, Kp 20, Ki 0.2 | `300 40 0 100`, `700 40 16 100` | 16.7 min | T+3:02 | 12:32 |

Total 182 min from the click (the 500 s step is gone). The last run is optional (its box in the GUI is ticked by default); STOP cancels everything that has not started.

- **Run 2.** The hold is 1200 s. On 17 Nov, after a 300 s hold, the T5 mean was 0.8 °C below its final value in the middle of cycle 1 and still 0.4, 0.1 and 0.07 °C below it in cycles 2 to 4 (a tail of about
  500 s); 1200 s cuts the starting deficit to about 0.2 °C. The hold ends at T+0:50. The 400 s step has 10 cycles: the first is lost to the start-up transient and on 17 Nov four more were lost to the creeping mean, so 10 leaves
  at least 5; it ends at T+1:57. There is no 500 s step: the 480 s runs stand in for 500 s.
- **Run 3.** The counts are for a room at 22.4 °C: U0 = (40 − 22.4)/0.50127 = 35.1, U = 16/0.50127 = 31.9. U0 must stay above U, so the plan holds only for a room below 24 °C
  (U0 would be 36.9 at 21.5 °C, 33.9 at 23 °C). Use the measured room T in the analysis; the counts only need changing (`FULL_PLAN`, phase 3) if the room is far from 22.4 °C.
- **Runs 4 to 6.** One gain changes per run against the PI Kp 12, Ki 0.2 baseline of 16 Nov (12 cycles at 100 s). At 100 s that baseline reached B_TEC/Tb = 0.86 with a lag of 0.63 rad and PWM down to
  −225, so more gain may hit ±255; if it does, that is the result to report (the page asks for the limiting factor).

## 3. Before START PLAN (supply and pump off)

1. Laptop on AC, Arduino IDE closed (the board already runs `angstrom_tec_sammy`; no upload).
2. Start the GUI detached from the repository root, so closing a terminal cannot end it:
   ```bash
   cd "/Users/samuelcohen/Documents/GitHub/Sammy Cohen module 4 kapil"
   nohup caffeinate -dims python3 -u python/sammy_module8_angstrom_gui.py > /tmp/gui_day.log 2>&1 &
   ```
   The "One long run" box must list six runs and "Total 182 min".
3. Calipers, no thermistor moved. Note: `calipers T1-T2 __, T1-T3 __, T1-T4 __, T1-T5 __ mm`.
4. Five minutes idle, supply and pump off: six flat lines, no spikes or nan, within about 0.3 °C (T2 about 0.2 °C low is normal). If a line jumps, reseat that thermistor's leads, its
   100 kΩ resistor and its A-pin jumper (no pin changes) and wait 2 more minutes. Room T = mean of T1 to T5 over the last 60 s (the analysis applies the calibration offsets; use the value after the offsets for `--t-room`, as on 16 and 17 Nov). Note `room T baseline X`; put X in the **room T** box.
5. Supply on, pump on, check the pump and fans. Note `supply and pump on`. The TEC thermistor must show a number and the state must read idle.
6. Click **START PLAN**, read the settings the dialog lists for each run, answer Yes. Do not use Send settings, START, Send schedule or the schedule box while the plan runs.

## 4. During the run

- Hands, ruler, camera and people away from the rod; no door or window changes. On 17 Nov cycle 5 sat 3.6 % off in T3 and ended the settled block; the cause is unknown (the creeping mean or a disturbance), so keep the room undisturbed. Type a note for anything unusual (door, someone near the rod).
- Watch T1 below 54 °C (latch 56 °C) and the TEC below 62 °C (latch 65 °C). STOP if a channel starts spiking or reads nan.
- If the GUI dies, the Arduino keeps its schedule (no host watchdog) and idles when it ends. Start the GUI again (a new file) to keep logging, then run what is left by hand.

## 5. By hand (only if the plan cannot be used)

For each run: set the boxes, **Send settings**, wait 3 s, **GET** and check the `# SETTINGS` line, paste the schedule, **Send schedule** (left button), check `# SCHEDULE n steps`,
**START schedule** (right button). Never send settings during a run.

| Run | Mode | Kp | Ki | U | U0 | Schedule box |
|---|---|---|---|---|---|---|
| 1 | RAW | | | 50 | 0 | `1800 40 0 300` |
| 2 | PI | 12 | 0.2 | | | `1200 40 0 100` / `4000 40 16 400` |
| 3 | RAW | | | 32 | 35 | `900 40 0 100` |
| 4 | P | 12 | 0 | | | `300 40 0 100` / `700 40 16 100` |
| 5 | PI | 12 | 0.5 | | | `300 40 0 100` / `700 40 16 100` |
| 6 | PI | 20 | 0.2 | | | `300 40 0 100` / `700 40 16 100` |

## 6. After the run

1. Close the GUI (it sends STOP). Supply and pump off.
2. `python3 python/sammy_module8_angstrom_gui.py --check-file data/module_08_sammy/sammy_angstrom_live_<stamp>.csv` (expect 0 malformed, 0 duplicated, 0 restarts).
3. One slice per phase, byte for byte from the file (the cutting rule reproduces the 16 Nov slices exactly):
   `python3 python/sammy_module8_plan_slices.py data/module_08_sammy/sammy_angstrom_live_<stamp>.csv`
   writes `..._phase1_raw_zero_centered_300s.csv`, `..._phase2_pi_production_400s.csv`, `..._phase3_raw_feedforward_100s.csv`, `..._phase4_p_only_kp_12_100s.csv`,
   `..._phase5_pi_kp_12_ki_0_5_100s.csv`, `..._phase6_pi_kp_20_ki_0_2_100s.csv`.
4. Analysis, with T the room T of the baseline:
   ```bash
   python3 python/sammy_module8_angstrom_analysis.py <phase2 slice> --t-room T --summary none     # also phases 4, 5, 6: tracking_by_period.csv has B_TEC/Tb, lag, PWM range, samples at +-255
   python3 python/sammy_module8_s184_analysis.py <phase3 slice> --t-amb T --t-room T            # feedforward against its prediction
   python3 python/sammy_module8_s183_analysis.py <phase1 slice> --no-doc                         # S18.3 at 300 s
   python3 python/sammy_module8_finite_rod.py <stamp>_phase2_pi_production_400s --out data/module_08_sammy/finite_rod_fits_18nov.csv
   ```
   If T5 or another sensor spikes, write `<slice>_mask.csv` (channel, t_start_s, t_end_s, reason) as for the 10 Nov run and rerun; the raw file stays unchanged.
5. Pass or fail: the strict settled-cycle count for 400 s (`settled_blocks.csv`). If 400 s still has fewer than 5, report the strict count and the all-cycles result and ask for the supervised repeat;
   do not loosen the 3 % and 0.05 rad rule afterwards (the page wants the tolerances justified by the measured noise before the fit).
6. Commit by explicit path: the run files (`.csv`, `_events.txt`, `_meta.json`, `_notes.csv`), the slices, the analysis folders and figures. Never `git add -A`; the three unrelated modified files stay unstaged.
