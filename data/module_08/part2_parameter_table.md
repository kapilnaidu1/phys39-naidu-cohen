| Quantity | Value | Uncertainty | Unit | Source |
|---|---|---|---|---|
| Forcing periods | 100, 180, 240, 300, 480 | exact (Arduino clock) | s | run files, `angstrom_tec.ino` |
| ω = 2π/period | 0.0628, 0.0349, 0.0262, 0.0209, 0.0131 | exact | rad/s | from the period |
| Sensor positions T1 to T5 | 0, 25.4, 50.8, 76.2, 101.6 | T1 0 (defines x = 0); T2 to T5 ±1 each | mm | tape 28 Oct, calipers 10 Nov; `sensor_map.csv` |
| Diameter D | 12.757 | 0.006 | mm | calipers, 3 readings; `rod_geometry.csv` |
| Radius R = D/2 | 6.378 | 0.003 | mm | from D |
| Area A = πR² | 127.82 | 0.12 | mm² | from D |
| Perimeter P = πD | 40.08 | 0.02 | mm | from D |
| A/P = R/2 | 3.1892 | 0.0015 | mm | from D |
| Analysis length L (T1 hole to tip) | 281.9 | 1.3 | mm | ruler; `rod_geometry.csv` |
| q, q′: 2 Nov 100 s (5 settled cycles) | 18.60, 17.54 | 0.39, 0.72 (stat) | 1/m | finite-rod fit of `angstrom_fit_angstrom_live_20261102_094506_PI_100s.csv` |
| q, q′: 2 Nov 480 s (5 settled cycles) | 9.09, 7.75 | 0.24, 0.17 (stat) | 1/m | finite-rod fit of `angstrom_fit_angstrom_live_20261102_094506_PI_480s.csv` |
| q, q′: 4 Nov 180 s (5 settled cycles) | 13.97, 13.52 | 0.38, 0.39 (stat) | 1/m | finite-rod fit of `angstrom_fit_angstrom_live_20261104_092527_PI_180s.csv` |
| q, q′: 4 Nov 240 s (5 settled cycles) | 12.44, 11.37 | 0.20, 0.28 (stat) | 1/m | finite-rod fit of `angstrom_fit_angstrom_live_20261104_092527_PI_240s.csv` |
| q, q′: 4 Nov 300 s (6 settled cycles) | 11.05, 10.22 | 0.20, 0.25 (stat) | 1/m | finite-rod fit of `angstrom_fit_angstrom_live_20261104_110306_PI_300s.csv` |
| q, q′: 10 Nov 480 s (3 settled cycles) | 9.29, 7.94 | 0.16, 0.29 (stat) | 1/m | finite-rod fit of `angstrom_fit_sammy_angstrom_live_20261110_164057_PI_480s.csv` |
| q, q′: 10 Nov 240 s (6 settled cycles) | 12.53, 11.58 | 0.24, 0.19 (stat) | 1/m | finite-rod fit of `angstrom_fit_sammy_angstrom_live_20261110_164057_PI_240s.csv` |
| q, q′: 10 Nov 100 s (3 settled cycles) | 18.72, 18.21 | 0.39, 0.24 (stat) | 1/m | finite-rod fit of `angstrom_fit_sammy_angstrom_live_20261110_164057_PI_100s.csv` |
| q, q′: 11 Nov 480 s (6 settled cycles) | 9.25, 7.91 | 0.34, 0.22 (stat) | 1/m | finite-rod fit of `angstrom_fit_angstrom_live_20261111_094735_PI_480s.csv` |
| κ = ω/(2qq′) | 9.17 | 0.10 stat, 0.18 total (χ² 3.1/8) | 10⁻⁵ m²/s | derived, weighted over 9 windows |
| ν = κ(q² − q′²) | 2.02 | 0.23 stat, 0.25 total (χ² 1.4/8) | 10⁻³ 1/s | derived, weighted over 9 windows |
| ρ (6061-T6) | 2700 | none cited yet | kg/m³ | handbook value used in A4 and A5; source to confirm |
| c (6061-T6) | 896 | none cited yet | J/(kg K) | handbook value used in A4 and A5; source to confirm |
| k = κρc | 222 | 2 stat, 4 total (χ² 3.1/8) | W/(m K) | derived |
| h = νρcA/P | 15.6 | 1.8 stat, 1.9 total (χ² 1.4/8) | W/(m² K) | derived |
| k, literature (6061-T6) | 167 (166 to 172 over 0 to 100 °C) | | W/(m K) | Lienhard, *A Heat Transfer Textbook*, Table A.1, as cited in A4 |
