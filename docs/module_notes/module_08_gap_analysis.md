# Module 8 Part I: what we have, what the updated page asks for, and what is missing

Naidu / Cohen, 16 November (S22). Compared against the course page as it reads
today (<https://sethfraden.github.io/Phys39F26-course/labs/lab-09/>).

## Short version

The page was rewritten after our S18 and S19 runs. The old version asked for a
100 s run plus a second period of our choice, so we chose 480 s and later added
240, 180 and 300 s. The new version fixes the periods: pilots at 100 and 200 s,
production at 100, 200, 300, 400 and 500 s, and it adds a raw-PWM stage. Our
data are good (κ agrees across every period we ran), but they are at the wrong
periods for the new list. **Missing on the bench: 200 and 400 s with PI, and
the positive-only PWM run.** Where our runs follow the earlier version of the
page (480 s for 500 s, the raw sweep at 500 s instead of 300 s, the open-loop
method), we keep them and say so: the page changed after the runs were made. Everything else missing is analysis or
simulation and needs no bench time.

## Requirement by requirement

| Page item | What the page asks for now | What we have | Status |
|---|---|---|---|
| Stage 1 (S18.1, S18.2) | Sensor map, limits, live GUI, saved record | All of it, since 2 Nov | Done |
| S18.3 raw PWM, zero-centred | u = 50 sin ωt at **300, 200, 100 s**, settled records | Sammy, 11 Nov: **100, 200, 500 s**, u = 50; 3, 3 and 2 cycles fitted | Done: 500 s used in place of 300 s (see the check below) |
| S18.3 one-lump simulator table | 6 runs in the course simulator, χc 0.23 and 0.46 | Sammy fitted the one-lump model in Python instead | Partly: course simulator table not filled |
| S18.4 raw PWM, positive only | 100 s, PWM stays positive, mean TEC near 40 °C | Sammy's page has predictions only, no run | Missing |
| S18.5, S18.6 feedforward | Straight line on the heating branch: ua = (Ta − Troom)/χh, ub = Tb/χh | 2 Nov: inverse of the measured steady-state curve, both branches (what the old page asked for) | Done the earlier way: the page changed after the 2 Nov run |
| S18.7 P vs PI, same Kp, 100 s | P and PI at the same Kp, then tuning trials | 2 Nov: P and PI both Kp 12 (Ki 0 and 0.2) | Comparison done; no tuning trials (one gain pair used throughout) |
| S18.7 PI at 200 and 300 s | Start with the 100 s gains, retune if needed | 300 s on 4 Nov, Kp 12, Ki 0.2 | 300 s done, 200 s missing |
| S18.8 tracking tables | Mean error, amplitude ratio, lag to setpoint, RMS error | Data exist for 100 and 300 s; numbers not yet tabulated | Partly: analysis only |
| Focused 100 s P/PI simulation | Course six-sensor simulator, P and PI at the same Kp | Not done | Missing (simulator only) |
| S18.9 pilot at 100 s | At least 5 settled cycles, 3 or more sensors | 2 Nov PI 100 s, 5 settled cycles, all 5 sensors | Done |
| S18.10 pilot at 200 s | Same, at 200 s | Nothing usable (4 Nov fast test had one 200 s cycle) | Missing |
| Stage 5, 100 s | At least 5 settled cycles | 2 Nov (5 cycles); Sammy's run today should add 12 | Done |
| Stage 5, 200 s | Same | None | Missing |
| Stage 5, 300 s | Same | 4 Nov `110306`, cycles 2 to 7 | Done |
| Stage 5, 400 s | Same | None | Missing |
| Stage 5, 500 s | Same | **480 s** on 2 Nov and 11 Nov, and Sammy's run today | Done: 480 s used for 500 s (the list changed after these runs) |
| Extra periods | Not asked for | 180 s and 240 s (4 Nov, 10 Nov) | Keep as supporting data |
| Stage 6 fits | q, q′, κ, ν, mean-profile m, checks | Done for every period we have | Done |
| Stage 6 characteristic-length plot | 1/m, 1/q, 1/q′ curves from our κ, ν over 100 to 500 s, with fitted points | Not done | Missing (analysis only) |
| Stage 6 matched 300 s comparison | Theory traces, measured traces and the course simulator at 300 s | Theory and data overlay exist (`model_compare_*`); simulator part not done | Partly |
| S18 evidence table | One row per step S18.1 to S18.10 with links | Our notes have it all but not as this table | Partly: analysis only |
| A5 | New 4-question format, about 4 to 6 pages, **Mon 23 Nov 9:05** | Old-format A5 | Missing (rewrite) |

## What Sammy is running today

Schedule: `300 40 0 100`, `1200 40 16 100`, `3840 40 16 480`, about 89 min.

- The 100 s part (12 cycles) is a good repeat of a period we already have.
- The 480 s part (8 cycles) is a third copy of 480 s. Now that 480 s counts
  for 500 s it is useful as a repeat, but it does not fill a missing row.

Better use of the same time: stop after the 100 s step (25 min in) and run
`1400 40 16 200` (about 23 min). That one run fills three rows at once: the
200 s pilot, 200 s production and PI at 200 s.

## What to run, in priority order

| # | Run | Fills | Time |
|---|---|---|---|
| 1 | PI 200 s, `1400 40 16 200` | S18.10, Stage 5 200 s, S18.7 200 s | ~25 min |
| 2 | RAW, U0 = 38, U = 36, `900 40 0 100` | S18.4 | ~15 min |
| 3 | PI 400 s, 7 cycles | Stage 5 400 s | ~50 min |

Runs 1 and 2 fit today. If run 3 does not fit, it needs a supervised repeat
(the page says to bring an incomplete dataset to P4 with the missing period
named). Runs 1 and 3 use our PI settings; run 2 needs Sammy's sketch and GUI
(RAW mode).

## Decisions on the earlier-version runs

**480 s for 500 s.** Runs at 480 s on 2 Nov and 11 Nov (both qualify), plus Sammy's run today
(not yet fitted). A 4 % shorter
period changes q and q′ by about 2 %, well inside what the five-period
comparison tests.

**Raw sweep at 500 s instead of 300 s (S18.3).** Checked with the one-lump
model fitted to Sammy's own run (χh 0.417, χc 0.149 °C per count, τ 64.3 s;
`python/analysis/s183_300s_check.py`, figure
`docs/figures/module_08/s183_300s_vs_500s.png`):

