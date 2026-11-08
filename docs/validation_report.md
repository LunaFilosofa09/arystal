# Validation report

Phase 1 of Arystal: a 2D phase-field engine for amethyst growth in a geode. This report says, for every check, **what it shows and what it does not show**,
what is **imposed by assumption** and what is **predicted** by the model, and what remains open. Luna has no expert to review the science, so the checks and this report are the safeguard;
nothing here has been compared with a real crystal.

Run everything with `python scripts/validate.py all` (about 30 minutes); each check can be run alone (`python scripts/validate.py <name>`).
66 judged tests in 14 checks, plus 3 reported measurements.

## 1. Summary of the checks

| Check (name) | Tests | What it shows | What it does NOT show |
|---|---|---|---|
| 1 `isotropic` | 3 | Without anisotropy the crystal is a smooth half-disc (0.42% spread) and grows at the speed theory predicts (0.73% difference) | That the physics of silica transport or kinetics is right |
| 2 `symmetry` | 3 | Mirror symmetry about the c-axis when r = z (3e-16); it breaks when r and z differ; flat faces sit where Frank's construction puts them (1.9% m, 3.6% r and z) | That real amethyst has the assumed face speeds; the apex stays rounded (15% low) |
| 3 `mass` | 2 | Silica is conserved (1e-14) while growing and dissolving, never negative | That the physics is right (partly true by construction) |
| 3b `iron` | 4 | Iron conserved (1e-15), returned when the crystal dissolves, and sectors follow the coefficients (r/z 1.99, r/m 9.8) | That the coefficients (ASSUMED) or the colour law are real |
| 4b `ph_rate` | 6 | The pH-dependent rate law equals Table 4 of Palandri & Kharaka (2004) (difference 0), rises 0.5 log units per pH unit, leaves the Takeno law unchanged without pH, and changes only the real time, never the crystal (bit-identical) | That the base term (measured for dissolution) applies to growth, which printed base constant is right, or the real fluid pH |
| `renewal` | 4 | A fluid renewal sets the fluid to the target silica (exact), silica and iron balances close after discounting what it adds (1e-14), periodic renewals grow more crystal than the closed container (x2-x4 in the test) and are reproducible bit for bit, out-of-range temperatures are refused | That real geodes were renewed like this, how often or with what fluid |
| 4 `solubility` | 6 | The implemented curve equals the equation printed in Takeno et al. (2000) (difference 0), 10.97 ppm at 25 C vs 11.0 +/- 1.1, slope matches the enthalpy (1.2%) | That the Rimstidt curve is the right one (a 6.6-12 ppm spread exists in the literature) |
| 5 `convergence` | 3 + 1 info | The aspect ratio (changes 7.3, 4.95, 2.1%) and the r/m face ratio (3.5, 1.4, 0.45%) converge with resolution (200 to 1600 cells); supersaturation uniformity unchanged | Other conditions; and at 200 cells (explore) the aspect ratio is NOT converged (13% low) |
| 6 `fast` | 6 | Numba kernels equal the NumPy reference to about 1e-15 after 3000 steps in isotropic, faceted-with-iron-and-noise and dissolution scenarios, also in-place; conserve; do not depend on thread count; 2-3x faster per thread | That the physics is right |
| 6b `implicit` | 5 | Implicit diffusion = explicit (0.000%), step-independent, stable at huge steps, conserves; the uniform-fluid limit equals the full solution on the plateau (0.28%) | That the physics is right; the uniform limit is valid only for Da << 1 |
| 7 `qualitative` | 1 + 2 info | Higher supersaturation grows faster (4.3x between S = 1.6 and 3.3 in model time). REPORTED: no facet destabilisation up to S = 30 for crystals of 24 cells | Hopper or branched growth is neither reproduced nor excluded: the literature statement is unverified and the test is narrow |
| `reproducibility` | 6 | Same seed gives identical results bit for bit; saved folder complete; replay exact; noise does not roughen the surface | That the spread between seeds resembles real crystals (amplitudes ASSUMED) |
| `live` | 7 | Pause, temperature/iron changes, extend, stop work, are refused when invalid, and sessions replay exactly | That an instantaneous temperature jump or a fluid-renewal iron change is realistic |
| `ensemble` | 6 | A replica equals its seed run alone; the same timeline is applied; statistics are exact; serial = parallel | That the spread is realistic |
| `server` | 8 | Jobs run in separate processes, the server stays responsive, WebSocket frames are steady (about 4/s, independent of speed), commands, results, ensembles, notifications and the authentication hook work | Behaviour with a real browser, many users or a network |

