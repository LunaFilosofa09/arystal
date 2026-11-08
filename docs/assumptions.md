# Assumptions and simplifications

Every simplification of the physics and every ASSUMED value goes here.

## Simplifications (from the Phase 1 scope)

1. **2D only**: a single longitudinal section parallel to the c-axis. A real crystal is 3D.
2. **Pure-water fluid**: salinity set to 0 so that the pure-water solubility curve applies.
   Real Uruguayan geode fluids reach ~3 wt% NaCl-eq (UNVERIFIED).
3. **Time is non-dimensional** inside the engine. The conversion to physical time and its
   uncertainty are documented in physics_model.md (real geode growth is geological).
4. **Color is computed from incorporated iron** with an assumed mapping.
   Real amethyst color also needs natural irradiation (Cohen & Hassan 1974), so iron content
   is not linearly related to color.

5. **Scaled crystal capacity**: the crystal holds ~22000x less silica than real quartz, to get a visible crystal in a closed container. Model time is therefore not physical time (see physics_model.md).
6. **Constant temperature during a run** (apart from the live changes) and a fluid that starts exactly saturated at a chosen "saturation temperature".
7. **Driving force = lambda * ln(c / c_eq)**, clipped to +-0.3, with lambda assumed.
8. **Solid fraction h(phi)** smooth-step interpolation and diffusion blocked inside the crystal (standard phase-field choices).
9. **Mass-conservation check is partly by construction**: the update is written so silica can only move or be exchanged with the crystal. The check verifies the code really does that (no leaks, no negative concentrations), not that the physics is right.

10. **Kinetic (not surface-energy) anisotropy** gives the facets; see physics_model.md for what is imposed vs predicted.
11. **Section plane contains c and an m pole**, so r is on the right and z on the left; equal r and z speeds are assumed (mirror-symmetric section).
12. **Noise and seed variation**: interface noise sigma = 0.02, seed radius +-5%, seed position +-1 cell, all ASSUMED and uncalibrated. The spread between seeds is therefore not a prediction of the natural variability of crystals.
13. **Lower faces are mirror images of the upper ones**, only so that g is defined for all directions; the crystal is attached to the wall there.
14. **Growth regime** (found with the anisotropic model, resolved by the regime study): at the early default kinetics (tau = 1) the coupled model is diffusion-limited and shows round crystals, contradicting the evidence (real growth is surface-limited, Da ~ 1e-7 to 1e-3). The regime study showed a plateau (shape independent of Da below about 0.06, for the cases tested) and the modes run on it; see [regime_study.md](regime_study.md) and [kinetic_regime.md](kinetic_regime.md), section 9. The low-level default `relaxation_time = 1.0` (RunConfig, `run_growth.py`) is kept for compatibility and lies above the plateau. Remaining limits of the plateau: point 30.

15. **Iron is a passive trace** (no effect on growth, solubility or silica budget) and is incorporated by a molar Fe/Si distribution coefficient per sector.
16. **Sector = surface-normal direction**, with a smooth 12 deg Gaussian transition between faces; real sector boundaries are sharp.
17. **Colour law**: saturating in the crystal Fe/Si with scale 4e-4; uniform and sufficient irradiation assumed; Dauphine twinning ignored.
18. **Rendering** rounds the picture to 8 bits itself (otherwise plotting libraries truncate tiny interface tails into a faint halo; found and fixed during development).
19. **Seed carries no iron** (colourless nucleus): the composition of the first nucleus is unknown.

20. **Mass** = 2D area x assumed thickness (10 mm) x real density: order of magnitude only; not the silica budget of the scaled model.
21. **Bulk supersaturation** is measured at the top row of the container, the part farthest from the crystal.
22. **Face growth rate** in a non-faceted crystal is the support-distance rate in that direction (see physics_model.md).

23. **Instantaneous temperature jump** and **fluid-renewal iron change** as the live controls: modelling choices, not claims about real geodes.
24. **Surface exchange with noise**: deposit/release cycles driven by the (ASSUMED) interface noise mix the iron composition at fine scale (see physics_model.md, live changes).
25. **Explore size**: the live window uses a 200 x 100 grid; the explore and research modes set the resolution (200 x 100 and 800 x 400; docs/validation_report.md, section 4).

