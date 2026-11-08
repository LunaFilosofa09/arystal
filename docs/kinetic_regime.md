# Kinetic regime: diffusion-limited or surface-limited?

Status: **surface-limited growth is the regime justified by the evidence; a regime study shows a PLATEAU in the model (results independent of Da below about 0.06), so the model now runs
in that regime (Da about 1e-2 to 1e-3 in the modes) without tuning any physical parameter; numerical optimisation (Numba, implicit and uniform-fluid schemes) made it cheap. See [regime_study.md](regime_study.md).**
The sections below are the analysis written before the study; section 9 records what was decided and measured. Updated after Luna provided Takeno, Ishido & Pritchett (2000), which contains the quartz rate
law and rate constant. Rule followed: *do not choose a regime, or tune kinetics, for computational convenience; establish what is physically
justified, document the uncertainty, and only then deal with cost (numerical optimisation first).* Numbers: `python scripts/estimate_regime.py`.

## 1. The question

A growing crystal needs (a) silica to **reach** the surface (diffusion) and (b) silica to **attach** (surface reaction). The slower step controls growth.

- **Diffusion-limited** (Da >> 1): surface almost in equilibrium with the nearby fluid, depletion halo, round or unstable shapes, face-specific attachment rates matter little.
- **Surface-limited** (Da << 1): silica is replenished much faster than it is used; supersaturation is uniform around the crystal; face-specific rates (the kinetic anisotropy) decide the shape: flat faces.
- **Feed-limited**: silica entering the cavity through the host rock limits everything (outside the closed-container model).

`Da = v_kin / v_diff`; `v_kin = Vm * k+ * (S - 1)` (surface reaction), `v_diff = D (c - c_eq) / (Cs L)` (steady diffusion to a crystal of size L; Cs = real silica capacity of quartz, about 44 mol/kg).

## 2. Evidence

| Item | What it says | Source and status |
|---|---|---|
| Quartz rate law | net precipitation per unit surface = `k+ (Q/K - 1) = k+ (S - 1)`; first order in the departure from equilibrium, neutral dilute solution, activities taken as unity | Takeno, Ishido & Pritchett (2000), eq. (1). **Read in full** (secondary source). VERIFIED as quoted there. |
| Quartz rate constant | `log10 k+ = -0.7324 - 3705.12 / T` (mol m-2 s-1, T in K), recalculated from the data revised by Rimstidt (1997); k+ = 2.6e-14 (15 C), 6.9e-14 (25 C), 2.7e-13 (40 C), 1.4e-12 (60 C) | Takeno et al. (2000), eq. (6). **Read in full**. VERIFIED as quoted. Implied activation energy 71 kJ/mol (computed here) vs 49.8 +/- 11.9 kJ/mol for the earlier all-silica-phase constant of Rimstidt & Barnes (1980) (seen only in summaries): not reconciled. |
| Quartz solubility | `log10 K = -0.0254 - 1107.12 / T` | Takeno et al. (2000), eq. (3), quoting Rimstidt (1997). **Read**. The coefficients of the model are now VERIFIED. |
| Applicability | Neutral dilute solution; pH, salinity and surface-area effects neglected | Stated by Takeno et al. (2000). Geode fluids may be alkaline (basalt-hosted), and rates rise with pH (general knowledge, not verified here). |
| Geode temperature | 15 to 60 C | Summary of Arduin Rode et al. (2024). UNVERIFIED. |
| Geode growth time | Hundreds of thousands to millions of years for large crystals | Non-scientific web pages. Very weak. |
| Silica diffusivity | about 1e-9 m2/s | ASSUMED. |

## 3. Estimate (scripts/estimate_regime.py)

Surface-reaction speed `v_kin = Vm k+ (S - 1)`; years refer to growing 10 cm (scales linearly with size).

| T (C) | S | k+ (mol m-2 s-1) | v_kin (m/s) | years for 10 cm | Da at 1 mm / 1 cm / 10 cm |
|---|---|---|---|---|---|
| 15 | 2 to 10 | 2.6e-14 | 6e-19 to 5e-18 | 5e9 to 6e8 | 2e-7 / 2e-6 / 2e-5 |
| 40 | 2 to 10 | 2.7e-13 | 6e-18 to 6e-17 | 5e8 to 6e7 | 1e-6 / 1e-5 / 1e-4 |
| 60 | 2 to 10 | 1.4e-12 | 3e-17 to 3e-16 | 1e8 to 1e7 | 3e-6 / 3e-5 / 3e-4 |

