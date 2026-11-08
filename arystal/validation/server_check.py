"""Validation of the server, through FastAPI's test client with real job processes.

Tests:
  A. A job runs in its own process: the server keeps answering while it runs, and the job ends with its results saved and its cost reported.
  B. Control through the API: pause really stops the run, a parameter change is recorded in the timeline, stop ends and saves the run,
     and the saved run is reproduced exactly by replaying its timeline in the library.
  C. The WebSocket stream: frames arrive at a steady rate that does not depend on the simulation speed, with decodable pictures and
     JSON-safe metrics; commands sent through the WebSocket reach the job.
  D. Bad requests are refused (out-of-range or unstable settings, unknown jobs, commands to finished jobs, too many jobs, path tricks).
  E. Past results can be listed and loaded: summary, metrics, pictures and snapshot images.
  F. An ensemble can be launched through the API from a saved run.
  G. Notifications: a long job triggers one, a short one does not, and the AppleScript text is escaped safely.
  H. Authentication hook: replacing `authenticate` rejects every route, so authentication can be added without rewriting the routes.

WHAT THESE TESTS DO NOT SHOW: behaviour with a real browser, many simultaneous users, or on a network (the server is for local use only).
"""

import base64
import json
import tempfile
import time
import warnings
from pathlib import Path

import numpy as np

from arystal.engine.material_constants import MaterialConstants
from arystal.server.app import create_app
from arystal.server.authentication import authenticate
from arystal.server.job_manager import JobManager
from arystal.server.notifications import build_notification_script, escape_for_applescript, notify_macos
from arystal.simulation.controlled_run import run_to_end
from arystal.simulation.saved_run import load_run_for_replay
from arystal.storage.serialization import read_json
from arystal.storage.snapshots import FINAL_FIELDS, load_final_state
from arystal.validation.check_result import CheckResult

warnings.filterwarnings("ignore", message=".*httpx.*")

LIMITS_NOTE = (
    "Limits: tested with FastAPI's test client on this computer, not with a real browser, many users or a network (the server is for local use only)."
)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# Settings given explicitly (explicit diffusion, small tau, short steps) so the mechanics tests do not depend on the mode defaults.
SMALL_JOB = {"grid_width": 60, "grid_height": 30, "duration": 300, "seed": 4, "temperature_celsius": 30, "metrics_every_steps": 500, "snapshot_every_steps": 1000,
             "relaxation_time": 1.0, "time_step": 0.1, "diffusion_scheme": "explicit", "seed_radius": 15.0, "threads": 1}
LONG_JOB = {**SMALL_JOB, "duration": 3000}
WAIT_SECONDS = 90.0
POLL_SECONDS = 0.1
MAX_HEALTH_LATENCY_SECONDS = 1.0
FRAME_SECONDS_RANGE = (0.1, 0.6)  # the job produces a frame every 0.25 s
STREAM_SAMPLE_SECONDS = 2.5
MAX_FRAME_RATE_DIFFERENCE = 0.4  # fast and slow simulations may differ by at most this fraction in frames per second


def make_client(root: Path, **manager_options):
    """Return (client, manager) for an app that stores its results in `root`."""
    from fastapi.testclient import TestClient

    manager = JobManager(root, **manager_options)
    return TestClient(create_app(root, manager)), manager


