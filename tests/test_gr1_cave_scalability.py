"""Structural tests for the production GR(1) CAVE scalability benchmark."""

import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from pacti.iocontract import gr1_iocontract as gr1

_SPEC = importlib.util.spec_from_file_location(
    "gr1_cave_scalability", Path(__file__).parents[1] / "examples" / "gr1_cave_scalability.py"
)
assert _SPEC is not None and _SPEC.loader is not None
assert _SPEC is not None and _SPEC.loader is not None
benchmark = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = benchmark
_SPEC.loader.exec_module(benchmark)


def _instance(n_p=2, n_i=1, n_j=3, depth=1):
    """Return one small deterministic benchmark instance."""
    return benchmark.generate_synthetic_instance(benchmark.SyntheticParameters(n_p, n_i, n_j, depth))


def test_generator_is_deterministic_and_dimensions_are_real():
    """Ensure parameters affect the formulas and flattened variables."""
    first = _instance()
    second = _instance()
    assert first.target.to_bucket_dict() == second.target.to_bucket_dict()
    assert first.context.to_bucket_dict() == second.context.to_bucket_dict()

    depth_zero = _instance(depth=0)
    depth_two = _instance(depth=2)
    assert depth_zero.structural_metrics()["maximum_next_depth"] == 0
    assert depth_two.structural_metrics()["maximum_next_depth"] == 2
    assert depth_two.structural_metrics()["indexed_variables"] > depth_zero.structural_metrics()["indexed_variables"]

    one_eliminated = _instance(n_p=1)
    assert len(first.eliminated) == 2
    assert len(one_eliminated.eliminated) == 1
    assert len(_instance(n_i=2).target.liv_terms()) == 2
    assert len(_instance(n_j=2).context.liv_terms()) == 2


def test_pilot_constructs_complete_tagged_candidate_family():
    """Require synthetic plus every fixed support before selection."""
    pilot = benchmark.select_support_pilot(benchmark.SyntheticParameters(2, 1, 3, 1))
    assert len(pilot["candidates"]) == 4
    assert [term.tag for term in pilot["candidates"]] == [gr1.GR1Tag.LIV] + [gr1.GR1Tag.INV] * 3
    assert pilot["selected"] is pilot["candidates"][0]


def test_n_j_increases_fixed_candidates_and_always_constructs_synthetic():
    """Check actual production counters for the support sweep."""
    observed = []
    for n_j in (1, 2, 3):
        _, metrics = benchmark.run_instrumented_refinement(_instance(n_j=n_j))
        observed.append(
            (
                metrics.synthetic_candidates,
                metrics.support_candidates,
            )
        )
    assert observed == [(1, 1), (1, 2), (1, 3)]


def test_depth_elimination_and_target_dimensions_reach_cave():
    """Verify actual quantified windows, eliminated atoms, and target calls."""
    depth_metrics = []
    for depth in (0, 1, 2):
        _, metrics = benchmark.run_instrumented_refinement(_instance(n_j=2, depth=depth))
        depth_metrics.append((metrics.maximum_quantified_depth, metrics.maximum_quantified_indexed_variables))
    assert depth_metrics == [(0, 6), (1, 10), (2, 14)]

    _, one_p = benchmark.run_instrumented_refinement(_instance(n_p=1, n_j=2))
    _, two_p = benchmark.run_instrumented_refinement(_instance(n_p=2, n_j=2))
    assert one_p.maximum_quantified_atoms == 2
    assert two_p.maximum_quantified_atoms == 4

    _, one_i = benchmark.run_instrumented_refinement(_instance(n_i=1, n_j=2))
    _, two_i = benchmark.run_instrumented_refinement(_instance(n_i=2, n_j=2))
    assert one_i.liveness_targets == 1
    assert two_i.liveness_targets == 2


