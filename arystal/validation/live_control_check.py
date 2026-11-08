"""Validation of live control and the timeline.

Tests:
  A. Pausing does nothing to the physics: a paused run does not advance and ends identical to an uninterrupted one.
  B. Temperature changes have the expected direction: cooling speeds growth up; heating a depleted fluid dissolves the crystal.
  C. Timeline and replay: a session with several changes is saved, and replaying its timeline reproduces it bit for bit.
  D. Changing the fluid iron changes the iron taken up by the growing crystal in proportion, and the iron balance
     (discounting what was added) is conserved. Run WITHOUT noise: with noise the surface deposits and releases silica
     continuously, and the net Fe/Si of the increments is not the simple deposition ratio (see docs/physics_model.md).
  E. The duration can be extended, and stopping ends the run at the current step.
  F. Forbidden changes (temperature outside 15-60 C, iron when iron is off, a duration in the past) are refused and not recorded.
  G. The window's controls send the right requests (tested without a screen).

WHAT THESE TESTS DO NOT SHOW: that an instantaneous temperature jump is a realistic way to cool a geode (it is an
assumption), or that a fluid-renewal change of iron is how iron changes in nature. They check that the controls do what
they say and that results can be reproduced.
"""

import dataclasses
import tempfile
from pathlib import Path

import numpy as np

from arystal.engine.material_constants import MaterialConstants
from arystal.simulation.controlled_run import ControlledRun, run_to_end
from arystal.simulation.run_config import RunConfig
from arystal.simulation.saved_run import RunSaver, advance_and_sample, load_run_for_replay
from arystal.simulation.timeline import DURATION, IRON, TEMPERATURE
from arystal.storage.serialization import read_json
from arystal.storage.snapshots import FINAL_FIELDS, load_final_state
from arystal.validation.check_result import CheckResult

LIMITS_NOTE = (
    "Limits: an instantaneous temperature jump and a fluid-renewal change of iron are modelling assumptions, not claims about how "
    "conditions change in a real geode. These tests check that the controls do what they say and that runs can be reproduced."
)

BASE_CONFIG = RunConfig(
    temperature_celsius=40.0, saturation_temperature_celsius=60.0, iron_ppm=1.0, duration=400.0, grid_width=100, grid_height=50,
    seed=5, metrics_every_steps=500, snapshot_every_steps=2000,
)
CHUNK = 50  # steps between two looks at the "controls"

# Test B
RATE_START, CHANGE_STEP, RATE_END = 500, 2000, 4000  # steps
COOLED_CELSIUS = 15.0
HEATED_CELSIUS = 60.0
MINIMUM_SPEEDUP = 1.2
MAX_AREA_CHANGE_WHEN_HEATED = -0.005  # relative: the crystal must lose at least 0.5% of its area

# Test D
IRON_BEFORE_PPM = 1.0
IRON_AFTER_PPM = 3.0
IRON_CHANGE_STEP = 1500
IRON_WINDOW_STEPS = 500
IRON_RATIO_TOLERANCE = 0.10  # tight on purpose: the defect found during development (fluid-fraction weighting) gave x2.34, 22% off
MAX_IRON_DRIFT = 1e-9

# Test E
EXTENDED_DURATION = 150.0
EXTEND_STEP = 600
STOP_STEP = 400


def drive(config: RunConfig, material: MaterialConstants, script: dict[int, list[tuple]], saver_root: Path | None = None) -> tuple[ControlledRun, Path | None]:
    """Run a session in which a "user" makes the requests of `script` (step -> list of requests) at those steps.

    A request is ("pause",), ("stop",) or ("set", parameter, value). After a pause the "user" waits (the run must not
    advance) and then resumes. Returns (controller, run folder or None).
    """
    controller = ControlledRun(config, material)
    saver = RunSaver(controller, saver_root) if saver_root else None
    if saver:
        saver.sample(controller)
    done = set()
    while not controller.is_finished():
        for request in script.get(controller.step, []):
            if (controller.step, request) in done:
                continue
            done.add((controller.step, request))
            send_request(controller, request)
        controller.process_commands()
        wait_while_paused(controller)
        upcoming = [step for step in script if step > controller.step]
        limit = min([CHUNK] + [step - controller.step for step in upcoming])
        if saver:
            advance_and_sample(controller, saver, limit)
        else:
            controller.advance(limit)
    return controller, (saver.finish(controller) if saver else None)


