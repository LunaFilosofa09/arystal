"""The timeline: the list of changes made to a run, each at an exact simulation step.

Every change is recorded as (step, time, parameter, value). A run with the same settings, seed and
timeline is reproduced exactly, because the changes are applied at the same steps.
"""

from dataclasses import dataclass

TEMPERATURE = "temperature_celsius"
IRON = "iron_ppm"
DURATION = "duration"
RENEWAL = "fluid_renewal_saturation_celsius"

# The parameters that can change during a run. duration is the total simulated model time (can be extended or cut by stopping).
CHANGEABLE_PARAMETERS = (TEMPERATURE, IRON, DURATION, RENEWAL)

TIMELINE_NOTE = (
    "Each event is applied after `step` time steps have been completed and before the next one. "
    "Changing temperature is an instantaneous jump; changing iron renews the fluid iron (adds or removes iron); "
    "fluid_renewal_saturation_celsius replaces the whole fluid by fluid saturated with quartz at that temperature (with the current fluid iron); "
    "duration is the total simulated model time (a stop is recorded as a duration equal to the current time)."
)


@dataclass(frozen=True)
class TimelineEvent:
    """One change of a parameter: it happened after `step` steps (model time `time`)."""

    step: int
    time: float
    parameter: str
    value: float

    def __post_init__(self) -> None:
        """Refuse parameters that cannot change during a run."""
        if self.parameter not in CHANGEABLE_PARAMETERS:
            raise ValueError(f"Parameter {self.parameter!r} cannot change during a run; choose one of {CHANGEABLE_PARAMETERS}.")


def event_to_dict(event: TimelineEvent) -> dict:
    """Return the event as a plain dictionary for timeline.json."""
    return {"step": event.step, "time": event.time, "parameter": event.parameter, "value": event.value}


def event_from_dict(values: dict) -> TimelineEvent:
    """Rebuild an event from its dictionary in timeline.json."""
    return TimelineEvent(step=int(values["step"]), time=float(values["time"]), parameter=values["parameter"], value=float(values["value"]))


def build_timeline_record(events: list[TimelineEvent], final_step: int) -> dict:
    """Return the content of timeline.json."""
    return {"events": [event_to_dict(event) for event in events], "final_step": final_step, "note": TIMELINE_NOTE}


def read_scheduled_events(record: dict) -> list[TimelineEvent]:
    """Return the events of a timeline.json record, to be replayed."""
    return [event_from_dict(values) for values in record["events"]]