def test_instrumentation_preserves_result_and_resets():
    """Ensure observers delegate unchanged and counters can be reset."""
    instance = _instance(n_j=2)
    plain, _ = instance.target.elim_vars_by_refining(
        context=instance.context,
        vars_to_elim=list(instance.eliminated),
        simplify=False,
        tactics_order=[],
    )
    observed, metrics = benchmark.run_instrumented_refinement(instance)
    assert gr1._inv_terms_refine(plain.inv_terms(), observed.inv_terms())
    assert gr1._inv_terms_refine(observed.inv_terms(), plain.inv_terms())
    assert plain.refines(observed) and observed.refines(plain)
    assert metrics.cave_invocations == 1

    instrumentation = benchmark.CaveInstrumentation()
    with instrumentation.observe():
        instance.target.elim_vars_by_refining(
            context=instance.context,
            vars_to_elim=list(instance.eliminated),
            simplify=False,
            tactics_order=[],
        )
    assert instrumentation.metrics.solver_checks > 0
    instrumentation.reset()
    assert instrumentation.metrics == benchmark.CaveMetrics()


class _FakeInstance:
    """Minimal deterministic instance used to test checkpoint orchestration."""

    def structural_metrics(self):
        """Return stable structural fields without invoking CAVE."""
        return {"base_variables": 1, "indexed_variables": 1}


def _metadata():
    """Return stable checkpoint compatibility metadata."""
    return {
        "python_version": "test-python",
        "z3_version": "test-z3",
        "z3_solver_package_version": "test-z3-package",
        "pacti_version": "test-pacti",
        "git_commit": "test-commit",
        "git_dirty": "false",
        "platform": "test-platform",
        "processor": "test-processor",
    }


def _configure_tiny_sweep(monkeypatch):
    """Replace only orchestration dimensions; no benchmark formula is evaluated."""
    monkeypatch.setattr(benchmark, "_SWEEPS", {"n_p": (1,)})
    monkeypatch.setattr(benchmark, "_BASELINE", benchmark.SyntheticParameters(2, 2, 2, 1))
    monkeypatch.setattr(benchmark, "_environment_metadata", _metadata)
    monkeypatch.setattr(benchmark, "generate_synthetic_instance", lambda _parameters: _FakeInstance())
    monkeypatch.setattr(benchmark, "_term_list_z3_size", lambda _result: 7)


def _fake_success():
    """Return one deterministic untimed stand-in result and counter set."""
    return object(), benchmark.CaveMetrics(cave_invocations=1, solver_checks=2)


def test_completed_measurement_is_persisted_before_next_run(tmp_path, monkeypatch):
    """A completed raw row must survive an interruption in the following run."""
    _configure_tiny_sweep(monkeypatch)
    calls = 0

    def execute(_instance):
        nonlocal calls
        calls += 1
        if calls == 3:  # warm-up, measured 1, then interrupt measured 2
            raise KeyboardInterrupt
        return _fake_success()

    monkeypatch.setattr(benchmark, "run_instrumented_refinement", execute)
    checkpoint = tmp_path / "checkpoint.json"
    results = tmp_path / "results.csv"
    benchmark.run_synthetic_benchmark(
        3,
        results_path=results,
        checkpoint_path=checkpoint,
    )

    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert state["measured_runs_completed"] == 1
    assert state["current"]["status"] == "interrupted"
    assert state["current"]["active_repetition"] == 2
    with results.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [(row["row_type"], row["repetition"]) for row in rows] == [("raw", "1")]


