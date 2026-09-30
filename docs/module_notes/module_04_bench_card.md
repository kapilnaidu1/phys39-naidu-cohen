# Module 4 bench card

One page to work from at the bench. Fill values in as you go, then paste
back for the note. Numbers in brackets are what Module 3 measured.

---

## A. Before power (10 min)

| # | Check | Value |
|---|---|---|
| A1 | **Finger test.** Warm thermistor, reading rises; release, falls | pass / fail |
| A2 | **Pump circulating**, liquid moving, not just fans spinning | yes / no |
| A3 | ALITOVE input selector reads **110 V** | yes / no |
| A4 | **Which** of the two supplies feeds `B+`/`B-` | upper / lower |
| A5 | Supply voltage at the barrier strip, **under load** | ____ V |
| A6 | Thermal switch rating off the body marking | ____ C |
| A7 | Continuity through closed thermal switch | ____ ohm |
| A8 | Switch is **in series** with the TEC, traced by hand | yes / no |
| A9 | 18 AWG on all three high-current runs | yes / no |
| A10 | Spade crimps hold under a firm tug | yes / no |

A1 and A2 are the two that can waste the whole session. Do them first.

A1 matters because the channel sat frozen at exactly 24.27 C for 80
consecutive reports on 23 Sept. A frozen channel looks like perfect data.

---

## B. Power up (5 min)

1. Banner shows `SOFTWARE TEMPERATURE LIMIT: 60.0 C`, PWM 0, temperature plausible
2. Enable supply
3. `SET PWM 35 DIR HEAT`, hold **90 s**. Expect a rise. [35 s onset delay at duty 28]
4. `SET PWM 0`
5. `SET PWM 35 DIR COOL`, hold **90 s**. Expect a fall.
6. `SET PWM 0`

Strip chart: PWM trace red heating, blue cooling.

---

## C. Exploratory sweep (15 min)

Find the highest PWM in each direction whose **steady** temperature stays
inside **10 to 45 C**. Climb gradually, watch temperature and supply current.

Starting estimates from Module 3:

| | Module 3 evidence | try near |
|---|---|---|
| Heat | effective duty 64 headed for ~48 C | **50 to 60** |
| Cool | duty 251 floored at -6.79 C | **100 to 120** |

Heating maxes out at a much lower PWM than cooling. That is the asymmetry,
not a mistake.

| Direction | Max useful PWM | Steady T there |
|---|---|---|
| Heat | ____ | ____ C |
| Cool | ____ | ____ C |

---

## D. Steady-state points (45 to 50 min)

Five per direction: 0, 25%, 50%, 75%, 100% of that direction's max.
Record the **exact integers used**.

**Criterion: less than 0.1 C change over 30 s, minimum wait 180 s.**
0.1 C is just above the 0.079 C quantization step, so anything tighter is
measuring the ADC rather than the plate. 180 s is three of the ~50 s driven
time constant.

Two time savers:

- **Go ascending within a direction.** Each setting then starts from the
  previous steady state instead of a return to ambient. Roughly halves the
  total wait.
- **The two PWM 0 rows are one measurement.** Wait once, write it twice.

| Dir | PWM | Start C | Steady C | Waited s | Notes |
|---|---|---|---|---|---|
| Heat | 0 | | | | |
| Heat | | | | | |
| Heat | | | | | |
| Heat | | | | | |
| Heat | | | | | |
| Cool | 0 | | | | |
| Cool | | | | | |
| Cool | | | | | |
| Cool | | | | | |
| Cool | | | | | |

---

## E. Before you leave the bench

**Snapshot the traces.** `tec_control_run.csv` is overwritten on every
launch and a Module 3 run was nearly lost this way.

```
cd ~/Documents/GitHub/phys39-naidu-cohen
cp data/module_03/tec_control_run.csv data/module_04/heating_trace_01.csv
cp data/module_03/tec_control_run.csv data/module_04/cooling_trace_01.csv
```

Take one photo of the wiring for the A2 safety section.

---

## F. Back at a computer

1. Fill `data/module_04/steady_state.csv`
2. `python3 python/plot_open_loop_calibration.py` from the repo root
3. Gives the red/blue figure plus dT/dPWM both ways with R squared
4. Write Part 5, assemble A2, commit, push
