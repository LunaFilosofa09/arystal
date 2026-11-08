# Physics model

Status: implemented; the sections below follow the order in which the model was built.

## Overview

A phase-field model for growth from solution, with these ingredients:

1. **Phase field** `phi`: 1 inside the crystal, 0 in the fluid, smooth over a thin interface.
2. **Silica concentration** `c` in the fluid, diffusing; the crystal consumes it as it grows.
3. **Supersaturation** `sigma = c / c_eq(T) - 1`, where `c_eq(T)` is the quartz solubility
   curve (Rimstidt 1997). Cooling lowers `c_eq` and raises `sigma`.
4. **Anisotropy** with facets: surface energy as a function of the interface orientation,
   with rounded cusps at the facet orientations (Debierre, Karma, Celestini & Guerin 2003).
5. **Iron** `f` as a second dissolved species, trapped into the crystal with a
   sector-dependent partition coefficient.
6. **Noise** (thermal) and small random variations of the seed.
7. **Mass conservation**: silica and iron in solid + fluid constant in the closed container.

Equations, non-dimensionalization and the derivation of the 2D projection of the trigonal
faces are written in the sections below.

## Isotropic model

    tau * d(phi)/dt = epsilon^2 * laplacian(phi) + phi * (1 - phi) * (phi - 1/2 + m)

- `phi`: 1 in crystal, 0 in fluid. `m`: constant driving force (stand-in for supersaturation in this first model).
- The wall (bottom edge) and the other edges are mirrors (no flux).
- Equilibrium interface profile: phi = 0.5 * (1 - tanh(d / (2*sqrt(2)*epsilon))); 10-90% width is about 6.2*epsilon.
- Exact results used by validation check 1 (standard result for this equation; checked numerically by our run):
  flat front speed `v = sqrt(2) * epsilon * m / tau`; curved front `v(R) = v - epsilon^2 / (tau * R)`;
  critical radius `R_c = epsilon / (sqrt(2) * m)`.
- Numerics: explicit Euler, 5-point laplacian, dt = 0.1 (stability limit 0.25).
- Everything is non-dimensional (cells, model time units).

## Silica, solubility and temperature

Fields: `phi` (as before) and `c`, dissolved silica in mol/kg.

    m = lambda * ln(c / c_eq(T))                    clipped to +-0.3
    tau * d(phi)/dt = epsilon^2 * laplacian(phi) + phi*(1-phi)*(phi - 1/2 + m)
    d(c)/dt = div( D * (1 - h(phi)) * grad(c) )  -  Cs * d(h(phi))/dt
    h(phi) = phi^2 * (3 - 2*phi)

- `c_eq(T) = 10^(a/T + b)` mol/kg (Rimstidt 1997 form; a = -1107.12 K, b = -0.0254; UNVERIFIED coefficients, see materials file).
- Supersaturation S = c / c_eq. Cooling lowers c_eq, so the same silica gives S > 1.
- `ln(c/c_eq)` is the thermodynamic driving force (proportional to the chemical-potential difference); `lambda` (assumed 0.2) converts it into the model's `m`.
- `Cs` = extra silica held by a unit of crystal compared with the same volume of fluid (model value 0.002 mol/kg, ASSUMED, see below).
- Diffusion is computed as exchanges across cell faces, with face diffusivity `D * (fluid fraction)`: nothing can enter or leave the closed container, and silica never appears or disappears, so `sum(c + Cs*h)` is conserved to round-off (validation check 3).
- Expected end state of a closed run: fluid back at `c_eq(T)` and a crystal filling a fraction `(c0 - c_eq(T)) / Cs` of the container (apart from a small Gibbs-Thomson shift because curved surfaces are slightly more soluble). Not yet used as a test because it needs very long runs.
- Initial silica `c0` = `c_eq` at the "saturation temperature" (the fluid had been in equilibrium with quartz at that temperature).

