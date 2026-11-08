# Regime study

Question (docs/kinetic_regime.md): is growth of geode amethyst limited by the **diffusion** of silica or by its **attachment** at the surface, and does the answer
change what the model predicts? Rule followed (Luna): do not choose a regime or tune kinetics for convenience; establish what is justified; use numerical
optimisation before touching physical parameters.

Tools: `python scripts/regime_study.py` (map and `--sensitivity`), `arystal/validation/regime_study.py`. Same crystal grown (200 x 100 grid, 40 mm container, fluid saturated
at 60 C, run at 20 C, seed radius 12 cells, faceted growth, no noise, no iron) until its equivalent radius is 30 cells, for relaxation times tau from 1 to 1e6. The
Damkohler number of the model, Da = (attachment speed) / (diffusion speed) at that size, is `Da = 61 / tau` here.

## 1. Regime map (same crystal at different Da)

| tau | Da | scheme | steps | wall time | aspect ratio | r/m face ratio | S at surface / S bulk (uniformity) |
|---|---|---|---|---|---|---|---|
| 1 | 61 | explicit | 30 090 | 11 s | 0.517 | 1.026 | 0.098 |
| 10 | 6.1 | implicit | 2 960 | 163 s | 0.593 | 1.118 | 0.189 |
| 100 | 0.61 | implicit | 910 | 56 s | 0.804 | 1.304 | 0.654 |
| 1 000 | 0.061 | implicit | 730 | 45 s | 0.826 | 1.350 | 0.952 |
| 10 000 | 0.0061 | implicit | 710 | 45 s | 0.826 | 1.355 | 0.995 |
| 100 000 | 0.00061 | implicit | 710 | 42 s | 0.826 | 1.357 | 1.000 |
| 1 000 000 | 0.000061 | implicit | 710 | 42 s | 0.826 | 1.357 | 1.000 |

Relative change of the aspect ratio between consecutive rows: 14.6%, 35.7%, 2.7%, 0.0%, 0.0%, 0.0% (r/m face ratio: 9.0%, 16.6%, 3.5%, 0.4%, 0.1%, 0.0%).

**Result: a plateau.** Above Da of about 0.6 the shape changes strongly with Da (diffusion-limited: the surface sees only a fraction of the bulk supersaturation, the crystal is
low and rounded). Below Da of about 0.06 nothing that was measured changes any more (<= 0.4%), and the supersaturation at the surface equals that of the bulk (uniformity -> 1).
The estimated real Da (1e-7 to 1e-3, docs/kinetic_regime.md) lies on the plateau. Therefore the model run on the plateau gives the same shape as the real regime would,
**without having tuned any physical parameter**: the plateau is demonstrated, not assumed.

Cost note: with implicit diffusion the number of steps is about constant (about 700) at any Da, because the step is limited by the motion of the interface, not by the diffusion.

## 2. Sensitivity on the plateau (tau = 1e4, same size unless stated)

| Case | Da | aspect ratio | r/m | uniformity | change of aspect vs baseline |
|---|---|---|---|---|---|
| baseline | 6.1e-3 | 0.826 | 1.355 | 0.995 | |
| crystal capacity Cs x0.5 | 3.1e-3 | 0.864 | 1.366 | 0.998 | +4.6% |
| crystal capacity Cs x2 | 1.2e-2 | 0.804 | 1.307 | 0.992 | -2.7% |
| kinetic coupling lambda x0.5 | 3.1e-3 | 0.750 | 1.246 | 0.998 | -9.2% |
| kinetic coupling lambda x2 | 8.8e-3 | 0.886 | 1.387 | 0.989 | +7.3% |
| T = 40 C (S = 1.6), radius 24 | 3.8e-3 | 0.643 | 1.158 | 0.998 | -15.7% (vs baseline at radius 24: 0.763) |

All cases stay surface-limited (uniformity >= 0.99). But the **shape depends on lambda and on the supersaturation even on the plateau**: this is not physics of quartz; it is the
finite capillary length of the model (d0 = epsilon / (sqrt(2) lambda), about 3.5 cells for lambda = 0.2, against a crystal of 30 cells): the interface still rounds the shape (the effect
found with the anisotropic model). It must vanish when the grid is refined (next section): doubling lambda behaves like doubling the resolution (aspect 0.886 equals the 400-cell value).

## 3. Resolution convergence (validation check 5)

Same physical crystal on 100, 200, 400, 800 and 1600 cells across the same container (cell size 0.4 to 0.025 mm); tau, seed radius and target size scaled with the resolution so the physical
problem is the same.

