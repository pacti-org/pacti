"""GR(1) CAVE structural pilot, synthetic benchmark, and AEB benchmark.

All modes invoke the same CAVE implementation used by Pacti's GR(1) contract
operations. Instrumentation delegates every call to that implementation and
does not change generated formulas, solver options, or support selection.

``--pilot`` runs a small structural sanity check. It confirms that the
synthetic family exercises bounded-next finite-window construction, quantified
elimination, and synthetic plus every fixed-support certificate before
selection. Pilot output is diagnostic and is not part of the final repeated
scalability dataset.

``--synthetic`` runs the controlled one-parameter-at-a-time scalability
experiment. Its parameters are the number of eliminated variables ``n_p``,
target liveness cores ``n_I``, context liveness cores/supports ``n_J``, and
maximum bounded NEXT depth ``D``. The baseline is
``n_p=n_I=n_J=2, D=1``; the final sweeps are::

    n_p = 1, 2, 4, 6, 8
    n_I = 1, 2, 4, 6, 8
    n_J = 1, 2, 4, 6, 8
    D   = 0, 1, 2, 3, 4, 5

Each configuration receives one unrecorded warm-up followed by 10 measured
runs by default, with no benchmark timeout or intentional interruption. The
family isolates these principal complexity dimensions; it is not intended to
represent arbitrary GR(1) formula structure or establish an empirical
asymptotic runtime class. Every target constructs one recurrent synthetic
candidate plus every persistent fixed-support candidate. Selection does not
perform finite-core dominance comparisons across temporal wrappers.

``--aeb`` measures the paper's application example using exactly::

    C_COMP = C_S.compose(C_V, simplify=True)
    Q = C_COMP.quotient(C_V, simplify=True)

It records end-to-end operation time separately from cumulative time inside
CAVE. Imports, construction of ``C_S`` and ``C_V``, presentation and printing,
recomposition, validation, and CSV/report generation are outside the timing
boundary. Like the synthetic experiment, it uses one warm-up and 10 measured
runs by default. It complements the controlled family by measuring the
implemented method on the nontrivial AEB running example.

Schema 4 adds disjoint QE/non-QE CAVE times and row-level provenance.
QE time wraps Tactic.apply only inside _eliminate_quantifiers (currently qe2),
including Python goal marshalling; the driver's post-QE simplification is in
non-QE time. Nested applications contribute time only once. Non-QE is not
pure encoding time: it includes selection, simplification and observer overhead.
Input parsing/flattening occurs before the synthetic timing boundary. Observers
are intended for serial benchmark execution, not concurrent production use.
Historical schema-2 and partial schema-3 results cannot be resumed as schema 4.
Use --output-dir to preserve those files. No historical phase timings are inferred.

Generated artifacts are:

* ``gr1_cave_scalability_results.csv``: raw and aggregate synthetic results;
* ``gr1_cave_scalability_checkpoint.json``: authoritative incremental state
  while a synthetic run is incomplete;
* ``aeb_gr1_performance_results.csv``: raw and aggregate AEB results;
* ``gr1_cave_scalability_runtime.pdf`` and
  ``gr1_cave_scalability_runtime_*.pdf``: combined and separate runtime plots;
* ``gr1_cave_scalability_calls.pdf``: synthetic/fixed-support candidate counts.

Aggregate timings contain median, Q1, Q3, IQR, minimum, and maximum values.
The PDFs are generated separately by ``plot_gr1_cave_scalability.py``.

Synthetic progress is flushed immediately. Every completed measured run is
atomically checkpointed and reflected in the results CSV before the next run
starts. ``--resume`` validates the checkpoint identity, skips completed work,
and performs a fresh warm-up before continuing a partial configuration.
Progress, checkpoint I/O, aggregation, and resume bookkeeping remain outside
the unchanged operation timing boundary. Ctrl+C preserves completed rows and
prints the exact interrupted configuration. No automatic timeout is imposed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple
from unittest.mock import patch

import numpy as np
import z3
from z3.z3util import get_vars

from pacti.iocontract import Var
from pacti.iocontract import gr1_iocontract as gr1


def _next(variable: str, depth: int) -> str:
    """Return one parser expression with the requested nested NEXT depth."""
    result = variable
    for _ in range(depth):
        result = f"X({result})"
    return result


def _conjunction(parts: Sequence[str]) -> str:
    """Return a parenthesized conjunction."""
    return "(" + " & ".join(parts) + ")"


def _syntax_size(node: Any) -> int:
    """Count nodes in one retained parser syntax tree."""
    if node is None:
        return 0
    return 1 + sum(_syntax_size(child) for child in node.children)


def _term_list_syntax_size(terms: gr1.GR1TermList) -> int:
    """Return the sum of parser syntax-tree nodes across a term list."""
    return sum(_syntax_size(term.core.syntax) for term in terms.terms)


def _term_list_z3_size(terms: gr1.GR1TermList) -> int:
    """Return distinct Z3 DAG nodes in the conjunction of all cores."""
    return gr1._z3_ast_size(gr1._and_expr(list(terms.terms)))


def _indexed_names(*terms: gr1.GR1TermList) -> List[str]:
    """Return sorted flattened Z3 variable names in the supplied term lists."""
    names: set[str] = set()
    for term_list in terms:
        for term in term_list.terms:
            names.update(variable.decl().name() for variable in get_vars(term.core.expr))
    return sorted(names)


def _max_index(names: Sequence[str]) -> int:
    """Return the greatest flattened NEXT index in a collection of names."""
    return max((gr1._parse_flat_name(name)[1] for name in names), default=0)


@dataclass(frozen=True)
class SyntheticParameters:
    """Parameters of one deterministic synthetic refinement-CAVE instance."""

    n_p: int
    n_I: int
    n_J: int
    D: int

    def __post_init__(self) -> None:
        """Reject empty or negative dimensions."""
        if self.n_p < 1 or self.n_I < 1 or self.n_J < 1 or self.D < 0:
            raise ValueError("n_p, n_I, and n_J must be positive; D must be nonnegative")


@dataclass(frozen=True)
class SyntheticInstance:
    """One generated target/context pair for production CAVE refinement."""

    parameters: SyntheticParameters
    target: gr1.GR1TermList
    context: gr1.GR1TermList
    eliminated: Tuple[Var, ...]
    variable_sorts: Dict[str, str]

    @property
    def base_variable_count(self) -> int:
        """Return eliminated plus retained base-variable count."""
        return 2 * self.parameters.n_p + self.parameters.n_I + self.parameters.n_J

    def structural_metrics(self) -> Dict[str, int]:
        """Return reproducible input-structure measurements."""
        names = _indexed_names(self.target, self.context)
        return {
            "eliminated_base_variables": len(self.eliminated),
            "retained_base_variables": self.base_variable_count - len(self.eliminated),
            "base_variables": self.base_variable_count,
            "indexed_variables": len(names),
            "maximum_next_depth": _max_index(sorted(names)),
            "syntax_tree_nodes": _term_list_syntax_size(self.target) + _term_list_syntax_size(self.context),
            "flattened_z3_dag_nodes": _term_list_z3_size(self.target) + _term_list_z3_size(self.context),
            "target_liveness_cores": len(self.target.liv_terms()),
            "context_liveness_cores": len(self.context.liv_terms()),
        }


def generate_synthetic_instance(parameters: SyntheticParameters) -> SyntheticInstance:
    """Generate the deterministic support-selection family.

    Let ``P`` be the conjunction of the eliminated Boolean variables ``p_k``.
    The retained ``a_k`` variables anchor the invariant context with
    ``X^r(p_k) <-> X^r(a_k)`` for every ``r`` from zero through ``D``. Target
    liveness cores are ``GF(P <-> t_i)`` and context liveness supports are
    ``GF(P <-> s_j)``.

    Thus ``n_p`` enlarges the quantified elimination dimension, ``D`` enlarges
    the finite temporal window and indexed representation, ``n_I`` adds target
    liveness obligations, and ``n_J`` adds fixed-support projections. Every
    target also receives a synthetic projection. This is not a general GR(1)
    workload model.
    """
    p_names = [f"p{k}" for k in range(parameters.n_p)]
    a_names = [f"a{k}" for k in range(parameters.n_p)]
    t_names = [f"t{i}" for i in range(parameters.n_I)]
    s_names = [f"s{j}" for j in range(parameters.n_J)]
    variable_sorts = {name: "bool" for name in p_names + a_names + t_names + s_names}

    invariant_formulas = [
        f"{_next(p_name, depth)} <-> {_next(a_name, depth)}"
        for p_name, a_name in zip(p_names, a_names)
        for depth in range(parameters.D + 1)
    ]
    eliminated_conjunction = _conjunction(p_names)
    target_formulas = [f"{eliminated_conjunction} <-> {name}" for name in t_names]
    support_formulas = [f"{eliminated_conjunction} <-> {name}" for name in s_names]

    target = gr1.GR1TermList.from_bucket_formulas(
        liv=[gr1.parse_gr1_core(formula, variable_sorts) for formula in target_formulas]
    )
    context = gr1.GR1TermList.from_bucket_formulas(
        inv=[gr1.parse_gr1_core(formula, variable_sorts) for formula in invariant_formulas],
        liv=[gr1.parse_gr1_core(formula, variable_sorts) for formula in support_formulas],
    )
    return SyntheticInstance(
        parameters=parameters,
        target=target,
        context=context,
        eliminated=tuple(Var(name) for name in p_names),
        variable_sorts=variable_sorts,
    )


@dataclass
class CaveMetrics:
    """Measurements collected only while executing a CAVE elimination.

    Invocation counters distinguish refinement from relaxation. Solver and
    optimizer ``check()`` calls are recorded separately from ``qe2`` tactic
    applications and from universal/existential bound evaluations. Synthetic
    and fixed-support counters expose complete candidate construction. Quantified
    atoms, indexed variables, and NEXT depth record the largest quantified input seen.

    These are diagnostics of actual implementation paths. In particular,
    ``Solver.check()``, ``Optimize.check()``, and ``qe2`` applications are
    distinct quantities and must not be summed under the label "SMT queries".
    """

    cave_invocations: int = 0
    refinement_invocations: int = 0
    relaxation_invocations: int = 0
    cumulative_cave_seconds: float = 0.0
    refinement_seconds: float = 0.0
    relaxation_seconds: float = 0.0
    qe_seconds: float = 0.0
    non_qe_seconds: float = 0.0
    solver_checks: int = 0
    optimize_checks: int = 0
    forall_bounds: int = 0
    exists_bounds: int = 0
    qe_applications: int = 0
    qe_tactic_applications: int = 0
    total_candidates: int = 0
    liveness_targets: int = 0
    support_candidates: int = 0
    selected_supports: List[str] = field(default_factory=list)
    synthetic_candidates: int = 0
    maximum_quantified_atoms: int = 0
    maximum_quantified_indexed_variables: int = 0
    maximum_quantified_depth: int = 0
    maximum_quantified_ast_nodes: int = 0


class CaveInstrumentation:
    """Benchmark-local observer for unchanged production CAVE calls."""

    _METHODS = (
        "elim_vars_by_refining",
        "elim_vars_by_relaxing",
        "elim_vars_by_relaxing_assumptions",
        "elim_vars_by_relaxing_quotient_context",
        "elim_vars_by_refining_quotient_context",
    )

    def __init__(self) -> None:
        """Initialize empty counters and an inactive CAVE scope."""
        self.metrics = CaveMetrics()
        self._depth = 0
        self._projection_depth = 0
        self._qe_timer_depth = 0

    @property
    def active(self) -> bool:
        """Return whether execution is currently inside CAVE elimination."""
        return self._depth > 0

    def reset(self) -> None:
        """Reset counters between measured executions."""
        if self.active:
            raise RuntimeError("cannot reset instrumentation during a CAVE invocation")
        self.metrics = CaveMetrics()

    def _method_wrapper(self, name: str, original: Any) -> Any:
        def wrapped(term_list: gr1.GR1TermList, *args: Any, **kwargs: Any) -> Any:
            outermost = self._depth == 0
            category = "refinement" if "refining" in name else "relaxation"
            qe_before = self.metrics.qe_seconds
            started = perf_counter() if outermost else 0.0
            if outermost:
                self.metrics.cave_invocations += 1
                if category == "refinement":
                    self.metrics.refinement_invocations += 1
                else:
                    self.metrics.relaxation_invocations += 1
            self._depth += 1
            try:
                return original(term_list, *args, **kwargs)
            finally:
                self._depth -= 1
                if outermost:
                    elapsed = perf_counter() - started
                    self.metrics.cumulative_cave_seconds += elapsed
                    self.metrics.non_qe_seconds += elapsed - (self.metrics.qe_seconds - qe_before)
                    if category == "refinement":
                        self.metrics.refinement_seconds += elapsed
                    else:
                        self.metrics.relaxation_seconds += elapsed

        return wrapped

    def _record_quantified_input(self, target: Any, context: Any, variables: List[Var], universal: bool) -> None:
        atoms = gr1._z3_atoms_for_vars(variables, target, context)
        body = z3.Implies(context, target) if universal else z3.And(context, target)
        quantified = z3.ForAll(atoms, body) if atoms and universal else z3.Exists(atoms, body) if atoms else body
        names = {variable.decl().name() for variable in get_vars(z3.And(target, context))}
        self.metrics.maximum_quantified_atoms = max(self.metrics.maximum_quantified_atoms, len(atoms))
        self.metrics.maximum_quantified_indexed_variables = max(
            self.metrics.maximum_quantified_indexed_variables, len(names)
        )
        self.metrics.maximum_quantified_depth = max(self.metrics.maximum_quantified_depth, _max_index(sorted(names)))
        self.metrics.maximum_quantified_ast_nodes = max(
            self.metrics.maximum_quantified_ast_nodes, gr1._z3_ast_size(quantified)
        )

    @contextmanager
    def observe(self) -> Iterator[CaveMetrics]:
        """Install delegating wrappers for one benchmark execution."""
        original_solver_check = z3.Solver.check
        original_optimize_check = z3.Optimize.check
        original_tactic_apply = z3.Tactic.apply

        def solver_check(solver: Any, *args: Any, **kwargs: Any) -> Any:
            if self.active:
                self.metrics.solver_checks += 1
            return original_solver_check(solver, *args, **kwargs)

        def optimize_check(optimizer: Any, *args: Any, **kwargs: Any) -> Any:
            if self.active:
                self.metrics.optimize_checks += 1
            return original_optimize_check(optimizer, *args, **kwargs)

        original_forall = gr1._qe_forall_refinement
        original_exists = gr1._qe_exists_relaxation
        original_qe = gr1._eliminate_quantifiers
        original_refine_liv = gr1._refine_liv_term
        original_candidate = gr1._refine_liv_with_support
        original_select = gr1._select_refinement_support
        original_fallback = gr1._refine_liv_fallback

        def forall(target: Any, context: Any, variables: List[Var]) -> Any:
            if self.active:
                self.metrics.forall_bounds += 1
                self._record_quantified_input(target, context, variables, universal=True)
            return original_forall(target, context, variables)

        def exists(target: Any, context: Any, variables: List[Var]) -> Any:
            if self.active:
                self.metrics.exists_bounds += 1
                self._record_quantified_input(target, context, variables, universal=False)
            return original_exists(target, context, variables)

        def eliminate(expr: Any) -> Any:
            if self.active:
                self.metrics.qe_applications += 1
            self._projection_depth += 1
            try:
                return original_qe(expr)
            finally:
                self._projection_depth -= 1

        def tactic_apply(tactic: Any, *args: Any, **kwargs: Any) -> Any:
            # The production elimination helper invokes exactly Tactic("qe2").
            # Time apply(), not the whole helper (which also simplifies output).
            if not (self.active and self._projection_depth):
                return original_tactic_apply(tactic, *args, **kwargs)
            self.metrics.qe_tactic_applications += 1
            outermost = self._qe_timer_depth == 0
            started = perf_counter() if outermost else 0.0
            self._qe_timer_depth += 1
            try:
                return original_tactic_apply(tactic, *args, **kwargs)
            finally:
                self._qe_timer_depth -= 1
                if outermost:
                    self.metrics.qe_seconds += perf_counter() - started

        def refine_liv(target: Any, context: Any, variables: Any) -> Any:
            if self.active:
                self.metrics.liveness_targets += 1
            return original_refine_liv(target, context, variables)

        def candidate(target: Any, support: Any, context: Any, variables: Any) -> Any:
            result = original_candidate(target, support, context, variables)
            if self.active and result is not None:
                self.metrics.support_candidates += 1
                self.metrics.total_candidates += 1
            return result

        def select(terms: Any) -> Any:
            result = original_select(terms)
            if self.active and result is not None:
                self.metrics.selected_supports.append(f"{result.tag.value}: {result.core.expr}")
            return result

        def fallback(target: Any, context: Any, variables: Any) -> Any:
            result = original_fallback(target, context, variables)
            if self.active:
                self.metrics.synthetic_candidates += 1
                self.metrics.total_candidates += 1
            return result

        with ExitStack() as stack:
            for name in self._METHODS:
                original = getattr(gr1.GR1TermList, name)
                stack.enter_context(patch.object(gr1.GR1TermList, name, self._method_wrapper(name, original)))
            stack.enter_context(patch.object(z3.Solver, "check", solver_check))
            stack.enter_context(patch.object(z3.Optimize, "check", optimize_check))
            stack.enter_context(patch.object(z3.Tactic, "apply", tactic_apply))
            stack.enter_context(patch.object(gr1, "_qe_forall_refinement", forall))
            stack.enter_context(patch.object(gr1, "_qe_exists_relaxation", exists))
            stack.enter_context(patch.object(gr1, "_eliminate_quantifiers", eliminate))
            stack.enter_context(patch.object(gr1, "_refine_liv_term", refine_liv))
            stack.enter_context(patch.object(gr1, "_refine_liv_with_support", candidate))
            stack.enter_context(patch.object(gr1, "_select_refinement_support", select))
            stack.enter_context(patch.object(gr1, "_refine_liv_fallback", fallback))
            yield self.metrics


def run_instrumented_refinement(instance: SyntheticInstance) -> Tuple[gr1.GR1TermList, CaveMetrics]:
    """Execute unchanged production refinement CAVE with fresh counters."""
    instrumentation = CaveInstrumentation()
    with instrumentation.observe():
        result, _ = instance.target.elim_vars_by_refining(
            context=instance.context,
            vars_to_elim=list(instance.eliminated),
            simplify=False,
            tactics_order=[],
        )
    metrics = instrumentation.metrics
    # Exactly one public refinement invocation; the generator supplies n_I
    # targets and n_J supports. INIT processing constructs no LIV candidates.
    n_i, n_j = instance.parameters.n_I, instance.parameters.n_J
    if (
        metrics.cave_invocations,
        metrics.refinement_invocations,
        metrics.relaxation_invocations,
        metrics.synthetic_candidates,
        metrics.support_candidates,
        metrics.total_candidates,
    ) != (1, 1, 0, n_i, n_i * n_j, n_i * (1 + n_j)):
        raise RuntimeError("synthetic instrumentation disagrees with complete candidate construction")
    return result, metrics


_BASELINE = SyntheticParameters(n_p=2, n_I=2, n_J=2, D=1)
_SWEEPS = {
    "n_p": (1, 2, 4, 6, 8),
    "n_I": (1, 2, 4, 6, 8),
    "n_J": (1, 2, 4, 6, 8),
    "D": (0, 1, 2, 3, 4, 5),
}
_TIMING_FIELDS = ("median", "q1", "q3", "iqr", "min", "max")
_SYNTHETIC_SCHEMA_VERSION = 4
_SYNTHETIC_FAMILY = "gr1-cave-complete-candidates-v3"


def _distribution(values: Sequence[float]) -> Dict[str, float]:
    """Return the requested deterministic summary of measured timings."""
    q1, q3 = np.percentile(np.asarray(values, dtype=float), [25, 75])
    return {
        "median": median(values),
        "q1": float(q1),
        "q3": float(q3),
        "iqr": float(q3 - q1),
        "min": min(values),
        "max": max(values),
    }


def _environment_metadata() -> Dict[str, str]:
    """Return reproducibility metadata embedded in every results row."""
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        dirty = "true" if subprocess.run(["git", "diff", "--quiet"], check=False).returncode else "false"
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = "unavailable", "unavailable"
    try:
        from pacti import __version__ as pacti_version
    except ImportError:
        pacti_version = "unavailable"
    try:
        z3_solver_package_version = version("z3-solver")
    except PackageNotFoundError:
        z3_solver_package_version = "unavailable"
    return {
        "python_version": platform.python_version(),
        "z3_version": z3.get_version_string(),
        "z3_solver_package_version": z3_solver_package_version,
        "pacti_version": str(pacti_version),
        "git_commit": commit,
        "git_dirty": dirty,
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
    }


def _metric_counts(metrics: CaveMetrics) -> Dict[str, int]:
    """Convert deterministic instrumentation counters to CSV columns."""
    return {
        name: value
        for name, value in vars(metrics).items()
        if not name.endswith("_seconds") and name != "selected_supports"
    }


def _assert_same_counts(reference: Dict[str, int], observed: CaveMetrics) -> None:
    """Reject nondeterministic structural or solver-call measurements."""
    current = _metric_counts(observed)
    # Z3 may produce equivalent quantified DAGs with slightly different node
    # counts. Call counts and semantic dimensions must remain deterministic.
    checked = set(reference) - {"maximum_quantified_ast_nodes"}
    if any(current[name] != reference[name] for name in checked):
        raise RuntimeError(f"non-deterministic benchmark counters: {reference!r} != {current!r}")


_CAVE_TIME_FIELDS = ("cave_seconds", "refinement_seconds", "relaxation_seconds", "qe_seconds", "non_qe_seconds")


def _measurement_metadata(repetitions: int, mode: str) -> Dict[str, Any]:
    """Describe future measurements explicitly; never infer this for old rows."""
    digest = hashlib.sha256()
    for path in (Path(__file__), Path(gr1.__file__), Path(gr1.__file__).with_name("iocontract.py")):
        digest.update(path.read_bytes())
    return {
        "schema_version": _SYNTHETIC_SCHEMA_VERSION,
        "benchmark_family": _SYNTHETIC_FAMILY,
        "benchmark_mode": mode,
        "implementation_sha256": digest.hexdigest(),
        "warmup_count": 1,
        "resume_warmup_policy": "one-per-partial-configuration-on-resume",
        "measured_repetitions": repetitions,
        "baseline_json": json.dumps(vars(_BASELINE), sort_keys=True),
        "sweeps_json": json.dumps(_SWEEPS, sort_keys=True),
        "timing_protocol": "outer-cave-minus-nested-qe2-apply-v1",
    }


def _synthetic_identity(metadata: Dict[str, str], repetitions: int) -> Dict[str, Any]:
    """Return settings that must match before checkpoint data can be resumed."""
    return {
        **_measurement_metadata(repetitions, "synthetic"),
        "git_commit": metadata["git_commit"],
        "pacti_version": metadata["pacti_version"],
        "baseline": vars(_BASELINE),
        "sweeps": {name: list(values) for name, values in _SWEEPS.items()},
        "measured_repetitions": repetitions,
        "python_version": metadata["python_version"],
        "z3_version": metadata["z3_version"],
        "z3_solver_package_version": metadata["z3_solver_package_version"],
    }


def _atomic_write_json(path: Path, value: Dict[str, Any]) -> None:
    """Atomically replace one JSON checkpoint and force its bytes to disk."""
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def _csv_columns(rows: Sequence[Dict[str, Any]]) -> List[str]:
    """Return stable columns for heterogeneous raw and aggregate rows."""
    columns = sorted({column for row in rows for column in row})
    preferred = [
        "row_type",
        "sweep",
        "parameter_value",
        "scope",
        "repetition",
        "n_p",
        "n_I",
        "n_J",
        "D",
    ]
    return [column for column in preferred if column in columns] + [
        column for column in columns if column not in preferred
    ]


def _atomic_write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    """Atomically replace a CSV snapshot without exposing a partial rewrite."""
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=_csv_columns(rows))
        writer.writeheader()
        writer.writerows(rows)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def _configuration_key(sweep: str, value: int) -> str:
    """Return the stable identity of one one-at-a-time configuration."""
    return f"{sweep}={value}"


def _configuration_rows(rows: Sequence[Dict[str, Any]], sweep: str, value: int) -> List[Dict[str, Any]]:
    """Return ordered raw rows for one configuration."""
    selected = [
        row
        for row in rows
        if row["row_type"] == "raw" and row["sweep"] == sweep and int(row["parameter_value"]) == value
    ]
    return sorted(selected, key=lambda row: int(row["repetition"]))


def _aggregate_synthetic_rows(raw_rows: Sequence[Dict[str, Any]], repetitions: int) -> List[Dict[str, Any]]:
    """Append aggregates only for configurations with every expected raw row."""
    finalized: List[Dict[str, Any]] = list(raw_rows)
    for sweep, values in _SWEEPS.items():
        for value in values:
            measured = _configuration_rows(raw_rows, sweep, value)
            if len(measured) != repetitions:
                continue
            aggregate = {
                key: item
                for key, item in measured[0].items()
                if key
                not in {
                    "repetition",
                    "operation_seconds",
                    "cave_seconds",
                    "refinement_seconds",
                    "relaxation_seconds",
                    "qe_seconds",
                    "non_qe_seconds",
                }
            }
            aggregate.update({"row_type": "aggregate", "repetition": ""})
            for timing in ("operation_seconds",) + _CAVE_TIME_FIELDS:
                for statistic, statistic_value in _distribution([float(row[timing]) for row in measured]).items():
                    aggregate[f"{timing}_{statistic}"] = statistic_value
            finalized.append(aggregate)
    return finalized


def _checkpoint_state(
    identity: Dict[str, Any],
    metadata: Dict[str, str],
    raw_rows: Sequence[Dict[str, Any]],
    current: Dict[str, Any],
    repetitions: int,
) -> Dict[str, Any]:
    """Build inspectable state derived from the authoritative raw rows."""
    completed = []
    partial = []
    for sweep, values in _SWEEPS.items():
        for value in values:
            count = len(_configuration_rows(raw_rows, sweep, value))
            key = _configuration_key(sweep, value)
            if count == repetitions:
                completed.append(key)
            elif count:
                partial.append({"configuration": key, "measured_repetitions": count})
    expected = sum(len(values) for values in _SWEEPS.values()) * repetitions
    completed_sweeps = [
        sweep
        for sweep, values in _SWEEPS.items()
        if all(_configuration_key(sweep, value) in completed for value in values)
    ]
    return {
        "identity": identity,
        "environment": metadata,
        "raw_rows": list(raw_rows),
        "completed_configurations": completed,
        "completed_sweeps": completed_sweeps,
        "partial_configurations": partial,
        "current": current,
        "measured_runs_completed": len(raw_rows),
        "measured_runs_expected": expected,
        "dataset_complete": len(raw_rows) == expected,
    }


def _persist_synthetic_state(
    checkpoint_path: Path,
    results_path: Path,
    identity: Dict[str, Any],
    metadata: Dict[str, str],
    raw_rows: Sequence[Dict[str, Any]],
    current: Dict[str, Any],
    repetitions: int,
) -> None:
    """Persist raw/state first, then an atomic human- and plot-readable CSV."""
    state = _checkpoint_state(identity, metadata, raw_rows, current, repetitions)
    _atomic_write_json(checkpoint_path, state)
    _atomic_write_csv(results_path, _aggregate_synthetic_rows(raw_rows, repetitions))


def _load_synthetic_checkpoint(path: Path, expected_identity: Dict[str, Any]) -> Dict[str, Any]:
    """Load a compatible checkpoint or refuse to combine experiments."""
    if not path.exists():
        raise RuntimeError(f"cannot resume: checkpoint does not exist: {path}")
    with path.open(encoding="utf-8") as stream:
        state = json.load(stream)
    if state.get("identity") != expected_identity:
        raise RuntimeError(
            "cannot resume: checkpoint metadata does not match the current "
            "benchmark family, schema, baseline, sweeps, repetitions, or solver environment"
        )
    raw_rows = state.get("raw_rows")
    if not isinstance(raw_rows, list):
        raise RuntimeError("cannot resume: checkpoint raw_rows is missing or invalid")
    allowed = {_configuration_key(sweep, value) for sweep, values in _SWEEPS.items() for value in values}
    observed = set()
    repetitions = int(expected_identity["measured_repetitions"])
    for row in raw_rows:
        key = _configuration_key(str(row.get("sweep")), int(row.get("parameter_value", -1)))
        repetition = int(row.get("repetition", -1))
        identity = (key, repetition)
        if row.get("row_type") != "raw" or key not in allowed or not 1 <= repetition <= repetitions:
            raise RuntimeError("cannot resume: checkpoint contains an unexpected raw measurement")
        if identity in observed:
            raise RuntimeError(f"cannot resume: duplicate raw measurement {key}, repetition {repetition}")
        observed.add(identity)
    return state


def _progress(message: str = "") -> None:
    """Print progress immediately; callers invoke this outside measured regions."""
    print(message, flush=True)


def run_synthetic_benchmark(
    repetitions: int = 10,
    *,
    results_path: Path,
    checkpoint_path: Path,
    resume: bool = False,
) -> List[Dict[str, Any]]:
    """Run checkpointed one-at-a-time sweeps with one warm-up per configuration.

    Timing starts immediately before ``run_instrumented_refinement`` and stops
    immediately after it, exactly as before. Progress, persistence,
    aggregation, validation, and resume bookkeeping occur outside that timed
    interval.
    """
    metadata = {**_environment_metadata(), **_measurement_metadata(repetitions, "synthetic")}
    identity = _synthetic_identity(metadata, repetitions)
    if resume:
        state = _load_synthetic_checkpoint(checkpoint_path, identity)
        raw_rows: List[Dict[str, Any]] = list(state.get("raw_rows", []))
    else:
        if checkpoint_path.exists() or results_path.exists():
            raise RuntimeError(
                "refusing to overwrite existing synthetic results; move them, "
                "choose a clean output location, or use --resume"
            )
        raw_rows = []

    configurations = [(sweep, value) for sweep, values in _SWEEPS.items() for value in values]
    benchmark_started = perf_counter()
    mode = "resumed" if resume else "fresh"
    _progress(f"SYNTHETIC SCALABILITY ({mode})")
    _progress(f"Checkpoint: {checkpoint_path}")
    _progress(f"Results:    {results_path}")
    try:
        for configuration_number, (sweep, value) in enumerate(configurations, start=1):
            existing = _configuration_rows(raw_rows, sweep, value)
            if len(existing) == repetitions:
                _progress(
                    f"[{sweep}={value}] COMPLETE checkpoint found; "
                    f"skipping configuration {configuration_number}/{len(configurations)}"
                )
                continue
            dimensions = vars(_BASELINE).copy()
            dimensions[sweep] = value
            parameters = SyntheticParameters(**dimensions)
            instance = generate_synthetic_instance(parameters)
            structural = instance.structural_metrics()
            current = {
                "sweep": sweep,
                "parameter_value": value,
                "configuration": configuration_number,
                "total_configurations": len(configurations),
                "status": "warm-up",
                "measured_repetitions_completed": len(existing),
            }
            _persist_synthetic_state(checkpoint_path, results_path, identity, metadata, raw_rows, current, repetitions)
            _progress("-" * 70)
            _progress(f"Sweep: {sweep}  Value: {value}")
            _progress("Baseline: n_p=n_I=n_J=2, D=1")
            _progress(f"Configuration: {configuration_number} / {len(configurations)}")
            _progress("-" * 70)
            _progress(f"[{sweep}={value}] warm-up starting...")
            warmup_started = perf_counter()
            run_instrumented_refinement(instance)  # Warm-up, deliberately not recorded.
            _progress(f"[{sweep}={value}] warm-up complete ({perf_counter() - warmup_started:.2f} s)")

            reference_counts: Optional[Dict[str, int]] = (
                {name: existing[0][name] for name in _metric_counts(CaveMetrics())} if existing else None
            )
            output_size: Optional[int] = int(existing[0]["output_z3_dag_nodes"]) if existing else None
            for repetition in range(len(existing) + 1, repetitions + 1):
                current.update(
                    {
                        "status": "measured",
                        "measured_repetitions_completed": repetition - 1,
                        "active_repetition": repetition,
                    }
                )
                _persist_synthetic_state(
                    checkpoint_path, results_path, identity, metadata, raw_rows, current, repetitions
                )
                _progress(f"[{sweep}={value}] measured run {repetition}/{repetitions} starting...")
                started = perf_counter()
                result, metrics = run_instrumented_refinement(instance)
                elapsed = perf_counter() - started
                _progress(f"[{sweep}={value}] measured run {repetition}/{repetitions} complete ({elapsed:.2f} s)")
                counts = _metric_counts(metrics)
                if reference_counts is None:
                    reference_counts = counts
                    output_size = _term_list_z3_size(result)
                else:
                    _assert_same_counts(reference_counts, metrics)
                    if _term_list_z3_size(result) != output_size:
                        raise RuntimeError("non-deterministic synthetic output formula size")
                row = {
                    **metadata,
                    **dimensions,
                    **structural,
                    **counts,
                    "row_type": "raw",
                    "sweep": sweep,
                    "parameter_value": value,
                    "repetition": repetition,
                    "operation_seconds": elapsed,
                    "cave_seconds": metrics.cumulative_cave_seconds,
                    "refinement_seconds": metrics.refinement_seconds,
                    "relaxation_seconds": metrics.relaxation_seconds,
                    "qe_seconds": metrics.qe_seconds,
                    "non_qe_seconds": metrics.non_qe_seconds,
                    "output_z3_dag_nodes": output_size,
                }
                raw_rows.append(row)
                current["measured_repetitions_completed"] = repetition
                current["status"] = "checkpointed"
                _persist_synthetic_state(
                    checkpoint_path, results_path, identity, metadata, raw_rows, current, repetitions
                )
                _progress(f"[{sweep}={value}] checkpoint saved: {checkpoint_path}")
                completed_configurations = sum(
                    len(_configuration_rows(raw_rows, name, item)) == repetitions
                    for name, values in _SWEEPS.items()
                    for item in values
                )
                _progress(
                    f"[{sweep}={value}] measured completed {repetition}/{repetitions}; "
                    f"configurations complete {completed_configurations}/{len(configurations)}; "
                    f"experiment elapsed {perf_counter() - benchmark_started:.2f} s"
                )

            measured = _configuration_rows(raw_rows, sweep, value)
            cave_distribution = _distribution([float(row["cave_seconds"]) for row in measured])
            current.update({"status": "complete", "active_repetition": None})
            _persist_synthetic_state(checkpoint_path, results_path, identity, metadata, raw_rows, current, repetitions)
            _progress(f"[{sweep}={value}] COMPLETE")
            _progress(f"  measured runs : {len(measured)}/{repetitions}")
            _progress(f"  median        : {cave_distribution['median']:.6f} s")
            _progress(f"  Q1 / Q3       : {cave_distribution['q1']:.6f} / {cave_distribution['q3']:.6f} s")
            _progress(f"  IQR           : {cave_distribution['iqr']:.6f} s")
            _progress(f"  min / max     : {cave_distribution['min']:.6f} / {cave_distribution['max']:.6f} s")
            _progress(f"  total elapsed : {perf_counter() - benchmark_started:.2f} s")
            _progress(f"  configurations completed: {configuration_number}/{len(configurations)}")
    except KeyboardInterrupt:
        current = locals().get("current", {"status": "interrupted before first configuration"})
        current["status"] = "interrupted"
        _persist_synthetic_state(checkpoint_path, results_path, identity, metadata, raw_rows, current, repetitions)
        _progress("\nBENCHMARK INTERRUPTED")
        _progress(f"  sweep             : {current.get('sweep', 'not started')}")
        _progress(f"  value             : {current.get('parameter_value', 'not started')}")
        _progress(f"  measured completed: {current.get('measured_repetitions_completed', 0)}/{repetitions}")
        _progress(f"  interrupted run   : {current.get('active_repetition', 'warm-up')}/{repetitions}")
        _progress("  completed data    : saved")
        _progress(f"  checkpoint        : {checkpoint_path}")
        _progress(
            "  resume command     : python examples/gr1_cave_scalability.py "
            f"--synthetic --resume --repetitions {repetitions} "
            f"--output-dir {str(checkpoint_path.parent)!r}"
        )
        return _aggregate_synthetic_rows(raw_rows, repetitions)

    final_rows = _aggregate_synthetic_rows(raw_rows, repetitions)
    expected_runs = len(configurations) * repetitions
    complete = len(raw_rows) == expected_runs
    current = {"status": "complete" if complete else "incomplete"}
    _persist_synthetic_state(checkpoint_path, results_path, identity, metadata, raw_rows, current, repetitions)
    _progress("\nSYNTHETIC SCALABILITY COMPLETE" if complete else "\nSYNTHETIC SCALABILITY INCOMPLETE")
    _progress(f"  total wall time         : {perf_counter() - benchmark_started:.2f} s")
    _progress(f"  configurations complete : {len(configurations) if complete else 'partial'}")
    _progress(f"  measured runs           : {len(raw_rows)}/{expected_runs}")
    _progress(f"  results                 : {results_path}")
    _progress(f"  checkpoint              : {checkpoint_path}")
    _progress(f"  execution mode          : {mode}")
    _progress(f"  dataset complete        : {complete}")
    return final_rows


def _combine_metrics(left: CaveMetrics, right: CaveMetrics) -> CaveMetrics:
    """Combine additive counters and maxima from two disjoint CAVE scopes."""
    result = CaveMetrics()
    maxima = {
        "maximum_quantified_atoms",
        "maximum_quantified_indexed_variables",
        "maximum_quantified_depth",
        "maximum_quantified_ast_nodes",
    }
    ignored = {"selected_supports"}
    for name in vars(result):
        if name in ignored:
            continue
        left_value, right_value = getattr(left, name), getattr(right, name)
        setattr(result, name, max(left_value, right_value) if name in maxima else left_value + right_value)
    result.selected_supports = left.selected_supports + right.selected_supports
    return result


def run_aeb_benchmark(repetitions: int = 10) -> Tuple[List[Dict[str, Any]], Any, Any]:
    """Measure AEB composition and quotient with other work outside timing.

    End-to-end time covers each complete Pacti contract operation. Cumulative
    CAVE time covers only instrumented CAVE calls within those operations.
    Contract construction precedes the warm-up; presentation, printing,
    recomposition, validation, and report generation follow measurement.
    """
    from examples.aeb_gr1_composition import make_supervisor, make_vehicle

    metadata = {**_environment_metadata(), **_measurement_metadata(repetitions, "aeb")}
    supervisor, vehicle = make_supervisor(), make_vehicle()

    def execute() -> Tuple[Dict[str, Any], Any, Any]:
        composition_instrumentation = CaveInstrumentation()
        composition_started = perf_counter()
        with composition_instrumentation.observe():
            composition = supervisor.compose(vehicle, simplify=True)
        composition_seconds = perf_counter() - composition_started

        quotient_instrumentation = CaveInstrumentation()
        quotient_started = perf_counter()
        with quotient_instrumentation.observe():
            quotient = composition.quotient(vehicle, simplify=True)
        quotient_seconds = perf_counter() - quotient_started
        return (
            {
                "composition_seconds": composition_seconds,
                "quotient_seconds": quotient_seconds,
                "combined_seconds": composition_seconds + quotient_seconds,
                "composition_metrics": composition_instrumentation.metrics,
                "quotient_metrics": quotient_instrumentation.metrics,
                "combined_metrics": _combine_metrics(
                    composition_instrumentation.metrics, quotient_instrumentation.metrics
                ),
            },
            composition,
            quotient,
        )

    execute()  # Warm-up.
    rows: List[Dict[str, Any]] = []
    reference: Dict[str, Dict[str, int]] = {}
    final_composition = final_quotient = None
    for repetition in range(1, repetitions + 1):
        execution, final_composition, final_quotient = execute()
        for scope in ("composition", "quotient", "combined"):
            metrics = execution[f"{scope}_metrics"]
            counts = _metric_counts(metrics)
            if scope not in reference:
                reference[scope] = counts
            else:
                _assert_same_counts(reference[scope], metrics)
            end_to_end = execution[f"{scope}_seconds"]
            rows.append(
                {
                    **metadata,
                    **counts,
                    "row_type": "raw",
                    "scope": scope,
                    "repetition": repetition,
                    "end_to_end_seconds": end_to_end,
                    "cave_seconds": metrics.cumulative_cave_seconds,
                    "refinement_seconds": metrics.refinement_seconds,
                    "relaxation_seconds": metrics.relaxation_seconds,
                    "qe_seconds": metrics.qe_seconds,
                    "non_qe_seconds": metrics.non_qe_seconds,
                }
            )
        print(f"completed AEB repetition {repetition}/{repetitions}")
    for scope in ("composition", "quotient", "combined"):
        scoped = [row for row in rows if row["scope"] == scope]
        aggregate: Dict[str, Any] = {
            **metadata,
            **reference[scope],
            "row_type": "aggregate",
            "scope": scope,
            "repetition": "",
        }
        for timing in ("end_to_end_seconds",) + _CAVE_TIME_FIELDS:
            for statistic, statistic_value in _distribution([float(row[timing]) for row in scoped]).items():
                aggregate[f"{timing}_{statistic}"] = statistic_value
        rows.append(aggregate)
    return rows, final_composition, final_quotient


def write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    """Write heterogeneous raw and aggregate records with stable columns."""
    columns = _csv_columns(rows)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def select_support_pilot(parameters: SyntheticParameters) -> Dict[str, Any]:
    """Inspect the complete tagged family and non-mutating production selection."""
    instance = generate_synthetic_instance(parameters)
    target = instance.target.liv_terms()[0]
    candidates = gr1._refinement_liv_candidates(target, instance.context, list(instance.eliminated))
    before = [
        (term.tag, str(term.core.expr.sexpr()) if term.core.expr is not None else term.core.text) for term in candidates
    ]
    selected = gr1._select_refinement_support(candidates)
    assert before == [
        (term.tag, str(term.core.expr.sexpr()) if term.core.expr is not None else term.core.text) for term in candidates
    ]
    result, metrics = run_instrumented_refinement(instance)
    return {
        "instance": instance,
        "target": target,
        "candidates": candidates,
        "selected": selected,
        "result": result,
        "metrics": metrics,
    }


def run_structural_pilot() -> None:
    """Run a diagnostic structural validation excluded from final timings."""
    parameters = SyntheticParameters(n_p=2, n_I=1, n_J=3, D=1)
    pilot = select_support_pilot(parameters)
    instance = pilot["instance"]
    print("GR(1) CAVE STRUCTURAL PILOT")
    print("parameters:", parameters)
    print("structural metrics:", instance.structural_metrics())
    print("target:", pilot["target"].core.text)
    print("\nComplete candidate family (branch 0, then context order):")
    for index, candidate in enumerate(pilot["candidates"]):
        print(f"  branch {index}: {candidate.tag.value}({candidate.core.expr})")
    print("Selected candidate:", pilot["selected"])
    print("Production CAVE result:", pilot["result"].to_pretty_string())
    print("Production counters:", pilot["metrics"])

    print("\nn_J scaling:")
    for n_j in (1, 2, 3):
        scaled = generate_synthetic_instance(SyntheticParameters(2, 1, n_j, 1))
        _, metrics = run_instrumented_refinement(scaled)
        print(
            f"  n_J={n_j}: synthetic={metrics.synthetic_candidates}, "
            f"fixed-support candidates={metrics.support_candidates}"
        )

    print("\nDimension checks:")
    for depth in (0, 1, 2):
        scaled = generate_synthetic_instance(SyntheticParameters(2, 1, 2, depth))
        _, metrics = run_instrumented_refinement(scaled)
        print(
            f"  D={depth}: input depth={scaled.structural_metrics()['maximum_next_depth']}, "
            f"quantified depth={metrics.maximum_quantified_depth}, "
            f"quantified indexed vars={metrics.maximum_quantified_indexed_variables}"
        )
    for n_p in (1, 2):
        scaled = generate_synthetic_instance(SyntheticParameters(n_p, 1, 2, 1))
        _, metrics = run_instrumented_refinement(scaled)
        print(
            f"  n_p={n_p}: eliminated bases={len(scaled.eliminated)}, "
            f"maximum quantified atoms={metrics.maximum_quantified_atoms}"
        )
    for n_i in (1, 2):
        scaled = generate_synthetic_instance(SyntheticParameters(2, n_i, 2, 1))
        _, metrics = run_instrumented_refinement(scaled)
        print(f"  n_I={n_i}: liveness targets entering refinement={metrics.liveness_targets}")


def main() -> None:
    """Parse command-line arguments and run the requested benchmark phase."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pilot",
        action="store_true",
        help="run the fast structural diagnostic (excluded from final timing data)",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help=("run final synthetic sweeps with immediate progress and atomic per-run " "checkpoint/CSV persistence"),
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="resume a compatible interrupted --synthetic checkpoint; completed runs are skipped",
    )
    parser.add_argument(
        "--aeb",
        action="store_true",
        help="measure paper-example composition and quotient and write raw/aggregate CSV data",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=10,
        help="measured repetitions after one unrecorded warm-up (default: 10)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="output directory; choose a fresh directory for schema-4 measurements",
    )
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("--repetitions must be positive")
    if not (args.pilot or args.synthetic or args.aeb):
        parser.error("select --pilot, --synthetic, or --aeb")
    if args.resume and not args.synthetic:
        parser.error("--resume requires --synthetic")
    output_directory = args.output_dir
    output_directory.mkdir(parents=True, exist_ok=True)
    if args.pilot:
        run_structural_pilot()
    if args.synthetic:
        synthetic_rows = run_synthetic_benchmark(
            args.repetitions,
            results_path=output_directory / "gr1_cave_scalability_results.csv",
            checkpoint_path=output_directory / "gr1_cave_scalability_checkpoint.json",
            resume=args.resume,
        )
        expected_raw_rows = sum(len(values) for values in _SWEEPS.values()) * args.repetitions
        if sum(row["row_type"] == "raw" for row in synthetic_rows) != expected_raw_rows:
            return
    if args.aeb:
        if (output_directory / "aeb_gr1_performance_results.csv").exists():
            parser.error("refusing to overwrite existing AEB data; choose a fresh --output-dir")
        rows, _, _ = run_aeb_benchmark(args.repetitions)
        write_csv(output_directory / "aeb_gr1_performance_results.csv", rows)


if __name__ == "__main__":
    main()