### Scaled crystal capacity and time (IMPORTANT)

Real quartz holds about 44 mol of silica per kg of water-equivalent volume; real geode fluid about 0.0003 to 0.0004. In a truly closed cavity, cooling from 60 to 15 C could therefore form crystal filling only ~0.001% of it. Real geodes are replenished with silica-bearing fluid many times. To get a visible crystal inside a closed model container, the model uses `Cs = 0.002 mol/kg`, about 22000 times smaller than real (ASSUMED).

Time: the model time unit is `dx^2 / D` (cell size squared over silica diffusivity). With a 40 mm wide, 400-cell container and `D = 1e-9 m2/s` (ASSUMED), one model time unit = 10 s. That is the *diffusion* time scale. Depositing a real-density crystal at the same silica supply would take about 22000 times longer. Both numbers are order-of-magnitude; the uncertainty is dominated by the assumed `D`, the assumed `Cs`, and the interface kinetics (not calibrated against any measured growth rate).

Not modelled yet: temperature dependence of `D`, interface kinetics calibrated to Rimstidt & Barnes (1980), fluid replenishment, fluid cooling over time (the temperature is constant during a run unless it is changed live).

## Kinetic anisotropy

### Geometry of the 2D section
The section plane contains the c-axis (up) and the pole of one prism face m. In that plane:
the m faces are vertical (normals along +x and -x); the pole of r {10-11} is tilted 51.78 deg
from the c-axis (38.22 deg from the m pole, from the lattice parameters, UNVERIFIED); r is on one
side and z on the OPPOSITE side, because the 3-fold axis alternates r, z, r, z, ... every 60 deg
around the c-axis and the plane cuts opposite sides. So the right termination is r and the left
one is z. (Assumed from standard trigonal-quartz geometry, not checked against a crystallography
text in this project; the face-family names r/z follow the Phase 1 specification.) Mirror symmetry about the
c-axis therefore holds only if r and z are given equal properties, which is a simplification
(Cohen & Hassan 1974: r and z take up different amounts of iron).

### Equation
    tau / g(theta) * d(phi)/dt = epsilon^2 * laplacian(phi) + phi*(1-phi)*(phi - 1/2 + m)
    g(theta) = smooth-max over corners V_k of the speed polygon ( V_k . n(theta) ),  n = outward normal
The speed polygon is bounded by half-planes `n_face . x <= v_face`, with v_m = 0.5, v_r = v_z = 1 (ASSUMED).
g equals v_face at each face normal, where it has a rounded cusp (V-shaped minimum). This is
Frank's kinetic Wulff construction: slow orientations survive as flat faces, fast ones grow out.
The cusp is rounded by a log-sum-exp with sharpness beta = 40 and corrected so g is exact at the face normals.
A face set where a face would never appear (too fast) is refused.

Why kinetic and not surface-energy anisotropy: relative growth rates of the faces, not the equilibrium shape,
normally set the habit of crystals growing from solution far from equilibrium. This is a modelling choice,
not a result. Surface-energy anisotropy (rounded-cusp gamma-plot, Debierre et al. 2003, UNVERIFIED) is not implemented.

### What is IMPOSED and what is PREDICTED
- IMPOSED by assumption: the three face speeds (aspect ratio of the prism vs the termination), the r = z equality,
  the angle between faces (from lattice parameters), the cusp rounding.
- PREDICTED by the model given those inputs: the positions and orientations of the flat faces (Frank's construction,
  checked in validation check 2), and how the shape is modified by the silica supply.
- NOT predicted: the real habit of geode amethyst. No quantitative face-speed ratios were found in the literature.

### Known numerical limitations
1. Rounded apex: orientations between r and z are "missing" and have near-zero stiffness; interface curvature keeps the
   apex round (15% lower than the sharp polygon in the constant-force test). The sharp-interface limit needs crystals much larger than epsilon.