| Cells across | aspect ratio | change | r/m face ratio | change | wall time (uniform fluid) |
|---|---|---|---|---|---|
| 100 | 0.750 | | 1.227 | | 0.2 s |
| 200 | 0.826 | 10.1% | 1.358 | 10.7% | 0.3 s |
| 400 | 0.886 | 7.3% | 1.405 | 3.5% | 1.4 s |
| 800 | 0.930 | 4.95% | 1.425 | 1.4% | 20 s |
| 1600 | 0.950 | 2.1% | 1.431 | 0.45% | 114-125 s |

The aspect ratio converges **slowly** (the difference to the next finer grid shrinks by about 0.7 per doubling): the apex of the crystal is rounded by the interface and that rounding
decreases slowly with refinement. At 200 cells across (explore mode) the aspect ratio is **about 13% below** its value at 1600; at 800 (research mode) about 2%. The r/m face ratio converges faster (0.45% at 800).
With the full implicit solution at 100, 200 and 400 cells the values were identical to four digits (0.7500, 0.8261, 0.8864), which is why the uniform-fluid scheme was trusted for 800 and 1600.

## 4. The numerical schemes that made this possible (check 6b)

* **Implicit diffusion** (backward Euler with a sparse direct solver): same equations, any time step, silica and iron conserved to 1e-14. Equal to the explicit scheme at the same step (area difference 0.000%) and
  independent of the step (0.000% between steps 1 and 5 against the explicit reference).
* **Uniform fluid** (Da -> 0): dissolved silica and iron kept uniform, recomputed each step from the conserved totals. Equal to the full implicit solution on the plateau (area 0.28%, faces 0.04 cells), conserving to 1e-15,
  86 times faster. It cannot show depletion halos or an effect of slow supply, so it is valid only when Da is much smaller than 1 (the runs warn when it is not).

## 5. Capacity scaling (docs/kinetic_regime.md, test 3)

Halving or doubling the model's crystal capacity Cs changed the aspect ratio by +4.6% and -2.7% at equal size. The change comes from the depletion of the closed container at equal crystal size (S drops
more with a larger Cs: 2.44, 2.06, 1.31 for Cs x0.5, x1, x2), and through S from the capillary effect above, not from the transport. So **Cs_model is not innocent**: it changes the supersaturation history of the closed container.
Its value stays ASSUMED and the sensitivity is small (a few per cent) compared with the resolution effect.

## 6. What this does and does not establish

* ESTABLISHED (within this model): for Da below about 0.06 the shape, at equal size, does not depend on Da; the real regime (Da 1e-7 to 1e-3) is on that plateau; the cost of that regime is small with the schemes above.
* NOT ESTABLISHED: the real Da itself (the rate law is a secondary source for neutral dilute solutions; D, Cs, supersaturation and face-specific rates are assumed); the plateau was measured for one geometry and a few conditions (T 20 and 40 C); fluid motion,
  replenishment and external feed are outside the closed-container model.
* The shape (aspect ratio) is imposed by the ASSUMED face speeds; the study shows how that imposed habit is distorted by the numerical regularisation, and that at 800 cells it is within about 2% of its converged value.

## 7. Does the plateau hold under other conditions?

Question (validation_report.md, section 5, point 9): the plateau was measured for one crystal. Here the same Da sweep (tau 30 to 1e6, implicit diffusion: transport solved in full,
200 x 100 grid, no noise, no iron) is repeated changing one thing at a time. Run: `python scripts/plateau_robustness.py` (5 processes, 96 runs, about 30 minutes; `--summary-only` recomputes
the table from the saved rows). Code: `arystal/validation/plateau_robustness.py`. Results and figure (aspect ratio against Da, one panel per group): `results/plateau_robustness/`.

**How the onset is measured.** Plateau onset = the largest Da (at the target size) below which every step to a lower Da changes the r/m face ratio by at most 0.5% **and** the aspect ratio by at
most about one cell. The aspect ratio is a bounding box counted in whole cells, so at radius 20-40 one cell is 1.5-3% of it and a 0.5% test cannot be applied to it; the r/m ratio
(support distances) is continuous. Da values come in steps of about 3x (the tau grid), so each onset is known only to within that factor.

