"""The shapes of the requests the API accepts, with limits that refuse nonsense before it reaches the engine."""

from typing import Literal

from pydantic import BaseModel, Field

from arystal.simulation.modes import build_mode_config
from arystal.simulation.run_config import RunConfig
from arystal.simulation.timeline import CHANGEABLE_PARAMETERS

MAXIMUM_GRID_SIDE = 800
MINIMUM_GRID_SIDE = 20


class JobRequest(BaseModel):
    """Settings to start a simulation job. Everything has a default; what is not given comes from the mode (explore or research)."""

    temperature_celsius: float = Field(40.0, ge=15.0, le=60.0, description="run temperature (geode range 15-60 C)")
    saturation_temperature_celsius: float = Field(60.0, ge=15.0, le=60.0)
    iron_ppm: float | None = Field(1.0, ge=0.0, le=100.0, description="dissolved iron, ppm by mass; null = iron not simulated")
    seed: int = Field(0, ge=0, le=2**32 - 1)
    mode: Literal["explore", "research"] = Field("explore", description="explore (200x100, fast, qualitative) or research (800x400, converged); see docs/validation_report.md")
    duration: float | None = Field(None, gt=0.0, le=1e12, description="model time units; default: the mode's default length (can be extended while running)")
    grid_width: int | None = Field(None, ge=MINIMUM_GRID_SIDE, le=MAXIMUM_GRID_SIDE, description="default: the mode's grid")
    grid_height: int | None = Field(None, ge=MINIMUM_GRID_SIDE, le=MAXIMUM_GRID_SIDE)
    container_width_mm: float = Field(40.0, gt=0.0, le=10_000.0)
    seed_radius: float | None = Field(None, gt=0.0)
    relaxation_time: float | None = Field(None, gt=0.0, description="tau; default: on the plateau of the regime study (surface-limited growth)")
    time_step: float | None = Field(None, gt=0.0, le=1e9)
    anisotropy_on: bool = True
    noise_on: bool = True
    backend: Literal["numba", "reference"] = "numba"
    diffusion_scheme: Literal["explicit", "implicit", "uniform"] | None = Field(None, description="default: uniform (valid for surface-limited growth)")
    threads: int | None = Field(None, ge=1, le=12, description="CPU threads of the fast kernels; default: the mode's")
    fluid_ph: float | None = Field(None, ge=7.0, le=10.0, description="fluid pH for the pH-dependent rate law (real time only); null = Takeno law")
    renewal_interval: float | None = Field(None, gt=0.0, description="model time between periodic fluid renewals; null = closed container")
    renewal_saturation_celsius: float = Field(60.0, ge=15.0, le=60.0, description="the renewed fluid is saturated with quartz at this temperature")
    metrics_every_steps: int | None = Field(None, ge=1)
    snapshot_every_steps: int | None = Field(None, ge=1)

    def to_run_config(self) -> RunConfig:
        """Return the RunConfig of the request: the mode's settings, overridden by the fields the request actually gave."""
        given = self.model_dump(exclude_unset=True, exclude={"mode"})
        overrides = {key: value for key, value in given.items() if value is not None or key == "iron_ppm"}
        return build_mode_config(self.mode, **overrides)


class ParameterChange(BaseModel):
    """A change of a parameter of a running job."""

    parameter: Literal["temperature_celsius", "iron_ppm", "duration", "fluid_renewal_saturation_celsius"]
    value: float


class EnsembleRequest(BaseModel):
    """Settings to launch an ensemble from a saved run."""

    source: str = Field(description="name of a saved run folder inside the results folder")
    replicas: int = Field(10, ge=2, le=100)
    workers: int = Field(5, ge=1, le=12)
    base_seed: int | None = Field(None, ge=0, le=2**32 - 1)


assert set(CHANGEABLE_PARAMETERS) == {"temperature_celsius", "iron_ppm", "duration", "fluid_renewal_saturation_celsius"}  # the request type must follow the timeline
