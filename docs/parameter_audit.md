# Parameter audit of materials/amethyst.yaml

Date: 2026-10-31. The tables in sections 1-4 describe the yaml **before** the audit. Proposals P1-P5 (section 5) were approved by Luna and applied the same day:
lattice constants (P1), density 2.65 -> 2.646 (P3), and status/source updates only (P2, P4, P5).

How impact was judged:
- **Existing tests**: regime study sensitivity and resolution convergence (docs/regime_study.md, sections 2 and 3), validation checks.
- **New quick test** (this audit): explore-size crystal of the regime study (200 x 100 cells, 20 C run, fluid saturated at 60 C, tau = 1e4 on the plateau,
  uniform fluid, no noise, no iron), grown to an equivalent radius of 30 cells, one parameter changed at a time. Baseline: aspect ratio 0.826, r/m face ratio 1.358.
  Scratch script, not part of the repository; the numbers are reproduced in section 3.
- **Code reading**: where each constant actually enters the engine (`arystal/simulation/material_loader.py` and its users).

Impact scale: **high** = changes a headline result (shape, colour, time) by more than about 5% within a plausible range or IMPOSES it;
**medium** = 1-5%, or affects only one output family; **low** = below 1%, or only a derived diagnostic.
Impact is on the model's outputs; it says nothing about whether the value is right.

## 1. Physical parameters