| Case (one change from the baseline) | Target radius | Plateau onset Da (at target size) | Onset Da at 50 cells (warning size) | Da of the modes (same case) | Modes below the onset? | Aspect ratio on the plateau |
|---|---|---|---|---|---|---|
| baseline: 20 C, saturated at 60 C, m/r 0.5 | 30 | 6.1e-2 | 1.0e-1 | 6.1e-3 | yes (10x) | 0.826 |
| T = 15 C | 30 | 6.5e-2 | 1.1e-1 | 6.5e-3 | yes (10x) | 0.864 |
| T = 37 C | 24 | 4.0e-2 | 8.3e-2 | 4.0e-3 | yes (10x) | 0.700 |
| T = 45 C (55 and 60 C impossible: no or too little supersaturation, the seed dissolves) | 16 | 8.0e-2 | 2.5e-1 | 2.4e-3 | yes (33x) | 0.567 |
| small crystal | 20 | 1.4e-2 | 3.4e-2 | 4.1e-3 | yes (3x) | 0.719 |
| large crystal | 40 | **8.1e-3** | 1.0e-2 | 8.1e-3 | **at the onset** | 0.897 |
| m/r = 0.3 | 30 | **6.1e-3** | 1.0e-2 | 6.1e-3 | **at the onset** | 1.050 |
| m/r = 0.8 | 30 | 2.0e-2 | 3.4e-2 | 6.1e-3 | yes (3x) | 0.673 |
| low S (saturated at 40 C, S0 1.74) | 20 | 1.8e-2 | 4.5e-2 | 5.4e-3 | yes (3x) | 0.647 |
| high S (silica x1.5, S0 4.26) | 30 | 4.8e-2 | 8.0e-2 | 4.8e-3 | yes (10x) | 0.886 |
| Cs_model x0.5 | 30 | 1.0e-1 | 1.7e-1 | 3.1e-3 | yes (33x) | 0.864 |
| Cs_model x2 | 30 | 4.1e-2 | 6.8e-2 | 1.2e-2 | yes (3x) | 0.804 |

Reading:
1. **A plateau exists in every case**: below its onset the r/m ratio changes by at most 0.5% and the aspect ratio by at most one cell, down to Da of about 5e-5.
2. **The onset moves**: by the r/m ratio alone it is at or above 1.8e-2 in every case. With the aspect ratio included it drops to about 6e-3 to 8e-3 in two cases (large crystal, m/r 0.3),
   where the last change is a single step of one to two cells at about 1e-2 (large: 0.879 -> 0.897; m/r 0.3: 1.025 -> 1.079 -> 1.050, not monotonic). At this resolution a one-cell flip
   cannot be told apart from a real change; a finer grid would be needed to decide (not done: an implicit 800-cell sweep would cost hours).
3. **The modes**: explore and research use the **uniform-fluid scheme**, which is the Da -> 0 limit of the transport by construction (uniform_fluid.py); their nominal Da (column 5) only describes
   the attachment speed. So the modes are not at risk from a moving onset: what matters is that the real geode Da is on the plateau. The real Da estimated in kinetic_regime.md
   (1e-7 to 3e-4 for crystals up to 10 cm in neutral fluid) is below the lowest onset found (6e-3) in every case. **With an alkaline fluid** (kinetic_regime.md section 10) the real Da reaches
   about 4e-2 (60 C, pH 9, 10 cm) and 0.11 (pH 10): above the onset in several of these cases, i.e. those crystals would not be purely surface-limited.
4. **The run warning** (saved_run.py and metrics_recorder.py, Da at 50 cells > 0.06) does not cover the worst case: onsets at 50 cells go down to 1.0e-2 (3.4e-2 using r/m only).
   A run with the explicit or implicit scheme and Da (at 50 cells) between about 0.01 and 0.06 may be off the plateau without a warning. Proposal in validation_report.md, section 5, point 9.

Limits: 200 x 100 grid (not converged for the aspect ratio, which is also why one-cell steps matter); one parameter changed at a time; no noise or iron; the Da grid has steps of 3-10x.

## 8. Facet destabilisation at high supersaturation: expected in geodes?

The Phase 1 specification (an unpublished planning document; check 7) says that "very high supersaturation destabilizes the facets". Check 7 never saw it (crystals of 24 cells, S up to 30).

### 8.1 The physics (sources)

Read: Libbrecht, K.G. (2019, 2021) *Snow Crystals* (open book, arXiv:1910.06389), chapter 3. Its argument is general to growth from a fluid by diffusion and attachment:
- The **Berg effect** (Berg 1938, cited there): around a growing faceted crystal the supersaturation is higher at the corners, which stick out into the fluid, than at the facet centres.
  This happens **because of diffusion**: the surface supersaturation is `sigma_surf = alpha_diff / (alpha + alpha_diff) sigma_inf` (eq. 3.17), with alpha the attachment coefficient and alpha_diff
  a diffusion coefficient that falls as 1/R. In the **kinetics-limited case (alpha << alpha_diff, i.e. Da << 1)** `sigma_surf ~ sigma_inf` (eq. 3.22): the supersaturation is the same everywhere on the surface.