Reading of the table:
1. **Da does not depend on S** (both speeds are proportional to S - 1) and stays between 1e-7 and 3e-4 for crystals up to 10 cm. Even if the rate constant were 1000 times
   larger (for example at high pH) Da would remain below 0.3. **The conclusion "surface-limited" is robust to S, to L up to 10 cm, to D within 1-2 orders and to k+ within 2-3 orders.**
2. **Tension with geological time.** The rate law gives 1e7 to 5e9 years for 10 cm. Only the warm end (60 C) fits comfortably in the age of typical host rocks (order 1e8 years, general knowledge, not looked up here).
   At 15 C the law is too slow by one to two orders for a 10 cm crystal (a 1 cm crystal needs ten times less). Possible reasons, none verified here: alkaline fluids (faster rates), a warmer early stage,
   crystals smaller than 10 cm, fluids strongly supersaturated, growth by other mechanisms (for example crystallisation through silica gel or chalcedony precursors) or a rate constant that
   does not extrapolate to these conditions. **This tension is a reason for caution about absolute growth rates, not for the regime**: every route that speeds growth up by 1-2 orders still leaves Da << 1.
3. Da would approach 1 only for crystals of metres, or if the fluid were stagnant over very long distances.

## 4. Conclusion (with its uncertainty)

**Growth of geode amethyst crystals up to about 10 cm is surface-limited (Da between 1e-7 and 1e-3, depending on size, temperature and assumptions).** In this regime supersaturation around the crystal is
essentially the bulk value, the silica field is almost uniform, and the habit is set by the face-specific attachment rates, which is where the kinetic anisotropy matters. Remaining caveats: the rate law is from a secondary source for neutral dilute
solutions at lab conditions and is not face-specific; D, Cs and the fluid supersaturation are assumed; the absolute timescale is uncertain by two or more orders; fluid motion, replenishment and the external feed are not modelled.

**The early default kinetics (tau = 1) give Da_model of about 100, nine to ten orders of magnitude on the wrong side.** They were a provisional starting value, not a physical statement, and the shapes they produced (round crystals) are not
representative of this regime.

## 5. Provisional assumptions in the code before the regime study (kept as history; current values in section 9)

| Item | Current value | Status |
|---|---|---|
| Relaxation time tau (attachment slowness) | 1 default (`--relaxation-time`) | Provisional placeholder, Da_model ~ 100: **contradicted by the evidence**. Must be replaced by a value consistent with Da << 1. **Done**: the modes set tau on the plateau (1e4 at 200 cells across, scaled with the resolution); 1.0 remains only as the low-level default of RunConfig and `run_growth.py`, above the plateau. |
| Kinetic coupling lambda | 0.2 | ASSUMED |
| Scaled crystal capacity Cs_model | 0.002 mol/kg (real ~44) | ASSUMED. Affects how fast the closed fluid is depleted; in the surface-limited regime the diffusion speed-up no longer matters, but the depletion dynamics still depend on it (test 3 below). |
| Silica diffusivity | 1e-9 m2/s | ASSUMED |
| Closed container | as in the spec | Spec choice. |
| Face speed ratios m : r : z | 0.5 : 1 : 1 | ASSUMED (no face-specific data found) |

## 6. Decisions still open

1. **Value of Da in the model** (resolved, section 9 point 2). Physically justified range: 1e-7 to about 1e-3. Candidate approach (to be demonstrated, not assumed): show that every result that matters becomes independent of Da below some threshold
   (a plateau, expected around Da of 0.01 or lower). If so, any Da on the plateau is equivalent and can be chosen for cost without changing the physics. If no plateau appears, the real Da must be used.
2. **Mapping of the real attachment rate to tau and lambda**, including the scaled capacity. In the surface-limited regime the model time can be tied to real time through the face speed
   (`t_real = (model displacement x cell size) / v_real`), which would give the spec's time conversion an uncertainty tied to k+ rather than to the diffusion time.