| Parameter (yaml key) | Value | Units | Status | Current source | Where it enters | Impact | Justification |
|---|---|---|---|---|---|---|---|
| `crystallography.lattice_a` | 4.9134 | angstrom | UNVERIFIED | Levien et al. 1980 (summary) | Not read by the engine; documents the angle below | low | Levien 1980 abstract and Table 5 now read: a = 4.916(1) at 1 atm (see proposal P1). Angle changes by 0.009 deg. |
| `crystallography.lattice_c` | 5.4042 | angstrom | UNVERIFIED | Levien et al. 1980 (summary) | Not read by the engine | low | Read value c = 5.4054(4) (P1). |
| `crystallography.angle_r_pole_to_c_axis` | 51.78 | degree | LITERATURE_ESTIMATE | computed from a, c | Face normals of the anisotropy and face metrics | low | 51.784 (current a, c) vs 51.775 (Levien values): 0.009 deg, far below the 1-2 deg cusp rounding. |
| `crystallography.angle_m_pole_to_r_pole` | 38.22 | degree | LITERATURE_ESTIMATE | 90 - angle above | Not read by the engine | low | Derived, documentation only. |
| `crystallography.face_families` | m, r, z | Miller-Bravais | UNVERIFIED | Phase 1 specification (unpublished) | Structure of the anisotropy | high | Defines which faces exist. Not checked against a source on geode amethyst habit. |
| `thermodynamics.quartz_solubility_log10_molal_A`, `_B` | -1107.12, -0.0254 | K, - | VERIFIED (secondary) | Takeno et al. 2000 eq. 3, quoting Rimstidt 1997 | Equilibrium silica, supersaturation | high | Sets S for each temperature. Check 4. The literature spread (6.6 vs 11.0 ppm at 25 C) is larger than any other uncertainty here. |
| `thermodynamics.quartz_solubility_valid_range` | 0-300 | C | UNVERIFIED | Rimstidt 1997 | Range check | low | Geode range is far inside. |
| `thermodynamics.quartz_solubility_check_value_25C` | 11.0 | ppm | VERIFIED (as quoted by Verma) | Verma | Check 4 target only | low | Validation target, not a model input. |
| `thermodynamics.alternative_solubility_curve` | Fournier & Potter 1982 | - | UNVERIFIED | - | Not used | low | Comparison only. |
| `thermodynamics.molar_mass_SiO2` | 60.0843 | g/mol | ASSUMED | textbook | Real crystal capacity (density scaling), molar volume Vm in the kinetic time | low | CIAAW 2024 intervals give 60.082-60.086 (P2): change below 0.003%. |
| `thermodynamics.density_quartz` | 2.65 | g/cm3 | ASSUMED | textbook | Same as above, plus mass estimate | low | Levien cell gives 2.646 (P3): -0.16%, linear in the mass and time conversion. |
| `environment.geode_temperature_min`, `_max` | 15, 60 | C | UNVERIFIED (abstract only) | Arduin Rode et al. 2024 | Allowed range of the temperature parameter | medium | Not an input of a single run, but S and kinetics depend strongly on T (regime study: T = 40 C changes the aspect ratio by -15.7% at equal size). |
| `environment.fluid_salinity` | 0 | wt% NaCl-eq | ASSUMED | Arduin Rode 2024 (0 to ~3) | Not read by the engine (pure-water curve) | low (in the model) | No salinity correction exists in the code; the effect on real solubility is not quantified here. |
| `transport.silica_diffusivity_in_water` | 1.0e-9 | m2/s | ASSUMED | order of magnitude | **Only** `time_diffusion_hours` (time_scaling.py). The model's own diffusivity is fixed to 1 (MODEL_DIFFUSIVITY) | low | New test: D x0.1 changes nothing (aspect 0.826, uniformity 0.995 identical), because the yaml D does not enter the model equations. It also enters the real-Da estimate of kinetic_regime.md, which is robust to 1-2 orders in D. Rebreanu et al. 2008 (read): 0.85-1.17e-9 m2/s at 15-25 C in pure water (P4). |
| `kinetics.quartz_rate_constant_log10_A`, `_B` | -0.7324, -3705.12 | log10(mol m-2 s-1), K | VERIFIED (secondary) | Takeno et al. 2000 eq. 6 | Kinetic time conversion `time_kinetic_years` only | high (time only) | Time is linear in 1/k+; shape unaffected on the plateau. Activation energy 71 vs 50 kJ/mol unresolved. |
| `kinetics.quartz_rate_law` | k+ (S - 1) | - | VERIFIED (secondary) | Takeno et al. 2000 eq. 1 | Kinetic time | high (time only) | Same. |
| `iron.sector_iron_ratio_r_over_z` | > 1 | - | VERIFIED (qualitative) | Cohen & Hassan 1974 | Justifies the order of the coefficients | - | Qualitative. |
| `iron.iron_in_m_sector`, `iron.boudi_morocco_zoning`, `iron.color_mechanism` | qualitative | - | ASSUMED / VERIFIED | see yaml | Documentation | - | Qualitative statements. |
| `iron.partition_coefficient_r`, `_z`, `_m` | 0.01, 0.005, 0.001 | mol/mol | ASSUMED | none | Iron per sector, colour | high (colour), none (shape) | Iron is a passive trace: shape is unaffected. Crystal iron of each sector is proportional to its coefficient, so the sector contrast (r/m 9.8 in check 3b) and the colour are set by these numbers. No quantitative source found (section 4). |
| `iron_model.default_fluid_iron` | 1.0 | ppm | ASSUMED | none | Crystal iron, colour | high (colour) | Crystal iron is proportional to fluid iron; the colour law saturates, so the effect on colour is non-linear. |
| `iron_model.color_iron_to_silicon_scale` | 4e-4 | mol/mol | ASSUMED | none | Rendered colour only | high (colour) | Sets the colour intensity for a given iron content. No metric depends on it. |
| `iron_model.iron_diffusivity_ratio` | 0.7 | - | ASSUMED | none | Iron transport in explicit/implicit schemes | low | In the uniform-fluid scheme of the modes transport is not solved; in the full schemes the iron supply is not limiting (Da << 1). Not measured here. |
| `iron_model.iron_molar_mass` | 55.845 | g/mol | ASSUMED | textbook | ppm to mol/kg | low | CIAAW 2024: 55.845(2) (P2). |
| `model_scaling.solid_silica_capacity_model` (Cs_model) | 0.002 | mol/kg | ASSUMED | model choice | Depletion of the closed container | medium | Regime study: x0.5 gives +4.6%, x2 gives -2.7% in aspect ratio. Real value about 44 mol/kg cannot be used in a closed container (documented in yaml). |
| `model_scaling.kinetic_coupling` (lambda) | 0.2 | - | ASSUMED | model choice | Driving force, capillary length | high | Regime study: x0.5 gives -9.2%, x2 gives +7.3% in aspect ratio, through the finite capillary length (a regularisation effect that shrinks with resolution). Physical in name, numerical in effect. |
| `stochastic.thermal_noise_amplitude` | 0.02 | - | ASSUMED | modelling device | Interface noise | high (ensemble spread), low (mean shape) | Sets the spread between replicas by construction; the reproducibility check shows it does not roughen the surface. Spread vs sigma not measured. |
| `stochastic.seed_radius_variation` | 0.05 | fraction | ASSUMED | modelling device | Initial seed | medium (ensemble spread) | Not measured. |
| `stochastic.seed_offset_std` | 1.0 | cells | ASSUMED | modelling device | Initial seed | medium (ensemble spread, asymmetry) | Not measured. |
| `mass_estimate.assumed_thickness` | 10.0 | mm | ASSUMED | none | Mass metric only | low (high for mass) | Mass is linear in it; nothing else uses it. |

