"""Statistics over the replicas of an ensemble: mean, standard deviation, minimum and maximum of each metric."""

import numpy as np

# Columns of metrics.csv that are only labels of the sampling moment, not results.
NON_RESULT_COLUMNS = ("step", "time_model", "time_diffusion_hours", "time_kinetic_years", "temperature_celsius")


def compute_statistics(values: list[float]) -> dict:
    """Return mean, std (sample standard deviation, n - 1), min, max and n of the real (non-nan) values; None where undefined."""
    array = np.array(values, dtype=float)
    array = array[~np.isnan(array)]
    if len(array) == 0:
        return {"mean": None, "std": None, "min": None, "max": None, "n": 0}
    return {
        "mean": float(array.mean()),
        "std": float(array.std(ddof=1)) if len(array) > 1 else None,
        "min": float(array.min()),
        "max": float(array.max()),
        "n": int(len(array)),
    }


def compute_final_statistics(final_rows: list[dict]) -> dict[str, dict]:
    """Return the statistics of every result column over the final metrics row of each replica."""
    columns = [column for column in final_rows[0] if column not in NON_RESULT_COLUMNS]
    return {column: compute_statistics([row[column] for row in final_rows]) for column in columns}


def rows_are_aligned(all_rows: list[list[dict]]) -> bool:
    """True if every replica has the same sampling steps (as happens when they follow the same timeline)."""
    reference = [row["step"] for row in all_rows[0]]
    return all([row["step"] for row in rows] == reference for rows in all_rows)


def compute_timeseries_statistics(all_rows: list[list[dict]]) -> list[dict]:
    """Return, for every sampling moment, the mean and standard deviation over the replicas of each result column.

    Columns are named <metric>_mean and <metric>_std. Requires aligned rows (see rows_are_aligned).
    """
    columns = [column for column in all_rows[0][0] if column not in NON_RESULT_COLUMNS and column not in ("step", "time_model")]
    table = []
    for index, reference in enumerate(all_rows[0]):
        row = {"step": reference["step"], "time_model": reference["time_model"]}
        for column in columns:
            statistics = compute_statistics([rows[index][column] for rows in all_rows])
            row[f"{column}_mean"] = float("nan") if statistics["mean"] is None else statistics["mean"]
            row[f"{column}_std"] = float("nan") if statistics["std"] is None else statistics["std"]
        table.append(row)
    return table