PAUSED_POLLS = 3  # how many times the "user" looks at a paused run before resuming


def wait_while_paused(controller: ControlledRun) -> None:
    """If the run is paused, let a few turns pass (checking that nothing advances) and then resume it."""
    if controller.status != "paused":
        return
    for _ in range(PAUSED_POLLS):
        assert controller.advance(CHUNK) == 0
    controller.request_resume()
    controller.process_commands()


def send_request(controller: ControlledRun, request: tuple) -> None:
    """Send one request of a script to the controller."""
    kind = request[0]
    if kind == "pause":
        controller.request_pause()
    elif kind == "resume":
        controller.request_resume()
    elif kind == "stop":
        controller.request_stop()
    else:
        controller.request_change(request[1], request[2])


def states_equal(first, second) -> bool:
    """True if two states are identical in all fields."""
    return all(np.array_equal(getattr(first, name), getattr(second, name)) for name in FINAL_FIELDS)


def check_pause(material: MaterialConstants) -> CheckResult:
    """Test A."""
    reference, _ = run_to_end(BASE_CONFIG, material)
    controller = ControlledRun(BASE_CONFIG, material)
    controller.advance(300)
    controller.request_pause()
    controller.process_commands()
    frozen = controller.state
    steps_while_paused = controller.advance(500)
    unchanged = controller.state is frozen and steps_while_paused == 0
    controller.request_resume()
    controller.process_commands()
    while not controller.is_finished():
        controller.advance(CHUNK)
    identical = states_equal(controller.state, reference)
    message = f"Steps taken while paused: {steps_while_paused} (must be 0); final state identical to an uninterrupted run: {identical}."
    return CheckResult("pause stops the run and does not change the result", unchanged and identical, message)


