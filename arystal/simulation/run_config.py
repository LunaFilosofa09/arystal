"""The configuration of one run: everything needed to repeat it exactly (together with the material file)."""

from dataclasses import dataclass

VALID_MODES = ("explore", "research")


@dataclass(frozen=True)
class RunConfig:
    """All user-level settings of a run.

    temperature_celsius: run temperature (15-60 C).
    saturation_temperature_celsius: temperature at which the fluid started saturated (sets the initial silica).
    iron_ppm: dissolved iron in the fluid, ppm by mass (None = iron is not simulated).
    duration: simulated time in model units.
    seed: integer that fixes all random numbers (same seed + same settings = identical result).
    mode: "explore" or "research". A label here; the settings of each mode are applied by simulation/modes.py.
    anisotropy_on: face-dependent growth speeds (flat faces) on or off.
    noise_on: thermal noise and random seed variations on or off (amplitudes come from the material file).
    relaxation_time: tau, slowness of attachment. The default 1.0 is the original provisional value and is above the plateau (diffusion-limited);
        the modes set tau on the plateau (docs/regime_study.md, docs/kinetic_regime.md section 9).
    backend: "numba" (fast kernels, default) or "reference" (readable NumPy code). Same physics; results agree to rounding, so a run should be
        replayed with the backend it was recorded with to be bit-for-bit identical.
    diffusion_scheme: "explicit" (default) or "implicit" (any time step: for slow, surface-limited growth; see docs/kinetic_regime.md).
    fluid_ph: pH of the fluid (None = no pH: Takeno rate law). With a pH the real-time conversion uses the neutral + base law of
        Palandri & Kharaka (2004); the simulated shape does not change (docs/kinetic_regime.md section 10).
    renewal_interval: model time between periodic renewals of the fluid (None = closed container, the default). Each renewal replaces the fluid by
        fluid saturated with quartz at renewal_saturation_celsius, with the current fluid iron (episodic infiltration; docs/kinetic_regime.md, decision 5).
    threads: CPU threads used by the fast kernels (1 is right when several runs share the machine, as in an ensemble).
    metrics_every_steps, snapshot_every_steps: how often metrics are recorded and grids saved (the second
        must be a multiple of the first).
    """

    temperature_celsius: float = 40.0
    saturation_temperature_celsius: float = 60.0
    iron_ppm: float | None = 1.0
    duration: float = 2000.0
    seed: int = 0
    mode: str = "explore"
    grid_width: int = 400
    grid_height: int = 200
    container_width_mm: float = 40.0
    seed_radius: float = 15.0
    relaxation_time: float = 1.0
    time_step: float = 0.1
    anisotropy_on: bool = True
    noise_on: bool = True
    backend: str = "numba"
    threads: int = 1
    diffusion_scheme: str = "explicit"
    fluid_ph: float | None = None
    renewal_interval: float | None = None
    renewal_saturation_celsius: float = 60.0
    metrics_every_steps: int = 500
    snapshot_every_steps: int = 5000

    def __post_init__(self) -> None:
        """Refuse inconsistent settings early."""
        if self.backend not in ("numba", "reference"):
            raise ValueError("backend must be 'numba' or 'reference'")
        if self.threads < 1:
            raise ValueError("threads must be at least 1")
        if self.renewal_interval is not None and self.renewal_interval <= 0:
            raise ValueError("renewal_interval must be positive (or None for a closed container)")
        if self.mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {VALID_MODES}, got {self.mode!r}")
        if self.snapshot_every_steps % self.metrics_every_steps != 0:
            raise ValueError("snapshot_every_steps must be a multiple of metrics_every_steps")


def create_config_from_dict(values: dict) -> RunConfig:
    """Rebuild a RunConfig from the dictionary stored in params.json."""
    return RunConfig(**{key: value for key, value in values.items() if key != "timeline"})
