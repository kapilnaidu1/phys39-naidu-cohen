Module 4 raw data. Naidu / Cohen.

Files expected here:

  steady_state.csv                    the Part 3 table, one row per
                                      measurement. Input to
                                      python/plot_open_loop_calibration.py

  part1_safety_shutdown_test.txt      serial transcript of the TEST LIMIT
                                      shutdown demonstration

  heating_trace_*.csv                 at least one temperature-vs-time trace
  cooling_trace_*.csv                 for each direction, snapshotted out of
                                      tec_control_run.csv

NOTE ON SNAPSHOTS. python/tec_control_gui.py writes to
data/module_03/tec_control_run.csv and OVERWRITES it on every launch. Copy
anything worth keeping to a named file in this folder before starting the
next run. A Module 3 run was nearly lost this way.