3. ~~Form and units of the Rimstidt & Barnes rate law~~ **Resolved** (Takeno et al. 2000): rate per unit area is `k+ (S - 1)`. The 71 vs 50 kJ/mol question and the pH dependence are answered in section 10 (71 is k+ of quartz, 50 is k- of all silica phases; pH can speed growth by up to about 2.5 orders). Still open: Rimstidt (1997) unread, the base-term constant (two printed values), and the real fluid pH.
4. Bulk supersaturation of real geode fluids (cooling from a saturation temperature as now, versus a silica-gel or opal-saturated start). Da does not depend on it, but the growth time does. **Decided by Luna (2026-11-01), see section 11**: cooling from a saturation temperature stays the default; an amorphous-silica-saturated start is deferred until Gunnarsson & Arnorsson (2000) is read and the driving-force clip is reviewed.
5. Open (feed from outside) versus closed container. **Decided by Luna (2026-11-01), see section 11**: episodic renewal pulses, implemented as an option; the closed container stays the default.
6. The 1e7-5e9 year growth time vs rock ages (section 3, point 2): which of the candidate explanations applies. Does not change the regime. Analysed in [growth_time.md](growth_time.md): still open, candidates quantified; no candidate threatens the surface-limited regime.

## 7. Tests needed (done; results in section 9 and regime_study.md)

1. **Regime map**: run the full model over a grid of Da (vary tau at fixed everything else) from diffusion-limited (Da ~ 100) to Da ~ 1e-4 or lower, recording interface supersaturation, depletion-halo size, face positions, aspect ratio, facet sharpness, iron sector contrast.
2. **Plateau test (decides open decision 1)**: determine below which Da the outputs stop changing within a stated tolerance.
3. **Capacity-scaling test**: confirm that rescaling Cs_model leaves the dimensionless results unchanged (or quantify how the depletion dynamics change), at fixed Da.
4. **Sensitivity** of aspect ratio, face positions and iron zoning to D, lambda, Cs_model and the face speed ratios across the plausible range.
5. **Resolution convergence in the surface-limited regime** (spec check 5), including the dependence of facet sharpness on crystal size relative to the interface thickness found with the anisotropic model.
6. **Cost measurement** of the physically justified regime with the current explicit scheme and then with each optimisation below; only if it is still too slow, bring the options to Luna with the evidence, before touching any physical parameter.

## 8. Numerical optimisations to try first (in order; none changes the physics)

1. **Numba kernels** (parallel) for diffusion, phase-field and anisotropy, keeping the readable NumPy versions as reference (check 6).
2. **Implicit or semi-implicit diffusion**: the silica field relaxes far faster than the crystal grows (Da << 1), so the explicit limit dt < 0.25 is the only bottleneck; steps could be limited by interface motion instead (orders of magnitude larger). Validate against the explicit scheme where both are feasible.
3. **Quasi-steady or uniform-field limit** of the silica transport: for Da << 1 the silica field is essentially uniform with a slow depletion, so it can be solved per growth step (or replaced by a uniform value) and compared against the full time-dependent solution at moderate Da.
4. **Adaptive time stepping** from the actual interface speed.
5. **Compute only near the crystal** while keeping the full container for the mass balance.
6. Reduced precision or coarser grids only after convergence checks.

In the surface-limited regime the justified model may be *cheaper* than the earlier diffusion-limited default, because diffusion no longer sets the time step.

## 9. Outcome of the regime study (decisions, in order of the rule: justify, then measure, then optimise, only then discuss parameters)

1. **Regime**: surface-limited (Da 1e-7 to 1e-3 estimated). Unchanged by the study: it remains a leaning supported by one secondary source for the rate law and assumed D, Cs and S.
2. **Plateau** (open decision 1, tests 1 and 2): demonstrated. Shape metrics at equal size change by <= 0.4% for Da between 6e-2 and 6e-5 (aspect ratio 0.826, r/m 1.35, uniformity -> 1), against 15-245% above Da of 0.6.
   Hence any Da on the plateau is equivalent to the real one for the shape: the choice is not a tuning for convenience but a demonstrated insensitivity.
3. **Optimisations used, none changing the physics** (section 8 of this document): Numba kernels (3x single thread, 5-6x with 4-6 threads); implicit diffusion (exact to the explicit scheme, any time step); uniform-fluid limit (86x faster than the implicit solution, validated to 0.3%).
   Parameters untouched: tau was NOT chosen to be cheap; it is on the plateau (1e4 at 200 cells across, scaled with the resolution), where the result is independent of it.
4. **Mapping to real time** (open decision 2): in the surface-limited regime model time is tied to real time through the verified rate law (`time_kinetic_years` in metrics.csv). Result of the first runs: of the order of 1e7 to 1e9 years for crystals of a few millimetres to centimetres at 15-60 C,
   the same tension with the age of the rocks as in section 3 (open decision 6, still unexplained).