Bugs found by these checks during development (all fixed, each by a test that fails on the buggy version): a job reported "finished" before its files were saved; NaN in JSON responses; noise that did not scale with tau (rough surfaces);
an iron-slider defect that left the interface cells half-way to the new value; a test tolerance that was too wide to detect it.

## 2. IMPOSED by assumption vs PREDICTED by the model

**Imposed (inputs; none of them was found in a source, or only qualitatively):**
the relative growth speeds of the m, r and z faces (0.5 : 1 : 1) and therefore the habit of the crystal; the equality r = z in the section (a simplification: in quartz r and z differ);
the iron incorporation coefficients (0.01 / 0.005 / 0.001: only the order r > z > m is supported, qualitatively) and the colour law; the fluid iron (1 ppm); the noise and seed-variation amplitudes; the diffusivity of silica (1e-9 m2/s);
the crystal silica capacity used in the model (22000 times below real); the kinetic coupling lambda; the closed container and the saturation-temperature start.

**Predicted given those inputs:** positions and orientations of flat faces (Frank's construction, check 2); the sector structure of iron; conservation; the response to temperature and iron changes; the dependence of the shape on Da and its plateau (regime study);
the supersaturation history of the closed container; the numerical convergence behaviour.

**Not predicted:** the real habit of geode amethyst, its colour intensity, or its growth time. The simulated aspect ratio is a consequence of the assumed face speeds distorted by the numerical regularisation.

## 3. The growth regime (the decision that mattered most)

Evidence (docs/kinetic_regime.md): the verified quartz rate law and constant (Takeno et al. 2000) give a Damkohler number Da between 1e-7 and 3e-4 for crystals up to 10 cm: growth is **surface-limited**.
The model's early default kinetics (Da about 60-100, diffusion-limited, round crystals) contradicted this. The regime study (docs/regime_study.md) shows a **plateau**: for Da below about 0.06 the shape at equal size
does not change (<= 0.4%) and the supersaturation at the surface equals the bulk's. The modes therefore run on the plateau (Da about 1e-2 to 1e-3), which is demonstrated to be equivalent to the real regime for the shape, and cost was handled with
exact-to-rounding numerical schemes (Numba, implicit diffusion, uniform-fluid limit) before touching any physical parameter. Details and the sensitivity table: docs/regime_study.md.

## 4. The two modes

| | explore | research |
|---|---|---|
| Grid | 200 x 100 (0.2 mm per cell, 40 mm container) | 800 x 400 (0.05 mm per cell) |
| Time per run (full model, saved) | about 5 s | about 1.5 minutes |
| Aspect ratio vs converged (1600 cells) | about 13% low | about 2% low |
| r/m face ratio vs converged | about 5% low | 0.45% |
| Use | live control, trends, quick comparison at the same resolution | numbers to report |

Resolutions were chosen from the convergence study and the benchmark (docs/benchmark.md): research is the smallest grid whose aspect ratio is within the 5% tolerance of the finest grid and whose cost is about a minute; explore is the cheapest grid that gives a recognisable crystal.

## 5. Open issues and limits (what a reader must not forget)

1. **Absolute growth time**: with the verified rate law, a crystal of a few millimetres to centimetres takes 1e7 to 1e9 years at 15-60 C, in tension with the age of the host rocks. Unresolved (docs/kinetic_regime.md, section 3 and 9); candidate explanations quantified in [growth_time.md](growth_time.md) (still open: the age and duration of the amethyst stage are not known from any source read). The conversion `time_kinetic_years` carries at least two orders of magnitude of uncertainty.
2. **Rate law source**: read in a secondary source (neutral dilute solution). the 71 vs 50 kJ/mol question is resolved (two different constants, k+ of quartz and k- of all silica phases; first page of Rimstidt & Barnes 1980 read); an alkaline fluid could speed growth by up to about 2.5 orders and make Da marginal (about 0.1) for 10 cm crystals at 60 C and pH 10; the pH term is not in the model (docs/kinetic_regime.md, section 10). Several other sources are UNVERIFIED (see materials/amethyst.yaml and docs/sources.md).
3. **Face-specific rates unknown**: the m : r : z speeds are assumed; the crystal habit is a direct consequence. no usable measurement found; the shape as a function of m : r : z is mapped in [face_speed_study.md](face_speed_study.md) (aspect ratio and face ratios depend on it, sector iron does not).
4. **No comparison with real crystals**: every validation compares the code with its own equations, with theory, or with another numerical scheme. Not one check compares with an observation of a real amethyst. a protocol and a tool exist (docs/observation_comparison.md, scripts/compare_with_observation.py), tested only with fictitious data; no real measurement yet. It separates checks, calibrations and predictions; a validation needs two independent samples.
5. **Facet destabilisation** at very high supersaturation: **not expected in this regime; the sentence of the spec does not apply to geodes** (docs/regime_study.md, section 8). It is a diffusion-limited (Mullins-Sekerka / Berg-effect) instability (Libbrecht, Snow Crystals, read); at the real Da of geode crystals (<< 0.1 in neutral fluid) the surface supersaturation is uniform. Only decimetre crystals in warm, strongly alkaline fluid would approach it. Separately, the model cannot produce hopper faces even far from the plateau (probe: Da 1-170, radius 80 cells, noise: it rounds instead), because it has no step-source kinetics; options (not implemented): vicinal step-density kinetics, a 2D-nucleation facet law, larger crystals relative to the interface, 3D. Check 7's 'S = 30' only raised the supply: the driving force is clipped above S of about 4.5.
6. **2D section only**, closed container, constant or stepped temperature, trace iron that does not affect growth, geometric surface area.
7. **Explore shapes are qualitative**; compare runs at the same resolution; use research for numbers.
8. **Bit-for-bit replay** needs the same backend and library versions; the backends agree to about 1e-15 per step.
9. **The plateau** was measured for one geometry and a few conditions; other temperatures, sizes and face-speed ratios may shift it (the runs report the model Da and warn if it is above the plateau). Later (docs/regime_study.md, section 7): a plateau exists in all 12 conditions tested (temperature 15-45 C, size, m/r 0.3-0.8, low and high S, Cs_model x0.5 and x2); its onset moves between about 6e-3 and 1e-1 (at the target size). The modes use the uniform-fluid scheme (Da -> 0 by construction) and are unaffected; the real neutral-fluid Da (<= 3e-4) is below every onset; strongly alkaline fluids at 60 C would not be. The run warning (Da at 50 cells > 0.06) does not cover the worst onsets (1e-2 at 50 cells): proposed (not applied) to lower it to 0.01 and to skip it for the uniform-fluid scheme, which has no transport.
10. **Server** is local-only, with an in-memory job list; ensembles use the assumed noise amplitudes, so their spread is not a prediction of natural variability.

## 6. What Phase 1 delivers

A working, documented engine and tools: live animated and controllable simulation (matplotlib and a local web page), timeline and exact replay, ensembles in parallel, metrics and results on disk, a local server with a WebSocket stream, a validation suite and this report.
The next scientific steps, if the project continues, are the open issues above: especially the face-specific growth rates, comparison with a real crystal, the growth-time tension, and the effect of pH and replenishment.
