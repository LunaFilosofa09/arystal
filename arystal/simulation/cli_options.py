"""Command-line options shared by the scripts that start runs: the mode and the settings that can override it."""

import argparse

from arystal.simulation.material_loader import load_material
from arystal.simulation.modes import MODE_SETTINGS, build_mode_config
from arystal.simulation.run_config import RunConfig


def add_run_options(parser: argparse.ArgumentParser) -> None:
    """Add the options that define a run. Everything not given comes from the chosen mode."""
    parser.add_argument("--mode", choices=list(MODE_SETTINGS), default="explore", help="explore (200x100, fast, qualitative) or research (800x400, converged)")
    parser.add_argument("--temperature", type=float, default=None, help="run temperature in C (15-60; default 40)")
    parser.add_argument("--saturation-temperature", type=float, default=None, help="temperature in C at which the fluid was saturated (default 60)")
    parser.add_argument("--duration", type=float, default=None, help="model time units (default: the mode's length)")
    parser.add_argument("--seed", type=int, default=None, help="integer seed: same seed + settings = identical result")
    parser.add_argument("--iron-ppm", type=float, default=None, help=f"dissolved iron, ppm by mass (default {load_material().default_fluid_iron_ppm})")
    parser.add_argument("--no-iron", action="store_true", help="do not simulate iron")
    parser.add_argument("--no-noise", action="store_true", help="switch thermal noise and seed variations off")
    parser.add_argument("--isotropic", action="store_true", help="switch the facet anisotropy off")
    parser.add_argument("--grid-width", type=int, default=None)
    parser.add_argument("--grid-height", type=int, default=None)
    parser.add_argument("--relaxation-time", type=float, default=None, help="tau (default: on the plateau, scaled with the grid)")
    parser.add_argument("--time-step", type=float, default=None)
    parser.add_argument("--diffusion-scheme", choices=["explicit", "implicit", "uniform"], default=None, help="default: uniform (valid for surface-limited growth)")
    parser.add_argument("--threads", type=int, default=None, help="CPU threads for the fast kernels (default: the mode's)")
    parser.add_argument("--backend", choices=["numba", "reference"], default=None)
    parser.add_argument("--renewal-interval", type=float, default=None, help="model time between periodic renewals of the fluid (default: closed container)")
    parser.add_argument("--renewal-saturation", type=float, default=None, help="renewed fluid saturated with quartz at this temperature in C (default 60)")
    parser.add_argument("--fluid-ph", type=float, default=None, help="fluid pH (7-10): real time from the pH-dependent rate law; default: none (Takeno law)")


# command-line option -> RunConfig field
OPTION_TO_FIELD = {
    "temperature": "temperature_celsius", "saturation_temperature": "saturation_temperature_celsius", "duration": "duration", "seed": "seed",
    "iron_ppm": "iron_ppm", "grid_width": "grid_width", "grid_height": "grid_height", "relaxation_time": "relaxation_time", "time_step": "time_step",
    "diffusion_scheme": "diffusion_scheme", "threads": "threads", "backend": "backend", "fluid_ph": "fluid_ph", "renewal_interval": "renewal_interval", "renewal_saturation": "renewal_saturation_celsius",
}


def config_from_arguments(arguments: argparse.Namespace) -> RunConfig:
    """Return the run configuration: the mode's settings overridden by the options that were given."""
    overrides = {field: getattr(arguments, option) for option, field in OPTION_TO_FIELD.items() if getattr(arguments, option) is not None}
    if arguments.no_iron:
        overrides["iron_ppm"] = None
    if arguments.no_noise:
        overrides["noise_on"] = False
    if arguments.isotropic:
        overrides["anisotropy_on"] = False
    return build_mode_config(arguments.mode, **overrides)
