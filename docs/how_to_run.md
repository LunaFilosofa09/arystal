# How to run

## One-time setup

The project uses Python 3.12 inside a virtual environment in `.venv`, created with `uv`.

```bash
git clone https://github.com/LunaFilosofa09/arystal.git
export PATH="$HOME/.local/bin:$PATH"      # so the terminal finds uv
cd arystal                                 # the folder where the repository was cloned
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

## Every time you work on the project

```bash
cd path/to/arystal                         # the folder where the repository was cloned
source .venv/bin/activate
```

## Check that the installation works

```bash
python -c "import numba, numpy, scipy, yaml, matplotlib, fastapi; print('ok')"
```

## Notes

- `numba` is pinned to 0.61.2 because the newest version has no prebuilt package for
  Intel Macs and would need a compiler toolchain (cmake) to install.

## Isotropic growth

```bash
python scripts/run_isotropic.py                       # live window (close it to finish)
python scripts/run_isotropic.py --driving-force 0.2   # faster growth
python scripts/run_isotropic.py --no-window --png final.png   # no window, save a picture
python scripts/validate.py isotropic                  # validation check 1 (about 15 s)
```

## Silica, solubility, temperature

```bash
python scripts/run_growth.py                                  # live window, run at 40 C, fluid saturated at 60 C
python scripts/run_growth.py --temperature 20 --duration 8000 # colder = more supersaturation = faster growth
python scripts/run_growth.py --no-window --png out.png --duration 3000
python scripts/validate.py mass                               # check 3 (about 25 s)
python scripts/validate.py solubility                         # check 4 (instant)
python scripts/validate.py all                                # checks 1, 3 and 4 (about 45 s)
```

Temperatures must be between 15 and 60 C. A full-size run is slow (about 2.5 ms per step):
8000 time units = 80000 steps = about 3 minutes. Growth is limited by silica diffusion, so the
crystal grows slowly and the "time" in the title is model time, not real time (see docs/physics_model.md).

## Amethyst shape

```bash
python scripts/run_growth.py --isotropic                      # round growth, for comparison
python scripts/run_growth.py --relaxation-time 40 --time-step 0.2 --duration 12000 --grid-width 300 --grid-height 160
python scripts/validate.py symmetry                           # check 2 (about 30 s)
python scripts/validate.py all                                # all checks (about 90 s)
```

Anisotropy is on by default in `run_growth.py`. IMPORTANT: this script's default fast attachment kinetics
(`--relaxation-time 1`, the original provisional value) are above the plateau of the regime study: growth is limited by silica diffusion
and the crystal stays round. Real growth is surface-limited; the explore and research modes set tau on the plateau.
See the "Regime problem" section of docs/physics_model.md (resolved) and docs/regime_study.md.

## Iron and color

```bash
python scripts/run_growth.py --iron-ppm 1.0                   # with iron: the left panel shows the colour
python scripts/validate.py iron                               # iron conservation and sector zoning (about 3.5 minutes)
python scripts/estimate_regime.py                             # diffusion- vs surface-limited estimate (instant)
```

Colour is computed from the iron locked into the crystal with ASSUMED coefficients and an ASSUMED colour law.

## Saved runs, seeds and metrics

```bash
python scripts/run_saved.py --duration 2000 --seed 1          # run and save everything to results/<date>_<time>_<id>/
python scripts/run_saved.py --duration 2000 --seed 2          # same settings, other seed: slightly different crystal
python scripts/run_saved.py --duration 2000 --seed 1 --no-noise --no-iron
python scripts/run_saved.py --replay results/<folder>         # repeat a saved run exactly (same params.json)
python scripts/validate.py reproducibility                    # seed reproducibility and saved files (about 1 minute)
```

What is inside a results folder: `params.json` (all settings, seed, mode, software version, material constants), `timeline.json` (live changes; empty if nothing was changed),
`metrics.csv` (metrics over time), `final_state.npz` (full-precision final grids), `snapshots/` (compressed grids every `snapshot_every_steps`, float32),
`plots/` (PNG graphs), `final_image.png`, `summary.json` (headline results, conservation, compute cost, and the **scientific caveats** that go with the run).
Read the `scientific_status` block of summary.json before using any number: it states what is imposed by assumption, the model Da of the run and whether it is on the plateau of the regime study (a warning if not).

## Live control

```bash
python scripts/run_live.py                                     # window with sliders and buttons (200 x 100 grid, "explore" size)
python scripts/run_live.py --temperature 30 --duration 6000 --seed 4 --relaxation-time 40
python scripts/run_saved.py --replay results/<folder>          # repeat a live session exactly, timeline included
python scripts/validate.py live                                # live-control checks (about 3 minutes)
```

In the window: **T slider** (15-60 C) and **Fe slider** (dissolved iron, ppm; only if iron is simulated), **Pause / Resume**, **Extend +50%** (lengthens the duration), **Stop and save**.
Closing the window also stops and saves. Every change is recorded at the exact step it took effect in `timeline.json`, so the session can be reproduced.
The run is saved in `results/<date>_<time>_<id>/` when it ends (same files as a saved run).

Assumptions: a temperature change is an instantaneous jump of the solubility (drag the slider in small steps for a gradual cooling); an iron change renews the fluid with the new concentration
(adds or removes iron: the iron balance in `metrics.csv` discounts what was added). Neither is a claim about how conditions change in a real geode.

## Ensemble of replicas

```bash
python scripts/run_saved.py --duration 2400 --seed 21                       # (or run_live.py) a first run
python scripts/run_ensemble.py --from results/<folder of that run>          # 10 replicas, 5 at a time
python scripts/run_ensemble.py --from results/<folder> --replicas 10 --workers 3
python scripts/validate.py ensemble                                         # ensemble checks (about 30 seconds)
```

`--from` takes the settings and the **recorded timeline** (live changes included) of a saved run; every replica uses them, with its own seed derived from the base seed
(the seed of the saved run, or `--base-seed`). The ensemble folder `results/<date>_<time>_<id>_ensemble/` contains: the replica folders (`replica_01_seed...`, each a complete run),
`ensemble_summary.json` (mean, standard deviation, min and max of every metric over the replicas, seeds, compute cost and caveats), `ensemble_metrics.csv` (mean and std over time),
`comparison.png` (the final crystals side by side, same scale), and mean +/- std graphs (`ensemble_size.png`, `ensemble_shape.png`, `ensemble_faces.png`, `ensemble_iron.png`).

Cost: replicas share the machine, so each one runs slower than alone. Measured on this Mac (240 x 120 grid, 24000 steps): 95 s alone, 219 s each with 5 in parallel,
so 10 replicas took 439 s instead of about 945 s serially (real speed-up about x2.2, not x5). Fewer workers may be more efficient; see docs/benchmark.md for the later measurement.

## Server and test page

```bash
python scripts/run_server.py                     # then open http://127.0.0.1:8000 in a browser
python scripts/run_server.py --port 8010
python scripts/validate.py server                # server checks (about 2 minutes)
```

The page lets you start a simulation, watch the crystal and the supersaturation live (about 4 frames per second), move the temperature and iron sliders, pause/resume/stop,
see metric graphs, list past results and launch a 10-replica ensemble from any saved run. All routes are listed in [api.md](api.md) (and, with the server running, at http://127.0.0.1:8000/docs).
The server only listens on this computer. A notification appears on macOS when a job that took 60 seconds or more finishes.

## Modes, speed, studies, validation

```bash
python scripts/run_saved.py --seed 1                      # explore mode: 200 x 100, a few seconds
python scripts/run_saved.py --mode research --seed 1      # research mode: 800 x 400, about 1.5 minutes
python scripts/run_live.py --mode explore                 # live window (fast enough to see the crystal grow)
python scripts/run_ensemble.py --mode explore --temperature 20      # 10 replicas without a saved run
python scripts/benchmark.py                               # speed on this computer (about 3 minutes)
python scripts/regime_study.py --taus 1 100 10000         # regime map (minutes); --sensitivity 10000 for the sensitivity table
python scripts/validate.py all                            # every check (about 30 minutes)
python scripts/validate.py fast | implicit | convergence | qualitative     # checks 6, 6b, 5, 7 separately
```

Optional fluid pH (7-10). It changes only `time_kinetic_years` (the real-time conversion), never the simulated crystal; without it the Takeno law is used.
See docs/kinetic_regime.md section 10 for the sources and the caveats.

```bash
python scripts/run_saved.py --temperature 20 --fluid-ph 9   # same crystal as without pH, shorter real time
python scripts/validate.py ph_rate                          # check 4b (instant)
python scripts/estimate_regime.py                           # regime tables, the second one with pH 7-10
```

Every option can override the mode (`--grid-width`, `--relaxation-time`, `--diffusion-scheme explicit|implicit|uniform`, `--backend reference`, `--threads`...). In the default modes model durations are long (millions of model time units)
because growth is slow compared with diffusion; `metrics.csv` has `time_kinetic_years` (real-time conversion, see docs/physics_model.md). The first run of Numba code compiles it (a few seconds, cached afterwards).


## Fluid renewal pulses (open system)

```bash
python scripts/run_saved.py --temperature 20 --renewal-interval 200000                       # renew the fluid every 200000 model time units
python scripts/run_saved.py --temperature 20 --renewal-interval 200000 --renewal-saturation 50   # renewed fluid saturated at 50 C
python scripts/validate.py renewal                                                            # check of the renewals (about 1 minute)
```
Without `--renewal-interval` the container is closed, as before. The server accepts the same fields and a live change `fluid_renewal_saturation_celsius`.

## Comparing a run with a real amethyst

```bash
python scripts/run_saved.py --mode research --seed 1
python scripts/compare_with_observation.py examples/observation_example_FICTITIOUS.yaml results/<run folder>   # FICTITIOUS example: tests the code only
```
How to measure a real sample and write its file: docs/observation_comparison.md.

