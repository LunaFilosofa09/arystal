# Face-speed study: what the assumed m : r : z speeds decide

Question (validation_report.md, section 5, point 3): the relative normal growth speeds of the prism m and the rhombohedra r and z are ASSUMED (0.5 : 1 : 1) and set the crystal habit.
Is there a measured value, and, if not, which features of the simulated crystal depend on them?

Run: `python scripts/face_speed_study.py` (about 11 minutes). Code: `arystal/validation/face_speed_study.py`. Results: `results/face_speed_study/` (`face_speed_study.json`, `shape_vs_speed_ratio.png`, `crystals.png`; results/ is not in git).

## 1. Literature search (what was read and what was not)

| Source | What it gives | Conditions | Access |
|---|---|---|---|
| Gratz, Bird & Quiro (1990) GCA 54, 2911-2922, doi 10.1016/0016-7037(90)90109-X | **Dissolution** rates of nominally perfect faces (negative-crystal method): prism E = 86.39 kJ/mol, A = 2.99e9 um/h; average of the rhombohedra E = 90.19 kJ/mol, A = 1.43e10 um/h. r and z not separated | 0.01 M KOH, 106-236 C | **Abstract only** (OSTI record) |
| Synthetic hydrothermal quartz (Z-cut seeds, Na2CO3) | Growth along c about 5x faster than r, and more than 150x faster than m | Industrial autoclaves, about 300-400 C, alkaline mineraliser | **Search summary only** (ScienceDirect blocked); authors not seen |
| Synthetic quartz, z-face growth 32-38 mil/day; amethyst patent: 0.1-0.2 mm/day on major-rhombohedron seeds, 0.2-0.4 on minor-rhombohedron seeds | Absolute rates in autoclaves | High T, high pressure (1500 kg/cm2), alkaline | **Search summary only** |
| Mineralogical Magazine vol. 29 (year not seen), "The growth and properties of large crystals of synthetic quartz" | Probably face rates | Autoclave | Not read (site asked for a CAPTCHA, not attempted) |
| Ihinger & Zink (2000) Nature 404, doi 10.1038/35009091 (title not seen): relative growth rates of faces of a natural Brazilian quartz from hydrogen impurities | Relative face rates in a natural crystal | Natural, conditions not seen | Title and summary only |
| Laudise, Ballman, Barns (classic synthetic quartz work) | Face rates in autoclaves | High T, NaOH / Na2CO3 | Not found / not read |
| Aspect ratios of natural geode amethyst | - | - | **Nothing found** |

Computed from Gratz et al. (abstract): dissolution rate of the prism relative to the mean rhombohedron = (2.99e9 / 1.43e10) exp(3.80 kJ/mol / RT) = **0.61 at 150 C, 0.51 at 236 C**; extrapolated outside the measured range: 0.82 at 60 C, 0.97 at 25 C.

Why none of this gives m : r : z for geode amethyst:
1. Gratz et al. measured **dissolution**, not growth. In dissolution the fastest faces vanish, in growth the slowest faces survive; the two orderings need not be the same.
2. Synthetic quartz grows at 300-400 C in NaOH or Na2CO3, 250-400 C away from the geode range and at a much higher pH; the ordering (m slowest) is the same as the model's, but the ratio (m more than 150x slower than c) is for different faces (the basal Z face does not exist on natural crystals) and conditions.
3. No measured face ratio or aspect ratio of geode amethyst was found.

**Conclusion: no LITERATURE_ESTIMATE can be given for m : r : z.** Qualitatively, every source read or seen agrees that m is the slowest growth face; that supports m < r, the order already assumed. The value 0.5 stays ASSUMED.

## 2. Sensitivity study (research resolution, 800 x 400)

Same crystal as convergence check 5 at 800 cells: 40 mm container, fluid saturated at 60 C, run at 20 C, uniform fluid on the plateau, no noise, iron at 1 ppm, grown until its equivalent radius is 120 cells (6 mm). r = 1 always.