## 2. Numerical parameters (need a convergence test, not a physical source)

| Parameter | Value | Where | Status | Impact | Justification |
|---|---|---|---|---|---|
| `phase_field_model.interface_width_in_grid_cells` | 6 | Documentation; the code uses epsilon of about 1 cell with INTERFACE_WIDTH_OVER_EPSILON = 6.2 (`engine/isotropic_params.py`) | ASSUMED | high (at explore resolution) | Not read from the yaml by the loader (finding F1). Its effect is the resolution convergence of check 5: aspect ratio 13% low at 200 cells, 2% at 800. |
| `phase_field_model.formulation` | rounded-cusp | - | UNVERIFIED | - | Description; Debierre et al. 2003 abstract only. |
| `anisotropy.cusp_sharpness` | 40 | anisotropy | ASSUMED | low (metrics), medium (facet fraction) | New test: x0.5 and x2 leave the aspect ratio unchanged (0.826), r/m -0.15% and -0.24%; the measured facet fraction drops from 0.245 to 0.222 and 0.204. |
| `model_scaling.max_driving_force` | 0.3 | phase field | ASSUMED | low (in this case) | New test: 0.2 leaves the aspect ratio unchanged and r/m -0.15%: the clip is not reached in the baseline. It could matter at very high supersaturation (not tested). |
| `iron_model.sector_transition_width` | 12 | deg | ASSUMED | medium (zoning picture) | Smooths sector boundaries; affects the look of the zoning and per-sector averages near boundaries. Not measured. |
| tau, time step, grid (modes, not in the yaml) | `simulation/modes.py` | demonstrated | - | Plateau and convergence in docs/regime_study.md. |

### Imposed habit parameters (physical in meaning, no source: they IMPOSE the shape)

| Parameter | Value | Status | Impact | New test |
|---|---|---|---|---|
| `anisotropy.facet_speed_m` | 0.5 | ASSUMED | **high** | 0.4: aspect 0.929 (+12.4%), r/m 1.471 (+8.3%); 0.6: aspect 0.771 (-6.7%), r/m 1.258 (-7.3%). |
| `anisotropy.facet_speed_r` | 1.0 | ASSUMED | sets the time unit | Reference speed; only ratios matter for shape. |
| `anisotropy.facet_speed_z` | 1.0 | ASSUMED | **high** | 0.8: aspect 0.787 (-4.7%) and breaks the left-right symmetry (check 2). |

## 3. Raw numbers of the new quick test

| Case | aspect ratio | r/m | facet fraction | uniformity |
|---|---|---|---|---|
| baseline (uniform fluid) | 0.826 | 1.358 | 0.245 | 1.000 |
| cusp_sharpness 20 | 0.826 | 1.356 | 0.222 | 1.000 |
| cusp_sharpness 80 | 0.826 | 1.355 | 0.204 | 1.000 |
| facet_speed_m 0.4 | 0.929 | 1.471 | 0.359 | 1.000 |
| facet_speed_m 0.6 | 0.771 | 1.258 | 0.185 | 1.000 |
| facet_speed_z 0.8 | 0.787 | 1.343 | 0.223 | 1.000 |
| max_driving_force 0.2 | 0.826 | 1.356 | 0.226 | 1.000 |
| baseline (implicit diffusion) | 0.826 | 1.355 | 0.226 | 0.995 |
| silica diffusivity x0.1 (implicit) | 0.826 | 1.355 | 0.226 | 0.995 |

