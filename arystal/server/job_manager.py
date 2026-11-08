"""Creates, controls and watches jobs.

A job is one simulation or one ensemble: parameters in, results out, with a status and a compute cost. Each job runs in its
own process, so the server stays responsive. The manager keeps what the server needs to know about each job in memory
(status, latest frame, metrics history); the results themselves are files in the results folder. After a server restart the
finished results are still available (through the results routes) but the job list starts empty.
"""

import multiprocessing
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from arystal.server.job_worker import job_process_main
from arystal.server.notifications import DEFAULT_NOTIFY_AFTER_SECONDS, notify_macos, should_notify
from arystal.storage.serialization import read_json

# Job statuses.
STARTING = "starting"
RUNNING = "running"
PAUSED = "paused"
FINISHED = "finished"
FAILED = "failed"
ACTIVE_STATUSES = (STARTING, RUNNING, PAUSED)

JOB_ID_LENGTH = 8
DEFAULT_MAX_ACTIVE_JOBS = 3
POLL_INTERVAL_SECONDS = 0.05
EVENT_QUEUE_SIZE = 16
MAXIMUM_HISTORY_ROWS = 5000
SHUTDOWN_WAIT_SECONDS = 20


class TooManyJobsError(Exception):
    """Raised when more jobs are active than the limit allows."""


@dataclass
class Job:
    """Everything the server knows about one job."""

    job_id: str
    kind: str
    spec: dict
    process: multiprocessing.Process
    command_queue: object
    event_queue: object
    status: str = STARTING
    created: float = field(default_factory=time.time)
    finished_at: float | None = None
    folder: str | None = None
    latest_frame: dict | None = None
    metrics_history: list = field(default_factory=list)
    replicas_done: int = 0
    rejected: list = field(default_factory=list)
    error: str | None = None
    cost: dict | None = None
    notified: bool = False

    @property
    def wall_seconds(self) -> float:
        """Seconds since the job was created (or until it finished)."""
        return (self.finished_at or time.time()) - self.created

    def describe(self) -> dict:
        """Return a JSON-safe description of the job for the API."""
        frame = self.latest_frame or {}
        return {
            "job_id": self.job_id, "kind": self.kind, "status": self.status, "wall_seconds": self.wall_seconds,
            "folder": Path(self.folder).name if self.folder else None, "step": frame.get("step"), "time": frame.get("time"),
            "duration": frame.get("duration"), "temperature_celsius": frame.get("temperature_celsius"),
            "iron_ppm": frame.get("iron_ppm"), "metrics": frame.get("metrics"), "replicas_done": self.replicas_done,
            "rejected_changes": self.rejected, "error": self.error, "compute_cost": self.cost,
        }