def test_resume_continues_partial_and_does_not_duplicate_rows(tmp_path, monkeypatch):
    """Resume performs a fresh warm-up and continues at the first missing run."""
    _configure_tiny_sweep(monkeypatch)
    calls = 0

    def interrupt_after_one(_instance):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise KeyboardInterrupt
        return _fake_success()

    monkeypatch.setattr(benchmark, "run_instrumented_refinement", interrupt_after_one)
    checkpoint = tmp_path / "checkpoint.json"
    results = tmp_path / "results.csv"
    benchmark.run_synthetic_benchmark(3, results_path=results, checkpoint_path=checkpoint)

    resumed_calls = 0

    def finish(_instance):
        nonlocal resumed_calls
        resumed_calls += 1
        return _fake_success()

    monkeypatch.setattr(benchmark, "run_instrumented_refinement", finish)
    rows = benchmark.run_synthetic_benchmark(
        3,
        results_path=results,
        checkpoint_path=checkpoint,
        resume=True,
    )
    raw = [row for row in rows if row["row_type"] == "raw"]
    assert resumed_calls == 3  # one fresh warm-up and two missing measurements
    assert [row["repetition"] for row in raw] == [1, 2, 3]
    assert len({(row["sweep"], row["parameter_value"], row["repetition"]) for row in raw}) == 3
    assert json.loads(checkpoint.read_text(encoding="utf-8"))["dataset_complete"] is True


def test_resume_skips_completed_configuration(tmp_path, monkeypatch):
    """A complete configuration is skipped without another warm-up or measurement."""
    _configure_tiny_sweep(monkeypatch)
    monkeypatch.setattr(benchmark, "run_instrumented_refinement", lambda _instance: _fake_success())
    checkpoint = tmp_path / "checkpoint.json"
    results = tmp_path / "results.csv"
    benchmark.run_synthetic_benchmark(1, results_path=results, checkpoint_path=checkpoint)

    def unexpected(_instance):
        raise AssertionError("completed configuration was executed again")

    monkeypatch.setattr(benchmark, "run_instrumented_refinement", unexpected)
    benchmark.run_synthetic_benchmark(
        1,
        results_path=results,
        checkpoint_path=checkpoint,
        resume=True,
    )


def test_incompatible_or_duplicate_checkpoint_is_rejected(tmp_path, monkeypatch):
    """Metadata mismatches and duplicate raw identities cannot be resumed."""
    _configure_tiny_sweep(monkeypatch)
    metadata = _metadata()
    identity = benchmark._synthetic_identity(metadata, 2)
    checkpoint = tmp_path / "checkpoint.json"
    benchmark._atomic_write_json(
        checkpoint,
        benchmark._checkpoint_state(identity, metadata, [], {}, 2),
    )
    incompatible = dict(identity)
    incompatible["measured_repetitions"] = 3
    with pytest.raises(RuntimeError, match="metadata does not match"):
        benchmark._load_synthetic_checkpoint(checkpoint, incompatible)

    row = {"row_type": "raw", "sweep": "n_p", "parameter_value": 1, "repetition": 1}
    state = benchmark._checkpoint_state(identity, metadata, [row, dict(row)], {}, 2)
    benchmark._atomic_write_json(checkpoint, state)
    with pytest.raises(RuntimeError, match="duplicate raw measurement"):
        benchmark._load_synthetic_checkpoint(checkpoint, identity)


def test_aggregates_require_all_expected_repetitions(monkeypatch):
    """Partial data remain raw-only; complete data receive exact aggregates."""
    _configure_tiny_sweep(monkeypatch)

    def row(repetition, duration):
        return {
            "row_type": "raw",
            "sweep": "n_p",
            "parameter_value": 1,
            "repetition": repetition,
            "operation_seconds": duration,
            "cave_seconds": duration,
            "refinement_seconds": duration,
            "relaxation_seconds": 0.0,
            "qe_seconds": duration / 2,
            "non_qe_seconds": duration / 2,
        }

    partial = [row(1, 1.0)]
    assert all(item["row_type"] == "raw" for item in benchmark._aggregate_synthetic_rows(partial, 2))
    complete = benchmark._aggregate_synthetic_rows(partial + [row(2, 3.0)], 2)
    aggregates = [item for item in complete if item["row_type"] == "aggregate"]
    assert len(aggregates) == 1
    assert aggregates[0]["cave_seconds_median"] == 2.0
    state = benchmark._checkpoint_state(
        benchmark._synthetic_identity(_metadata(), 2),
        _metadata(),
        partial,
        {},
        2,
    )
    assert state["dataset_complete"] is False