def wait_until(condition, description: str, timeout: float = WAIT_SECONDS):
    """Poll until `condition()` returns something truthy, and return it. Raises AssertionError if it takes too long (so a test fails instead of hanging)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = condition()
        if value:
            return value
        time.sleep(POLL_SECONDS)
    raise AssertionError(f"Timed out waiting for: {description}")


def wait_for_job(client, job_id: str, statuses=("finished", "failed")) -> dict:
    """Wait until the job has one of the statuses and return its description."""
    return wait_until(lambda: (lambda job: job if job["status"] in statuses else None)(client.get(f"/jobs/{job_id}").json()), f"job {job_id} in {statuses}")


def start_job(client, settings: dict) -> str:
    """Start a job through the API and return its id."""
    response = client.post("/jobs", json=settings)
    assert response.status_code == 201, response.text
    return response.json()["job_id"]


def check_job_isolated_and_complete(root: Path) -> CheckResult:
    """Test A (also tests G, the notification of a long job, with a notification threshold of zero)."""
    sent = []
    client, manager = make_client(root, notifier=lambda title, message: sent.append((title, message)), notify_after_seconds=0.0)
    with client:
        job_id = start_job(client, LONG_JOB)
        latencies = []
        wait_until(lambda: client.get(f"/jobs/{job_id}").json()["status"] == "running", "job running")
        for _ in range(5):
            started = time.time()
            health = client.get("/health").json()
            latencies.append(time.time() - started)
            time.sleep(0.2)
        client.post(f"/jobs/{job_id}/stop")
        job = wait_for_job(client, job_id)
        folder = root / job["folder"]
        files_ok = all((folder / name).exists() for name in ("summary.json", "metrics.csv", "timeline.json", "final_state.npz", "final_image.png"))
        cost = job["compute_cost"] or {}
    slowest = max(latencies)
    passed = health["active_jobs"] >= 1 and slowest <= MAX_HEALTH_LATENCY_SECONDS and job["status"] == "finished" and files_ok and cost.get("steps", 0) > 0 and len(sent) == 1
    message = (
        f"Server answered {len(latencies)} times while the job ran (slowest {1000 * slowest:.0f} ms, limit {1000 * MAX_HEALTH_LATENCY_SECONDS:.0f} ms); "
        f"job finished with all result files: {files_ok}; compute cost reported: {cost.get('steps')} steps, {cost.get('wall_clock_seconds', 0):.1f} s; "
        f"notification sent once for the long job: {len(sent)}."
    )
    return CheckResult("jobs run in their own process; server stays responsive; results and cost are saved", passed, message)


def wait_for_step_to_stop(client, job_id: str) -> tuple[int, int]:
    """After a pause, return (step, step a moment later); they must be equal."""
    wait_until(lambda: client.get(f"/jobs/{job_id}").json()["status"] == "paused", "job paused")
    time.sleep(0.5)
    first = client.get(f"/jobs/{job_id}").json()["step"]
    time.sleep(0.8)
    return first, client.get(f"/jobs/{job_id}").json()["step"]


def check_control_and_replay(root: Path, material: MaterialConstants) -> CheckResult:
    """Test B."""
    client, _ = make_client(root)
    with client:
        job_id = start_job(client, LONG_JOB)
        wait_until(lambda: (client.get(f"/jobs/{job_id}").json()["step"] or 0) > 200, "job advancing")
        client.post(f"/jobs/{job_id}/pause")
        before, after = wait_for_step_to_stop(client, job_id)
        client.post(f"/jobs/{job_id}/parameters", json={"parameter": "temperature_celsius", "value": 20.0})
        client.post(f"/jobs/{job_id}/resume")
        wait_until(lambda: client.get(f"/jobs/{job_id}").json()["step"] > after + 100, "job advancing again")
        client.post(f"/jobs/{job_id}/stop")
        job = wait_for_job(client, job_id)
    folder = root / job["folder"]
    timeline = read_json(folder / "timeline.json")
    parameters = [event["parameter"] for event in timeline["events"]]
    config, events = load_run_for_replay(folder)
    replayed, _ = run_to_end(config, material, events)
    saved = load_final_state(folder)
    identical = all(np.array_equal(saved[name], getattr(replayed, name)) for name in FINAL_FIELDS)
    passed = before == after and parameters == ["temperature_celsius", "duration"] and identical and job["status"] == "finished"
    message = (
        f"Step did not move while paused ({before} -> {after}); timeline events recorded: {parameters} (expected temperature then duration, the stop); "
        f"replaying the saved timeline in the library reproduces the saved result exactly: {identical}."
    )
    return CheckResult("pause, parameter change and stop work through the API and the run is reproducible", passed, message)


def read_stream(client, job_id: str, seconds: float, commands: list[dict] | None = None) -> list[tuple[float, dict]]:
    """Collect (arrival time, frame) pairs from the WebSocket for `seconds`, sending the commands at the start."""
    frames = []
    with client.websocket_connect(f"/jobs/{job_id}/stream") as stream:
        for command in commands or []:
            stream.send_text(json.dumps(command))
        started = time.time()
        while time.time() - started < seconds:
            message = json.loads(stream.receive_text())
            if message["type"] == "frame":
                frames.append((time.time() - started, message))
            else:
                break
    return frames


def frame_is_valid(frame: dict) -> bool:
    """True if a frame has decodable PNG pictures, JSON-safe metrics and the expected fields."""
    pictures = [base64.b64decode(frame[key]) for key in ("crystal_png", "supersaturation_png")]
    fields = all(key in frame for key in ("step", "time", "status", "metrics", "temperature_celsius"))
    metrics_ok = "crystal_area_mm2" in frame["metrics"] and all(value is None or isinstance(value, (int, float)) for value in frame["metrics"].values())
    return all(picture.startswith(PNG_SIGNATURE) for picture in pictures) and fields and metrics_ok


def measure_frame_rate(client, settings: dict) -> float:
    """Start a job, read its stream for a few seconds and return frames per second; the job is then stopped."""
    job_id = start_job(client, settings)
    wait_until(lambda: client.get(f"/jobs/{job_id}").json()["status"] == "running", "job running")
    frames = read_stream(client, job_id, STREAM_SAMPLE_SECONDS)
    client.post(f"/jobs/{job_id}/stop")
    wait_for_job(client, job_id)
    return len(frames) / frames[-1][0] if len(frames) > 1 else 0.0


def check_websocket_stream(root: Path) -> CheckResult:
    """Test C."""
    client, _ = make_client(root)
    with client:
        job_id = start_job(client, LONG_JOB)
        wait_until(lambda: client.get(f"/jobs/{job_id}").json()["status"] == "running", "job running")  # the process needs a moment to start
        frames = read_stream(client, job_id, STREAM_SAMPLE_SECONDS, [{"command": "pause"}])
        paused_seen = any(frame["status"] == "paused" for _, frame in frames)
        client.post(f"/jobs/{job_id}/stop")
        wait_for_job(client, job_id)
        intervals = np.diff([arrival for arrival, _ in frames])
        valid = all(frame_is_valid(frame) for _, frame in frames)
        slow_rate = measure_frame_rate(client, {**LONG_JOB, "grid_width": 200, "grid_height": 100})
        fast_rate = measure_frame_rate(client, {**LONG_JOB, "grid_width": 40, "grid_height": 20})
    mean_interval = float(np.mean(intervals)) if len(intervals) else float("inf")
    rate_difference = abs(slow_rate - fast_rate) / max(fast_rate, 1e-9)
    passed = (
        len(frames) >= 3 and FRAME_SECONDS_RANGE[0] <= mean_interval <= FRAME_SECONDS_RANGE[1] and valid and paused_seen
        and rate_difference <= MAX_FRAME_RATE_DIFFERENCE
    )
    message = (
        f"{len(frames)} frames in {STREAM_SAMPLE_SECONDS} s, mean interval {mean_interval:.2f} s (expected {FRAME_SECONDS_RANGE[0]}-{FRAME_SECONDS_RANGE[1]}); "
        f"pictures and metrics valid: {valid}; a 'pause' sent through the WebSocket reached the job: {paused_seen}; "
        f"frames per second with a 200x100 grid {slow_rate:.1f} vs a 40x20 grid {fast_rate:.1f} (difference {100 * rate_difference:.0f}%, limit {100 * MAX_FRAME_RATE_DIFFERENCE:.0f}%)."
    )
    return CheckResult("WebSocket frames arrive at a steady rate and commands get through", passed, message)


def check_refusals(root: Path) -> CheckResult:
    """Test D."""
    client, _ = make_client(root, max_active_jobs=1)
    with client:
        statuses = {
            "temperature 70 C": client.post("/jobs", json={"temperature_celsius": 70}).status_code,
            "negative duration": client.post("/jobs", json={"duration": -5}).status_code,
            "unstable time step": client.post("/jobs", json={"time_step": 0.25, "diffusion_scheme": "explicit", "relaxation_time": 1.0}).status_code,  # unstable only for the explicit scheme with fast kinetics
            "unknown job": client.get("/jobs/nope").status_code,
            "unknown job command": client.post("/jobs/nope/pause").status_code,
            "result with path tricks": client.get("/results/..%2Fetc").status_code,
            "file outside the result": client.get("/results/x/files/..%2F..%2Fsecret.json").status_code,
            "ensemble from nothing": client.post("/ensembles", json={"source": "does_not_exist"}).status_code,
        }
        expected = {"temperature 70 C": 422, "negative duration": 422, "unstable time step": 422, "unknown job": 404, "unknown job command": 404, "result with path tricks": 404, "file outside the result": 404, "ensemble from nothing": 404}
        job_id = start_job(client, LONG_JOB)
        statuses["second job over the limit"] = client.post("/jobs", json=SMALL_JOB).status_code
        expected["second job over the limit"] = 409
        client.post(f"/jobs/{job_id}/stop")
        wait_for_job(client, job_id)
        statuses["command to a finished job"] = client.post(f"/jobs/{job_id}/pause").status_code
        expected["command to a finished job"] = 409
    wrong = {name: (code, expected[name]) for name, code in statuses.items() if code != expected[name]}
    message = f"{len(statuses) - len(wrong)} of {len(statuses)} bad requests got the expected error code (422 invalid, 404 unknown, 409 not allowed now); wrong: {wrong if wrong else 'none'}."
    return CheckResult("bad requests are refused with the right error", not wrong, message)


def check_results_access(root: Path) -> tuple[CheckResult, str]:
    """Test E. Also returns the name of a saved run, used by the ensemble test."""
    client, _ = make_client(root)
    with client:
        job_id = start_job(client, SMALL_JOB)
        job = wait_for_job(client, job_id)
        name = job["folder"]
        listing = client.get("/results").json()
        summary = client.get(f"/results/{name}").json()
        metrics = client.get(f"/results/{name}/metrics").json()
        picture = client.get(f"/results/{name}/files/final_image.png")
        snapshots = client.get(f"/results/{name}/snapshots").json()["steps"]
        snapshot_picture = client.get(f"/results/{name}/snapshots/{snapshots[0]}/image")
        missing_snapshot = client.get(f"/results/{name}/snapshots/123456789/image").status_code
        home = client.get("/")
    passed = (
        any(item["name"] == name for item in listing) and summary["kind"] == "run" and len(metrics) >= 2
        and picture.content.startswith(PNG_SIGNATURE) and snapshot_picture.content.startswith(PNG_SIGNATURE) and missing_snapshot == 404
        and home.status_code == 200 and "Arystal" in home.text
    )
    message = (
        f"Run listed: {any(item['name'] == name for item in listing)}; summary loaded ({summary['kind']}); {len(metrics)} metric rows; final image and snapshot "
        f"image are PNGs: {picture.content.startswith(PNG_SIGNATURE) and snapshot_picture.content.startswith(PNG_SIGNATURE)}; unsaved snapshot gives {missing_snapshot}; test page served: {home.status_code == 200}."
    )
    return CheckResult("past results can be listed and loaded", passed, message), name


def check_ensemble_through_api(root: Path, source_name: str) -> CheckResult:
    """Test F."""
    client, _ = make_client(root)
    with client:
        response = client.post("/ensembles", json={"source": source_name, "replicas": 2, "workers": 2})
        assert response.status_code == 201, response.text
        job = wait_for_job(client, response.json()["job_id"])
        listing = client.get("/results").json()
        name = job["folder"]
        picture = client.get(f"/results/{name}/files/comparison.png")
    entry = next((item for item in listing if item["name"] == name), None)
    passed = job["status"] == "finished" and job["replicas_done"] == 2 and entry is not None and entry["kind"] == "ensemble" and entry["replicas"] == 2 and picture.content.startswith(PNG_SIGNATURE)
    message = f"Ensemble job {job['status']} with {job['replicas_done']} replicas reported; listed as an ensemble of {entry and entry['replicas']}; comparison.png served as PNG: {picture.content.startswith(PNG_SIGNATURE)}; cost reported: {bool(job['compute_cost'])}."
    return CheckResult("an ensemble can be launched through the API", passed, message)


def check_notifications(root: Path) -> CheckResult:
    """Test G (the escaping and the threshold; the long-job notification itself is checked in test A)."""
    sent = []
    client, _ = make_client(root, notifier=lambda title, message: sent.append(title), notify_after_seconds=3600.0)
    with client:
        wait_for_job(client, start_job(client, SMALL_JOB))
    dangerous = 'He said "hi" \\ and\nleft'
    escaped = escape_for_applescript(dangerous)
    script = build_notification_script("Arystal", dangerous)
    safe_text = '"' not in escaped.replace('\\"', "") and "\n" not in escaped
    import sys

    original = sys.platform
    sys.platform = "linux"
    try:
        other_system = notify_macos("t", "m") is False
    finally:
        sys.platform = original
    passed = not sent and safe_text and script.startswith("display notification") and other_system
    message = f"Short job below the threshold sent {len(sent)} notifications (must be 0); AppleScript text escaped safely: {safe_text}; does nothing on other systems: {other_system}."
    return CheckResult("short jobs do not notify and the notification text is escaped", passed, message)


def check_authentication_hook(root: Path) -> CheckResult:
    """Test H."""
    from fastapi import HTTPException
    from fastapi.testclient import TestClient

    app = create_app(root, JobManager(root))

    def reject_everyone():
        raise HTTPException(status_code=401, detail="not allowed")

    app.dependency_overrides[authenticate] = reject_everyone
    with TestClient(app) as client:
        codes = [client.get("/health").status_code, client.get("/jobs").status_code, client.post("/jobs", json={}).status_code, client.get("/results").status_code]
        websocket_refused = False
        try:
            with client.websocket_connect("/jobs/anything/stream"):
                pass
        except Exception:  # noqa: BLE001 - any refusal of the connection counts
            websocket_refused = True
    passed = all(code == 401 for code in codes) and websocket_refused
    message = f"With a rejecting `authenticate`, HTTP routes answered {codes} (expected all 401) and the WebSocket was refused: {websocket_refused}."
    return CheckResult("replacing the authentication hook protects every route", passed, message)


def run_safely(name: str, test) -> CheckResult:
    """Run one test; if it raises, report it as a failed test with the error instead of stopping the whole report."""
    try:
        return test()
    except Exception as error:  # noqa: BLE001 - any failure must show up in the report
        return CheckResult(name, False, f"The test stopped with {type(error).__name__}: {str(error)[:300]}")


def run_server_check(material: MaterialConstants) -> list[CheckResult]:
    """Run all tests of the server check."""
    results = []
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        results.append(run_safely("jobs run in their own process", lambda: check_job_isolated_and_complete(root)))
        results.append(run_safely("control through the API", lambda: check_control_and_replay(root, material)))
        results.append(run_safely("WebSocket stream", lambda: check_websocket_stream(root)))
        results.append(run_safely("bad requests are refused", lambda: check_refusals(root)))
        source = {}
        def access():
            result, source["name"] = check_results_access(root)
            return result
        results.append(run_safely("past results", access))
        results.append(run_safely("ensemble through the API", lambda: check_ensemble_through_api(root, source["name"])))
        results.append(run_safely("notifications", lambda: check_notifications(root)))
        results.append(run_safely("authentication hook", lambda: check_authentication_hook(root)))
    return results