def measure_area_rate(config: RunConfig, material: MaterialConstants, new_celsius: float) -> tuple[float, float, float]:
    """Run with a temperature change at CHANGE_STEP; return (area rate before, area rate after, relative area change after)."""
    controller = ControlledRun(config, material)
    areas = {}
    script = {CHANGE_STEP: [("set", TEMPERATURE, new_celsius)]}
    boundaries = sorted({RATE_START, CHANGE_STEP, CHANGE_STEP + (RATE_END - CHANGE_STEP) // 4, RATE_END})
    for boundary in boundaries:
        while controller.step < boundary:
            controller.advance(boundary - controller.step)
        if boundary == CHANGE_STEP:
            send_request(controller, script[CHANGE_STEP][0])
            controller.process_commands()
        areas[boundary] = float((controller.state.phase_field > 0.5).sum())
    after_start = CHANGE_STEP + (RATE_END - CHANGE_STEP) // 4
    time_step = config.time_step
    before = (areas[CHANGE_STEP] - areas[RATE_START]) / ((CHANGE_STEP - RATE_START) * time_step)
    after = (areas[RATE_END] - areas[after_start]) / ((RATE_END - after_start) * time_step)
    return before, after, (areas[RATE_END] - areas[CHANGE_STEP]) / areas[CHANGE_STEP]


def check_temperature_response(material: MaterialConstants) -> CheckResult:
    """Test B."""
    config = dataclasses.replace(BASE_CONFIG, duration=RATE_END * BASE_CONFIG.time_step)
    before_cool, after_cool, _ = measure_area_rate(config, material, COOLED_CELSIUS)
    _, _, change_heated = measure_area_rate(config, material, HEATED_CELSIUS)
    speedup = after_cool / before_cool if before_cool > 0 else float("nan")
    passed = speedup >= MINIMUM_SPEEDUP and change_heated <= MAX_AREA_CHANGE_WHEN_HEATED
    message = (
        f"Cooling 40 -> {COOLED_CELSIUS:.0f} C: area growth rate {before_cool:.3f} -> {after_cool:.3f} cells/time (x{speedup:.2f}, needs >= {MINIMUM_SPEEDUP}). "
        f"Heating 40 -> {HEATED_CELSIUS:.0f} C: crystal area changes by {100 * change_heated:+.2f}% (needs <= {100 * MAX_AREA_CHANGE_WHEN_HEATED:.1f}%, i.e. it dissolves)."
    )
    return CheckResult("temperature changes act in the expected direction", passed, message)


def check_timeline_and_replay(material: MaterialConstants) -> CheckResult:
    """Test C."""
    script = {
        300: [("set", TEMPERATURE, 25.0)], 600: [("pause",)], 900: [("set", IRON, 2.5)],
        1200: [("set", DURATION, 150.0)], 1400: [("set", TEMPERATURE, 35.0)], 1450: [("stop",)],
    }
    with tempfile.TemporaryDirectory() as root:
        controller, folder = drive(BASE_CONFIG, material, script, Path(root))
        record = read_json(folder / "timeline.json")
        config, events = load_run_for_replay(folder)
        replayed, _ = run_to_end(config, material, events)
        saved = load_final_state(folder)
        identical = all(np.array_equal(saved[name], getattr(replayed, name)) for name in FINAL_FIELDS)
    recorded = [(event["step"], event["parameter"]) for event in record["events"]]
    expected = [(300, TEMPERATURE), (900, IRON), (1200, DURATION), (1400, TEMPERATURE), (1450, DURATION)]
    times_consistent = all(abs(event["time"] - event["step"] * BASE_CONFIG.time_step) < 1e-12 for event in record["events"])
    passed = recorded == expected and identical and times_consistent and record["final_step"] == 1450
    message = (
        f"Recorded events {recorded} (expected {expected}); final step {record['final_step']}; "
        f"replay of the saved timeline identical to the saved result: {identical}; times consistent with steps: {times_consistent}."
    )
    return CheckResult("timeline is recorded and replaying it reproduces the run exactly", passed, message)


def measure_iron_per_silica(controller: ControlledRun) -> tuple[float, float]:
    """Return (iron, silica) deposited so far by the r family."""
    return float(controller.state.sector_iron[1].sum()), float(controller.state.sector_silica[1].sum())


def check_iron_change(material: MaterialConstants) -> CheckResult:
    """Test D."""
    config = dataclasses.replace(BASE_CONFIG, iron_ppm=IRON_BEFORE_PPM, duration=400.0, noise_on=False)
    controller = ControlledRun(config, material)
    controller.advance(IRON_CHANGE_STEP - IRON_WINDOW_STEPS)
    start = measure_iron_per_silica(controller)
    controller.advance(IRON_WINDOW_STEPS)
    middle = measure_iron_per_silica(controller)
    controller.request_change(IRON, IRON_AFTER_PPM)
    controller.process_commands()
    controller.advance(IRON_WINDOW_STEPS)
    end = measure_iron_per_silica(controller)
    ratio_before = (middle[0] - start[0]) / (middle[1] - start[1])
    ratio_after = (end[0] - middle[0]) / (end[1] - middle[1])
    factor = ratio_after / ratio_before
    expected = IRON_AFTER_PPM / IRON_BEFORE_PPM
    initial_total = BASE_CONFIG.grid_width * BASE_CONFIG.grid_height * controller.params.initial_iron
    balance = abs(float(controller.state.iron.sum() + controller.state.crystal_iron.sum()) - controller.injected_iron - initial_total) / initial_total
    passed = abs(factor / expected - 1.0) <= IRON_RATIO_TOLERANCE and balance <= MAX_IRON_DRIFT
    message = (
        f"Fe/Si of the r-sector material deposited rose by x{factor:.2f} after raising the fluid iron {IRON_BEFORE_PPM} -> {IRON_AFTER_PPM} ppm "
        f"(expected about x{expected:.1f}, tolerance {100 * IRON_RATIO_TOLERANCE:.0f}%); iron balance after discounting the iron added: {balance:.1e} (limit {MAX_IRON_DRIFT:.0e})."
    )
    return CheckResult("changing the fluid iron changes the iron taken up, and the balance holds", passed, message)


def check_extend_and_stop(material: MaterialConstants) -> CheckResult:
    """Test E."""
    extended, _ = drive(BASE_CONFIG, material, {EXTEND_STEP: [("set", DURATION, EXTENDED_DURATION)]})
    stopped, _ = drive(BASE_CONFIG, material, {STOP_STEP: [("stop",)]})
    expected_extended = int(round(EXTENDED_DURATION / BASE_CONFIG.time_step))
    passed = extended.step == expected_extended and stopped.step == STOP_STEP and stopped.is_finished()
    message = (
        f"Extending the duration {BASE_CONFIG.duration:.0f} -> {EXTENDED_DURATION:.0f} ended at step {extended.step} (expected {expected_extended}); "
        f"stopping at step {STOP_STEP} ended at step {stopped.step}."
    )
    return CheckResult("the duration can be extended and a stop ends the run at once", passed, message)


def check_refusals(material: MaterialConstants) -> CheckResult:
    """Test F."""
    controller = ControlledRun(dataclasses.replace(BASE_CONFIG, iron_ppm=None), material)
    controller.advance(200)
    controller.request_change(TEMPERATURE, 70.0)
    controller.request_change(IRON, 2.0)
    controller.request_change(DURATION, 5.0)
    controller.process_commands()
    nothing_recorded = not controller.timeline
    temperature_kept = controller.params.temperature_celsius == BASE_CONFIG.temperature_celsius
    passed = len(controller.rejected) == 3 and nothing_recorded and temperature_kept
    message = f"{len(controller.rejected)} of 3 forbidden changes refused; nothing recorded in the timeline: {nothing_recorded}; temperature unchanged: {temperature_kept}."
    return CheckResult("forbidden changes are refused and not recorded", passed, message)


def check_window_controls(material: MaterialConstants) -> CheckResult:
    """Test G: the sliders and buttons of the window send the right requests (no screen needed)."""
    import matplotlib

    matplotlib.use("Agg")
    from arystal.viewer.control_panel import create_control_panel, handle_extend_click, handle_pause_click, handle_stop_click

    controller = ControlledRun(dataclasses.replace(BASE_CONFIG, duration=100.0), material)
    panel = create_control_panel(controller)
    panel.temperature_slider.set_val(30.0)
    panel.iron_slider.set_val(2.0)
    handle_pause_click(controller)
    controller.process_commands()
    paused = controller.status == "paused"
    handle_pause_click(controller)
    controller.process_commands()
    resumed = controller.status == "running"
    handle_extend_click(controller)
    handle_stop_click(controller)
    controller.process_commands()
    parameters = [event.parameter for event in controller.timeline]
    passed = paused and resumed and parameters == [TEMPERATURE, IRON, DURATION, DURATION] and controller.params.temperature_celsius == 30.0 and controller.is_finished()
    message = f"Pause button paused: {paused}; second click resumed: {resumed}; requests recorded in order: {parameters}; stop finished the run: {controller.is_finished()}."
    return CheckResult("window controls send the right requests", passed, message)


def run_live_control_check(material: MaterialConstants) -> list[CheckResult]:
    """Run all tests of the live-control check."""
    return [
        check_pause(material),
        check_temperature_response(material),
        check_timeline_and_replay(material),
        check_iron_change(material),
        check_extend_and_stop(material),
        check_refusals(material),
        check_window_controls(material),
    ]
