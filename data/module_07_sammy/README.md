# Sammy Module 7 Rod Instrument

This is a new Module 7 workspace based on the shared Module 8 files. The shared Module 8 Arduino sketch and GUI remain unchanged.

## New files

- Arduino copy: `arduino/module_07_sammy/rod_tec_multichannel_sammy/rod_tec_multichannel_sammy.ino`
- Python GUI copy: `python/sammy_module7_rod_pi_logger.py`
- Sensor map: `data/module_07_sammy/sensor_map.csv`
- New raw runs: `data/module_07_sammy/sammy_rod_run_*.csv`

From the repository root, the GUI launch command is:

```bash
python3 python/sammy_module7_rod_pi_logger.py
```

The logger uses the Module 6 PI controller and TEC safety sensor on A0. The five rod channels are measurement-only and never enter the control or safety loop. It writes a new timestamped raw CSV, metadata JSON, and timed-notes CSV on each launch. Plot smoothing defaults to one point (off); if increased later, it changes only the display, never the saved raw readings.

## Sensor map and positions

Keep the TEC-base sensor on A0. Use the permanent map T1–T5 on A1–A5. T1 in the first rod hole defines x = 0; all other x positions are measured from that hole. The `target_position_mm` values are a planning proposal, not measured coordinates. The actual-position and measured-resistor fields are blank on purpose; fill them with a ruler/caliper and multimeter before analysis.

Proposed placement if the rod has a usable hole at each location. In physical hole order, put T1 in hole 1, T2 in hole 3, T3 in hole 5, T4 in hole 7, and T5 in hole 9 (skip one nominal 1-inch hole between sensors):

| Sensor | Arduino pin | Planned x | Rationale |
|---|---|---:|---|
| T1 | A1 | 0 mm | First rod hole; analysis base |
| T2 | A2 | 50.8 mm | About 2 in from T1 |
| T3 | A3 | 101.6 mm | About 4 in from T1 |
| T4 | A4 | 152.4 mm | About 6 in from T1 |
| T5 | A5 | 203.2 mm | About 8 in from T1; farthest hole in the previous record |

This uses every other nominal 1-inch hole and spreads measurements across the rod. Confirm hole numbering and positions physically; do not rely on nominal spacing for the fit. T1 is the first **rod** hole at x=0, not the TEC-base thermistor. If there is no usable hole at one of these targets, use the nearest sensible available hole, measure its position from T1, and update the map before fitting. Do not move T1: the model uses it as the base boundary.

Use the same approved tape method for all five sensors, with the thermistor bead pressed consistently against the rod. Tape can add contact resistance and lag compared with thermal glue. Record this in the map and notes; do not hide the physical lag with filtering. Rod sensors are measurement-only, so their lag cannot make the PI controller oscillate. If display noise is distracting, the new GUI has a plot-only moving average setting; leave `DISPLAY_SMOOTH_POINTS = 1` for the real measurement and fit raw CSV data.

The previous profile had the five sensors at 0, 25.4, 50.8, 76.2, and 101.6 mm and measured theta5/theta1 = 0.74. The previous finite fit estimated theta/theta1 about 0.60 at the farthest available hole near 203.2 mm. Thus spreading the sensors improves the spatial leverage but is not expected to reach the course target theta5/theta1 <= 1/e (about 0.368) with this rod and boundary condition. Confirm the official threshold with the instructor if the pasted handout omitted it.

## Before connecting TEC power

1. Copy and edit only the new Sammy files; leave Module 6 and shared Module 8 originals untouched.
2. Measure and enter all five upper fixed-resistor values in the Arduino copy.
3. Measure T1–T5 positions from T1, actual rod diameter, and T1-to-tip length; fill the sensor map.
4. With TEC power off, verify every one of six thermistors changes only its assigned displayed channel when warmed. Check the common-bath spread using the official criterion; apply offsets only if the check fails, and retain raw data.
5. Close Arduino Serial Monitor/Plotter before starting the Python GUI. Confirm plausible base temperature, pump circulation, instructor approval, and PWM zero before enabling the TEC.

After the run, preserve the raw CSV, map, metadata, notes, transient history, room temperature, and stationary interval. Fit the finite and semi-infinite profiles to excess temperature `theta = T - T_room`, inspect residuals, and keep length and radial validity as separate checks.