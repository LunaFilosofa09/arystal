"""A run that can be paused, resumed, stopped, extended and have its temperature or iron changed.

The controller has no window and no threads: whoever drives it (the live viewer, a script, a test or later the
server) calls `advance` to compute steps and `request_*` to ask for changes. Requests wait in a queue and are applied
between steps, each at an exact step number, and recorded in the timeline. Replaying the same settings, seed and
timeline (as `scheduled_events`) gives the identical result.

Pause, resume and the moment at which a request is made do not change the physics, so they are not recorded; only
the step at which each change takes effect is.
"""

import queue
from collections.abc import Iterable

import numpy as np

from arystal.engine.live_changes import change_temperature, renew_fluid, set_fluid_iron
from arystal.engine.material_constants import MaterialConstants
from arystal.engine.solution_growth import SolutionState, advance_one_step
from arystal.engine.solution_params import SolutionParams
from arystal.simulation.run_config import RunConfig
from arystal.simulation.seeded_run import compute_total_steps, draw_noise, prepare_run
from arystal.simulation.timeline import DURATION, IRON, RENEWAL, TEMPERATURE, TimelineEvent, build_timeline_record

RUNNING = "running"
PAUSED = "paused"
FINISHED = "finished"

# A very large number of steps: "advance until something stops me".
UNLIMITED_STEPS = 10**12


def compute_renewal_every_steps(config: RunConfig) -> int | None:
    """Return the number of steps between periodic fluid renewals (None if the run does not renew its fluid periodically)."""
    if config.renewal_interval is None:
        return None
    return max(1, int(round(config.renewal_interval / config.time_step)))