2. Facet sharpness depends on the size of the crystal relative to the interface thickness (epsilon = 1 cell) and on the driving force:
   with m = 0.1 a crystal of 100 cells is a dome; with m = 0.3 it shows straight r/z faces. This is a numerical regularisation effect, not quartz physics.
   Quantified by validation check 5: the aspect ratio is about 13% below its converged value at 200 cells across and about 2% at 800 (docs/regime_study.md, section 3).
3. Time step limited by the fastest orientation (g_max about 1.6).

### Regime problem (found with the anisotropic model, resolved by the regime study)
History: with the early default kinetics (tau = 1) the full model is diffusion-limited and shows round crystals, while the evidence (quartz rate law and constant read in
Takeno et al. 2000, a secondary source) says real growth of geode crystals up to ~10 cm is surface-limited (Da between 1e-7 and 1e-3).
Resolved by the regime study ([regime_study.md](regime_study.md)): below Da of about 0.06 the shape at equal size no longer depends on Da (<= 0.4%), for the geometry and conditions tested.
The explore and research modes run on that plateau (tau = 1e4 at 200 cells across, scaled with the resolution); see [kinetic_regime.md](kinetic_regime.md), section 9.
A run configured above the plateau (for example tau = 1) is still possible and is flagged by a warning in its summary.json. The regime fixes the shape only given the ASSUMED face speeds:
shapes are still not predictions of real amethyst habit (docs/validation_report.md, sections 2 and 5).

## Iron and colour

Two more fields: `f` (iron dissolved in the fluid, mol/kg) and `I` (iron locked in the crystal, same units per volume).

    d(f)/dt = div( D_Fe * (1 - h) * grad(f) ) - dI/dt
    dI = k(sector) * (f / c) * Cs * dh        where the solid fraction h grows (dh > 0)
    dI = I * dh / h                           where it shrinks (dh < 0): iron is given back in the proportion held

- `k(sector)`: molar distribution coefficient, (Fe/Si in crystal) / (Fe/Si in fluid), by face family: k_r = 0.01, k_z = 0.005, k_m = 0.001 (ASSUMED; only r > z > m is supported by the literature, qualitatively).
  It is defined per unit of silica deposited, so it does not depend on the scaled crystal capacity Cs.
- Sector of a piece of surface = direction of its normal; the coefficient is a Gaussian-weighted blend of the face coefficients (width 12 deg, ASSUMED numerical choice), which keeps the model smooth and symmetric.
- Iron is a TRACE: it does not change growth, silica supply or solubility (assumption).
- Iron is conserved exactly: `sum(f + I)` constant (validation check 3b).
- A consequence of the model, not an input: silica is depleted at the surface but iron much less, so the fluid Fe/Si at the surface rises, and so does the Fe/Si of the crystal growing there (about 3x the starting fluid ratio in the tested runs).
- Colour (storage/rendering.py): `intensity = 1 - exp(-(Fe/Si in crystal) / s)` with `s = 4e-4` (ASSUMED), blended from pale quartz to deep amethyst. Saturating, not linear, because iron alone does not make amethyst: natural irradiation is also required (Cohen & Hassan 1974); a uniform, sufficient dose is assumed. The end colours are aesthetic.
- r and z have different coefficients by default, so with iron switched on the section is NOT mirror-symmetric in colour (the shape stays symmetric unless the face speeds differ).

### What is IMPOSED and what is PREDICTED (iron)
- IMPOSED: the three coefficients and their magnitudes, the sector transition width, the colour law and its scale, the fluid iron concentration, the trace assumption, the uniform irradiation.
- PREDICTED given those: the spatial pattern of sectors (concentric zones following the surface direction as the crystal grows), the enrichment of iron where silica is depleted, and conservation.
- NOT predicted: actual amethyst colour intensities or zoning contrast. The m : r : z contrast (1 : 10 : 5) is invented; only its order is literature-supported.
- Interior note: like silica, the dissolved iron left inside the crystal region is "trapped fluid" that stays in the field `f`; the colour uses only `I`.
- Not done yet: sector boundaries are smeared over ~12 deg and the crystal base on the wall has no special treatment; Dauphine twinning (lower iron in twinned parts of r sectors, Cohen & Hassan 1974) is ignored.

