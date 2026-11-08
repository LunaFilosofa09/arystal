# Comparing the model with real amethyst

Until now every check compared the code with its own equations, with theory or with another numerical scheme (validation_report.md, section 5, point 4).
This document is the protocol for the first comparison with real crystals, and the tool that does it: `scripts/compare_with_observation.py`.

## 1. Three kinds of agreement (read this first)

| Kind | What it is | What it proves |
|---|---|---|
| (a) **check** | A feature of the sample that was **not** used to set any parameter, compared with the model | Evidence for (or against) the model |
| (b) **calibration** | A parameter (for example m:r:z) was **tuned** so that the model matches this value | Nothing about the model: agreement is built in. It only fixes the parameter |
| (c) **prediction** | A value of a **second, independent** sample, compared with the model calibrated on the first one | The real validation |

At least **two samples** are needed to validate: one to calibrate the assumed parameters, one to test. Every measurement in an observation file carries its role; the tool reports the three
kinds separately and refuses to call a calibration a validation.

Data sources must be approved by Luna before use (`approved_by_luna: true` in the file); until then the tool prints that the results must not be used.

## 2. What can be compared (model output: a 2D longitudinal section through the c-axis and an m pole)

| Quantity (file name) | On a real crystal | In the model | Reasonable tolerance | Role it can have |
|---|---|---|---|---|
| `aspect_ratio` | Length along c from the base (where it leaves the wall or its neighbours) to the tip, divided by the width across the prism, on a photo with scale or with a caliper. Several crystals: mean and standard deviation | `metrics.csv` aspect_ratio (bounding box height / width) at the end of the run | Observed spread of crystals (typically 10-20%) combined with the model's numerical error (13% explore, 2% research) | Calibration of m:r:z (it is set by them, face_speed_study.md); a check only if m:r:z was calibrated on something else |
| `face_ratio_r_over_m` | Distance from the crystal centre line to the r face divided by the distance to the m face (normal distances), on a section or a photo looking along a face edge | face_distance_r / face_distance_m in metrics.csv | Combined; model 5% explore, 0.5% research | Like the aspect ratio |
| `angle_m_to_r_degrees`, `apex_angle_r_to_z_degrees` | Interior angles of the outline between prism and rhombohedron (expected about 141.8 deg) and at the tip between r and z (about 76.4 deg), protractor on a photo taken square to the section | From the crystallography in the material file | +/- 1-2 deg for a careful photo | **Check of the cut and of the face identification**, not of the growth model (they are set by the lattice) |
| `sector_share_m` (and `_r`, `_z`) | Area of each growth sector (traced from colour boundaries on a polished section along c) divided by the section area | Share of silica deposited by each family (final_state.npz sector_silica) | +/- 0.05 | Check (depends weakly on m:r:z, face_speed_study.md) |
| `color_contrast_r_over_m`, `_r_over_z` | Colour intensity of r vs m (vs z) sectors: mean of a colour channel (or of 1 - brightness) inside each sector on a photo with constant lighting and a white/grey card | Ratio of the rendered colour intensities (ASSUMED colour law of the iron) | Large (factor 1.5) until the colour law is calibrated | **Calibration** of the iron coefficients or colour law at first; the **order** (r > z > m) is a check |
| Growth bands | Number and spacing of colour bands parallel to the faces | Only if the run had changes (temperature, iron, renewals) | Qualitative | Informational |

Not comparable today: absolute size and growth time (scaled model time and container), 3D shape, twinning.

## 3. Published material (none used yet; Luna must approve before any is used)

| Source | What it has | Usable numbers? | Licence / access |
|---|---|---|---|
| Cohen & Hassan (1974) Am. Mineral. 59, 719-728 | Optical spectra of amethyst and Fe-quartz by orientation; iron r > z (from Schlossin & Lang) | **No** geometric or colour measurements of sectors; only the qualitative order | PDF free on msaweb.org; copyright Mineralogical Society of America (quote / cite only) |
| Schlossin & Lang (1965) | X-ray topographs of amethyst sectors | Possibly sector geometry | **Not read**; reference to be completed |
| Troilo et al. (2015) Gems & Gemology 51(1), "Amethyst from Boudi, Morocco" | Photos of hourglass colour zoning on rhombohedral sectors | Angles and sector order could be measured on the published photos, if the scale and orientation are given | Read as web text; copyright GIA: measuring from a figure for research and citing it is usually acceptable, reproducing the image is not without permission. **Luna to decide** |
| "Genesis and gemological quality of amethyst from different Brazilian deposits" (Pesquisas em Geociencias, UFRGS) | Brazilian amethyst description | Unknown | Open journal; **not read** |
| Brazilian Journal of Geology (2020), colourless geode quartz from the Serra Geral Group, irradiation colour zones | Zoning in geode quartz (not amethyst) | Possibly band patterns | Open access (DOAJ); **not read** |
| Mineral dealer photos (Uruguay, Brazil) | Many geode sections | No scale or orientation control; not scientific | Copyright of the sellers: not usable |