5. **Capacity scaling** (test 3): Cs_model changes the aspect ratio by 3-5% through the supersaturation history of the closed container; not innocent, small, and its value remains ASSUMED.
6. **Resolution convergence** (test 5): the aspect ratio is about 13% below its converged value at 200 cells across and about 2% at 800; the r/m ratio is within 0.5% at 800 (docs/regime_study.md, section 3).
7. **Cost** (test 6): with the schemes above an explore run takes seconds and a research run about a minute and a half (docs/benchmark.md). Nothing had to be discussed with Luna as a trade-off against a physical parameter.

Still open: open decisions 3 (original Rimstidt & Barnes paper, activation energy 71 vs 50 kJ/mol, pH), 4 (silica-gel start), 5 (open vs closed container) and 6 (growth time vs rock age); sensitivity of the plateau to other temperatures, sizes and face-speed ratios beyond the cases in regime_study.md.

## 10. Origin of the rate law, the activation energy, and the effect of pH (open decision 3)

Sources and how they were read (details in docs/sources.md):
- **Rimstidt & Barnes (1980)**, GCA 44, 1683-1699: the **first page of the original paper** (abstract, rate equation and table of constants) was read, from a copy on a university course page. The rest of the paper was not read.
- **Palandri & Kharaka (2004)**, USGS Open-File Report 2004-1068 (open access): equations (4)-(6), the quartz section (3.1.1.1) and Tables 3-4 were read in the PDF. Not the whole report.
- **Not accessed** (only cited inside Palandri & Kharaka or in search results): Rimstidt (1997), Brady & Walther (1990), Dove (1994), Dove & Crerar (1990), Knauss & Wolery (1988), Tester et al. (1994).

### 10.1 Where the rate constant comes from, and why 71 and 50 kJ/mol are both right

Rimstidt & Barnes (1980) write the rate as `(A/M) (k+ a_SiO2 a_H2O^2 - k- a_H4SiO4)` and give **one precipitation constant for all silica phases**:
`log k- = -0.707 - 2598/T`, with an activation energy of **49.8 kJ/mol** (first page, read). The dissolution constant of each phase follows from `K = k+ / k-`, and for quartz they give an activation energy of
61.4-76.6 kJ/mol (it varies with T because their log K has a term in T).

Takeno et al. (2000) eq. (6) is exactly the same construction with the newer solubility of Rimstidt (1997):
`log k+ = log k- + log K = (-0.707 - 2598/T) + (-0.0254 - 1107.12/T) = -0.7324 - 3705.12/T` (checked here digit by digit).
So:
- **49.8 kJ/mol** belongs to the precipitation constant k- (all silica phases).
- **71 kJ/mol** belongs to the quartz dissolution constant k+ = 49.8 + 21.2 kJ/mol, where 21.2 kJ/mol = 1107.12 x R x ln 10 is the dissolution enthalpy implied by the Rimstidt (1997) solubility.

There is **no contradiction**: the two numbers describe two different constants, and they are tied by thermodynamics. The model's law `k+ (S - 1)` is the same as
`k- K (S - 1) = k- (c - c_eq)` in molal units, so its temperature dependence for growth is 71 kJ/mol through k+ and the solubility together.
Remaining limits: the original paper states the precipitation constant is common to all silica phases (an assumption of theirs, repeated by Palandri & Kharaka for the polymorphs); Rimstidt (1997) itself was not read; the original units are relative (A/M), Takeno's are mol m-2 s-1 (conversion not re-checked).

### 10.2 An independent compilation: Palandri & Kharaka (2004)

Their rate law (eq. 6, read): `rate = SA * sum_i [ k_i(25 C) exp(-E_i/R (1/T - 1/298.15)) a_H+^n_i (1 - Omega^p)^q ]`, with p = q = 1 assumed for quartz ("The chemical affinity parameters were not determined").
Quartz, Table 4 (read from the rendered page):

| Mechanism | log k at 25 C (mol m-2 s-1) | E (kJ/mol) | n (order in H+) | Origin |
|---|---|---|---|---|
| neutral, geometric area | -13.40 | 90.9 | - | their regression of pure-water data, 25-625 C |
| neutral, BET area | -13.99 | 87.6 | - | same |
| base | -16.29 (at pH 0) | "108366" (printed in a kJ/mol column; 108.4 kJ/mol is meant) | -0.5 | Knauss & Wolery (1988), "A adjusted here from 491 to 10" |

