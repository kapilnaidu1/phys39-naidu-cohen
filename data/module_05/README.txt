Module 5 raw data. Naidu / Cohen.

  p_control_run.csv    live file written by python/tec_p_control_gui.py.
                       OVERWRITTEN ON EVERY LAUNCH. Snapshot anything worth
                       keeping before the next run:
                         cp data/module_05/p_control_run.csv \
                            data/module_05/kp_2p00_run.csv

  droop.csv            one row per gain, filled in by hand from the runs.
                       Input to python/plot_droop.py.
                         kp,setpoint_c,final_t_c,final_pwm,notes

  kp_*_run.csv         retained traces, one per gain. Keep at least one
                       low-gain and one high-gain trace; the assignment asks
                       for representative examples of each.

A Module 3 run was nearly lost to the overwrite. Snapshot as you go.