class ControlledRun:
    """The state of a run plus the commands that can change it while it advances."""

    def __init__(self, config: RunConfig, material: MaterialConstants, scheduled_events: Iterable[TimelineEvent] = ()) -> None:
        """Prepare the run. `scheduled_events` are applied automatically at their steps (used to replay a timeline)."""
        self.config = config
        self.material = material
        if config.backend == "numba":
            from arystal.engine.fast_step import set_thread_count

            set_thread_count(config.threads)
        self.params, self.state, self.noise_rng = prepare_run(config, material)
        self.step = 0
        self.total_steps = compute_total_steps(config)
        self.status = RUNNING
        self.timeline: list[TimelineEvent] = []
        self.injected_iron = 0.0
        self.injected_silica = 0.0
        self.renewal_every_steps = compute_renewal_every_steps(config)
        self.last_renewal_celsius: float | None = None
        self.current_iron_ppm = config.iron_ppm
        self.rejected: list[str] = []
        self.scheduled = sorted(scheduled_events, key=lambda event: event.step)
        self.commands: queue.Queue = queue.Queue()

    @property
    def time(self) -> float:
        """Current model time."""
        return self.step * self.params.time_step

    def is_finished(self) -> bool:
        """True when the run has reached its (possibly extended) duration and nothing is scheduled any more."""
        return self.status == FINISHED and not self.has_due_scheduled_event()

    def has_due_scheduled_event(self) -> bool:
        """True if a scheduled event is waiting at the current step."""
        return bool(self.scheduled) and self.scheduled[0].step <= self.step

    # ----- requests (can be made at any time; applied between steps) -----

    def request_pause(self) -> None:
        """Ask to pause."""
        self.commands.put(("pause", None, None))

    def request_resume(self) -> None:
        """Ask to resume after a pause."""
        self.commands.put(("resume", None, None))

    def request_stop(self) -> None:
        """Ask to stop now: the run ends at the current step (recorded as a duration change)."""
        self.commands.put(("stop", None, None))

    def request_change(self, parameter: str, value: float) -> None:
        """Ask to change a parameter (temperature_celsius, iron_ppm or duration)."""
        self.commands.put(("set", parameter, value))

    # ----- applying changes -----

    def apply_change(self, parameter: str, value: float) -> None:
        """Apply a change now, at the current step, and record it in the timeline. Raises ValueError if it is not allowed."""
        if parameter == TEMPERATURE:
            self.params = change_temperature(self.params, self.material, value)
        elif parameter == IRON:
            self.state, added = set_fluid_iron(self.state, self.params, self.material, value)
            self.injected_iron += added
            self.current_iron_ppm = value
        elif parameter == DURATION:
            self.apply_duration(value)
        elif parameter == RENEWAL:
            self.apply_renewal(value)
        else:
            raise ValueError(f"Parameter {parameter!r} cannot change during a run.")
        self.timeline.append(TimelineEvent(self.step, self.time, parameter, value))

    def apply_renewal(self, saturation_celsius: float) -> None:
        """Replace the fluid by fluid saturated at `saturation_celsius` with the current fluid iron, and count what it adds."""
        self.state, added_silica, added_iron = renew_fluid(self.state, self.params, self.material, saturation_celsius, self.current_iron_ppm)
        self.injected_silica += added_silica
        self.injected_iron += added_iron
        self.last_renewal_celsius = saturation_celsius

    def is_periodic_renewal_due(self) -> bool:
        """True if the run renews its fluid periodically and the current step is one of the renewal steps (not step 0)."""
        every = self.renewal_every_steps
        return every is not None and self.step > 0 and self.step % every == 0

    def apply_due_periodic_renewal(self) -> None:
        """Renew the fluid if a periodic renewal is due now. Periodic renewals come from the run settings, so they are not timeline events."""
        if self.is_periodic_renewal_due():
            self.apply_renewal(self.config.renewal_saturation_celsius)

    def apply_duration(self, duration: float) -> None:
        """Set the total simulated time; it cannot be before the current step. Reopens a finished run if extended."""
        steps = int(round(duration / self.params.time_step))
        if steps < self.step:
            raise ValueError("The new duration is earlier than the current time.")
        self.total_steps = steps
        self.status = FINISHED if steps == self.step else (PAUSED if self.status == PAUSED else RUNNING)

    def get_current_value(self, parameter: str) -> float | None:
        """Return the current value of a changeable parameter (None if it does not apply)."""
        if parameter == TEMPERATURE:
            return self.params.temperature_celsius
        if parameter == IRON:
            return self.current_iron_ppm
        if parameter == RENEWAL:
            return None  # a renewal is an action: asking twice renews twice
        return self.total_steps * self.params.time_step

    def apply_requested_change(self, parameter: str, value: float) -> None:
        """Apply a change asked by the user; if it is not allowed, remember why and carry on."""
        if self.get_current_value(parameter) == value:
            return
        try:
            self.apply_change(parameter, value)
        except ValueError as error:
            self.rejected.append(f"step {self.step}: {parameter} = {value}: {error}")

    def drain_commands(self) -> list[tuple]:
        """Take all waiting commands; of several changes to the same parameter only the last one is kept (slider dragging)."""
        commands = []
        while not self.commands.empty():
            commands.append(self.commands.get())
        last_change = {parameter: index for index, (kind, parameter, _) in enumerate(commands) if kind == "set"}
        return [c for index, c in enumerate(commands) if c[0] != "set" or last_change[c[1]] == index]

    def process_commands(self) -> None:
        """Apply the waiting commands at the current step."""
        for kind, parameter, value in self.drain_commands():
            if kind == "pause" and self.status == RUNNING:
                self.status = PAUSED
            elif kind == "resume" and self.status == PAUSED:
                self.status = RUNNING
            elif kind == "stop":
                self.apply_requested_change(DURATION, self.time)
            elif kind == "set":
                self.apply_requested_change(parameter, value)

    def apply_due_scheduled_events(self) -> None:
        """Apply the scheduled events that wait at the current step (in order)."""
        while self.has_due_scheduled_event():
            event = self.scheduled.pop(0)
            self.apply_change(event.parameter, event.value)

    # ----- advancing -----

    def steps_until_next_boundary(self, max_steps: int) -> int:
        """Return how many steps can be taken before the end, a scheduled event or `max_steps`."""
        limit = min(max_steps, self.total_steps - self.step)
        if self.scheduled:
            limit = min(limit, self.scheduled[0].step - self.step)
        if self.renewal_every_steps is not None:
            limit = min(limit, self.renewal_every_steps - self.step % self.renewal_every_steps)
        return limit

    def advance(self, max_steps: int) -> int:
        """Compute up to `max_steps` steps (fewer at a scheduled event or at the end). Returns the steps taken (0 if paused)."""
        self.apply_due_scheduled_events()
        if self.status == PAUSED:
            return 0
        steps = self.steps_until_next_boundary(max_steps)
        for _ in range(max(steps, 0)):
            self.state = advance_one_step(self.state, self.params, draw_noise(self.noise_rng, self.params), in_place=True)
            self.step += 1
        self.apply_due_periodic_renewal()
        if self.step >= self.total_steps:
            self.status = FINISHED
        return max(steps, 0)

    def build_timeline_record(self) -> dict:
        """Return the content of timeline.json for what happened so far."""
        return build_timeline_record(self.timeline, self.step)


def run_to_end(config: RunConfig, material: MaterialConstants, scheduled_events: Iterable[TimelineEvent] = ()) -> tuple[SolutionState, SolutionParams]:
    """Run to the end without saving anything (events, if any, are replayed) and return (final state, final params)."""
    controller = ControlledRun(config, material, scheduled_events)
    while not controller.is_finished():
        controller.advance(UNLIMITED_STEPS)
    return controller.state, controller.params