Two inconsistencies in the printed table, not resolved here: (1) the base E is printed as 108366 under kJ/mol; (2) log k = -16.29 is what A = **491** gives with E = 108.4 kJ/mol; A = 10 (the adjusted value of the footnote) gives **-17.98**. Both are carried below.
Acid: "dissolution rates are apparently independent of pH" in the acidic region (their text, citing Dove 1994, Knauss & Wolery 1988, Rimstidt & Barnes 1980). Base: rate grows as `a_H+^-0.5`, i.e. **x3.16 per pH unit**.
They also note that sodium (and Li, K, Mg, Ca, Ba) catalyses the base mechanism (Dove and co-workers); not included in their table and not here.

At 25 C their neutral constant (-13.40) is 0.57 times Takeno's (-13.16); across 15-60 C the two neutral laws differ by less than a factor 2.5 (their activation energies differ: 90.9 vs 71 kJ/mol).

### 10.3 Plausible pH of geode fluids

No pH measurement of a geode-forming fluid was found. Present-day groundwater of the Serra Geral basalt aquifer (Brazil) is reported as neutral to alkaline: pH 6.69-9.95 (57 wells, SW Parana) and 6.9-9.7 (Sao Paulo), from search summaries of articles in Revista Aguas Subterraneas (UNVERIFIED, abstracts only). Present-day groundwater is not the fluid that grew the amethyst; the range 7-10 is used here only as a plausible bracket.

### 10.4 Effect on Da and on growth time (scratch calculation; same method and inputs as section 3, S = 2 and 10, D = 1e-9 m2/s, Da for a 10 cm crystal)

| Law | 15 C: years for 10 cm (S=2 / S=10) | 15 C: Da | 40 C: years | 40 C: Da | 60 C: years | 60 C: Da |
|---|---|---|---|---|---|---|
| Takeno 2000 (current model) | 5.4e9 / 6.0e8 | 2e-5 | 5.1e8 / 5.7e7 | 1e-4 | 1.0e8 / 1.1e7 | 3e-4 |
| P&K neutral only | 1.3e10 / 1.4e9 | 8e-6 | 6.1e8 / 6.7e7 | 8e-5 | 7.4e7 / 8.3e6 | 4e-4 |
| P&K neutral + base, pH 7 | 3.0e9 / 3.3e8 | 3e-5 | 9.0e7 / 1.0e7 | 6e-4 | 7.8e6 / 8.7e5 | 4e-3 |
| P&K neutral + base, pH 8 | 1.1e9 / 1.3e8 | 9e-5 | 3.2e7 / 3.5e6 | 2e-3 | 2.7e6 / 3.0e5 | 1e-2 |
| P&K neutral + base, pH 9 | 3.8e8 / 4.2e7 | 3e-4 | 1.0e7 / 1.2e6 | 5e-3 | 8.6e5 / 9.6e4 | 4e-2 |
| P&K neutral + base, pH 10 | 1.2e8 / 1.4e7 | 8e-4 | 3.3e6 / 3.7e5 | 1.5e-2 | 2.7e5 / 3.1e4 | **0.11** |
| same, pH 10, base log k = -17.98 | 4.1e9 / 4.5e8 | 3e-5 | 1.3e8 / 1.4e7 | 4e-4 | 1.1e7 / 1.3e6 | 3e-3 |

Reading:
1. **Growth time**: an alkaline fluid can shorten the growth time by up to about **2.5 orders of magnitude** (60 C, pH 10, with the larger base constant), down to 1e4-1e5 years for 10 cm, within geological time. With the smaller base constant the gain is only about one order. The pH is therefore a candidate explanation of the time tension of section 3 (open decision 6), **not a demonstrated one**.
2. **Regime**: Da stays below the plateau threshold (about 0.06, docs/regime_study.md) in every case **except** 60 C, pH 10, larger base constant, 10 cm crystal (Da about 0.1, between the plateau and the diffusion-limited range). For crystals of 1 cm Da is ten times smaller (0.01) and on the plateau. The real D at 60 C is probably larger than 1e-9 m2/s (Rebreanu et al. 2008 report a factor 2-3 between 2 and 30 C; not extrapolated), which would lower Da. **Conclusion: "surface-limited" still holds for geode crystals up to about 1 cm in all cases, and up to 10 cm except at the warm, most alkaline corner, where it becomes marginal.**
3. Caveats: the base term was measured for **dissolution** far from equilibrium; using it for precipitation near equilibrium assumes p = q = 1 (as Palandri & Kharaka do), not verified for quartz growth. Sodium catalysis is ignored. The pH of the real fluid is unknown.

