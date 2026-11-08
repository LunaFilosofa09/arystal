# Architecture

Folder layout:

| Folder | Role |
|---|---|
| `materials/` | One YAML file per material. All physical constants live here. |
| `arystal/engine/` | Physics only: phase field, diffusion, solubility, anisotropy, iron, noise, time stepping. Knows nothing about files, the server or the UI. |
| `arystal/simulation/` | Run configuration, timeline of live changes, run loop, ensemble. |
| `arystal/metrics/` | Shape, growth rates, iron statistics. |
| `arystal/storage/` | Saving and loading results, rendering images. |
| `arystal/viewer/` | Local matplotlib live viewer. |
| `arystal/server/` | FastAPI app, WebSocket stream, job manager, notifications. |
| `arystal/validation/` | The validation checks, each with a plain-language report. |
| `scripts/` | Command-line entry points. |
| `test_page/` | Minimal page to test the server (not the real frontend). |
| `results/` | Output of runs (git-ignored). |

Dependency rule: `server` -> `simulation` -> `engine`. Never the other way around.

Every simulation is a **job** (parameters in, results out, with status and compute cost).

## Results folder

`simulation/saved_run.py` runs a configured simulation (`RunConfig`, `seeded_run.py`) and `storage/` writes, in `results/<date>_<time>_<id>/`:
`params.json`, `timeline.json`, `metrics.csv`, `final_state.npz`, `snapshots/`, `plots/`, `final_image.png`, `summary.json`.
The engine never writes files and never creates random numbers itself: the run loop draws them from seeded generators and passes them in (so the engine stays a pure function of its inputs).

## Live control

`simulation/controlled_run.py` is a controller with no window and no threads: whoever drives it calls `advance` and `request_*`.
Requests wait in a queue and are applied between steps, each at an exact step number, and recorded in the timeline. The matplotlib viewer
(`viewer/control_panel.py`) only sends requests; the same controller is also driven by the job manager of the server and by the replicas of the ensemble (
which replay the recorded timeline as `scheduled_events`).

## Ensemble

`simulation/ensemble.py` builds one job per replica (same `RunConfig` and timeline events, different seed) and runs them with `ProcessPoolExecutor` in separate processes (start method "spawn", 5 workers by default),
each calling `run_and_save` into its own folder inside the ensemble folder. The parent process only collects the results and writes the statistics and pictures, so one failed replica cannot corrupt the others.
The same jobs run in this process if `workers = 1`, which gives identical results (tested).

## Server

```
browser / test page --HTTP + WebSocket--> FastAPI app (server/app.py) --> JobManager (server/job_manager.py)
                                                                                |  one OS process per job (spawn)
                                                                                v
                                                       job_worker.py: ControlledRun + RunSaver  (messages through two queues)
```
- The server only creates, controls and watches jobs. Each job (a simulation or an ensemble) runs in its own process, so a long computation never blocks the server.
- Messages from a job: `started`, `frame` (may be dropped if the reader is slow), `status`, `replica_done`, `finished` (sent only after everything is saved) and `failed`. Commands to a job: pause, resume, stop, set.
- Results are files (no database). The job list is kept in memory only.
- Every route depends on `authenticate`; the server listens on 127.0.0.1 only.
- The engine and the simulation layer know nothing about the server (the dependency goes server -> simulation -> engine).

## Speed and schemes

`solution_growth.advance_one_step` is the single entry point of the time step and dispatches on two switches of the parameters:
`backend` (`reference` = readable NumPy, the definition of the physics; `numba` = `fast_kernels.py`, same calculation, parallel) and
`diffusion_scheme` (`explicit`, `implicit`, `uniform`). The run controller (`controlled_run.py`) passes `in_place=True`, which lets the fast backend update the crystal arrays directly.
`simulation/modes.py` fixes what "explore" and "research" mean; the server and the scripts take their defaults from it.