| m | z | aspect ratio | r/m face distance | z/m face distance | Fe/Si m | Fe/Si r | Fe/Si z | iron contrast r/m | share of crystal grown by m / r / z |
|---|---|---|---|---|---|---|---|---|---|
| 0.2 | 1.0 | 1.396 | 2.058 | 2.058 | 4.78e-5 | 4.65e-4 | 2.33e-4 | 9.73 | 0.20 / 0.40 / 0.40 |
| 0.3 | 1.0 | 1.182 | 1.772 | 1.772 | 4.77e-5 | 4.65e-4 | 2.33e-4 | 9.75 | 0.22 / 0.39 / 0.39 |
| 0.4 | 1.0 | 1.038 | 1.570 | 1.570 | 4.76e-5 | 4.66e-4 | 2.33e-4 | 9.78 | 0.22 / 0.39 / 0.39 |
| 0.5 | 1.0 | 0.930 | 1.425 | 1.425 | 4.75e-5 | 4.66e-4 | 2.33e-4 | 9.81 | 0.23 / 0.39 / 0.39 |
| 0.6 | 1.0 | 0.852 | 1.307 | 1.307 | 4.74e-5 | 4.66e-4 | 2.33e-4 | 9.84 | 0.22 / 0.39 / 0.39 |
| 0.7 | 1.0 | 0.786 | 1.214 | 1.214 | 4.73e-5 | 4.67e-4 | 2.33e-4 | 9.87 | 0.22 / 0.39 / 0.39 |
| 0.8 | 1.0 | 0.728 | 1.135 | 1.135 | 4.71e-5 | 4.67e-4 | 2.33e-4 | 9.90 | 0.20 / 0.40 / 0.40 |
| 0.9 | 1.0 | 0.684 | 1.071 | 1.071 | 4.70e-5 | 4.68e-4 | 2.34e-4 | 9.94 | 0.19 / 0.40 / 0.40 |
| 1.0 | 1.0 | 0.650 | 1.020 | 1.020 | 4.68e-5 | 4.68e-4 | 2.34e-4 | 9.99 | 0.18 / 0.41 / 0.41 |
| 0.5 | 0.6 | 0.834 | 1.450 | 1.098 | 4.74e-5 | 4.64e-4 | 2.34e-4 | 9.78 | 0.23 / 0.38 / 0.39 |
| 0.5 | 0.8 | 0.882 | 1.433 | 1.269 | 4.75e-5 | 4.65e-4 | 2.34e-4 | 9.80 | 0.23 / 0.38 / 0.39 |

The baseline (m 0.5) reproduces convergence check 5 at 800 cells (aspect 0.930, r/m 1.425), as it should.

## 3. What depends on m : r : z and what does not

**Set by the assumed speeds (cannot be claimed as predictions):**
- The **aspect ratio**: from 1.40 (m 0.2) to 0.65 (m 1.0), monotonic, about -0.9 per unit of m/r near the baseline. Any stated length/width ratio is an input in disguise.
- The **r/m face distance ratio**: 2.06 to 1.02, monotonic.
- The **left-right asymmetry**: with z < r the z side lags (z/m 1.10 at z = 0.6) and the crystal leans; with z = r it is exactly symmetric (check 2).
- How pointed the termination is and how long the prism is (pictures in crystals.png).

**Not set by the speeds (within the range tested):**
- The **iron content of each sector**: Fe/Si of m, r and z changes by less than 2% over the whole sweep; the contrast r/m stays 9.7-10.0. It is fixed by the ASSUMED incorporation coefficients (0.001 / 0.01 / 0.005), not by the shape.
- The **size of the growth sectors** changes little: the m sector holds 18-23% of the crystal, r and z about 40% each, at all speeds. (At this size much of the m sector is the lower flank near the wall.)
- The **positions and orientations** of the flat faces: they follow from the crystallography (Frank's construction, check 2), whatever the speeds.
- Conservation, the regime (all runs are on the plateau) and the response to temperature and iron changes.

**Inverse problem (for when real measurements exist):** within this model a measured aspect ratio or r/m face ratio of a real section would fix m/r through the monotonic curves above
(for example aspect 0.93 gives m/r = 0.5; aspect 1.18 gives 0.3). Two cautions, both open:
1. The measured face-distance ratio is far from the ideal speed ratio (1.43 against 2.0 at m = 0.5), very probably because the distances include the initial seed (radius 48 cells, final radius 120): the ratio depends on how much the crystal grew. An inversion must use the same seed-to-size ratio as the real crystal, or subtract the seed (not tested).
2. The curves are for one size, temperature and resolution; at 800 cells the aspect ratio is still about 2% below its converged value (check 5).

## 4. Should r and z be separated?

They are already separate in the code: `facet_speed_z` is its own material entry and the r != z cases above run without changes. What "r = z" means today is only the **default value** (ASSUMED equal).
- Evidence that they differ: iron uptake differs between r and z sectors (Cohen & Hassan 1974, read), so their surfaces are not equivalent; no growth-rate ratio was found.
- What separating them would cost: nothing in code; a material value. But choosing z < r without data would replace one assumption with another and break the mirror symmetry of check 2's main test (check 2 already tests r != z).
- In a real crystal r and z alternate around the c-axis (three of each); a section through c and an m pole shows one r and one z, so r != z makes the section asymmetric, which is what real sections would show if the speeds differ.
- Recommendation: keep z = r as the default until a measurement exists; offer z as an advanced parameter if Luna wants to explore it.
