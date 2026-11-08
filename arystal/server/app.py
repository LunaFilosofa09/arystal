"""The web API of Arystal: create and control jobs, stream them live, and read past results.

The server only creates, controls and watches jobs; the simulations run in their own processes (see job_manager.py).
Every route depends on `authenticate`, so authentication can be added later without rewriting the routes.
The server is meant to run on the local machine (127.0.0.1) only.
"""

import asyncio
import dataclasses
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response

from arystal.server.authentication import authenticate
from arystal.server.job_manager import ACTIVE_STATUSES, FAILED, FINISHED, Job, JobManager, TooManyJobsError
from arystal.server.results_access import (
    ENSEMBLE,
    list_results,
    list_snapshot_steps,
    load_metrics,
    load_result,
    render_snapshot_png,
    resolve_result_file,
    resolve_result_folder,
)
from arystal.server.schemas import EnsembleRequest, JobRequest, ParameterChange
from arystal.simulation.material_loader import load_material
from arystal.simulation.seeded_run import build_params
from arystal.storage.result_folder import DEFAULT_RESULTS_ROOT

TEST_PAGE = Path(__file__).resolve().parent.parent.parent / "test_page" / "index.html"

# Frames per second sent through the WebSocket (the job produces them at its own steady rate).
DEFAULT_STREAM_SECONDS = 0.25
WEBSOCKET_POLL_SECONDS = 0.05


def find_job_or_404(manager: JobManager, job_id: str) -> Job:
    """Return the job, or answer 404."""
    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No job {job_id!r}.")
    return job


def require_active_simulation(job: Job) -> None:
    """Answer 409 unless the job is an active simulation (the only kind that accepts commands)."""
    if job.kind != "run" or job.status not in ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail="Only an active simulation job accepts this command.")


def command_from_message(message: dict) -> tuple | None:
    """Turn a client message ({"command": "pause"} or {"command": "set", "parameter": ..., "value": ...}) into a job command, or None if it is not valid."""
    kind = message.get("command")
    if kind in ("pause", "resume", "stop"):
        return (kind,)
    if kind == "set":
        try:
            change = ParameterChange(parameter=message.get("parameter"), value=message.get("value"))
        except ValueError:
            return None
        return ("set", change.parameter, change.value)
    return None


async def send_frames(websocket: WebSocket, job: Job, stream_seconds: float) -> None:
    """Send every new frame of the job at most once, then a final message when the job ends."""
    last_sequence = 0
    while True:
        frame = job.latest_frame
        if frame is not None and frame["sequence"] != last_sequence:
            last_sequence = frame["sequence"]
            await websocket.send_text(json.dumps(frame))
        if job.status in (FINISHED, FAILED) and (job.latest_frame is None or job.latest_frame["sequence"] == last_sequence):
            await websocket.send_text(json.dumps({"type": "end", "status": job.status, "folder": job.folder and Path(job.folder).name, "error": job.error}))
            return
        await asyncio.sleep(min(stream_seconds, WEBSOCKET_POLL_SECONDS))


async def receive_commands(websocket: WebSocket, manager: JobManager, job: Job) -> None:
    """Read the commands the client sends through the WebSocket and pass the valid ones to the job."""
    while True:
        message = json.loads(await websocket.receive_text())
        command = command_from_message(message)
        if command is not None and job.kind == "run" and job.status in ACTIVE_STATUSES:
            manager.send_command(job, command)


