"""Command-line entry point for the validation checks.

Examples:
    python scripts/validate.py isotropic     # check 1
    python scripts/validate.py symmetry      # check 2
    python scripts/validate.py mass          # check 3
    python scripts/validate.py iron          # iron: conservation and sector zoning
    python scripts/validate.py reproducibility   # seeds and saved results
    python scripts/validate.py live          # live control and timeline
    python scripts/validate.py ensemble      # ensemble of replicas
    python scripts/validate.py server        # web server
    python scripts/validate.py fast          # check 6: fast kernels vs reference
    python scripts/validate.py implicit      # check 6b: implicit vs explicit diffusion
    python scripts/validate.py convergence   # check 5: resolution convergence (about 10 minutes)
    python scripts/validate.py qualitative   # check 7: qualitative behaviour
    python scripts/validate.py solubility    # check 4
    python scripts/validate.py ph_rate       # check 4b: pH-dependent rate law
    python scripts/validate.py renewal       # fluid renewal pulses
    python scripts/validate.py all
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from arystal.engine.isotropic_params import IsotropicParams  # noqa: E402
from arystal.simulation.material_loader import load_material  # noqa: E402
from arystal.validation.check_result import CheckResult, format_report  # noqa: E402
from arystal.validation.iron_check import LIMITS_NOTE as IRON_LIMITS  # noqa: E402
from arystal.validation.iron_check import run_iron_check  # noqa: E402
from arystal.validation.convergence_check import LIMITS_NOTE as CONVERGENCE_LIMITS  # noqa: E402
from arystal.validation.convergence_check import run_convergence_check  # noqa: E402
from arystal.validation.ensemble_check import LIMITS_NOTE as ENSEMBLE_LIMITS  # noqa: E402
from arystal.validation.ensemble_check import run_ensemble_check  # noqa: E402
from arystal.validation.fast_vs_reference_check import LIMITS_NOTE as FAST_LIMITS  # noqa: E402
from arystal.validation.fast_vs_reference_check import run_fast_vs_reference_check  # noqa: E402
from arystal.validation.implicit_check import LIMITS_NOTE as IMPLICIT_LIMITS  # noqa: E402
from arystal.validation.implicit_check import run_implicit_check  # noqa: E402
from arystal.validation.isotropic_check import run_isotropic_check  # noqa: E402
from arystal.validation.live_control_check import LIMITS_NOTE as LIVE_LIMITS  # noqa: E402
from arystal.validation.live_control_check import run_live_control_check  # noqa: E402
from arystal.validation.mass_check import run_mass_check  # noqa: E402
from arystal.validation.qualitative_check import LIMITS_NOTE as QUALITATIVE_LIMITS  # noqa: E402
from arystal.validation.qualitative_check import run_qualitative_check  # noqa: E402
from arystal.validation.ph_rate_check import LIMITS_NOTE as PH_RATE_LIMITS  # noqa: E402
from arystal.validation.ph_rate_check import run_ph_rate_check  # noqa: E402
from arystal.validation.renewal_check import LIMITS_NOTE as RENEWAL_LIMITS  # noqa: E402
from arystal.validation.renewal_check import run_renewal_check  # noqa: E402
from arystal.validation.reproducibility_check import LIMITS_NOTE as REPRODUCIBILITY_LIMITS  # noqa: E402
from arystal.validation.reproducibility_check import run_reproducibility_check  # noqa: E402
from arystal.validation.server_check import LIMITS_NOTE as SERVER_LIMITS  # noqa: E402
from arystal.validation.server_check import run_server_check  # noqa: E402
from arystal.validation.solubility_check import run_solubility_check  # noqa: E402
from arystal.validation.symmetry_check import LIMITS_NOTE as SYMMETRY_LIMITS  # noqa: E402
from arystal.validation.symmetry_check import run_symmetry_check  # noqa: E402

CHECK_NAMES = ["isotropic", "symmetry", "mass", "iron", "reproducibility", "live", "ensemble", "server", "fast", "implicit", "convergence", "qualitative", "solubility", "ph_rate", "renewal"]


def parse_arguments() -> argparse.Namespace:
    """Read the command-line options."""
    parser = argparse.ArgumentParser(description="Run Arystal validation checks.")
    parser.add_argument("check", choices=CHECK_NAMES + ["all"], help="which check to run")
    return parser.parse_args()


def run_check(name: str) -> list[CheckResult]:
    """Run one validation check by name and return its test results."""
    if name == "isotropic":
        return run_isotropic_check(IsotropicParams())
    if name == "symmetry":
        return run_symmetry_check(load_material())
    if name == "mass":
        return run_mass_check(load_material())
    if name == "iron":
        return run_iron_check(load_material())
    if name == "reproducibility":
        return run_reproducibility_check(load_material())
    if name == "live":
        return run_live_control_check(load_material())
    if name == "ensemble":
        return run_ensemble_check(load_material())
    if name == "server":
        return run_server_check(load_material())
    if name == "fast":
        return run_fast_vs_reference_check(load_material())
    if name == "implicit":
        return run_implicit_check(load_material())
    if name == "convergence":
        return run_convergence_check(load_material())
    if name == "qualitative":
        return run_qualitative_check(load_material())
    if name == "renewal":
        return run_renewal_check(load_material())
    if name == "ph_rate":
        return run_ph_rate_check(load_material())
    return run_solubility_check(load_material())


LIMITS = {"symmetry": SYMMETRY_LIMITS, "iron": IRON_LIMITS, "reproducibility": REPRODUCIBILITY_LIMITS, "live": LIVE_LIMITS, "ensemble": ENSEMBLE_LIMITS, "server": SERVER_LIMITS, "fast": FAST_LIMITS, "implicit": IMPLICIT_LIMITS, "convergence": CONVERGENCE_LIMITS, "qualitative": QUALITATIVE_LIMITS, "ph_rate": PH_RATE_LIMITS, "renewal": RENEWAL_LIMITS}

TITLES = {
    "isotropic": "VALIDATION CHECK 1 - isotropic growth (no anisotropy)",
    "symmetry": "VALIDATION CHECK 2 - symmetry and faceted shape",
    "mass": "VALIDATION CHECK 3 - mass conservation (silica)",
    "iron": "VALIDATION CHECK 3b - iron conservation and sector zoning",
    "reproducibility": "VALIDATION - seed reproducibility and saved results",
    "live": "VALIDATION - live control and timeline",
    "ensemble": "VALIDATION - ensemble of replicas",
    "server": "VALIDATION - web server",
    "fast": "VALIDATION CHECK 6 - fast kernels vs reference code",
    "implicit": "VALIDATION CHECK 6b - implicit diffusion vs explicit diffusion",
    "convergence": "VALIDATION CHECK 5 - resolution convergence",
    "qualitative": "VALIDATION CHECK 7 - qualitative behaviour",
    "solubility": "VALIDATION CHECK 4 - solubility curve",
    "ph_rate": "VALIDATION CHECK 4b - pH-dependent quartz rate law",
    "renewal": "VALIDATION - fluid renewal pulses (open system)",
}


def main() -> None:
    """Run the requested check(s), print the reports and exit with an error code if any test failed."""
    name = parse_arguments().check
    names = CHECK_NAMES if name == "all" else [name]
    everything_passed = True
    for check_name in names:
        results = run_check(check_name)
        print(format_report(TITLES[check_name], results, LIMITS.get(check_name, "")) + "\n")
        everything_passed &= all(r.passed for r in results if not r.informational)
    sys.exit(0 if everything_passed else 1)


if __name__ == "__main__":
    main()