Limits: one geometry, one temperature, explore resolution (not converged, so only relative changes are meaningful), one size; aspect ratio is measured in whole cells, so changes below about 2% are not resolved.

## 4. Source search (step 3 of the audit)

| Topic | What was found | Access | Result |
|---|---|---|---|
| a. Silica diffusivity | Rebreanu, Vanderborght & Chou (2008) Marine Chemistry 112, 230-233: measured D at salinity 0 and 36, 2-30 C, pH about 8.1. Table 1, salinity 0: 0.58 (4.2 C), 0.74 (10 C), 0.85 (15 C), 1.00 (20 C), 1.17 (25 C) x 1e-5 cm2/s. Stokes-Einstein fit D = 3.33e-12 T / eta. They say Applin (1987) found a value twice that of Wollast & Garrels in pure water at pH 5.5. | **Read** (PDF, open on vliz.be) | Supports the order of 1e-9 m2/s at 15-25 C (P4). Values above 30 C are not measured there; the units of eta in the fit are ambiguous in the extracted text, so the extrapolation to 60 C is not done here. Applin (1987) not accessed. |
| b. Lattice constants | Levien, Prewitt & Weidner (1980) Am. Mineral. 65, 920-930. Abstract: "Unit-cell parameters are a = 4.916(1) and c = 5.4054(4) A at 1 atm"; same values in Table 5. | **Read** (PDF, msaweb.org; text extraction, some OCR noise) | The yaml values (4.9134, 5.4042) are not those of Levien (P1). |
| c. Geode temperature | Arduin Rode et al. (2024) Mineralium Deposita, DOI 10.1007/s00126-024-01310-2: 15-60 C, nucleation-assisted microthermometry of one-phase inclusions and triple oxygen isotopes, meteoric, very low salinity. Gilg et al. (2003) Mineralium Deposita 38, 1009-1025 (Ametista do Sul, Brazil); a search summary says Gilg et al. (2014) cite Juchem et al. (1999) for temperatures below 50 C in Brazilian amethyst. | Abstract and press release only (paywall) | Status stays UNVERIFIED, now "abstract only". No Brazilian value read. |
| d. Iron partition by sector | No quantitative sector-resolved Fe distribution coefficient found. Qualitative: Jourdan et al. (2009, Eur. J. Mineral., DOI 10.1127/0935-1221/2009/0021-1881): sector zoning strongest between prism and rhombohedral faces (abstract only); a search summary of Noffke et al. (2019) mentions hydroxyl, not iron. Synthetic Fe-doped quartz zones of about 0.01-0.07 wt% Fe (search summary, source document not read). | Abstracts / summaries only | Coefficients stay ASSUMED. |
| e. Molar mass and density | CIAAW, Standard Atomic Weights 2024 (ciaaw.org): O [15.99903, 15.99977], Si [28.084, 28.086], Fe 55.845(2). Density: computed here from Levien's 1 atm cell (Z = 3): V = 113.13 A3, rho = 2.646 g/cm3. | CIAAW page read through a web-fetch tool that quoted the rows (not a PDF I read line by line); Levien read | P2, P3. No handbook (CRC) page was accessible. |

## 5. Proposed changes (P1-P5 approved by Luna and applied on 2026-10-31)