## Noise, seeds and metrics

- **Noise**: `dphi = sigma * sqrt(dt / tau) * 4 phi (1 - phi) * N(0,1)` added at the interface (zero in the bulk), sigma = 0.02 (ASSUMED). The `1/sqrt(tau)` factor keeps the noise in proportion to the deterministic dynamics (which are divided by tau; fluctuation-dissipation). A first version without it made the surface visibly ragged when tau was large (roughness 0.083 vs 0.015); found by looking at an output image and now guarded by a test. Noise is not scaled by the anisotropy factor g (simplification). Real thermal noise is negligible at millimetre scale; the term is a modelling device
  for all small random irregularities, so that replicas differ slightly as real crystals do. It does not break mass conservation (silica and iron follow the actual change of the phase field).
- **Seed variation**: the initial radius varies by 5% (relative standard deviation) and the position by 1 cell (standard deviation) between seeds (ASSUMED). In short runs this variation of the starting size is the main source of difference between seeds.
- **Reproducibility**: one integer seed -> two independent streams (`numpy.random.SeedSequence.spawn`): initial-seed variation and thermal noise. Same seed + settings + material file = identical result bit for bit (same machine and library versions).
- **Metrics**: area; estimated mass (area x ASSUMED thickness 10 mm x real density 2.65 g/cm3; an order of magnitude only); height / width (aspect ratio); growth of each face family measured as the **support distance**
  (how far the crystal extends along the normal of the m, r and z face; sub-cell accuracy about 0.3 cells) and its rate between samples; mean crystal Fe/Si and Fe/Si per growth sector (exact, from iron and silica deposited by each family at the time of deposition);
  S at the interface and in the bulk (top row); totals of silica and iron and their relative drift.
- **Meaning of "growth rate of a face family" in a round crystal**: the support distance in that direction, which exists for any shape; it equals the face position only when a flat face of that family exists.
- **Time columns**: `time_model` is the model time; `time_diffusion_hours` is the diffusion time scale (see time_scaling.py) and is NOT physical growth time.

## Live changes

- **Temperature**: `c_eq(T)` jumps to its new value at one step; the silica of the container is unchanged. Cooling raises S and speeds growth; heating can make S < 1 and dissolve the crystal (tested: cooling 40 -> 15 C multiplied the area growth rate by 2.9; heating 40 -> 60 C dissolved 30% of the crystal in the test run).
  ASSUMPTION: instantaneous; real cooling is gradual and slow.
- **Fluid iron**: the dissolved iron is set to the new concentration in every cell with an appreciable fluid fraction (more than 1% fluid), like renewing the fluid; the iron locked in the crystal is untouched. This adds or removes iron from the container
  (it is an intervention outside the closed budget), so the metrics discount the iron added: `(total iron - injected iron) / initial iron`.
- **Timeline**: each event is applied after `step` steps have been completed and before the next one, so a replay with the same seed applies it at the same instant. Pausing, resuming and the wall-clock moment of a request do not matter; the only thing recorded is the step.
  A stop is recorded as a duration equal to the current time; extending the duration is recorded too.
- **Surface exchange with noise (observation)**: with interface noise on, the surface continually deposits and releases silica. On release, iron leaves with the stored Fe/Si of the crystal; on deposit, iron enters with the current fluid Fe/Si. So the *net* Fe/Si of the increments of a short window
  is not the simple deposition ratio when the net growth is small compared with the exchange (found when testing the iron slider: measured x10 instead of x3 with noise on). The sector structure of the bulk crystal (checked by the iron check) is unaffected, but fine-scale composition depends on the noise amplitude (ASSUMED).