@pytest.mark.parametrize("n_i,n_j", [(1, 1), (2, 3), (3, 2)])
def test_complete_family_count_identity(n_i, n_j):
    """One synthetic invocation has n_I synthetic and n_I*n_J fixed candidates."""
    _, metrics = benchmark.run_instrumented_refinement(_instance(n_p=1, n_i=n_i, n_j=n_j, depth=0))
    assert (metrics.cave_invocations, metrics.refinement_invocations, metrics.relaxation_invocations) == (1, 1, 0)
    assert metrics.synthetic_candidates == n_i
    assert metrics.support_candidates == n_i * n_j
    assert metrics.total_candidates == n_i * (1 + n_j)
    assert metrics.qe_tactic_applications == metrics.qe_applications
    assert metrics.cumulative_cave_seconds == pytest.approx(metrics.qe_seconds + metrics.non_qe_seconds)


def test_schema_four_protocol_and_metrics():
    """Current rows identify the implementation/protocol and exclude legacy counters."""
    metadata = benchmark._measurement_metadata(10, "synthetic")
    assert metadata["schema_version"] == 4
    assert metadata["benchmark_family"] == "gr1-cave-complete-candidates-v3"
    assert metadata["warmup_count"] == 1 and metadata["measured_repetitions"] == 10
    assert len(metadata["implementation_sha256"]) == 64
    assert vars(benchmark._BASELINE) == {"n_p": 2, "n_I": 2, "n_J": 2, "D": 1}
    assert benchmark._SWEEPS == {
        "n_p": (1, 2, 4, 6, 8),
        "n_I": (1, 2, 4, 6, 8),
        "n_J": (1, 2, 4, 6, 8),
        "D": (0, 1, 2, 3, 4, 5),
    }
    counters = benchmark._metric_counts(benchmark.CaveMetrics())
    assert {
        "synthetic_candidates",
        "support_candidates",
        "total_candidates",
        "qe_applications",
        "qe_tactic_applications",
        "solver_checks",
        "optimize_checks",
    } <= set(counters)
    assert not any(word in key for key in counters for word in ("viab", "domin", "associated", "fallback"))
    assert not any(key.endswith("_seconds") for key in counters)


@pytest.mark.parametrize("fail", [False, True])
def test_qe_timer_is_nested_safe_and_restores_wrappers(monkeypatch, fail):
    """Fake clocks establish a disjoint partition without measuring a workload."""
    token = object()

    def apply(_tactic, stage):
        if stage == "outer":
            return benchmark.z3.Tactic.apply(None, "inner")
        if fail:
            raise ValueError("test failure")
        return token

    def eliminate(_expr):
        return benchmark.z3.Tactic.apply(None, "outer")

    def refine(_self):
        return gr1._eliminate_quantifiers(None)

    monkeypatch.setattr(benchmark.z3.Tactic, "apply", apply)
    monkeypatch.setattr(gr1, "_eliminate_quantifiers", eliminate)
    monkeypatch.setattr(gr1.GR1TermList, "elim_vars_by_refining", refine)
    ticks = iter([0.0, 1.0, 3.0, 5.0])
    monkeypatch.setattr(benchmark, "perf_counter", lambda: next(ticks))
    observer = benchmark.CaveInstrumentation()
    with observer.observe():
        if fail:
            with pytest.raises(ValueError, match="test failure"):
                getattr(gr1.GR1TermList, "elim_vars_by_refining")(None)
        else:
            assert getattr(gr1.GR1TermList, "elim_vars_by_refining")(None) is token
    assert observer.metrics.cumulative_cave_seconds == 5.0
    assert observer.metrics.qe_seconds == 2.0
    assert observer.metrics.non_qe_seconds == 3.0
    assert observer.metrics.qe_tactic_applications == 2
    assert not observer.active and observer._projection_depth == observer._qe_timer_depth == 0
    assert benchmark.z3.Tactic.apply is apply
    assert gr1._eliminate_quantifiers is eliminate


