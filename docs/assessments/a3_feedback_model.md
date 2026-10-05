# A3: Feedback Data and Lumped-Model Memo

**Team:** Naidu / Cohen
**Type:** team, 10 points
**Moodle file:** `A3_Naidu_Cohen.pdf`, each of us uploads the same PDF separately
**Repository file:** this one, `docs/assessments/a3_feedback_model.md`

> **Due date is inconsistent on the course site.** The Module 6 page says
> Wednesday 21 October, 6:00 PM. The
> [session calendar](https://sethfraden.github.io/Phys39F26-course/labs/)
> puts A3 at S13, **Wednesday 14 October**, and uses 21 October for the C4
> checkoff instead. A2 already moved once by email, so **work to 14 October**
> and confirm with the instructor.

Working notes this draws on:

- [`module_04_open_loop_tec.md`](../module_notes/module_04_open_loop_tec.md), susceptibility
- [`module_05_p_control.md`](../module_notes/module_05_p_control.md), droop and the three interpretation answers
- [`module_06_pi_modeling.md`](../module_notes/module_06_pi_modeling.md), time constant, simulations, windup

> The assembly is selection and writing, not new analysis. Everything below
> already exists; A3 is choosing from it and adding the short interpretation.

---

## The ten required items, and where each already lives

| # | Required | Where it is now |
|---|---|---|
| 1 | Derivation of the P-control droop equation | Module 6 note sections 1 and 6 |
| 2 | The three Module 5 interpretation answers, **integrated with the derivation and the droop data rather than repeated separately** | Module 5 note section 6 |
| 3 | Estimate of &chi;<sub>T,u</sub> | 0.50127 &deg;C/count, Module 4 heating branch |
| 4 | Estimate of &tau; | 62.9 &plusmn; 5.0 s, Module 6 section 3, `python/estimate_tau.py` |
| 5 | Open-loop simulation against one measured trace | `docs/figures/module_06/open_loop_sim_vs_measured.png` |
| 6 | P-only simulation against the Module 5 droop data | `docs/figures/module_06/p_control_sim.png` |
| 7 | PI simulation against P-only | `docs/figures/module_06/pi_vs_p_sim.png` |
| 8 | Why the one-lump model does or does not oscillate | Module 6 section 6 |
| 9 | Windup thought-experiment answers | Module 6 section 8 |
| 10 | Link to the pushed Git checkpoint | **TO FILL IN after pushing** |

Item 2 is the one most easily got wrong: the page asks for those answers
*woven into* the derivation and the droop data, not appended as a separate
block.

---

## Rubric, and what carries each line

| Criterion | Points | What we have for it |
|---|---|---|
| P-control droop and instability evidence is quantitative and reproducible | 2 | Droop at eight gains, mean measured/predicted 1.003 &plusmn; 0.017; the K<sub>p</sub> = 32 overshoot, 0.041 &deg;C against a 0.020 &deg;C noise floor |
| One-lump balance, steady state, time constant, parameters and units correct; interpretation covers why droop is needed, &chi; = P<sub>u</sub>/H, and dimensionless gain | 2 | Module 6 sections 1 to 3; Module 5 section 6 answers all three |
| **P and PI use comparable conditions and quantitative transient metrics** | 2 | Same K<sub>p</sub> = 2, same setpoint, same start; droop, overshoot, settling time and &zeta; tabulated |
| **Integral action, anti-windup, thermal lag, and a model limitation explained** | 2 | Module 6 sections 6 to 8. All four, not three |
| PDF, code, data links and cited Git checkpoint clear and on time | 2 | Paths below; checkpoint still to add |

Two rubric lines are worth reading carefully. The third wants **comparable
conditions**: P and PI must be run at the same gain and setpoint, which ours
are, so the comparison is of the controller and nothing else. The fourth wants
**four** things, and "a model limitation" is separate from thermal lag.

---

## Numbers, one place

| Quantity | Value | Source |
|---|---|---|
| &chi;<sub>T,h</sub> | 0.50127 &deg;C per PWM count | Module 4, R<sup>2</sup> = 1.0000 |
| &#124;&chi;<sub>T,c</sub>&#124; | 0.18091 &deg;C per PWM count | Module 4, R<sup>2</sup> = 0.9989 |
| &tau; | 62.9 &plusmn; 5.0 s | 8 steps fitted, Module 6 section 3 |
| T<sub>amb</sub> | 21.54 &deg;C | Module 4 zero-command steady state |
| Noise floor | 0.16 &deg;C p-p open loop, 0.02 &deg;C closed | Modules 4 and 5 |
| Setpoint used throughout | 30.0 &deg;C, e<sub>0</sub> = 8.46 &deg;C | Module 5 |
| Droop agreement | mean 1.003, sd 0.017, 8 gains | Module 5 section 3 |
| K<sub>p</sub> = 32 overshoot | 0.041 &deg;C at t = 7 s | Module 5 section 5 |
| Open-loop model rms residual | 0.147 &deg;C driven, 0.094 &deg;C passive | Module 6 section 4 |
| Windup, limit 50 counts | +1.46 &deg;C plain, +0.26 &deg;C anti-windup | Module 6 section 7 |

---

## The argument, in the order it should be told

1. Module 4 measured &chi;. Module 5 closed the loop and found droop that
   1/(1+L) predicts to 0.3% on average with no fitting.
2. The same measurement gives &tau; = 62.9 s, so the model has both
   parameters it needs and still none are free.
3. Simulated open loop lands within 0.02 &deg;C of two measured steps.
4. Simulated P reproduces the measured droop across a 32-fold gain range.
5. PI removes the droop entirely, at the cost of overshoot once &zeta; < 1.
6. **The model is wrong in two places, and we can say where.** The P-only
   model forbids overshoot; ours overshoots at K<sub>p</sub> = 32. The
   open-loop residuals are structured rather than random. Both point at a
   second thermal mass.
7. Windup is a real failure mode but not one this apparatus can reach:
   holding 45 &deg;C needs 47 of 255 counts.

Point 6 is the memo's strongest content and should not be buried. A model that
fits everything says nothing; this one fits the steady state and fails the
transient in a specific, measured way.

---

## Assembly

1. Push, then paste the commit hash into item 10 above and into the PDF.
2. Build the PDF with a script modelled on `python/build_a2_pdf.py`, which
   already carries the A1 house style, into `docs/A3_Naidu_Cohen.pdf`.
3. Both of us upload it to Moodle separately.

**Do not repeat** apparatus descriptions, circuit sketches, the safety
demonstration, or code documentation, the same exclusions A2 had.

---

## Open items to resolve or declare

- Thermal lag and discrete sampling cannot be separated at a 1.97 Hz log rate.
  Declare it rather than picking one silently; a faster log is a Part II
  measurement.
- `sampleCount` was 500 for all Module 5 data, where Modules 4 and 5 ask for
  about 1000. Inside the 100 to 1000 band Module 6 Part 3 quotes. Restore 1000
  before the next run.
- Saturation was never reached on the real apparatus, so every clamped result
  here is simulated.