Conclusion: **no published dataset with usable numbers was found.** The most promising route is Luna's own measurements (section 4), plus Troilo et al. (2015) photos if Luna approves.

## 4. What Luna can measure without a laboratory

What to get: two or more amethyst geode pieces (ideally from the same geode and from a second geode or locality, for calibration and test); a cut slab through a crystal parallel to its long axis if a
lapidary shop can cut one (most sell polished geode slices: choose one where the crystals are cut lengthwise); a digital caliper (0.01 mm); a ruler with mm marks; a protractor or a photo-angle app; a white sheet and a grey card.

Photos:
1. Daylight from a window, no direct sun, no flash; or two identical lamps at 45 degrees on both sides. Always the same light for all photos.
2. Put the mm ruler and the grey card next to the crystal, in the same plane.
3. Camera square to the surface (phone parallel to the table; check with a level app), at 20-30 cm, no zoom distortion (use the 1x lens).
4. For each crystal: one photo looking at the prism face (side view) and one looking down the c-axis if possible.
5. Save the original files (no filters). Name them sample_crystalNumber_view.jpg.

Measurements (at least 10 crystals per sample, so that mean and spread are meaningful):
1. **Length** along the c-axis: from where the crystal leaves the geode wall (or its neighbours) to the tip, with the caliper. **Width** across two opposite prism faces just below the termination.
2. If the prism faces are hidden (common in geodes, where crystals grow side by side), write "prism not visible" and measure the width of the termination base instead; that is a different quantity and gets a different name.
3. On a cut slab along c: trace the colour boundaries (the hourglass of r/z sectors and the prism sectors) on a printed photo or in a free image program; measure each region's area (count squares on graph paper or use the program's area tool).
4. Angles: on the side-view photo, the angle between the prism edge and the rhombohedral face edge, and the tip angle.
5. Colour: on the slab photo, take the average colour inside each sector (most image programs show RGB values); record the grey card values too, to correct for the light.
6. Write everything in a copy of the file below, with the uncertainty = standard deviation over the crystals (for a single measurement: half the smallest division you can read).

## 5. Observation file (template)

```yaml
sample_id: GEODE_A          # one file per sample
source: "Luna, own measurement, geode from <locality>, bought <where>, <date>"
fictitious: false
approved_by_luna: true      # Luna sets this after checking the data
image: GEODE_A_slab.jpg     # optional photo, relative to this file
measurements:
  aspect_ratio: {value: 1.8, uncertainty: 0.3, units: dimensionless, role: calibration, how_measured: "caliper, 12 crystals, mean +/- std"}
  apex_angle_r_to_z_degrees: {value: 76.0, uncertainty: 1.5, units: degree, role: check, how_measured: "protractor on photo"}
```

Example with invented numbers, to test the code only: `examples/observation_example_FICTITIOUS.yaml` (marked `fictitious: true`; the tool prints that nothing can be concluded).

## 6. Running the comparison

```bash
python scripts/compare_with_observation.py path/to/GEODE_A.yaml results/<run folder>
```

Output: a table (observed, simulated, difference, tolerance, within tolerance, role), the summary by role and an honest status line; `comparison.csv` and `comparison.png`
(photo, simulated crystal, values) in `results/<run folder>/comparison_<sample id>/`. The tolerance is 2 x sqrt(u_obs^2 + u_model^2), with the model's numerical uncertainty from validation check 5.
Use a research-mode run for any number that will be reported.

## 7. The path to a real validation

1. Sample A: calibrate m:r:z on its aspect ratio and face ratio, and the colour law on its colour contrast (role: calibration).
2. Same sample: check the angles, the sector order and the sector shares (role: check).
3. Sample B (another geode): run the calibrated model with B's conditions (as far as known) and compare everything (role: prediction). Only this step can support the claim that the model reproduces amethyst.