def test_schema_three_checkpoint_cannot_resume(tmp_path):
    identity = benchmark._synthetic_identity(_metadata(), 10)
    old = dict(identity, schema_version=3)
    path = tmp_path / "old.json"
    path.write_text(json.dumps({"identity": old}))
    with pytest.raises(RuntimeError, match="metadata does not match"):
        benchmark._load_synthetic_checkpoint(path, identity)


def _plotter():
    spec = importlib.util.spec_from_file_location(
        "plot_gr1_cave_scalability", Path(__file__).parents[1] / "examples" / "plot_gr1_cave_scalability.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _publication_rows():
    """Fabricated schema fixtures only; never represent these as measurements."""
    rows = []
    for sweep, values in benchmark._SWEEPS.items():
        for value in values:
            dimensions = dict(vars(benchmark._BASELINE), **{sweep: value})
            n_i, n_j = dimensions["n_I"], dimensions["n_J"]
            common = {
                **_metadata(),
                **benchmark._measurement_metadata(10, "synthetic"),
                **dimensions,
                "sweep": sweep,
                "parameter_value": value,
                "synthetic_candidates": n_i,
                "support_candidates": n_i * n_j,
                "total_candidates": n_i * (1 + n_j),
                "qe_applications": 1,
                "qe_tactic_applications": 1,
                "solver_checks": 1,
                "optimize_checks": 0,
            }
            for repetition in range(1, 11):
                rows.append(
                    dict(
                        common,
                        row_type="raw",
                        repetition=repetition,
                        cave_seconds=1.0,
                        qe_seconds=0.25,
                        non_qe_seconds=0.75,
                    )
                )
            rows.append(
                dict(
                    common,
                    row_type="aggregate",
                    repetition="",
                    cave_seconds_median=1.0,
                    cave_seconds_q1=1.0,
                    cave_seconds_q3=1.0,
                    qe_seconds_median=0.25,
                    non_qe_seconds_median=0.75,
                    operation_seconds_median=1.1,
                )
            )
    return rows


def test_plot_validation_accepts_only_complete_current_data(tmp_path):
    path = tmp_path / "new.csv"
    benchmark.write_csv(path, _publication_rows())
    assert len(_plotter()._aggregate_rows(path)) == 21


@pytest.mark.parametrize("damage", ["schema", "legacy", "partial", "duplicate", "candidates", "timing", "mixed"])
def test_plot_validation_rejects_historical_or_invalid_data(tmp_path, damage):
    rows = _publication_rows()
    if damage == "schema":
        rows[0]["schema_version"] = 2
    elif damage == "legacy":
        rows[0]["viability_checks"] = 1
    elif damage == "partial":
        rows.pop(0)
    elif damage == "duplicate":
        rows.append(dict(rows[0]))
    elif damage == "candidates":
        rows[0]["total_candidates"] = 999
    elif damage == "timing":
        rows[0]["qe_seconds"] = 2.0
    else:
        rows[0]["implementation_sha256"] = "different"
    path = tmp_path / "bad.csv"
    benchmark.write_csv(path, rows)
    with pytest.raises(ValueError):
        _plotter()._aggregate_rows(path)


def test_plot_validation_rejects_missing_phase_columns(tmp_path):
    path = tmp_path / "historical.csv"
    benchmark.write_csv(path, [{"row_type": "aggregate", "sweep": "n_J", "parameter_value": 1}])
    with pytest.raises(ValueError, match="Historical"):
        _plotter()._aggregate_rows(path)
