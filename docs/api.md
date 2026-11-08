# API of the Arystal server

Start it with `python scripts/run_server.py` (local use only: it listens on 127.0.0.1:8000). Interactive documentation of every route and its fields is served at `/docs`.
The page at `/` (`test_page/index.html`) is a minimal test page, not the real frontend.

All routes depend on one function, `authenticate` (arystal/server/authentication.py). It accepts everyone today; replacing it adds authentication to every route, WebSocket included.

## Jobs (simulations that run in their own process)

| Method and path | What it does |
|---|---|
| `POST /jobs` | Start a simulation. Body: any of mode (`explore` or `research`: sets the grid, tau, time step, duration, sampling and threads), temperature_celsius (15-60), saturation_temperature_celsius, iron_ppm (null = no iron), seed, and overrides of the mode: duration, grid_width, grid_height, relaxation_time, time_step, diffusion_scheme (`explicit`, `implicit`, `uniform`), backend, threads, anisotropy_on, noise_on, fluid_ph (7-10 or null: real-time conversion only), metrics_every_steps, snapshot_every_steps. Fields not given come from the mode. 422 if a value is out of range or numerically unstable; 409 if too many jobs are active (default limit 3). |
| `GET /jobs`, `GET /jobs/{id}` | Status (`starting`, `running`, `paused`, `finished`, `failed`), step, time, current metrics, compute cost, errors. |
| `GET /jobs/{id}/metrics` | The metrics the server has seen for the job (one point per frame). |
| `POST /jobs/{id}/pause`, `/resume`, `/stop` | Control a running simulation. A stopped run is saved. 409 if the job is not an active simulation. |
| `POST /jobs/{id}/parameters` | Body `{"parameter": "temperature_celsius" \| "iron_ppm" \| "duration", "value": number}`. Applied at an exact step and recorded in the timeline. |
| `POST /ensembles` | Body `{"source": "<saved run folder name>", "replicas": 10, "workers": 5, "base_seed": null}`. Same settings and timeline as the source, one seed per replica. |
| `GET /health` | `{"status": "ok", "active_jobs": n}`. |

## Live stream

`WebSocket /jobs/{id}/stream` sends one JSON message per frame, at a steady rate (about 4 per second, independent of how fast the simulation runs):
`{"type": "frame", "sequence", "status", "step", "time", "duration", "temperature_celsius", "iron_ppm", "metrics": {...}, "crystal_png": base64, "supersaturation_png": base64}`
and, when the job ends, `{"type": "end", "status", "folder", "error"}`. The client can send `{"command": "pause" | "resume" | "stop"}` or
`{"command": "set", "parameter": ..., "value": ...}`. Frames are dropped, never queued, if a reader is slow.

## Results (files on disk)

| Method and path | What it does |
|---|---|
| `GET /results` | Saved runs and ensembles, newest first (also those from earlier sessions). |
| `GET /results/{name}` | Summary, parameters and timeline of a run, or the summary of an ensemble. |
| `GET /results/{name}/metrics` | Metrics over time of a run. |
| `GET /results/{name}/files/{path}` | Download a `.png`, `.json` or `.csv` of the result (for example `final_image.png`, `plots/growth.png`, `comparison.png`). Nothing outside the result folder can be reached. |
| `GET /results/{name}/snapshots` and `/snapshots/{step}/image` | Steps of the saved snapshots and the crystal image at one of them, to replay an animation without recalculating. |

## Notes
- The job list lives in memory: after a restart the results are still there (`/results`) but the job list starts empty.
- Values that are not available are `null` (JSON has no NaN).
- A macOS notification appears when a job that took 60 s or more ends (`notifications.py`).
- Status of a job is `finished` only after all its files are saved. (The `status` inside a frame is the state of the simulation itself.)
- Not covered: many simultaneous users, a network, a real browser (only tested with FastAPI's test client and one real server run).
