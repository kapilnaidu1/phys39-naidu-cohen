# Module 8 Part I: what we have, what the updated page asks for, and what is missing

Naidu / Cohen, 16 November (S22). Compared against the course page as it reads
today (<https://sethfraden.github.io/Phys39F26-course/labs/lab-09/>).

## Short version

The page was rewritten after our S18 and S19 runs. The old version asked for a
100 s run plus a second period of our choice, so we chose 480 s and later added
240, 180 and 300 s. The new version fixes the periods: pilots at 100 and 200 s,
production at 100, 200, 300, 400 and 500 s, and it adds a raw-PWM stage. Our
data are good (κ agrees across every period we ran), but they are at the wrong
periods for the new list. **Missing on the bench: 200, 400 and 500 s with PI,
and the positive-only PWM run.** Everything else missing is analysis or
simulation and needs no bench time.

## Requirement by requirement

| Page item | What the page asks for now | What we have | Status |
|---|---|---|---|
| Stage 1 (S18.1, S18.2) | Sensor map, limits, live GUI, saved record | All of it, since 2 Nov | Done |
| S18.3 raw PWM, zero-centred | u = 50 sin ωt at **300, 200, 100 s**, settled records | Sammy, 11 Nov: **100, 200, 500 s**, u = 50; 3, 3 and 2 cycles fitted | Partly: 300 s not run (500 s instead) |
| S18.3 one-lump simulator table | 6 runs in the course simulator, χc 0.23 and 0.46 | Sammy fitted the one-lump model in Python instead | Partly: course simulator table not filled |
| S18.4 raw PWM, positive only | 100 s, PWM stays positive, mean TEC near 40 °C | Sammy's page has predictions only, no run | Missing |
| S18.5, S18.6 feedforward | Straight line on the heating branch: ua = (Ta − Troom)/χh, ub = Tb/χh | 2 Nov: inverse of the measured steady-state curve, both branches (what the old page asked for) | Partly: different method |
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
| Stage 5, 500 s | Same | None. We have **480 s** on 2 Nov, 11 Nov and today | Missing (ask if 480 counts) |
| Extra periods | Not asked for | 180 s and 240 s (4 Nov, 10 Nov) | Keep as supporting data |
| Stage 6 fits | q, q′, κ, ν, mean-profile m, checks | Done for every period we have | Done |
| Stage 6 characteristic-length plot | 1/m, 1/q, 1/q′ curves from our κ, ν over 100 to 500 s, with fitted points | Not done | Missing (analysis only) |
| Stage 6 matched 300 s comparison | Theory traces, measured traces and the course simulator at 300 s | Theory and data overlay exist (`model_compare_*`); simulator part not done | Partly |
| S18 evidence table | One row per step S18.1 to S18.10 with links | Our notes have it all but not as this table | Partly: analysis only |
| A5 | New 4-question format, about 4 to 6 pages, **Mon 23 Nov 9:05** | Old-format A5 | Missing (rewrite) |

## What Sammy is running today

Schedule: `300 40 0 100`, `1200 40 16 100`, `3840 40 16 480`, about 89 min.

- The 100 s part (12 cycles) is a good repeat of a period we already have.
- The 480 s part (8 cycles) is a third copy of a period the new page does not
  list. It does not fill any gap.

Better use of the same time: stop after the 100 s step (25 min in) and run
`1400 40 16 200` (about 23 min). That one run fills three rows at once: the
200 s pilot, 200 s production and PI at 200 s.

## What to run, in priority order

| # | Run | Fills | Time |
|---|---|---|---|
| 1 | PI 200 s, `1400 40 16 200` | S18.10, Stage 5 200 s, S18.7 200 s | ~25 min |
| 2 | RAW, U0 = 38, U = 36, `900 40 0 100` | S18.4 | ~15 min |
| 3 | PI 400 s, 7 cycles | Stage 5 400 s | ~50 min |
| 4 | PI 500 s, 7 cycles | Stage 5 500 s | ~60 min |
| 5 | RAW zero-centred 300 s, U = 50 | S18.3 300 s | ~30 min |

Runs 1 and 2 fit today. Runs 3 to 5 need a supervised repeat if the professor
wants them (the page says to bring an incomplete dataset to P4 with the missing
periods named).

## Questions for the professor

1. Can our 480 s runs (three of them) stand in for 500 s, or do we book 400 and
   500 s?
2. Is Sammy's raw sweep at 500 s acceptable in place of 300 s?
3. Our feedforward used the inverted steady-state curve, as the earlier page
   asked. Do we also need the new straight-line heating-branch version
   (ua ≈ 35, ub ≈ 32 counts at room 22.5 °C)?

## What needs no bench time (we can do this now)

S18 evidence table, S18.8 tracking numbers, the course simulator runs (one-lump
table and the 100 s P/PI comparison), the characteristic-length plot, the 300 s
three-way comparison, and the A5 rewrite.