- A facet stays flat under a Berg effect because steps bunch near its centre and raise the local attachment there; whether it survives depends on the anisotropy of the attachment kinetics,
  the size and the growth rate. The book's rule of thumb (read): "faceting dominates when: 1) crystals are small, 2) the degree of anisotropy in the attachment kinetics is large, and 3) the growth is slow".
- Hollow (hopper-like) faces and branches are "a form of the Mullins-Sekerka instability" (Mullins & Sekerka 1963-64, cited there), which applies "whenever growth is limited by diffusion".
- Not read: Chernov (1974) "Stability of faceted shapes", J. Crystal Growth (seen cited only); Nelson & Baker; Kuroda & Lacmann (named in the book).
- Hopper or skeletal amethyst exists in nature (sceptres with skeletal terminations: Mindat and dealer pages, not scientific sources); no read source links it to geodes or gives its conditions.

### 8.2 The criterion, with the model's own numbers

In the model the departure from uniform surface supersaturation is the "uniformity" of the regime map (section 1): 1 - uniformity = 0.05 at Da 0.06, 0.005 at Da 6e-3, so roughly **(non-uniformity) = 0.8 Da**.
A facet can only be destabilised if the corner-to-centre difference is a sizeable fraction of the driving force: Da of order 0.1 or more. Using the real Da of kinetic_regime.md (proportional to size):

| Fluid | Real Da of a 10 cm crystal | Size at which Da reaches 0.1 |
|---|---|---|
| Neutral, 15 C | 2e-5 | about 500 m |
| Neutral, 60 C | 3e-4 | about 30 m |
| pH 9, 60 C (Palandri & Kharaka, printed base constant) | 4e-2 | about 25 cm |
| pH 10, 60 C | 0.11 | about 9 cm |

**For geode crystals in neutral fluid the instability is out of reach by 2-4 orders of magnitude.** It becomes conceivable only for decimetre crystals grown warm in strongly alkaline fluid, which no read source supports.
(The same reasoning assumes still fluid; convection would make the surface even more uniform.)

### 8.3 What the model does far from the plateau (probe, NOT the realistic regime)

`python scripts/facet_stability_probe.py` (results/facet_stability_probe/): radius 80 cells on 400 x 200 (8 mm), run at 15 C, noise on, S0 = 3.3 and 4.6, Da at the final size 170, 1.7 and 4e-3.

| S0 | Da (final size) | solidity | facet share | what is seen |
|---|---|---|---|---|
| 3.3 | 173 | 0.990 | 0.11 | round dome |
| 3.3 | 1.7 | 0.990 | 0.23 | rounded termination, straight prism |
| 3.3 | 0.004 (plateau) | 0.989 | 0.23 | faceted |
| 4.6 | 138 | 0.989 | 0.13 | round dome |
| 4.6 | 1.4 | 0.989 | 0.27 | rounded termination |
| 4.6 | 0.003 (plateau) | 0.989 | 0.28 | faceted |

**The model does not produce hopper faces or branches, even far into the diffusion-limited regime: it rounds the crystal instead.** Reason (model structure): the kinetic anisotropy is a smooth speed-versus-orientation
function; where the supersaturation is lower (facet centres) the interface simply tilts to vicinal orientations, which grow faster in the model, so faces turn into curves instead of staying flat and then
caving in. Real facets grow by steps from discrete sources (dislocations, two-dimensional nucleation at corners); that is what makes hoppers, and the model has no such mechanism. The interface width (6 cells)
and the closed container (supersaturation falls as the crystal grows) also damp any instability.

Note on check 7: the driving force is `m = lambda ln S`, clipped at 0.3 (max_driving_force), so above S of about 4.5 the attachment does not get any stronger; "S = 30" in check 7 only raised the silica supply.

### 8.4 Conclusion

**Not expected in this regime: the sentence of the spec does not apply to geode amethyst grown under the conditions the evidence supports (Da << 0.1).** Separately, the model would not reproduce
hopper growth even where it is expected (diffusion-limited, large, fast crystals), because it has no step-source kinetics. That second point is a limit of the model outside its intended regime, not a
failure inside it. Options to give the model that capability (not implemented, see validation_report.md section 5 point 5): step-density (vicinal) kinetics, a two-dimensional-nucleation law for facets,
much larger crystals relative to the interface width, and 3D.