### 10.5 Implementation (approved by Luna and implemented)

- New material entries: `kinetics.quartz_rate_neutral_log10_k25` (-13.40), `kinetics.quartz_rate_neutral_activation_energy` (90.9 kJ/mol), `kinetics.quartz_rate_base_log10_k25` (-16.29 or -17.98: to be decided), `kinetics.quartz_rate_base_activation_energy` (108.4 kJ/mol), `kinetics.quartz_rate_base_order_in_h_plus` (-0.5); status VERIFIED as printed in Palandri & Kharaka (2004), with the inconsistency noted.
- New run parameter `fluid_ph` (default 7, range 7-10, UNVERIFIED), not changeable during a run at first.
- New engine function `compute_rate_constant(temperature_celsius, ph, material) -> float` returning the sum of the neutral and base terms, with the current Takeno law kept as an option for comparison.
- Implemented as above: `engine/ph_rate_law.py`, run option `--fluid-ph` (None = Takeno law, so old runs are unchanged), validation check 4b `ph_rate`. The base constant used is the printed -16.29.
- In the model, pH changes **only** the conversion to real time (`time_kinetic_years`) and the Da indicator: on the plateau the shape does not depend on the absolute rate. It would not change any simulated shape unless Da left the plateau.
- Validation: a check that the function reproduces Table 4 of Palandri & Kharaka at 25 C (log k = -13.40 at pH 7 for the neutral term, slope 0.5 per pH unit for the base term).

## 11. Open decisions 4 and 5: container and initial fluid (decided by Luna, 2026-11-01)

Evidence:
- **Mass balance** (computed here from the verified solubility and density): cooling a quartz-saturated fluid from 60 to 15 C deposits quartz equal to about 0.0007% of the cavity volume;
  a fluid saturated with amorphous silica, about 0.004%. Filling a geode therefore needs of the order of 1e4-1e5 cavity volumes of fluid. A closed cavity with the real crystal capacity cannot grow a geode;
  the model's closed container works only because Cs_model is 22000x smaller than real (materials/amethyst.yaml).
- Arduin Rode et al. (2024), abstract only: "combination of open- and closed-system crystallisation ... due to the episodic infiltration of meteoric water".
- Gilg et al. (2014), title only: fluids from "low-temperature sedimentary brines". Chalcedony before amethyst in the mineral sequence (search summary, UNVERIFIED).
- Amorphous silica solubility 8-11x that of quartz at 15-60 C (Gunnarsson & Arnorsson 2000 equation seen in a search summary, UNVERIFIED).

Demonstration (explore size, uniform fluid, scratch code, crystal grown to radius 30 cells at 20 C): open (renewed every step) vs closed: shape unchanged, time x1.3 shorter; amorphous-saturated start (S0 11): aspect +2.5%,
time x7 shorter, Fe/Si of the crystal 4x lower (more silica per unit of iron), sector contrast unchanged. Above S of about 4.5 the phase-field driving force is clipped (max_driving_force), the real-time conversion is not.

**Decision:**
- **Container (decision 5): episodic renewal pulses**, as an option. A pulse replaces the fluid by fluid saturated with quartz at a chosen temperature, carrying the current fluid iron
  (`engine/live_changes.py: renew_fluid`). Two ways: a timeline event `fluid_renewal_saturation_celsius` (live, server, replay) and periodic pulses from the run settings (`renewal_interval`, `renewal_saturation_celsius`; CLI `--renewal-interval`, `--renewal-saturation`).
  Silica and iron added are counted, so the conservation checks still close (renewal check: balance 1e-14). The closed container stays the default so that earlier results are unchanged.
- **Initial fluid (decision 4): cooling from a saturation temperature stays the default.** A start saturated with amorphous silica is the factor that would help the growth-time tension most (x7, growth_time.md),
  but it is deferred until Gunnarsson & Arnorsson (2000) is read and the clip of the driving force above S of about 4.5 is reviewed (it would hide most of the extra supersaturation from the phase field).
- Still open: the real frequency and composition of the pulses; with renewals the depletion of the closed container no longer limits the size, so Cs_model matters less, but it is still ASSUMED.

