# Growth-time tension (open decision 6 of kinetic_regime.md)

Status: **OPEN.** None of the candidate explanations below is demonstrated. They are quantified so that the size of the gap and what would be needed to close it are clear.
The simulation model was not changed for this analysis.

## 1. The tension

With the quartz rate law of Takeno et al. (2000), growth per unit area is `k+(T) (S - 1)` and a face advances at `Vm k+ (S - 1)`. Growing one face by 10 cm at S = 2 takes
5.4e9 years at 15 C, 5.1e8 at 40 C and 1.0e8 at 60 C (scripts/estimate_regime.py). The simulated runs report 1e7 to 1e9 years for crystals of millimetres to centimetres (`time_kinetic_years`).
Time is linear in crystal size and in 1 / (S - 1), so 1 cm takes ten times less and S = 10 nine times less.

## 2. How much time was available

| Item | Value | Source and access |
|---|---|---|
| Age of the host basalts (Parana-Etendeka) | 134.7 +/- 1 Ma, short eruption (new ages "statistically indistinguishable" from that value) | Thiede & Vasconcelos (2010) Geology 38, 747-750: **abstract and introduction read** (PDF) |
| Main phase of volcanism | 1.6-3.0 Myr, start 135.0 +/- 0.6 Ma | Gomes & Vasconcelos (compilation of 378 Ar-Ar and 32 U-Pb ages): **search summary only** (UNVERIFIED) |
| Timing of amethyst at Los Catalanes | After the emplacement of the complete basalt pile; episodic infiltration of meteoric water, open- and closed-system crystallisation; 15-60 C | Arduin Rode et al. (2024): **abstract only** |
| Direct age of geode mineralisation | 40Ar/39Ar dating of celadonite in amethyst geodes exists as an AGU abstract (Vasconcelos 1998); secondary summaries mention celadonite ages of about 70 Ma and geode filling 20-60 Myr after the basalts, with scattered ages | **Title only / unattributed search summaries** (UNVERIFIED). No number from a primary source was read |
| Growth duration of a geode crystal | **No measurement found.** Popular sources say "millions of years" without data | - |

Upper bound: the crystals cannot be older than about 135 Myr. If the celadonite age of about 70 Ma (unverified) dated the geode stage, growth could have taken place anywhere in a window of tens of Myr,
but nothing says growth was continuous; episodic infiltration (Arduin Rode et al. 2024) suggests it was not. A real growth budget is therefore **unknown**: this document uses 1, 10 and 100 Myr.

## 3. Candidate explanations, one by one

Speed-up = (time with the Takeno law at S = 2) / (time with the candidate). Da is the Damkohler number for a 10 cm crystal (D = 1e-9 m2/s); the plateau of the model is Da below about 0.06.

| # | Candidate | Speed-up | Published evidence (and how it was accessed) | Da still << 1? |
|---|---|---|---|---|
| a | **Alkaline fluid** (base mechanism of Palandri & Kharaka 2004) | pH 8 / 9 / 10: x5 / x14 / x44 at 15 C; x16 / x49 / x153 at 40 C; x38 / x116 / x363 at 60 C (with the printed base constant; about 50x less with the alternative -17.98) | Rate law read (USGS OFR 2004-1068). pH of basalt groundwater today 6.7-9.95 (search summaries, UNVERIFIED). **No pH of the amethyst-forming fluid found** | Yes, except 60 C + pH 10 + 10 cm (Da about 0.1, marginal); see kinetic_regime.md section 10 |
| b | **Warmer early stage** (> 60 C) | Takeno law: x4.3 at 80 C, x15.6 at 100 C, relative to 60 C | Arduin Rode et al. (2024): 15-60 C (abstract). One unattributed search snippet gives 40-80 C for amethyst at Ametista do Sul; Gilg et al. (2003) and (2014) not read. **No read source supports > 60 C** | Yes (Da grows with k+: about 5e-3 at 100 C for 10 cm, before the faster diffusion at that temperature) |
| c | **Smaller crystals** | Linear: 1 cm is x10 faster than 10 cm, 5 mm x20 | Typical crystal sizes in these geodes not looked up in a source | Yes (Da proportional to size) |
| d | **Higher supersaturation** (fluid saturated with amorphous silica or chalcedony) | From S = 2 to S = 10: x9 (time proportional to 1 / (S - 1)). Cooling a quartz-saturated fluid from 60 to 15 C gives only S = 3.3 | Mineral sequence celadonite / chalcedony then amethyst (search summary of Gilg et al. 2014, UNVERIFIED). Amorphous silica solubility not read in a source here (about 10x quartz at 25 C: general knowledge, UNVERIFIED) | Yes: Da does not depend on S |
| e | **Another mechanism** (silica gel, opal or chalcedony precursor recrystallising to quartz) | Not quantifiable with the information read | Chalcedony/agate in the same geodes (search summaries). No read source describes amethyst growing through a precursor | Not applicable: the rate law and Da refer to growth from solution |
| f | **Reactive surface different from the geometric one** | The rate per unit geometric area is 3.9x the rate per unit BET area in Palandri & Kharaka's quartz data (log k -13.40 vs -13.99): a rough surface reacts up to a few times faster than its outline. Plausible range x0.25 to x4 | Palandri & Kharaka (2004), Table 4 (read) | Yes |
| g | **k+ does not extrapolate** to these conditions | Temperature: none needed: quartz rate data exist at 23-70 C (Palandri & Kharaka Table 3, read: log k = -13.41 and -13.38 at 23 C, against -13.24 from the Takeno law). Near equilibrium, a spiral-growth law (rate proportional to (S - 1)^2 at low S) would make growth **slower**, not faster (general crystal-growth theory, not looked up). Face-specific rates: unknown | Partly read | Yes |