| Period | Mean shift (°C) | Amplitude (°C) | Lag behind PWM (rad) | 2nd harmonic / fundamental |
|---|---|---|---|---|
| 200 s measured | 4.31 | 6.60 | 1.12 | 0.110 |
| 300 s predicted | 4.27 | 8.45 | 0.93 | 0.117 |
| 500 s measured | 4.28 | 10.88 | 0.69 | 0.138 |

The model matches the measured 200 s and 500 s points to 5 % in amplitude and
0.01 rad in lag, and a 300 s run would land between them on the same smooth
curve: same mean shift, same distortion, nothing new. The questions the page
asks of this sweep (does a fixed PWM amplitude give the same temperature
amplitude, how do lag and mean change with period) are answered the same way
with 500 s. One weakness to state: the 500 s fit used 2 complete cycles
(cycle-to-cycle spread 0.012 °C in amplitude), one short of the 3 the page asks
for in the control comparisons.

**Open-loop method (S18.5, S18.6).** The 2 Nov open-loop trial inverted the
full Module 4 heating and cooling curve, which is what the page asked for then.
The new page uses a heating-only command (it would be 35 + 32 sin ωt counts for
our χh and room temperature). We keep the 2 Nov trial and note the difference.

## What needs no bench time (we can do this now)

S18 evidence table, S18.8 tracking numbers, the course simulator runs (one-lump
table and the 100 s P/PI comparison), the characteristic-length plot, the 300 s
three-way comparison, and the A5 rewrite.