class JobManager:
    """Starts jobs in separate processes and keeps their state up to date from the messages they send."""

    def __init__(
        self, results_root: Path, max_active_jobs: int = DEFAULT_MAX_ACTIVE_JOBS,
        notifier: Callable[[str, str], object] = notify_macos, notify_after_seconds: float = DEFAULT_NOTIFY_AFTER_SECONDS,
    ) -> None:
        """Prepare the manager; call `start` to begin watching the jobs."""
        self.results_root = Path(results_root)
        self.max_active_jobs = max_active_jobs
        self.notifier = notifier
        self.notify_after_seconds = notify_after_seconds
        self.jobs: dict[str, Job] = {}
        self.context = multiprocessing.get_context("spawn")
        self.lock = threading.RLock()
        self.stop_watching = threading.Event()
        self.watcher: threading.Thread | None = None

    # ----- life of the manager -----

    def start(self) -> None:
        """Start the thread that reads the messages of the jobs."""
        self.stop_watching.clear()
        self.watcher = threading.Thread(target=self.watch_jobs, name="job-watcher", daemon=True)
        self.watcher.start()

    def shutdown(self) -> None:
        """Ask the active jobs to stop (so they save), wait a little, terminate the rest, and stop watching."""
        for job in self.list_jobs():
            if job.status in ACTIVE_STATUSES and job.kind == "run":
                job.command_queue.put(("stop",))
        deadline = time.time() + SHUTDOWN_WAIT_SECONDS
        while time.time() < deadline and any(job.process.is_alive() for job in self.list_jobs()):
            time.sleep(0.1)
        for job in self.list_jobs():
            if job.process.is_alive():
                job.process.terminate()
        self.stop_watching.set()
        if self.watcher:
            self.watcher.join(timeout=2.0)

    # ----- creating and controlling jobs -----

    def count_active_jobs(self) -> int:
        """Return how many jobs are starting, running or paused."""
        return sum(job.status in ACTIVE_STATUSES for job in self.list_jobs())

    def create_job(self, kind: str, spec: dict) -> Job:
        """Start a job in its own process and return it. Raises TooManyJobsError if the limit of active jobs is reached."""
        with self.lock:
            if self.count_active_jobs() >= self.max_active_jobs:
                raise TooManyJobsError(f"At most {self.max_active_jobs} jobs can be active at once.")
            spec = {**spec, "kind": kind, "results_root": str(self.results_root)}
            command_queue = self.context.Queue()
            event_queue = self.context.Queue(maxsize=EVENT_QUEUE_SIZE)
            process = self.context.Process(target=job_process_main, args=(spec, command_queue, event_queue), daemon=False)
            job = Job(uuid.uuid4().hex[:JOB_ID_LENGTH], kind, spec, process, command_queue, event_queue)
            self.jobs[job.job_id] = job
            process.start()
            return job

    def get_job(self, job_id: str) -> Job | None:
        """Return the job with this id, or None."""
        with self.lock:
            return self.jobs.get(job_id)

    def list_jobs(self) -> list[Job]:
        """Return all the jobs, oldest first."""
        with self.lock:
            return sorted(self.jobs.values(), key=lambda job: job.created)

    def send_command(self, job: Job, command: tuple) -> None:
        """Send a command (pause, resume, stop, set) to a simulation job."""
        job.command_queue.put(command)

    # ----- watching -----

    def watch_jobs(self) -> None:
        """Until stopped: read the messages of every job and notice processes that ended without saying so."""
        while not self.stop_watching.is_set():
            for job in self.list_jobs():
                self.read_events(job)
                self.check_process(job)
            time.sleep(POLL_INTERVAL_SECONDS)

    def read_events(self, job: Job) -> None:
        """Read and apply all the waiting messages of one job."""
        while True:
            try:
                event = job.event_queue.get_nowait()
            except queue.Empty:
                return
            self.apply_event(job, event)

    def apply_event(self, job: Job, event: dict) -> None:
        """Update the job with one message."""
        kind = event["type"]
        if kind == "started":
            job.folder = event.get("folder")
            job.status = RUNNING
        elif kind == "status" and job.status in ACTIVE_STATUSES and event["status"] in (RUNNING, PAUSED):
            job.status = event["status"]
        elif kind == "frame":
            job.latest_frame = event
            if len(job.metrics_history) < MAXIMUM_HISTORY_ROWS:
                job.metrics_history.append({"time": event["time"], "step": event["step"], **{key: value for key, value in event["metrics"].items() if key not in ("step", "time_model")}})
        elif kind == "replica_done":
            job.replicas_done += 1
        elif kind == "finished":
            job.folder = event["folder"]
            job.rejected = event.get("rejected", [])
            self.finish_job(job, FINISHED)
        elif kind == "failed":
            job.error = event["error"]
            self.finish_job(job, FAILED)

    def check_process(self, job: Job) -> None:
        """If the process has ended but the job never said it finished, mark it failed."""
        if job.status in ACTIVE_STATUSES and job.process.exitcode is not None:
            self.read_events(job)
            if job.status in ACTIVE_STATUSES:
                job.error = f"The job process ended unexpectedly (exit code {job.process.exitcode})."
                self.finish_job(job, FAILED)

    def finish_job(self, job: Job, status: str) -> None:
        """Mark a job as ended, read its compute cost, and notify if it was long."""
        job.status = status
        job.finished_at = time.time()
        job.cost = self.read_compute_cost(job)
        if should_notify(job.wall_seconds, self.notify_after_seconds) and not job.notified:
            job.notified = True
            outcome = "finished" if status == FINISHED else "FAILED"
            self.notifier("Arystal", f"Job {job.job_id} ({job.kind}) {outcome} after {job.wall_seconds:.0f} s")

    def read_compute_cost(self, job: Job) -> dict | None:
        """Return the compute cost recorded in the job's summary file, if there is one."""
        if not job.folder:
            return {"wall_clock_seconds": job.wall_seconds}
        for name in ("summary.json", "ensemble_summary.json"):
            path = Path(job.folder) / name
            if path.exists():
                return read_json(path).get("compute_cost")
        return None