26. **Ensemble spread** is set by the assumed noise and seed-variation amplitudes (see 12); with 10 replicas the standard deviation itself is uncertain (about 22% for a normal distribution).
27. **Parallel cost**: 5 workers did not give 5x; measured about 2.2x on this machine. Measured again with the Numba code: about 3.7x with 5 workers ([benchmark.md](benchmark.md)).

28. **Server is for local use only** (127.0.0.1, no accounts, no encryption); the job list is in memory; at most 3 active jobs; frames at about 4 per second and downsampled to at most 400 columns.
29. **Files use `null` for "not available"** (JSON has no NaN); older files with NaN are still read.

30. **Modes and plateau**: the regime of the modes (Da about 1e-2 to 1e-3, uniform fluid) is justified by the regime study for the cases tested (one geometry; T 20 and 40 C); other conditions may move the plateau.
31. **Kinetic time conversion**: the quartz rate constant (neutral dilute solution, secondary source) is assumed to apply to the fastest face family and the geometric surface; uncertain by at least two orders of magnitude. The result (1e7-1e9 years) is in tension with the age of host rocks: unresolved.
32. **Explore resolution is not converged** for absolute shape: the aspect ratio is about 13% below its converged value (2% at research resolution). Trends between runs at the same resolution are more reliable than absolute values.
33. **Replaying a run bit for bit** needs the same backend (numba or reference) and the same library versions; the two backends agree to about 1e-15 per step, not bitwise.
34. **Uniform fluid scheme** drops the transport of dissolved species (valid for Da much smaller than 1): no depletion halo, no slow-supply effect.

35. **pH-dependent rate law** (optional): the base term measured for quartz dissolution is applied to growth (p = q = 1, as assumed by Palandri & Kharaka 2004); a_H+ = 10^-pH (activity coefficient 1); the printed base constant is used although the source is inconsistent (-16.29 vs -17.98, a factor of about 50); sodium catalysis ignored; the fluid pH (7-10 allowed) is UNVERIFIED; the pH is constant during a run. It changes only time_kinetic_years.

36. **Fluid renewal pulses** (optional; kinetic_regime.md section 11): instantaneous and complete replacement of the fluid by fluid saturated with quartz at a chosen temperature, with the current fluid iron; the crystal is not touched; frequency and composition ASSUMED (no source gives them). The closed container remains the default; a closed cavity with the real crystal capacity could not grow a geode (mass balance), so the closed model relies on the scaled Cs_model.
37. **Initial fluid**: cooling from a quartz saturation temperature (default, unchanged). An amorphous-silica-saturated start is not implemented (deferred, section 11).

## ASSUMED values (no source found yet)

| Value | Where | Why |
|---|---|---|
| Silica diffusivity 1e-9 m2/s | `transport` | Order of magnitude only; since cited (Rebreanu et al. 2008). |
| Iron partition coefficients r=0.01, z=0.005, m=0.001 | `iron` | Only the ordering r > z is supported (qualitatively) by literature; magnitudes and m are placeholders. |
| Density 2.65 g/cm3, molar mass 60.0843 g/mol | `thermodynamics` | Textbook values, not looked up. |
| Solid capacity Cs = 0.002 mol/kg, lambda = 0.2, max driving force 0.3 | `model_scaling` | Model choices, see above. |
| Face speeds m : r : z = 0.5 : 1 : 1, cusp sharpness 40 | `anisotropy` | No quantitative growth-rate ratios found. IMPOSE the habit. |
| Iron: coefficients r/z/m = 0.01 / 0.005 / 0.001, fluid iron 1 ppm, D ratio 0.7, sector width 12 deg, colour scale 4e-4, iron molar mass | `iron`, `iron_model` | No measured values found; only the order r > z > m is literature-supported (qualitatively). |
| Noise sigma 0.02, seed radius variation 5%, seed offset 1 cell, assumed thickness 10 mm | `stochastic`, `mass_estimate` | Modelling devices, not calibrated. |
| Interface width 6 grid cells | `phase_field_model` | Common numerical practice; its effect is part of the resolution convergence study (check 5): the shape converges slowly as the interface becomes thinner relative to the crystal. |

## Literature items NOT verified (only abstracts / summaries seen)

Rimstidt 1997 coefficients, Levien et al. 1980 lattice parameters, Arduin Rode et al. 2024
temperature range, Rimstidt & Barnes 1980 rate constant, Debierre et al. 2003.