| # | Parameter | Old | New | Status old -> new | Source and exact text read | Effect on results |
|---|---|---|---|---|---|---|
| P1 | `lattice_a`, `lattice_c` (and recomputed `angle_r_pole_to_c_axis`, `angle_m_pole_to_r_pole`) | 4.9134, 5.4042 (51.78, 38.22) | 4.916, 5.4054 (51.78, 38.22 after rounding: 51.775 / 38.225) | UNVERIFIED -> VERIFIED | Levien et al. 1980, abstract: "Unit-cell parameters are a = 4.916(1) and c = 5.4054(4) A at 1 atm" | Angle changes by 0.009 deg. If the stored angle keeps two decimals (51.78), nothing changes in any run. |
| P2 | `molar_mass_SiO2`, `iron_molar_mass` | 60.0843, 55.845 | unchanged values | ASSUMED -> LITERATURE_ESTIMATE (SiO2: computed from CIAAW 2024 intervals, 60.082-60.086) and VERIFIED (Fe, quoted value 55.845(2)) | CIAAW 2024 rows as quoted above | None. |
| P3 | `density_quartz` | 2.65 | 2.646 (or keep 2.65) | ASSUMED -> LITERATURE_ESTIMATE (computed from Levien's cell, Z = 3, CIAAW masses) | Levien Table 5 values; Z = 3 for alpha-quartz is standard crystallography, not read in Levien's text | -0.16% in mass estimate and in the real crystal capacity; kinetic time changes by +0.16% (Vm grows). Shape unchanged. |
| P4 | `silica_diffusivity_in_water` | 1.0e-9 (ASSUMED) | 1.0e-9 kept (Rebreanu value at 20 C, salinity 0: 1.00e-9) | ASSUMED -> LITERATURE_ESTIMATE | Rebreanu et al. 2008 Table 1 (see section 4) | None on the model (the yaml D enters only `time_diffusion_hours`). Temperature dependence (factor about 2 between 4 and 25 C, they say) is not modelled. |
| P5 | `geode_temperature_min`, `_max` notes | "Seen via a news release and search summary" | add "abstract only" and the DOI | UNVERIFIED (unchanged) | Abstract | None. |

Findings that are not value changes (for Luna to decide whether to act):
- **F1**: `interface_width_in_grid_cells` is in the yaml but the loader does not read it; the engine uses its own constant in `engine/isotropic_params.py` with a comment pointing to the yaml. Same for `lattice_a`, `lattice_c`, `angle_m_pole_to_r_pole`, `fluid_salinity`. That is consistent today (6 vs 6.2 epsilon), but a change in the yaml would have no effect.
- **F2**: `silica_diffusivity_in_water` does not enter the model equations (model diffusivity is fixed to 1 in model units; the plateau makes the shape independent of it). This should be stated in its yaml note and in docs/physics_model.md.

## 6. PDFs Luna should try to obtain (paywalled or not found)

1. Applin, K.R. (1987) The diffusion of dissolved silica in dilute aqueous solution. Geochimica et Cosmochimica Acta 51(8), 2147-2151.
2. Arduin Rode, F. et al. (2024) World-class amethyst-agate geodes from Los Catalanes, northern Uruguay: genetic implications from fluid inclusions and stable isotopes. Mineralium Deposita. DOI 10.1007/s00126-024-01310-2.
3. Gilg, H.A., Morteani, G., Kostitsyn, Y., Preinfalk, C., Gatter, I. & Strieder, A.J. (2003) Genesis of amethyst geodes in basaltic rocks of the Serra Geral Formation (Ametista do Sul, Rio Grande do Sul, Brazil): a fluid inclusion, REE, oxygen, carbon, and Sr isotope study on basalt, quartz, and calcite. Mineralium Deposita 38(8), 1009-1025. DOI 10.1007/s00126-002-0310-7.
4. Gilg, H.A. et al. (2014) (Ametista do Sul geodes, low-temperature sedimentary brines, fluid inclusions and H, O, S isotopes). Mineralium Deposita 49, 861-877. DOI 10.1007/s00126-014-0522-7. Exact title and authors to be confirmed from the DOI.
5. Juchem, P.L. et al. (1999) fluid inclusion data on Brazilian amethyst (cited in Gilg et al. 2014; full reference to be taken from that paper).
6. Jourdan et al. (2009) Evidence of growth and sector zoning in hydrothermal quartz from Alpine veins. European Journal of Mineralogy. DOI 10.1127/0935-1221/2009/0021-1881. (Co-authors, volume and pages not seen: take them from the DOI.)
7. Rimstidt, J.D. (1997) Quartz solubility at low temperatures. Geochim. Cosmochim. Acta 61, 2553-2558 (still only read through Takeno et al. 2000).
8. Rimstidt, J.D. & Barnes, H.L. (1980) The kinetics of silica-water reactions. Geochim. Cosmochim. Acta 44, 1683-1699.
9. Debierre, J.-M., Karma, A., Celestini, F. & Guerin, R. (2003) Phase-field approach for faceted solidification. Phys. Rev. E 68, 041604 (free on arXiv: cond-mat/0302368; can be read without paying).
10. A standard handbook table for quartz density (CRC Handbook of Chemistry and Physics, "Physical constants of minerals") to replace the computed value of P3 by a read one.
