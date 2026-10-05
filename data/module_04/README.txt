Module 4 raw data. Naidu / Cohen.

  full_run.csv              THE primary record. 4906 rows over 2497 s.
                            Contains the zero-command baseline and seven of
                            the eight driven steps. It does NOT contain the
                            heat-50 (46.6 C) step: the plate
                            never exceeds 40.48 C in this file, and no other
                            file here has that run.

  steady_state_from_raw.csv every step recomputed from full_run.csv by
                            python/steady_state_from_raw.py: final-minute
                            reading, drift, whether it met the 0.16 C
                            criterion, and the extrapolated asymptote for
                            several fitting windows.

  steady_state.csv          the ten steady-state points, one row each, with
                            how each value was obtained. Input to
                            python/plot_open_loop_calibration.py

  cooling_trace_01.csv      753 rows, 384 s, 22.88 -> 4.81 C. The cooling
                            trace, including the 110-then-65 step.

  part1_safety_shutdown_test.txt   the software-limit demonstration

NOTE. This folder previously held tec_run.csv, the live file the GUI wrote
to. It was removed: cooling_trace_01.csv was once overwritten by copying
tec_run.csv at a moment when the GUI had just restarted and the live file
held four rows, and the good version had to be recovered from git. The GUI
now writes to data/module_05/ instead, so nothing in this folder is live.

Snapshot immediately after a run, and check the row count before committing.
