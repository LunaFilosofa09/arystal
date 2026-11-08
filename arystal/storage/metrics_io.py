"""metrics.csv: reading and writing the metrics over time."""

import csv
from pathlib import Path


def write_metrics_csv(path: Path, rows: list[dict]) -> None:
    """Write the metric rows to a CSV file (column order of the first row; nan is written as 'nan')."""
    with open(path, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_metrics_csv(path: Path) -> list[dict]:
    """Read a metrics CSV file back into a list of rows with float values."""
    with open(path, newline="") as file:
        return [{key: float(value) for key, value in row.items()} for row in csv.DictReader(file)]
