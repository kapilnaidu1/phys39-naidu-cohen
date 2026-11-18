#!/usr/bin/env python3
"""
Phys 39 Module 8, Part I: numerical TEC-rod simulation (focused P/PI simulation and the matched comparison of A5).  SAMMY.

A one-lump TEC plate with the controller of angstrom_tec(_sammy).ino, coupled through a contact conductance G_c to a finite
insulated-tip rod:

    plate  C dTp/dt = H chi(u) u - H (Tp - Tinf) - G_c (Tp - T(0))          chi = chi_h for u > 0, chi_c for u < 0
    rod    dT/dt = kappa d2T/dx2 - nu (T - Tinf),   -kA dT/dx(0) = G_c (Tp - T(0)),   dT/dx(L) = 0

Controller, once every dt_c: e = setpoint - Tp; P: u = Kp e; PI: q += e dt_c unless the command would be pushed further out of
+-255 (conditional integration), u = Kp e + Ki q; a negative command is multiplied by r = chi_h / chi_c; rounded and clamped to
+-255 counts and held until the next step. Explicit finite differences; numpy only.

Provenance of the inputs (see the A5 text): the plate numbers are the measured Module 4 and Module 6 ones, kappa and nu are the
Angstrom fits, G_c is fitted to the T1 to TEC amplitude ratio and lag, rho c is the handbook value.
"""

import math

import numpy as np

CHI_H, CHI_C = 0.50127, 0.18091          # degC per PWM count (Module 4)
C_PLATE, H_PLATE = 74.0, 1.176           # J/K, W/K (Module 6 one-lump numbers; tau = C/H = 62.9 s)
R_COOL = CHI_H / CHI_C                   # 2.771
MAX_DUTY = 255
RHO_C = 2700.0 * 896.0                   # J/(m3 K), handbook 6061-T6 (assumed)
RADIUS = 6.378e-3                        # m, calipers
AREA = math.pi * RADIUS ** 2
L_ROD = 0.2819                           # m, T1 hole to rod top
X_SENSORS = np.array([0.0, 0.0254, 0.0508, 0.0762, 0.1016])


def command(mode, kp, ki, e, q, dt):
    """The sketch's control step: returns (applied PWM, new integral)."""
    comp = lambda v: v if v >= 0 else R_COOL * v
    if mode == "P":
        u = kp * e
        q = 0.0
    else:
        q_trial = q + e * dt
        u_trial = comp(kp * e + ki * q_trial)
        if not ((u_trial > MAX_DUTY and e > 0) or (u_trial < -MAX_DUTY and e < 0)):
            q = q_trial
        u = kp * e + ki * q
    return int(round(max(-MAX_DUTY, min(MAX_DUTY, comp(u))))), q


def simulate(setpoint, t_end, t_amb, tp0, rod0=None, mode="PI", kp=12.0, ki=0.2, kappa=9.26e-5, nu=1.74e-3, g_c=None,
             tau_s=0.0, dx=0.004, dt_c=0.54, sub=14, t_start=0.0):
    """Closed loop from t_start to t_end. setpoint(t) in degC. rod0 = (x_m, T_C) initial rod profile (None: room T), g_c = contact
    conductance in W/K (None: plate alone), tau_s = first-order lag of the rod thermistors in s (output only). Returns arrays t, Tp,
    T (len(t) x 5 at the sensor positions, after the sensor lag), u (applied counts)."""
    n = int(round(L_ROD / dx))
    x = np.arange(n + 1) * dx
    rod = np.full(n + 1, float(t_amb))
    if rod0 is not None:
        rod = np.interp(x, rod0[0], rod0[1])
    tp, q = float(tp0), 0.0
    sens = np.interp(X_SENSORS, x, rod)
    lag = 1.0 if tau_s <= 0 else 1.0 - math.exp(-dt_c / tau_s)
    h = dt_c / sub
    a = kappa / dx ** 2
    gc_node = 0.0 if not g_c else 2.0 * g_c / (RHO_C * AREA * dx)
    steps = int(round((t_end - t_start) / dt_c))
    out_t, out_tp, out_rod, out_u = [], [], [], []
    for k in range(steps):
        t = t_start + k * dt_c
        u, q = command(mode, kp, ki, setpoint(t) - tp, q, dt_c)
        chi = CHI_H if u > 0 else CHI_C
        p_in = H_PLATE * chi * u
        for _ in range(sub):
            lap = np.empty_like(rod)
            lap[1:-1] = rod[2:] - 2.0 * rod[1:-1] + rod[:-2]
            lap[0] = 2.0 * (rod[1] - rod[0])
            lap[-1] = 2.0 * (rod[-2] - rod[-1])
            d_rod = a * lap - nu * (rod - t_amb)
            flow = 0.0
            if g_c:
                flow = g_c * (tp - rod[0])
                d_rod[0] += gc_node * (tp - rod[0])
            d_tp = (p_in - H_PLATE * (tp - t_amb) - flow) / C_PLATE
            rod += h * d_rod
            tp += h * d_tp
        out_t.append(t + dt_c)
        out_tp.append(tp)
        sens = sens + lag * (np.interp(X_SENSORS, x, rod) - sens)
        out_rod.append(sens.copy())
        out_u.append(u)
    return np.array(out_t), np.array(out_tp), np.array(out_rod), np.array(out_u)


def rod_admittance(kappa, nu, w, length=L_ROD):
    """kA s tanh(sL): heat flow per kelvin of oscillating base temperature, finite insulated-tip rod (W/K, complex)."""
    s = np.sqrt((nu + 1j * w) / kappa)
    s = s if s.real > 0 else -s
    return RHO_C * kappa * AREA * s * np.tanh(s * length)


def base_ratio(g_c, kappa, nu, w, tau_s=0.0):
    """Complex T1/Tplate = 1 / (1 + Y_rod / G_c) for a contact conductance G_c in series with the rod, times the thermistor lag."""
    return 1.0 / (1.0 + rod_admittance(kappa, nu, w) / g_c) / (1.0 + 1j * w * tau_s)