## Ensembles

- An ensemble repeats one configuration and one recorded timeline with N different seeds. The seeds are derived from a base seed (`numpy.random.SeedSequence.generate_state`), so the ensemble is reproducible, and each replica is bit-for-bit identical to its seed run alone (tested).
- Replicas differ only through the random numbers: the interface noise and the seed variations (both ASSUMED, uncalibrated, see Noise, seeds and metrics). **The spread between replicas is therefore a property of those assumed amplitudes**, not a prediction of the variability
  of real crystals. In the demonstration (10 replicas, 240 x 120 grid, cooling at t = 1200) the final area was 31.1 mm2 with a standard deviation of 1.7 mm2 (5%), much of which comes from the 5% variation of the initial seed radius.
- Statistics: mean, sample standard deviation (n - 1), minimum and maximum over the replicas, for every metric, at the end and at every sampling moment.

## Numerical schemes, modes, time conversion

* **Schemes for the transport of dissolved silica and iron** (`diffusion_scheme`): `explicit` (the original; time step limited to 0.9 / (4 D) = 0.225), `implicit` (backward Euler, sparse direct solve, any time step, `engine/implicit_diffusion.py`)
  and `uniform` (the well-mixed limit Da -> 0: the concentrations are uniform and recomputed each step from the conserved totals, `engine/uniform_fluid.py`). They solve the same equations; the second and third are validated against the first (check 6b) and conserve silica and iron to rounding.
  `uniform` is valid only when Da is much smaller than 1; the summary of every run states the model Da and warns if it is above the plateau.
* **Fast kernels** (`backend`: `numba` or `reference`): `engine/fast_kernels.py` does the same calculation as the readable NumPy code (check 6: differences about 1e-15 after 3000 steps, conservation preserved, independent of the number of threads).
  The NumPy code remains the definition of the physics. Replaying a run bit for bit requires the same backend.
* **Modes** (`simulation/modes.py`): explore = 200 x 100 cells, research = 800 x 400; both on the plateau (tau = 1e4 at 200 cells across, scaled with the resolution), uniform fluid, time step 0.1 tau (the explicit phase-field stability limit is about 0.14 tau for the fastest orientation).
  Durations are therefore very long in model time units (hundreds of thousands to millions): use the mode default or `time_kinetic_years`.
* **Kinetic time** (`engine/time_scaling.py`): real seconds per model time unit = (model speed of the fastest face) x (cell size) / (real speed Vm k+(T) (S - 1)), valid in the surface-limited regime. Assumes the measured quartz rate constant applies to the fastest face family; uncertain by at least two orders of magnitude.
  Optional fluid pH (`engine/ph_rate_law.py`): k(T, pH) = k_neutral(T) + k_base(T) a_H+^-0.5, each k(T) = k(25 C) exp(-E/R (1/T - 1/298.15)), with log k = -13.40 and -16.29 (pH 0), E = 90.9 and 108.4 kJ/mol
  (Palandri & Kharaka 2004, Table 4 and eq. 6). In plain words: in alkaline water hydroxide ions help silica attach and detach, so the rate grows 3.16 times per pH unit above about 7. It changes only the real-time conversion.
  The diffusion time scale (`time_diffusion_hours`) is kept for the diffusion-limited runs.
* **Resolution**: the aspect ratio converges slowly; see docs/regime_study.md and docs/validation_report.md.

## Already computed

- Angle between the pole of r {10-11} and the c-axis: 51.78 deg (from lattice parameters
  a = 4.9134, c = 5.4042 angstrom, which are themselves UNVERIFIED). Angle m to r: 38.22 deg.
- Rimstidt (1997) curve gives 10.97 ppm SiO2 at 25 C.

## Sources

See [sources.md](sources.md) and [../materials/amethyst.yaml](../materials/amethyst.yaml).
