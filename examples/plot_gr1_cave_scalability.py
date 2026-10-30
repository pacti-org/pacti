"""Reproduce publication figures from final synthetic aggregate measurements.

``gr1_cave_scalability_results.csv`` supplies the median and Q1--Q3 interval
for each one-parameter-at-a-time runtime point, with a median qe2-time overlay.
Only complete schema-4 datasets are accepted; historical figures are not regenerated
until a new experiment is explicitly run. Zero QE times are omitted on log axes. The combined runtime PDF and
four ``gr1_cave_scalability_runtime_*.pdf`` files show the four sweeps. The
call-count PDF shows constructed synthetic and fixed-support candidates for ``n_J``;
these are algorithmic call counts, not empirical runtime-complexity claims.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt

_SWEEPS = ("n_p", "n_I", "n_J", "D")
_PANEL_LABELS = {
    "n_p": r"(a) Eliminated variables $n_p$",
    "n_I": r"(b) Target liveness cores $n_I$",
    "n_J": r"(c) Context liveness cores $n_J$",
    "D": r"(d) Maximum NEXT depth $D_B$",
}
_AXIS_LABELS = {
    "n_p": r"Eliminated variables $n_p$",
    "n_I": r"Target liveness cores $n_I$",
    "n_J": r"Context liveness cores $n_J$",
    "D": r"Maximum NEXT depth $D_B$",
}


def _aggregate_rows(path: Path) -> List[Dict[str, str]]:
    """Reject historical/incomplete data before creating any output figures."""
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    required = {
        "schema_version",
        "benchmark_family",
        "benchmark_mode",
        "implementation_sha256",
        "timing_protocol",
        "baseline_json",
        "sweeps_json",
        "resume_warmup_policy",
        "git_commit",
        "python_version",
        "z3_version",
        "pacti_version",
        "warmup_count",
        "measured_repetitions",
        "row_type",
        "sweep",
        "parameter_value",
        "n_p",
        "n_I",
        "n_J",
        "D",
        "synthetic_candidates",
        "support_candidates",
        "total_candidates",
        "qe_applications",
        "qe_tactic_applications",
        "solver_checks",
        "optimize_checks",
        "cave_seconds_median",
        "cave_seconds_q1",
        "cave_seconds_q3",
        "qe_seconds_median",
        "non_qe_seconds_median",
        "operation_seconds_median",
        "repetition",
        "cave_seconds",
        "qe_seconds",
        "non_qe_seconds",
    }
    if not rows or not required.issubset(rows[0]):
        raise ValueError("Historical or incomplete dataset: complete schema-4 repaired measurements required")
    forbidden = {
        "viability_checks",
        "dominance_checks",
        "dominance_frontier_inputs",
        "dominance_implication_checks",
        "associated_supports",
        "viable_supports",
        "nonviable_supports",
        "undominated_supports",
        "fallback_supports",
    }
    if forbidden.intersection(rows[0]):
        raise ValueError("Legacy filtering metrics are not valid schema-4 measurements")
    expected = {
        (sweep, value) for sweep in _SWEEPS for value in ((0, 1, 2, 3, 4, 5) if sweep == "D" else (1, 2, 4, 6, 8))
    }
    aggregates = {}
    raw = {}
    identities = set()
    for row in rows:
        if (row["schema_version"], row["benchmark_family"], row["benchmark_mode"]) != (
            "4",
            "gr1-cave-complete-candidates-v3",
            "synthetic",
        ):
            raise ValueError("Historical schema/family: rerun repaired schema-4 synthetic experiment")
        if row["timing_protocol"] != "outer-cave-minus-nested-qe2-apply-v1":
            raise ValueError("Unsupported phase timing protocol")
        if row["warmup_count"] != "1" or row["measured_repetitions"] != "10":
            raise ValueError("Publication protocol requires one warm-up and ten measured repetitions")
        identities.add(
            tuple(
                row[k]
                for k in (
                    "implementation_sha256",
                    "git_commit",
                    "python_version",
                    "z3_version",
                    "pacti_version",
                    "timing_protocol",
                    "baseline_json",
                    "sweeps_json",
                    "resume_warmup_policy",
                )
            )
        )
        key = row["sweep"], int(row["parameter_value"])
        if key not in expected:
            raise ValueError("Unexpected sweep configuration")
        dimensions = {"n_p": 2, "n_I": 2, "n_J": 2, "D": 1}
        dimensions[key[0]] = key[1]
        if any(int(row[k]) != v for k, v in dimensions.items()):
            raise ValueError("Sweep does not use the prescribed baseline")
        n_i, n_j = dimensions["n_I"], dimensions["n_J"]
        if tuple(int(row[k]) for k in ("synthetic_candidates", "support_candidates", "total_candidates")) != (
            n_i,
            n_i * n_j,
            n_i * (1 + n_j),
        ):
            raise ValueError("Candidate counts disagree with the complete theoretical family")
        if row["row_type"] == "aggregate":
            if key in aggregates:
                raise ValueError("Duplicate aggregate configuration")
            for name in (
                "cave_seconds_median",
                "cave_seconds_q1",
                "cave_seconds_q3",
                "qe_seconds_median",
                "non_qe_seconds_median",
                "operation_seconds_median",
            ):
                value = float(row[name])
                if not math.isfinite(value) or value < 0:
                    raise ValueError("Invalid aggregate timing")
            if float(row["cave_seconds_median"]) <= 0:
                raise ValueError("CAVE time must be positive for logarithmic plotting")
            aggregates[key] = row
        elif row["row_type"] == "raw":
            repetition = int(row["repetition"])
            seen = raw.setdefault(key, set())
            if repetition in seen or not 1 <= repetition <= 10:
                raise ValueError("Duplicate or invalid raw repetition")
            seen.add(repetition)
            total, qe, residual = (float(row[k]) for k in ("cave_seconds", "qe_seconds", "non_qe_seconds"))
            if not all(math.isfinite(v) and v >= 0 for v in (total, qe, residual)) or not math.isclose(
                total, qe + residual, rel_tol=1e-9, abs_tol=1e-9
            ):
                raise ValueError("Invalid disjoint QE/non-QE timing partition")
        else:
            raise ValueError("Unexpected row type")
    if (
        len(identities) != 1
        or set(aggregates) != expected
        or any(raw.get(key) != set(range(1, 11)) for key in expected)
    ):
        raise ValueError("Incomplete or mixed dataset: require 21 configurations and 210 raw measurements")
    return list(aggregates.values())


def _draw_runtime_axis(axis, rows: List[Dict[str, str]], sweep: str, label: str) -> None:
    """Draw one runtime sweep on an existing axis."""
    selected = sorted(
        (row for row in rows if row["sweep"] == sweep),
        key=lambda row: int(row["parameter_value"]),
    )
    values = [int(row["parameter_value"]) for row in selected]
    medians = [float(row["cave_seconds_median"]) for row in selected]
    first_quartiles = [float(row["cave_seconds_q1"]) for row in selected]
    third_quartiles = [float(row["cave_seconds_q3"]) for row in selected]
    axis.fill_between(values, first_quartiles, third_quartiles, color="#4C78A8", alpha=0.22, linewidth=0)
    axis.plot(values, medians, color="#2F5D8A", marker="o", markersize=4.5, linewidth=1.5, label="Total CAVE")
    qe_medians = [float(row["qe_seconds_median"]) or float("nan") for row in selected]
    axis.plot(values, qe_medians, color="#B04A3A", linestyle="--", linewidth=1.2, label="qe2 apply")
    axis.legend(frameon=False, fontsize=8)
    axis.set_yscale("log")
    axis.set_xticks(values)
    axis.set_xlabel(label)
    axis.grid(axis="y", which="both", color="0.88", linewidth=0.45)


def plot_runtime(rows: List[Dict[str, str]], output: Path) -> None:
    """Plot median CAVE runtime and interquartile ranges for four sweeps."""
    baseline = r"other parameters fixed at $n_p=n_I=n_J=2$, $D_B=1$"
    figure, axes = plt.subplots(2, 2, figsize=(6.5, 4.8), constrained_layout=True)
    for axis, sweep in zip(axes.flat, _SWEEPS):
        _draw_runtime_axis(axis, rows, sweep, _PANEL_LABELS[sweep])
    axes[0, 0].set_ylabel("CAVE runtime (s)")
    axes[1, 0].set_ylabel("CAVE runtime (s)")
    figure.supxlabel(baseline, fontsize=9)
    figure.savefig(output, format="pdf", bbox_inches="tight")
    plt.close(figure)


def plot_runtime_panels(rows: List[Dict[str, str]], directory: Path) -> None:
    """Save each runtime sweep separately without panel titles or annotations."""
    filenames = {"n_p": "np", "n_I": "nI", "n_J": "nJ", "D": "D_B"}
    for sweep in _SWEEPS:
        figure, axis = plt.subplots(figsize=(3.4, 2.65), constrained_layout=True)
        _draw_runtime_axis(axis, rows, sweep, _AXIS_LABELS[sweep])
        axis.set_ylabel("CAVE runtime (s)")
        figure.savefig(
            directory / f"gr1_cave_scalability_runtime_{filenames[sweep]}.pdf",
            format="pdf",
            bbox_inches="tight",
        )
        plt.close(figure)


def plot_calls(rows: List[Dict[str, str]], output: Path) -> None:
    """Plot constructed candidate counts for the context sweep."""
    selected = sorted((row for row in rows if row["sweep"] == "n_J"), key=lambda row: int(row["parameter_value"]))
    x = [int(row["parameter_value"]) for row in selected]
    synthetic = [int(row["synthetic_candidates"]) for row in selected]
    fixed = [int(row["support_candidates"]) for row in selected]
    figure, axis = plt.subplots(figsize=(3.45, 2.35), constrained_layout=True)
    axis.plot(x, synthetic, color="#2F5D8A", marker="o", linewidth=1.35, label="Synthetic candidates")
    axis.plot(x, fixed, color="#B04A3A", marker="s", linewidth=1.35, label="Fixed-support candidates")
    axis.set_xlabel(r"Context liveness cores $n_J$")
    axis.set_ylabel("Production call count")
    axis.set_xticks(x)
    axis.set_ylim(bottom=0)
    axis.grid(axis="y", color="0.88", linewidth=0.45)
    axis.legend(frameon=False, fontsize=9)
    figure.savefig(output, format="pdf", bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    """Create combined, standalone, and call-count vector PDFs from CSV data."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="complete schema-4 synthetic CSV")
    parser.add_argument("--output-dir", type=Path, required=True, help="directory for newly generated figures")
    args = parser.parse_args()
    rows = _aggregate_rows(args.input)  # Validate before creating files/directories.
    directory = args.output_dir
    directory.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 10,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "pdf.fonttype": 42,
        }
    )
    plot_runtime(rows, directory / "gr1_cave_scalability_runtime.pdf")
    plot_runtime_panels(rows, directory)
    plot_calls(rows, directory / "gr1_cave_scalability_calls.pdf")


if __name__ == "__main__":
    main()