def create_app(results_root: Path = DEFAULT_RESULTS_ROOT, manager: JobManager | None = None, stream_seconds: float = DEFAULT_STREAM_SECONDS) -> FastAPI:
    """Build the API application. `manager` can be given (for tests); by default one is created for `results_root`."""
    results_root = Path(results_root)
    results_root.mkdir(parents=True, exist_ok=True)
    manager = manager or JobManager(results_root)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        manager.start()
        yield
        await asyncio.get_running_loop().run_in_executor(None, manager.shutdown)

    app = FastAPI(title="Arystal", description="Crystal growth simulator: jobs, live stream and results.", lifespan=lifespan)
    app.state.manager = manager
    protected = [Depends(authenticate)]

    @app.get("/", include_in_schema=False)
    def home():
        """The minimal test page (not the real frontend)."""
        return FileResponse(TEST_PAGE)

    @app.get("/health", dependencies=protected)
    def health():
        """Say the server is alive, and how many jobs are active."""
        return {"status": "ok", "active_jobs": manager.count_active_jobs()}

    @app.post("/jobs", dependencies=protected, status_code=201)
    def create_job(request: JobRequest):
        """Start a simulation job."""
        try:
            config = request.to_run_config()
            build_params(config, load_material())  # refuses settings the engine would refuse (stability, ranges)
            job = manager.create_job("run", {"config": dataclasses.asdict(config)})
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except TooManyJobsError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return job.describe()

    @app.get("/jobs", dependencies=protected)
    def list_jobs():
        """List all the jobs of this server session."""
        return [job.describe() for job in manager.list_jobs()]

    @app.get("/jobs/{job_id}", dependencies=protected)
    def get_job(job_id: str):
        """Status, latest metrics and compute cost of a job."""
        return find_job_or_404(manager, job_id).describe()

    @app.get("/jobs/{job_id}/metrics", dependencies=protected)
    def get_job_metrics(job_id: str):
        """The metrics seen so far by the server for this job (one point per frame)."""
        return find_job_or_404(manager, job_id).metrics_history

    @app.post("/jobs/{job_id}/pause", dependencies=protected)
    def pause_job(job_id: str):
        """Pause a running simulation."""
        job = find_job_or_404(manager, job_id)
        require_active_simulation(job)
        manager.send_command(job, ("pause",))
        return {"requested": "pause"}

    @app.post("/jobs/{job_id}/resume", dependencies=protected)
    def resume_job(job_id: str):
        """Resume a paused simulation."""
        job = find_job_or_404(manager, job_id)
        require_active_simulation(job)
        manager.send_command(job, ("resume",))
        return {"requested": "resume"}

    @app.post("/jobs/{job_id}/stop", dependencies=protected)
    def stop_job(job_id: str):
        """Stop a simulation now; it is saved."""
        job = find_job_or_404(manager, job_id)
        require_active_simulation(job)
        manager.send_command(job, ("stop",))
        return {"requested": "stop"}

    @app.post("/jobs/{job_id}/parameters", dependencies=protected)
    def change_parameter(job_id: str, change: ParameterChange):
        """Change temperature, dissolved iron or the duration of a running simulation (recorded in its timeline)."""
        job = find_job_or_404(manager, job_id)
        require_active_simulation(job)
        manager.send_command(job, ("set", change.parameter, change.value))
        return {"requested": change.model_dump()}

    @app.post("/ensembles", dependencies=protected, status_code=201)
    def create_ensemble(request: EnsembleRequest):
        """Launch an ensemble of replicas from a saved run (same settings and timeline, different seeds)."""
        source = resolve_result_folder(results_root, request.source)
        if source is None or not (source / "timeline.json").exists():
            raise HTTPException(status_code=404, detail="The source must be the name of a saved run folder.")
        try:
            job = manager.create_job("ensemble", {"source_folder": str(source), "replicas": request.replicas, "workers": request.workers, "base_seed": request.base_seed})
        except TooManyJobsError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return job.describe()

    @app.get("/results", dependencies=protected)
    def get_results():
        """List the saved runs and ensembles (files on disk, so also those from earlier sessions)."""
        return list_results(results_root)

    def find_result_or_404(name: str) -> Path:
        folder = resolve_result_folder(results_root, name)
        if folder is None:
            raise HTTPException(status_code=404, detail="No such result.")
        return folder

    @app.get("/results/{name}", dependencies=protected)
    def get_result(name: str):
        """Summary, parameters and timeline of a saved run, or the summary of a saved ensemble."""
        return load_result(find_result_or_404(name))

    @app.get("/results/{name}/metrics", dependencies=protected)
    def get_result_metrics(name: str):
        """The metrics over time of a saved run."""
        folder = find_result_or_404(name)
        if load_result(folder)["kind"] == ENSEMBLE:
            raise HTTPException(status_code=404, detail="Ensembles have ensemble_metrics.csv (see the files route).")
        return load_metrics(folder)

    @app.get("/results/{name}/files/{relative:path}", dependencies=protected)
    def get_result_file(name: str, relative: str):
        """Download a picture, JSON or CSV file of a result (for example final_image.png or plots/growth.png)."""
        path = resolve_result_file(find_result_or_404(name), relative)
        if path is None:
            raise HTTPException(status_code=404, detail="No such file.")
        return FileResponse(path)

    @app.get("/results/{name}/snapshots", dependencies=protected)
    def get_snapshot_steps(name: str):
        """The steps of the saved snapshots of a run, to replay its animation without recalculating."""
        return {"steps": list_snapshot_steps(find_result_or_404(name))}

    @app.get("/results/{name}/snapshots/{step}/image", dependencies=protected)
    def get_snapshot_image(name: str, step: int):
        """The crystal at a saved snapshot, as a PNG."""
        png = render_snapshot_png(find_result_or_404(name), step)
        if png is None:
            raise HTTPException(status_code=404, detail="That step was not saved.")
        return Response(png, media_type="image/png")

    @app.websocket("/jobs/{job_id}/stream")
    async def stream_job(websocket: WebSocket, job_id: str, user: str = Depends(authenticate)):
        """Live frames (pictures and metrics) at a steady rate; the client may send commands as JSON messages."""
        job = manager.get_job(job_id)
        if job is None:
            await websocket.close(code=4404)
            return
        await websocket.accept()
        receiver = asyncio.create_task(receive_commands(websocket, manager, job))
        try:
            await send_frames(websocket, job, stream_seconds)
        except WebSocketDisconnect:
            pass
        finally:
            receiver.cancel()
        try:
            await websocket.close()
        except RuntimeError:
            pass

    return app
