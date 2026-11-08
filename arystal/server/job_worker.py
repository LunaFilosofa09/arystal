"""The code that runs inside a job's own process.

Messages from the job to the server (put on `event_queue`, plain dictionaries):
  {"type": "started", "folder": ...}                 the run folder exists
  {"type": "frame", ...}                             a picture and the current metrics (see frames.py), a few times per second
  {"type": "status", "status": "running"|"paused"}   the run state changed
  {"type": "finished", "folder": ..., "rejected": [...]}   everything is saved
  {"type": "failed", "error": ...}                   something went wrong
  {"type": "replica_done", ...}                      (ensembles) one replica finished

Commands from the server (on `command_queue`): ("pause",), ("resume",), ("stop",), ("set", parameter, value).

Frames are produced at a fixed wall-clock rate whatever the simulation speed. If the server is slow to read them they are dropped,
never the important messages (started, finished, failed).
"""

import queue
import time
import traceback
from pathlib import Path

from arystal.server.frames import build_frame
from arystal.simulation.controlled_run import PAUSED, ControlledRun
from arystal.simulation.ensemble import EnsembleSettings, run_ensemble
from arystal.simulation.material_loader import load_material
from arystal.simulation.metrics_recorder import MetricsRecorder
from arystal.simulation.run_config import RunConfig
from arystal.simulation.saved_run import RunSaver, advance_and_sample, load_run_for_replay

# Only these states of the simulation are reported as the status of the job. The job itself is "finished" only
# after everything is saved, which is announced by the separate "finished" message.
LIVE_STATUSES = ("running", "paused")

# Steps computed between two looks at the command queue.
STEPS_PER_TURN = 20

DEFAULT_FRAME_INTERVAL_SECONDS = 0.25  # 4 frames per second

WAIT_WHEN_PAUSED_SECONDS = 0.02

IMPORTANT_MESSAGE_TIMEOUT_SECONDS = 30


def send_important(event_queue, message: dict) -> None:
    """Send a message that must not be lost (waits if the queue is full)."""
    event_queue.put(message, timeout=IMPORTANT_MESSAGE_TIMEOUT_SECONDS)


def send_frame(event_queue, frame: dict) -> None:
    """Send a frame, or drop it if the server is not keeping up."""
    try:
        event_queue.put_nowait(frame)
    except queue.Full:
        pass


def apply_pending_commands(controller: ControlledRun, command_queue) -> None:
    """Move the waiting commands from the queue into the controller, then let it apply them at this step."""
    while True:
        try:
            command = command_queue.get_nowait()
        except queue.Empty:
            break
        kind = command[0]
        if kind == "pause":
            controller.request_pause()
        elif kind == "resume":
            controller.request_resume()
        elif kind == "stop":
            controller.request_stop()
        elif kind == "set":
            controller.request_change(command[1], command[2])
    controller.process_commands()


def run_simulation_job(spec: dict, command_queue, event_queue) -> None:
    """Run one simulation with live control, streaming frames, and save it at the end."""
    material = load_material()
    controller = ControlledRun(RunConfig(**spec["config"]), material)
    saver = RunSaver(controller, Path(spec["results_root"]))
    frame_recorder = MetricsRecorder(controller.params, material, controller.state)
    saver.sample(controller)
    send_important(event_queue, {"type": "started", "folder": str(saver.folder)})
    interval = spec.get("frame_interval", DEFAULT_FRAME_INTERVAL_SECONDS)
    sequence, last_frame, last_status = 0, 0.0, None
    while not controller.is_finished():
        apply_pending_commands(controller, command_queue)
        steps = advance_and_sample(controller, saver, STEPS_PER_TURN)
        if controller.status in LIVE_STATUSES and controller.status != last_status:
            last_status = controller.status
            send_important(event_queue, {"type": "status", "status": last_status})
        if steps == 0 and controller.status == PAUSED:
            time.sleep(WAIT_WHEN_PAUSED_SECONDS)
        if time.perf_counter() - last_frame >= interval:
            sequence += 1
            send_frame(event_queue, build_frame(sequence, controller, frame_recorder))
            last_frame = time.perf_counter()
    sequence += 1
    send_important(event_queue, build_frame(sequence, controller, frame_recorder))
    folder = saver.finish(controller)
    send_important(event_queue, {"type": "finished", "folder": str(folder), "rejected": controller.rejected})


def run_ensemble_job(spec: dict, command_queue, event_queue) -> None:
    """Run an ensemble from a saved run (its settings and timeline), reporting each replica as it finishes."""
    source = Path(spec["source_folder"])
    config, events = load_run_for_replay(source)
    settings = EnsembleSettings(spec["replicas"], spec["workers"], spec["base_seed"] if spec["base_seed"] is not None else config.seed)
    send_important(event_queue, {"type": "started", "folder": None})
    send_important(event_queue, {"type": "status", "status": "running"})
    folder = run_ensemble(
        config, events, settings, Path(spec["results_root"]),
        on_replica_done=lambda result: send_important(event_queue, {"type": "replica_done", "index": result["index"], "seed": result["seed"], "wall_seconds": result["wall_seconds"]}),
    )
    send_important(event_queue, {"type": "finished", "folder": str(folder), "rejected": []})


def job_process_main(spec: dict, command_queue, event_queue) -> None:
    """Entry point of a job's process: run the right kind of job and report any failure instead of dying silently."""
    try:
        if spec["kind"] == "ensemble":
            run_ensemble_job(spec, command_queue, event_queue)
        else:
            run_simulation_job(spec, command_queue, event_queue)
    except Exception:  # noqa: BLE001 - the server must learn about any failure, whatever it is
        send_important(event_queue, {"type": "failed", "error": traceback.format_exc()})
