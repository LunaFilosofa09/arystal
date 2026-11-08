"""Shared result type and report format for all validation checks."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckResult:
    """Outcome of one test: pass or fail, and a sentence a human can read."""

    name: str
    passed: bool
    message: str
    informational: bool = False  # a measurement that is reported but does not decide pass or fail


def format_report(title: str, results: list[CheckResult], limits: str = "") -> str:
    """Return the results of one validation check as plain text, one block per test.

    `limits` is an optional sentence saying what the check does NOT prove.
    """
    lines = [title]
    for result in results:
        status = "INFO" if result.informational else ("PASS" if result.passed else "FAIL")
        lines.append(f"  [{status}] {result.name}\n         {result.message}")
    verdict = "ALL PASSED" if all(r.passed for r in results if not r.informational) else "SOMETHING FAILED"
    lines.append(f"RESULT: {verdict}")
    if limits:
        lines.append(limits)
    return "\n".join(lines)