Remarks:
- The rate law of Takeno and the neutral term of Palandri & Kharaka agree within a factor of 2.5 at 15-60 C, so the gap is not an artefact of one constant.
- Candidates a, b, c, d and f multiply; e and g cannot be quantified.
- In the closed container of the model S falls as the crystal grows, which makes growth slower than the constant-S estimates above.

## 4. What combination is needed to grow X cm in Y Myr

Required speed-up over the Takeno law at S = 2 (one face advancing X cm):

| Budget | 0.5 cm | 1 cm | 5 cm | 10 cm |
|---|---|---|---|---|
| 1 Myr, 15 / 40 / 60 C | 270 / 26 / 5 | 540 / 51 / 10 | 2700 / 260 / 50 | 5400 / 510 / 100 |
| 10 Myr, 15 / 40 / 60 C | 27 / 2.6 / 0.5 | 54 / 5.1 / 1 | 270 / 26 / 5 | 540 / 51 / 10 |
| 100 Myr, 15 / 40 / 60 C | 2.7 / 0.3 / 0.05 | 5.4 / 0.5 / 0.1 | 27 / 2.6 / 0.5 | 54 / 5.1 / 1 |

How the candidates can reach these factors (examples, not claims):
- **1 cm in 10 Myr at 40 C** needs x5: S = 6 alone (x5), or pH 8 alone (x16), or a rough surface (x4) with S = 2.3.
- **10 cm in 10 Myr at 15 C** needs x540: pH 10 (x44) and S = 10 (x9) together give x400, almost; nothing read supports both.
- **10 cm in 1 Myr at 15 C** needs x5400: not reachable with the factors above, even all combined at their read upper ends (x44 x9 x4 = x1600), unless the crystal grew warmer.
- **Anything at 60 C** is within reach of one factor for budgets of 10 Myr or more.

## 5. Assessment (with the confidence the evidence allows)

1. **The tension is real but not large for centimetre crystals and generous budgets.** At 40-60 C a 1 cm crystal needs a speed-up of only 0.1-5 in 10-100 Myr. It is severe only for 5-10 cm crystals grown at 15-25 C in about 1 Myr.
2. **Most plausible contributors** (none demonstrated): higher supersaturation (d), since it needs no change of chemistry and the geodes contain earlier chalcedony; and a mildly alkaline fluid (a), since basaltic groundwater is often at pH 8-9.
   Together they give x25-x130 at 15 C (S = 6 with pH 8, up to S = 10 with pH 9). Confidence: **low**: both the fluid supersaturation and its pH are unmeasured for the amethyst stage.
3. A warmer stage (b) is not supported by the only temperature source read (15-60 C, abstract). Smaller crystals (c) and surface roughness (f) help by small factors. A precursor mechanism (e) cannot be evaluated.
4. **The growth budget itself is unknown**: no read source gives the age or duration of the amethyst stage. This, not the rate law, is the largest uncertainty.
5. **Regime**: every candidate keeps Da below the plateau threshold except the most alkaline and warmest corner for 10 cm crystals (marginal). The surface-limited assumption of the model is not threatened by any explanation of the time tension.

## 6. What would settle it

- Read Arduin Rode et al. (2024) and Gilg et al. (2014, open access in the Bern repository BORIS) for temperatures, salinity, isotopes and any timing; Gilg et al. (2003) for Ametista do Sul.
- A primary radiometric age of the geode stage (the Vasconcelos 1998 celadonite work or later papers that cite it).
- The pH and silica content of the amethyst-forming fluid (fluid-inclusion chemistry), or of present geode water if it was sampled (Arduin Rode et al. 2024 sampled geode water).
- Face-specific quartz growth rates at low temperature.
