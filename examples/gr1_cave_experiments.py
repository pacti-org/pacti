"""Unified GR(1) CAVE experiments: one protocol, schema and reporting pipeline.

E1 measures the original synthetic family in both directions; E2 measures
harder Boolean/LRA families and finite-window scaling. E3 is a finite-horizon
Z3 unrolling that drops liveness, not an exact temporal-contract baseline.
E4 tests soundness and precision on bounded external lasso encodings using
the independently tested explicit-state oracle; this is not an unbounded
soundness proof. E5 measures chain composition. E6's exact automata results
and acceptance shapes are descriptive, not a GR(1)-expressibility test.
E7 contains benchmark-local ablations; E8 times the Table 2 operations
C_SVD = (C_S || C_V) || C_D and Q = C_T / C_V.
The structural pilot is diagnostic and excluded from CSVs.

These baselines are not competing tools for the same problem: no competing
tool in this comparison computes composition/quotient of temporal-formula
contracts. OCRA/hypercontracts do not provide the compared CAVE operation.
E3 includes both the requested five-variable guarantee projection and the
interface-matched four-variable projection, since production retains v.

Each timing repetition starts a fresh spawned worker. Inside that worker the
operation runs twice: cold_seconds records the first call (warm-up); seconds
records the second, warm call. cold_* fields preserve the first call's phase
times and counters. Construction, validation and I/O remain outside operation
timers, and so does the harness's own bookkeeping (rebuilding quantified inputs
for size counters): it is accumulated in instrumentation_seconds, subtracted
from seconds/cave_seconds/non_qe_seconds, and the raw wall clock stays in
seconds_including_instrumentation. The hard deadline includes imports, preparation, both calls and checks.
The import-light supervisor reaps exactly one worker and reports its
RUSAGE_CHILDREN peak RSS in bytes. E4 has no warm-up or repetitions and makes
no runtime claim; its scan duration is scan_seconds, with seconds/cold_seconds
empty. E4 preselection uses a separate, at-most-60-second isolated precheck.

--preset quick selects tiny grids, one repetition, 100 instances per source
and hidden-variable batch, and a 30-second timing timeout. --preset paper
selects the full grids, ten repetitions (E2: five), 2000 instances per source
and batch, hidden-bit batches 1 and 2, and 600 seconds; E5 uses three
repetitions and 300 seconds. E4 costs about one fresh process per instance, so
--instances 500 is a reasonable cheaper override (the plan prints the launch count).
Explicit --repetitions/--instances/--timeout override
these defaults and are printed in the resolved plan. Without a preset the
paper grids and ten repetitions for every timing experiment are used.
A preset alone selects all experiments. --quick is an alias for --preset quick;
--synthetic and --aeb alias E1 and E8. E4 --int 2 adds the two-bit batch (the paper preset's default).

E4 source=uniform preserves the old generator and seed mapping. Nonblocking
rejection sampling uses an independent deterministic stream per instance,
identified by seed_stream_id and seed_stream_index; rejected_draws counts
rejected candidates in that stream. Acceptance checks every quick lasso.
Paper scans subsequently check the full lasso set, so accepted contexts may
still block there. target_pfree_cores counts semantically hidden-independent
INV/LIV input cores using the independent truth-table evaluator. trivial means
CAVE and the exact oracle are the same constant on the evaluated lasso suite.
All precision fractions count lasso encodings, including equivalent encodings.

E5 inconsistency and expected-range checks are diagnostics, not realizability
proofs; unsat does not discard measurements. Its stages are memoryless
(NEXT-depth zero) with every eliminated variable at one fixed offset; the two
earlier families were degenerate (step-bound degeneracy, then a preceding
guarantee instance that made the composed assumption false). Rows carry
degenerate / composed_assumption_false / composed_guarantee_empty, and
--selftest prints a non-fatal WARN when N=2 or 3 composes to something
unexpected. y0_0 is checked against [(N-1)/2, 100-(N-1)/2]; y0_1 is reported
"not-applicable" when absent. N<=4 records assumption and guarantee cores. Temporal
depth is covered by E1/E2/E8, not by E5.
E3 records CAVE-simplify-true and CAVE-simplify-false references; the primary
unrolled baseline is interface-matched-four. The old always-unknown agreement
column is removed. E7 equivalence uses sufficient
bucketwise certificates and reports unknown when inconclusive.
No production behavior is changed outside subprocess-local ablation patches.
Importing this module, including multiprocessing's supervisor import, imports
only the standard library. Pacti/Z3/NumPy are loaded explicitly by workers
and by the controller after argument parsing.

Artifacts: e1.csv ... e8.csv (raw plus aggregates), and an atomic MANIFEST.json
with command, resolved plan, provenance, versions and UTC start/end times.
Resume validates per-configuration experimental parameters, effective
repetitions, timeout, seed, environment and source digests; unrelated CLI flags
are excluded. Successful runs alone supply quantiles; failures remain data.
Sweep groups are shuffled with the seed, values ascend within each group.
After all repetitions at one value time out, larger values receive skipped
rows with an explicit reason. The E2 grid escalates D separately for each n_p.
--profile produces three isolated cProfile reports and profile_summary.csv,
excluded from timing CSVs. Category totals are disjoint Python/native-wrapper
self times; shared helper self times remain in other rather than being counted
under multiple parents. No profiler runs during timing experiments.

CSV column groups:
  provenance: schema_version, experiment, row_type, status, error, traceback,
    config_id, run_identity, parameters_json, cli_json, order_index, repetition, skip_reason,
    source_sha256, source_digests_json, git_commit/dirty, Python/Z3/Pacti/Spot/
    buddy versions, platform, processor, seed, timeout, measured_repetitions;
  protocol: timing_protocol, warmup_count, active_phase, cold_seconds, seconds,
    cold_* (first-call metrics), cold_rows_json (partial first-call results);
  metrics: cave_seconds, qe_seconds, non_qe_seconds, qe_share, end_to_end_seconds,
    all CaveMetrics counters, liveness_projections/expected/match,
    output_cores, output_z3_dag_nodes, peak_rss_bytes, supervisor_seconds;
  synthetic: family, direction, sweep, parameter_value, n_p/n_I/n_J/D/D_B,
    quantified_indexed_variables, base/indexed/retained/eliminated variable
    counts, maximum_next_depth, syntax_tree_nodes, flattened_z3_dag_nodes;
  E3: T, baseline, projection, liveness_dropped, quantified_atoms,
    refinement/relaxation_quantified_atoms, guarantee_eliminated, result sizes;
  E4: instance_id/seed, n_int, ext, source, seed_stream_id/index, rejected_draws,
    nonblocking_checked_on, context_nonblocking, uses_init, max_depth,
    target_pfree_cores, trivial, classification, diff_fraction, lassos,
    unsound_lassos, is_bottom_or_top, support_branch_selected, scan_seconds,
    instance_json, result_json, witness_json, likely_cause, likely_cause_method
    (syntactic heuristic only, not evidence for a claim);
  E5: N, order, steps_json, chain_wall_seconds, inconsistency_check,
    input_range_check/contained, observed_lower/upper_current/next,
    input_range_check/contained_current/next, expected_lower/upper, range_scope,
    result_a_json, result_g_json, diagnostic_error_current/next;
  E6: exists/complement_seconds, exists/complement_states/acceptance_sets,
    sound, exact, needs_nonbuchi_or_multiple_sets, acceptance_interpretation;
  E7: ablation, simplify, qe_tactic, unchanged, equivalence_method;
  E8: scope (composition/quotient/combined), component sizes and all metrics;
  aggregates: completed_runs, successful_runs, timeout_runs, error_runs,
    skipped_runs, complete, numeric-field_{median,q1,q3,iqr,min,max}, classification counts.
Empty cells mean unavailable/not applicable; unknown is never a proof.
"""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import itertools
import json
import math
import platform
import subprocess
import multiprocessing as mp
import os
import random
import re
from types import ModuleType
from typing import Optional

resource: Optional[ModuleType]
try:
    import resource
except ImportError:  # Windows has no Unix resource module.
    resource = None
import sys
import traceback
from collections import defaultdict
from contextlib import ExitStack, contextmanager, nullcontext
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from statistics import median
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterator, List, Optional, Sequence, Set, Tuple
from unittest.mock import patch

# Direct script invocation works from any cwd, without requiring installation.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

if TYPE_CHECKING:
    import numpy as np
    import z3
    from z3.z3util import get_vars
    from pacti.iocontract import Var
    from pacti.iocontract import gr1_iocontract as gr1


def _load_dependencies() -> None:
    """Load numerical/production modules only in the controller or worker."""
    global np, z3, get_vars, Var, gr1
    import numpy as np
    import z3
    from z3.z3util import get_vars
    from pacti.iocontract import Var
    from pacti.iocontract import gr1_iocontract as gr1


SCHEMA_VERSION = 2
TIMING_PROTOCOL = "spawn-two-calls-cold-then-warm-v1"
Row = Dict[str, Any]
AST = Tuple[Any, ...]
Edge = Tuple[int, int, int, bool, bool, bool, int]
_REPORTER: Optional[Callable[[Row], None]] = None


def publish_partial(row: Row) -> None:
    """Preserve completed subphases if a later automata operation times out."""
    if _REPORTER is not None:
        _REPORTER(row)


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
    names: Set[str] = set()
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
            "maximum_next_depth": _max_index(names),
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
    # Harness-only bookkeeping (rebuilding quantified inputs for size counters,
    # printing selected supports). It is excluded from every reported duration.
    instrumentation_seconds: float = 0.0


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

    @contextmanager
    def _harness_cost(self) -> Iterator[None]:
        """Account harness-only work so every reported duration can exclude it."""
        started = perf_counter()
        try:
            yield
        finally:
            self.metrics.instrumentation_seconds += perf_counter() - started

    def _method_wrapper(self, name: str, original: Any) -> Any:
        def wrapped(term_list: gr1.GR1TermList, *args: Any, **kwargs: Any) -> Any:
            outermost = self._depth == 0
            category = "refinement" if "refining" in name else "relaxation"
            qe_before = self.metrics.qe_seconds
            overhead_before = self.metrics.instrumentation_seconds
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
                    # Production CAVE time only: harness bookkeeping is subtracted.
                    elapsed = perf_counter() - started - (self.metrics.instrumentation_seconds - overhead_before)
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
                with self._harness_cost():
                    self._record_quantified_input(target, context, variables, universal=True)
            return original_forall(target, context, variables)

        def exists(target: Any, context: Any, variables: List[Var]) -> Any:
            if self.active:
                self.metrics.exists_bounds += 1
                with self._harness_cost():
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
                with self._harness_cost():
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


@dataclass
class Instance:
    """Source buckets and declarations, independent of production parsing."""

    context: Dict[str, List[str]]
    target: Dict[str, List[str]]
    sorts: Dict[str, str]
    eliminated: List[str]

    def terms(self) -> Tuple[gr1.GR1TermList, gr1.GR1TermList]:
        """Parse explicit sorts using the production public core parser."""

        def build(buckets: Dict[str, List[str]]) -> gr1.GR1TermList:
            return gr1.GR1TermList.from_bucket_formulas(
                **{tag: [gr1.parse_gr1_core(text, self.sorts) for text in values] for tag, values in buckets.items()}
            )

        return build(self.target), build(self.context)


def synthetic(config: Row) -> Instance:
    """Build substitution, partially constrained Boolean, or LRA families."""
    n, ni, nj, depth = (int(config[key]) for key in ("n_p", "n_I", "n_J", "D"))
    family = config["family"]
    if family == "substitution":
        old = generate_synthetic_instance(SyntheticParameters(n, ni, nj, depth))
        return Instance(
            old.context.to_bucket_dict(),
            old.target.to_bucket_dict(),
            old.variable_sorts,
            [v.name for v in old.eliminated],
        )
    if family == "bool-bound":
        ps, aa, bb = ([f"{prefix}{k}" for k in range(n)] for prefix in ("p", "a", "b"))
        ts, ss = [f"t{i}" for i in range(ni)], [f"s{j}" for j in range(nj)]
        sorts = {name: "bool" for name in ps + aa + bb + ts + ss}
        inv: List[str] = []
        for k in range(n):
            core = f"(({aa[k]} & X(!{aa[k]})) -> {ps[k]}) & ({ps[k]} -> ({aa[k]} | {bb[k]}))"
            inv.extend(_next(f"({core})", r) for r in range(depth + 1))

        # Cyclic subsets are distinct until n is exhausted. Context uses a
        # different width where possible; distinct subsets cannot exist at n=1.
        def subset(index: int, support: bool) -> str:
            width = min(n, max(1, n // 2) + int(support))
            return _conjunction([ps[(index + int(support) + offset) % n] for offset in range(width)])

        return Instance(
            {"inv": inv, "liv": [f"{subset(j, True)} <-> {s}" for j, s in enumerate(ss)]},
            {"liv": [f"{subset(i, False)} <-> {t}" for i, t in enumerate(ts)]},
            sorts,
            ps,
        )
    us, ds, vs = ([f"{prefix}{k}" for k in range(n)] for prefix in ("u", "d", "v"))
    sorts = {name: "real" for name in us + ds + vs}
    sorts.update({f"mt{i}": "bool" for i in range(ni)})
    sorts.update({f"ms{j}": "bool" for j in range(nj)})
    inv = []
    for u, d, v in zip(us, ds, vs):
        core = f"({d}/10 <= {u}) & ({u} <= {d}/5) & (X({v}) <= {u}+1/2) & (X({v}) >= {u}-1/2)"
        inv.extend(_next(f"({core})", r) for r in range(depth + 1))
    return Instance(
        {"inv": inv, "liv": [f"({us[j % n]} <= {3 + j}/2) & ms{j}" for j in range(nj)]},
        {
            "inv": [f"X({v}) <= {5 + k}" for k, v in enumerate(vs)],
            "liv": [f"({us[i % n]} >= {i % 3}/2) & mt{i}" for i in range(ni)],
        },
        sorts,
        us + (vs if config["direction"] == "refinement" else []),
    )


def eliminate(
    instance: Instance, direction: str, simplify: bool = False, enforce_counts: bool = False
) -> Tuple[gr1.GR1TermList, Row]:
    """Time one public CAVE call and verify projection instrumentation."""
    target, context = instance.terms()
    observer = CaveInstrumentation()
    projected = 0
    original = gr1._project_liv_terms

    def project(terms: Any, ctx: Any, variables: Any) -> Any:
        nonlocal projected
        projected += len(terms)
        return original(terms, ctx, variables)

    gc.collect()
    started = perf_counter()
    with patch.object(gr1, "_project_liv_terms", project), observer.observe():
        method = target.elim_vars_by_refining if direction == "refinement" else target.elim_vars_by_relaxing
        result, _ = method(
            context=context, vars_to_elim=[Var(v) for v in instance.eliminated], simplify=simplify, tactics_order=[]
        )
    row = metric_row(observer, perf_counter() - started)
    # Confirmed in _raw_relaxation_cave/_project_liv_terms: concatenate context
    # and target LIV lists and project each core once, BEFORE redundancy removal.
    # Still informational except for E1 refinement; output LIV count can differ.
    expected = len(context.liv_terms()) + len(target.liv_terms())
    if direction == "refinement":
        projected = observer.metrics.synthetic_candidates + observer.metrics.support_candidates
        expected = len(target.liv_terms()) * (1 + len(context.liv_terms()))
    row.update(
        liveness_projections=projected,
        liveness_projections_expected=expected,
        liveness_projections_match=projected == expected,
        output_z3_dag_nodes=_term_list_z3_size(result),
        output_cores=len(result.terms),
        support_branch_selected=any(s.startswith("inv:") for s in observer.metrics.selected_supports),
    )
    # E7 intentionally changes candidate construction.
    if enforce_counts and projected != expected and not getattr(gr1, "_evaluation_ablation", False):
        raise AssertionError(f"liveness projection counters: {projected} != {expected}")
    if enforce_counts and not getattr(gr1, "_evaluation_ablation", False):
        m = observer.metrics
        ni, nj = len(target.liv_terms()), len(context.liv_terms())
        assert (
            m.cave_invocations,
            m.refinement_invocations,
            m.relaxation_invocations,
            m.synthetic_candidates,
            m.support_candidates,
            m.total_candidates,
        ) == (1, 1, 0, ni, ni * nj, ni * (1 + nj)), "E1 original-refinement counter mismatch"
    row["D_B"] = observer.metrics.maximum_quantified_depth
    row["quantified_indexed_variables"] = len(instance.eliminated) * (row["D_B"] + 1)
    names = _indexed_names(target, context)
    row.update(
        eliminated_base_variables=len(instance.eliminated),
        retained_base_variables=len(instance.sorts) - len(instance.eliminated),
        base_variables=len(instance.sorts),
        indexed_variables=len(names),
        maximum_next_depth=_max_index(names),
        syntax_tree_nodes=_term_list_syntax_size(target) + _term_list_syntax_size(context),
        flattened_z3_dag_nodes=_term_list_z3_size(target) + _term_list_z3_size(context),
        target_liveness_cores=len(target.liv_terms()),
        context_liveness_cores=len(context.liv_terms()),
    )
    row["result_json"] = json.dumps([(t.tag.value, t.core.expr.sexpr()) for t in result.terms])
    return result, row


def metric_row(observer: CaveInstrumentation, seconds: float) -> Row:
    """Flatten all timing/counter diagnostics into scalar CSV columns."""
    row = vars(observer.metrics).copy()
    row["selected_supports"] = json.dumps(row["selected_supports"])
    row["cave_seconds"] = row.pop("cumulative_cave_seconds")
    # Reported durations exclude harness bookkeeping; the raw wall clock is kept for audit.
    row["seconds_including_instrumentation"] = seconds
    seconds = max(0.0, seconds - row["instrumentation_seconds"])
    row["seconds"] = seconds
    row["qe_share"] = row["qe_seconds"] / seconds if seconds else 0.0
    return row


def parse_boolean(text: str) -> AST:
    """Independent tiny Boolean parser for the oracle; never calls Z3/CAVE."""
    tokens = re.findall(r"<->|->|[()!&|]|[A-Za-z][A-Za-z0-9_]*", text)
    if "".join(tokens) != re.sub(r"\s+", "", text):
        raise ValueError(f"unsupported oracle syntax: {text}")
    cursor = 0

    def atom() -> AST:
        nonlocal cursor
        token = tokens[cursor]
        cursor += 1
        if token in ("!", "X"):
            return ("not" if token == "!" else "next", atom())
        if token == "(":
            node = expression(0)
            if tokens[cursor] != ")":
                raise ValueError("unclosed Boolean expression")
            cursor += 1
            return node
        if token.lower() in ("true", "false"):
            return ("constant", token.lower() == "true")
        return ("variable", token)

    levels = ({"<->": "eq"}, {"->": "implies"}, {"|": "or"}, {"&": "and"})

    def expression(level: int) -> AST:
        nonlocal cursor
        if level == len(levels):
            return atom()
        left = expression(level + 1)
        while cursor < len(tokens) and tokens[cursor] in levels[level]:
            op = levels[level][tokens[cursor]]
            cursor += 1
            right = expression(level if op == "implies" else level + 1)
            left = (op, left, right)
        return left

    result = expression(0)
    if cursor != len(tokens):
        raise ValueError(f"trailing oracle tokens: {tokens[cursor:]}")
    return result


def evaluate(node: AST, value: Callable[[str, int], bool], depth: int = 0) -> bool:
    """Evaluate Boolean syntax in ordinary Python, including arbitrary NEXT."""
    op = node[0]
    if op == "variable":
        return value(node[1], depth)
    if op == "constant":
        return bool(node[1])
    if op == "next":
        return evaluate(node[1], value, depth + 1)
    if op == "not":
        return not evaluate(node[1], value, depth)
    args = [evaluate(child, value, depth) for child in node[1:]]
    if op == "and":
        return all(args)
    if op == "or":
        return any(args)
    if op == "implies":
        return not args[0] or args[1]
    if op == "eq":
        return args[0] == args[1]
    if op == "xor":
        return sum(args) % 2 == 1
    if op == "ite":
        return args[1] if args[0] else args[2]
    raise ValueError(f"unsupported oracle operation {op}")


def z3_boolean(expr: Any) -> AST:
    """Decode output syntax only; no Z3 evaluation or solver in the oracle."""
    if z3.is_true(expr) or z3.is_false(expr):
        return ("constant", z3.is_true(expr))
    if z3.is_const(expr) and expr.decl().kind() == z3.Z3_OP_UNINTERPRETED:
        name, depth = gr1._parse_flat_name(expr.decl().name())
        node: AST = ("variable", name)
        for _ in range(depth):
            node = ("next", node)
        return node
    ops = {
        z3.Z3_OP_AND: "and",
        z3.Z3_OP_OR: "or",
        z3.Z3_OP_NOT: "not",
        z3.Z3_OP_EQ: "eq",
        z3.Z3_OP_IMPLIES: "implies",
        z3.Z3_OP_XOR: "xor",
        z3.Z3_OP_ITE: "ite",
    }
    if expr.decl().kind() not in ops:
        raise ValueError(f"unsupported Boolean QE result {expr.sexpr()}")
    return (ops[expr.decl().kind()], *(z3_boolean(c) for c in expr.children()))


def lassos(n_ext: int, quick: bool) -> Iterator[Tuple[Tuple[int, ...], int]]:
    """Enumerate all requested external lasso encodings in stable order."""
    for prefix in range(2 if quick else 3):
        for cycle in range(1, 3 if quick else 4):
            for letters in itertools.product(range(1 << n_ext), repeat=prefix + cycle):
                yield letters, prefix


def on_lasso(terms: Sequence[Tuple[str, AST]], names: Sequence[str], letters: Sequence[int], prefix: int) -> bool:
    """Evaluate INIT, G and GF with successor iteration, including wraparound."""
    positions = {name: bit for bit, name in enumerate(names)}

    def at(node: AST, start: int) -> bool:
        def value(name: str, depth: int) -> bool:
            pos = start
            for _ in range(depth):
                pos = pos + 1 if pos + 1 < len(letters) else prefix
            return bool(letters[pos] & (1 << positions[name]))

        return evaluate(node, value)

    for tag, node in terms:
        if tag == "init" and not at(node, 0):
            return False
        if tag == "inv" and not all(at(node, i) for i in range(len(letters))):
            return False
        if tag == "liv" and not any(at(node, i) for i in range(prefix, len(letters))):
            return False
    return True


def closure(count: int, edges: Sequence[Edge]) -> List[int]:
    """Bitset transitive closure, independent of solver and temporal library."""
    reach = [1 << i for i in range(count)]
    for u, v, *_ in edges:
        reach[u] |= 1 << v
    for k in range(count):
        for i in range(count):
            if reach[i] & (1 << k):
                reach[i] |= reach[k]
    return reach


def fair_nodes(count: int, edges: Sequence[Edge], required: int, target_required: int = 0) -> Tuple[int, List[int]]:
    """Find predecessors of cyclic SCCs covering all generalized-Buechi marks."""
    reach = closure(count, edges)
    unseen = (1 << count) - 1
    accepting = 0
    while unseen:
        i = (unseen & -unseen).bit_length() - 1
        component = sum(1 << j for j in range(count) if reach[i] & (1 << j) and reach[j] & (1 << i))
        unseen &= ~component
        internal = [edge for edge in edges if component & (1 << edge[0]) and component & (1 << edge[1])]
        ctx_marks = target_marks = 0
        for edge in internal:
            ctx_marks |= edge[2]
            target_marks |= edge[6]
        if internal and ctx_marks & required == required and target_marks & target_required == target_required:
            accepting |= component
    return sum(1 << i for i in range(count) if reach[i] & accepting), reach


class Oracle:
    """Exact hidden-run quantification for each fixed external omega word.

    INIT with NEXT is a first-edge predicate, not just a predicate of its
    source node. Keeping first edges separate prevents a subtle spurious-start
    bug when gamma_init mentions X(p). Internal runs may have longer periods
    than the external lasso; SCC analysis does not bound their periods.
    """

    def __init__(self, instance: Instance) -> None:
        """Compile input Boolean cores into independent edge truth tables."""
        self.internal = instance.eliminated
        self.external = [name for name in instance.sorts if name not in self.internal]
        self.np = len(self.internal)
        self.nq = len(self.external)
        self.ni = len(instance.target.get("liv", []))
        self.nj = len(instance.context.get("liv", []))
        names = self.internal + self.external
        parsed = [
            {tag: [parse_boolean(t) for t in buckets.get(tag, [])] for tag in ("init", "inv", "liv")}
            for buckets in (instance.context, instance.target)
        ]
        self.table: Dict[Tuple[int, int], Tuple[bool, bool, bool, bool, int, int]] = {}
        for now in range(1 << len(names)):
            for nxt in range(1 << len(names)):

                def value(name: str, depth: int) -> bool:
                    if depth > 1:
                        raise ValueError("oracle input depth exceeds one")
                    return bool((now if depth == 0 else nxt) & (1 << names.index(name)))

                ctx, phi = [
                    {tag: [evaluate(t, value) for t in nodes] for tag, nodes in buckets.items()} for buckets in parsed
                ]
                self.table[now, nxt] = (
                    all(ctx["init"]),
                    all(ctx["inv"]),
                    all(phi["init"]),
                    all(phi["inv"]),
                    sum(1 << j for j, b in enumerate(ctx["liv"]) if b),
                    sum(1 << i for i, b in enumerate(phi["liv"]) if b),
                )

    def graph(self, letters: Sequence[int], prefix: int) -> Tuple[int, List[Edge]]:
        """Construct phase/internal-valuation graph, labeling first edges."""
        width = 1 << self.np
        edges = []
        for phase, q in enumerate(letters):
            nxt = phase + 1 if phase + 1 < len(letters) else prefix
            for p in range(width):
                for pp in range(width):
                    ci, cv, ti, tv, cm, tm = self.table[p | (q << self.np), pp | (letters[nxt] << self.np)]
                    if cv:
                        edges.append((phase * width + p, nxt * width + pp, cm, ci and phase == 0, ti, tv, tm))
        return len(letters) * width, edges

    def exact(self, letters: Sequence[int], prefix: int) -> Tuple[bool, bool, bool]:
        """Return exact refinement, exact relaxation and context feasibility."""
        count, edges = self.graph(letters, prefix)
        required = (1 << self.nj) - 1
        fair, reach = fair_nodes(count, edges, required)
        starts = [e for e in edges if e[3]]
        feasible = any(fair & (1 << e[1]) for e in starts)
        reachable = 0
        for e in starts:
            reachable |= reach[e[1]]
        bad = any(not e[4] and fair & (1 << e[1]) for e in starts)
        bad |= any(not e[5] and fair & (1 << e[1]) for e in starts)
        bad |= any(reachable & (1 << e[0]) and not e[5] and fair & (1 << e[1]) for e in edges)
        for i in range(self.ni):
            avoid = [e for e in edges if not e[6] & (1 << i)]
            avoid_fair, _ = fair_nodes(count, avoid, required)
            bad |= bool(reachable & avoid_fair)
        safe = [e for e in edges if e[5]]
        joint_fair, _ = fair_nodes(count, safe, required, (1 << self.ni) - 1)
        relaxation = any(e[3] and e[4] and joint_fair & (1 << e[1]) for e in safe)
        return not bool(bad), relaxation, feasible


def random_instance(seed: int, n_ext: int, n_int: int) -> Instance:
    """Generate depth-three Boolean formulas using only an explicit RNG."""
    rng = random.Random(seed)
    names = [f"p{i + 1}" for i in range(n_int)] + [f"q{i + 1}" for i in range(n_ext)]

    def formula(depth: int = 3) -> str:
        if depth == 0 or rng.random() < 0.35:
            leaf = rng.choice(names + ["True", "False"])
            if leaf not in ("True", "False") and rng.random() < 0.45:
                leaf = f"X({leaf})"
            return f"!({leaf})" if rng.random() < 0.25 else leaf
        return f"({formula(depth - 1)} {rng.choice(['&', '|', '->', '<->'])} {formula(depth - 1)})"

    def buckets() -> Dict[str, List[str]]:
        return {
            "init": [formula()] if rng.random() < 0.5 else [],
            "inv": [formula()],
            "liv": [formula() for _ in range(rng.randrange(3))],
        }

    return Instance(buckets(), buckets(), {name: "bool" for name in names}, names[:n_int])


def fuzz(config: Row) -> List[Row]:
    """Classify both directions on the entire requested external lasso suite."""
    instance = random_instance(config["instance_seed"], config["ext"], config["n_int"])
    oracle = Oracle(instance)
    results = [eliminate(instance, direction) for direction in ("refinement", "relaxation")]
    formulas = [[(t.tag.value, z3_boolean(t.core.expr)) for t in terms.terms] for terms, _ in results]
    differences, unsound, true_counts = [0, 0], [0, 0], [0, 0]
    exact_true_counts = [0, 0]
    witnesses: List[Optional[Row]] = [None, None]
    nonblocking, total = True, 0
    for letters, prefix in lassos(config["ext"], config["quick"]):
        ref, rel, feasible = oracle.exact(letters, prefix)
        nonblocking &= feasible
        total += 1
        for i, exact in enumerate((ref, rel)):
            exact_true_counts[i] += exact
            actual = on_lasso(formulas[i], oracle.external, letters, prefix)
            differences[i] += actual != exact
            true_counts[i] += actual
            violation = actual and not exact if i == 0 else exact and not actual
            unsound[i] += violation
            if violation and witnesses[i] is None:
                witnesses[i] = {
                    "letters": letters,
                    "prefix": prefix,
                    "external_order": oracle.external,
                    "cave": actual,
                    "exact": exact,
                }
                print(
                    "UNSOUND INSTANCE",
                    json.dumps(vars(instance)),
                    "LASSO",
                    json.dumps(witnesses[i]),
                    "PSI",
                    results[i][1]["result_json"],
                    flush=True,
                )
    rows = []
    pfree = target_pfree_cores(instance)
    for i, direction in enumerate(("refinement", "relaxation")):
        rows.append(
            {
                **results[i][1],
                "direction": direction,
                "n_I": oracle.ni,
                "n_J": oracle.nj,
                "classification": "unsound" if unsound[i] else "conservative" if differences[i] else "exact",
                "diff_fraction": differences[i] / total,
                "unsound_lassos": unsound[i],
                "lassos": total,
                "is_bottom_or_top": true_counts[i] == (0 if i == 0 else total),
                "trivial": true_counts[i] in (0, total) and exact_true_counts[i] == true_counts[i],
                "target_pfree_cores": pfree,
                "context_nonblocking": nonblocking,
                "uses_init": bool(instance.context.get("init") or instance.target.get("init")),
                "max_depth": int(
                    any("X(" in t for b in (instance.context, instance.target) for texts in b.values() for t in texts)
                ),
                "instance_json": json.dumps(vars(instance), sort_keys=True),
                "witness_json": json.dumps(witnesses[i]) if witnesses[i] else "",
            }
        )
    for row in rows:
        row["likely_cause"] = likely_cause(instance, row) if row["classification"] == "conservative" else ""
        row["likely_cause_method"] = "syntactic heuristic only; not evidence for a claim"
    return rows


def likely_cause(instance: Instance, row: Row) -> str:
    """Assign a documented heuristic to conservative instances, never a proof."""

    def variables(texts: Sequence[str]) -> set:
        tokens = set(re.findall(r"[A-Za-z][A-Za-z0-9_]*", " ".join(texts)))
        return tokens & set(instance.sorts)

    init = variables(instance.context.get("init", []) + instance.target.get("init", []))
    inv = instance.context.get("inv", []) + instance.target.get("inv", [])
    defined = variables([text for text in inv if "<->" in text])
    if init & defined:
        return "init-inv-dependency"
    liv = variables(instance.target.get("liv", []) + instance.context.get("liv", []))
    if liv & set(instance.eliminated) and any("X(" in text for text in inv):
        return "liveness-needs-recurrence"
    if row["support_branch_selected"]:
        return "support-branch"
    if not row["context_nonblocking"]:
        return "blocking-context"
    return "other"


def target_pfree_cores(instance: Instance) -> int:
    """Count semantically hidden-independent INV/LIV cores without Z3."""
    names = list(instance.sorts)
    width = len(names)
    hidden_bits = [names.index(name) + offset for name in instance.eliminated for offset in (0, width)]
    independent = 0
    for text in instance.target.get("inv", []) + instance.target.get("liv", []):
        node = parse_boolean(text)
        table = []
        for valuation in range(1 << (2 * width)):

            def value(name: str, depth: int) -> bool:
                return bool(valuation & (1 << (names.index(name) + depth * width)))

            table.append(evaluate(node, value))
        independent += all(table[v] == table[v ^ (1 << bit)] for v in range(len(table)) for bit in hidden_bits)
    return independent


def sample_nonblocking(config: Row) -> Row:
    """Rejection-sample one indexed deterministic stream in an isolated precheck."""
    stream = f"{config['seed']}:{config['n_int']}:{config['instance_id']}:nonblocking"
    draw = 0
    while True:
        digest = hashlib.sha256(f"{stream}:{draw}".encode()).hexdigest()
        seed = int(digest[:16], 16)
        instance = random_instance(seed, config["ext"], config["n_int"])
        oracle = Oracle(instance)
        if all(oracle.exact(letters, prefix)[2] for letters, prefix in lassos(config["ext"], True)):
            return {
                "instance_seed": seed,
                "seed_stream_id": stream,
                "seed_stream_index": draw,
                "rejected_draws": draw,
                "nonblocking_checked_on": "quick-lassos",
                "status": "ok",
            }
        draw += 1


def brute_constant_external(instance: Instance, letter: int) -> Tuple[bool, bool]:
    """Independent bounded internal-lasso enumeration for tiny oracle tests.

    Only a constant external word and one hidden bit are used here. With n
    product states and k acceptance obligations, an accepting closed walk of
    length at most n*max(1,k) suffices; prefixes of length n cover INIT edges.
    Refinement liveness violations need context fairness only. This explicitly
    includes hidden cycles longer than the one-letter external cycle.
    """
    hidden = len(instance.eliminated)
    assert hidden == 1
    external = [n for n in instance.sorts if n not in instance.eliminated]
    names = instance.eliminated + external
    parsed = [
        [(tag, parse_boolean(t)) for tag, texts in buckets.items() for t in texts]
        for buckets in (instance.context, instance.target)
    ]
    count = 1 << hidden
    marks = len(instance.context.get("liv", [])) + len(instance.target.get("liv", []))
    ref, rel = True, False
    for prefix in range(count + 1):
        for cycle in range(1, count * max(1, marks) + 1):
            for ps in itertools.product(range(count), repeat=prefix + cycle):
                letters = [p | (letter << hidden) for p in ps]
                ctx, phi = [on_lasso(formula, names, letters, prefix) for formula in parsed]
                ref &= not ctx or phi
                rel |= ctx and phi
    return ref, rel


def selftest() -> Row:
    """Assert three known answers, negative control and oracle/brute agreement."""
    cases = [
        (
            Instance(
                {"inv": ["((q & X(!q)) -> X(p)) & (X(p) -> q)"]},
                {"inv": ["X(p) | s"], "liv": ["X(p)"]},
                {"p": "bool", "q": "bool", "s": "bool"},
                ["p"],
            ),
            "falling-edge",
        ),
        (Instance({"liv": ["p"]}, {"liv": ["p & s"]}, {"p": "bool", "s": "bool"}, ["p"]), "support-persistence"),
        (
            Instance(
                {"init": ["p"], "inv": ["X(p) <-> q"]},
                {"inv": ["p <-> s"]},
                {"p": "bool", "q": "bool", "s": "bool"},
                ["p"],
            ),
            "preceding-instance",
        ),
    ]
    negative_flagged = False
    for case_index, (instance, label) in enumerate(cases):
        oracle = Oracle(instance)
        outputs = [eliminate(instance, direction) for direction in ("refinement", "relaxation")]
        formulas = [[(t.tag.value, z3_boolean(t.core.expr)) for t in result.terms] for result, _ in outputs]
        strict = False
        if case_index == 1:
            assert outputs[0][1]["support_branch_selected"], "persistent certificate not selected"
        for letters, prefix in lassos(len(oracle.external), True):
            ref, rel, _ = oracle.exact(letters, prefix)
            actual = [on_lasso(f, oracle.external, letters, prefix) for f in formulas]
            assert not actual[0] or ref, (label, "unsound refinement", letters, prefix)
            assert not rel or actual[1], (label, "unsound relaxation", letters, prefix)
            if case_index == 0:
                expected = [
                    [("inv", parse_boolean("(q & X(!q)) | s")), ("liv", parse_boolean("q & X(!q)"))],
                    [("inv", parse_boolean("q | s")), ("liv", parse_boolean("q"))],
                ]
                assert [ref, rel] == [on_lasso(f, oracle.external, letters, prefix) for f in expected]
                assert actual == [ref, rel], (label, "CAVE not exact", letters, prefix)
                # Deliberately replace refinement with True.
                negative_flagged |= on_lasso([], oracle.external, letters, prefix) and not ref
            elif case_index == 1:
                bit = oracle.external.index("s")
                assert ref == all(letter & (1 << bit) != 0 for letter in letters[prefix:]), label
                strict |= ref and not actual[0]
            else:
                preceding = [("init", parse_boolean("s")), ("inv", parse_boolean("X(s) <-> q"))]
                assert ref == on_lasso(preceding, oracle.external, letters, prefix), label
                assert not actual[0], "preceding-instance CAVE should be bottom"
                strict |= ref and not actual[0]
        if case_index:
            assert strict, f"{label}: expected strict conservatism"
        print(f"PASS: {label}", flush=True)
    assert negative_flagged, "negative control missed an unsound weakening"
    # Include first-edge INIT and hidden two-cycle fairness explicitly.
    tiny = [
        Instance(
            {"init": ["X(p)"], "inv": ["X(p) <-> !p"], "liv": ["p"]},
            {"init": ["p | q1"], "liv": ["!p"]},
            {"p": "bool", "q1": "bool"},
            ["p"],
        )
    ]
    for seed in range(4):
        instance = random_instance(seed, 1, 1)
        instance.context["liv"] = instance.context["liv"][:1]
        instance.target["liv"] = instance.target["liv"][:1]
        tiny.append(instance)
    for instance in tiny:
        oracle = Oracle(instance)
        for letter in range(2):
            assert oracle.exact((letter,), 0)[:2] == brute_constant_external(instance, letter), vars(instance)
    print("PASS: negative control and independent brute-force consistency", flush=True)
    # E5 family guard. Non-fatal on purpose: a WARN means the chain contracts compose to a
    # degenerate or unexpected result, so inspect the printed cores BEFORE the long runs.
    for stages_count in (2, 3):
        chain_row = chain({"N": stages_count, "order": "left-fold"})
        cores = json.loads(chain_row.get("result_a_json") or "[]")
        healthy = (
            chain_row.get("status") == "ok"
            and not chain_row.get("degenerate")
            and chain_row.get("input_range_check_current") == "true"
        )
        print(
            f"{'PASS' if healthy else 'WARN'}: E5 stage family N={stages_count}: "
            f"y0 range [{chain_row.get('observed_lower_current')}, {chain_row.get('observed_upper_current')}] "
            f"expected [{chain_row.get('expected_lower')}, {chain_row.get('expected_upper')}]; "
            f"degenerate={chain_row.get('degenerate')}; assumption cores={cores}",
            flush=True,
        )
    pfree = Instance({"liv": ["p"]}, {"inv": ["q"], "liv": ["q"]}, {"p": "bool", "q": "bool"}, ["p"])
    for direction in ("refinement", "relaxation"):
        eliminate(pfree, direction, enforce_counts=False)
    print("PASS: hidden-variable-free target with informational counters", flush=True)
    return {"status": "ok", "selftest": "passed"}


def shift_expr(expr: Any, offset: int) -> Any:
    """Instantiate a finite flattened core at a global time index."""
    replacements = []
    for atom in get_vars(expr):
        name, depth = gr1._parse_flat_name(atom.decl().name())
        replacements.append((atom, z3.Const(f"{name}_{depth + offset}", atom.sort())))
    return z3.substitute(expr, *replacements) if replacements else expr


def finite_formula(terms: gr1.GR1TermList, horizon: int) -> Any:
    """Drop liveness, put INIT at zero and depth-one INV at 0,...,T-1."""
    assert all(gr1._core_next_depth(t.core) <= 1 for t in terms.terms), "E3 expects depth <= 1"
    return z3.And(
        *(
            [t.core.expr for t in terms.init_terms()]
            + [shift_expr(t.core.expr, pos) for t in terms.inv_terms() for pos in range(horizon)]
        )
    )


def aeb_compose(simplify: bool = True) -> Tuple[Any, Row]:
    """Measure exactly production supervisor.compose(vehicle)."""
    from examples.aeb_gr1_composition import make_supervisor, make_vehicle

    supervisor, vehicle = make_supervisor(), make_vehicle()
    observer = CaveInstrumentation()
    gc.collect()
    started = perf_counter()
    with observer.observe():
        result = supervisor.compose(vehicle, simplify=simplify)
    row = metric_row(observer, perf_counter() - started)
    row.update(
        output_z3_dag_nodes=_term_list_z3_size(result.a) + _term_list_z3_size(result.g),
        output_cores=len(result.a.terms) + len(result.g.terms),
    )
    return result, row


def unrolled(config: Row) -> Row:
    """Two monolithic QE calls; record the deliberate interface distinction."""
    from examples.aeb_gr1_composition import SORTS, make_supervisor, make_vehicle

    supervisor, vehicle = make_supervisor(), make_vehicle()
    horizon = config["T"]
    aa, gs, av, gv = [
        finite_formula(terms, horizon)
        for terms in (
            supervisor._operation_assumptions,
            supervisor._operation_guarantees,
            vehicle._operation_assumptions,
            vehicle._operation_guarantees,
        )
    ]
    names = ["u", "MOV", "DCL", "STP", "v"]
    atoms = {
        name: [
            z3.Const(f"{name}_{i}", z3.BoolSort() if SORTS[name] == "bool" else z3.RealSort())
            for i in range(horizon + 1)
        ]
        for name in names
    }
    universal = [a for values in atoms.values() for a in values]
    guarantee_names = names if config["projection"] == "requested-five" else names[:-1]
    existential = [a for name in guarantee_names for a in atoms[name]]
    apply = z3.Tactic.apply
    qe_seconds = 0.0

    def timed_apply(tactic: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal qe_seconds
        begin = perf_counter()
        try:
            return apply(tactic, *args, **kwargs)
        finally:
            qe_seconds += perf_counter() - begin

    gc.collect()
    started = perf_counter()
    with patch.object(z3.Tactic, "apply", timed_apply):
        ref_started = perf_counter()
        refined = gr1._eliminate_quantifiers(z3.ForAll(universal, z3.Implies(z3.And(aa, gs), av)))
        ref_seconds = perf_counter() - ref_started
        rel_started = perf_counter()
        relaxed = gr1._eliminate_quantifiers(z3.Exists(existential, z3.And(gs, gv)))
        rel_seconds = perf_counter() - rel_started
    seconds = perf_counter() - started
    return {
        "seconds": seconds,
        "refinement_seconds": ref_seconds,
        "cave_seconds": 0.0,
        "qe_seconds": qe_seconds,
        "non_qe_seconds": seconds - qe_seconds,
        "qe_share": qe_seconds / seconds,
        "qe_applications": 2,
        "qe_tactic_applications": 2,
        "forall_bounds": 1,
        "exists_bounds": 1,
        "phase_scope": "direct-QE operation, not CAVE",
        "relaxation_seconds": rel_seconds,
        "liveness_dropped": True,
        "quantified_atoms": len(universal) + len(existential),
        "refinement_quantified_atoms": len(universal),
        "relaxation_quantified_atoms": len(existential),
        "guarantee_eliminated": json.dumps(guarantee_names),
        "refinement_z3_dag_nodes": gr1._z3_ast_size(refined),
        "relaxation_z3_dag_nodes": gr1._z3_ast_size(relaxed),
        "output_z3_dag_nodes": gr1._z3_ast_size(refined) + gr1._z3_ast_size(relaxed),
        "baseline_semantics": "finite-horizon safety only",
    }


def stage(index: int) -> Any:
    """Construct one chain stage whose eliminated variable has one fixed offset.

    Every intermediate variable y_i occurs only at NEXT-offset zero: stage i+1's
    assumption bounds y_i, and stage i's guarantee bounds y_i in terms of
    y_{i-1} at the same position. The first E5 family had the guarantee on
    X(y_i) but the next assumption on y_i; the position-zero assumption instance
    then depended on a preceding guarantee instance outside the finite window,
    the composed assumption became false and the guarantee became empty
    (observed in the quick run). The mode output m_i is never eliminated and
    does not influence y_i, so no composed assumption depends on it.
    """
    x, y, mode = f"y{index - 1}", f"y{index}", f"m{index}"
    return gr1.GR1IoContract.from_dict(
        {
            "input_vars": [x],
            "output_vars": [y, mode],
            "variable_sorts": {x: "real", y: "real", mode: "bool"},
            "assumptions": {
                "init": [f"0 <= {x} & {x} <= 100"],
                "inv": [f"0 <= {x} & {x} <= 100"],
                "liv": [f"{x} <= 50"],
            },
            "guarantees": {
                "init": [f"{y} = {x}"],
                "inv": [f"{x}-1/2 <= {y} & {y} <= {x}+1/2"],
                "liv": [f"{y} <= 50", mode],
            },
        },
        simplify=False,
    )


def chain(config: Row, instrument: bool = True) -> Row:
    """Compose left folds or balanced contiguous subchains; retain step data.

    ``instrument=False`` (profiling only) installs no observer, so the profile
    shows production costs without the harness's bookkeeping.
    """
    stages = [stage(i) for i in range(1, config["N"] + 1)]
    observer = CaveInstrumentation()
    steps: List[Row] = []

    def consistent(contract: Any) -> str:
        try:
            solver = z3.Solver()
            solver.set(timeout=500)
            solver.add(
                *[
                    t.core.expr
                    for t in contract.a.init_terms()
                    + contract.a.inv_terms()
                    + contract.g.init_terms()
                    + contract.g.inv_terms()
                ]
            )
            return str(solver.check())
        except Exception as error:
            return f"unknown: {error}"

    def combine(left: Any, right: Any) -> Any:
        before = vars(observer.metrics).copy()
        started = perf_counter()
        result = left.compose(right, simplify=True)
        raw_elapsed = perf_counter() - started
        elapsed = raw_elapsed - (observer.metrics.instrumentation_seconds - before["instrumentation_seconds"])
        steps.append(
            {
                "step": len(steps) + 1,
                "seconds": elapsed,
                "seconds_including_instrumentation": raw_elapsed,
                "cave_seconds": observer.metrics.cumulative_cave_seconds - before["cumulative_cave_seconds"],
                "qe_seconds": observer.metrics.qe_seconds - before["qe_seconds"],
                "output_cores": len(result.a.terms) + len(result.g.terms),
            }
        )
        # Outside each step's timed compose region. Total time excludes these
        # diagnostic queries by summing measured compose durations below.
        status = consistent(result)
        steps[-1]["inconsistency_check"] = str(status)
        if status == "unsat":
            steps[-1]["diagnostic"] = "inconsistent finite INIT/INV buckets"
        return result

    def balanced(items: List[Any]) -> Any:
        if len(items) == 1:
            return items[0]
        middle = len(items) // 2
        return combine(balanced(items[:middle]), balanced(items[middle:]))

    gc.collect()
    started = perf_counter()
    try:
        with observer.observe() if instrument else nullcontext():
            if config["order"] == "balanced":
                result = balanced(stages)
            else:
                result = stages[0]
                for item in stages[1:]:
                    result = combine(result, item)
    except Exception as error:
        return {
            **metric_row(observer, perf_counter() - started),
            "status": "error",
            "error": str(error),
            "traceback": traceback.format_exc(),
            "steps_json": json.dumps(steps),
        }
    # metric_row subtracts the observer's harness cost once, so pass the raw sum.
    row = metric_row(observer, sum(step["seconds_including_instrumentation"] for step in steps))
    row["chain_wall_seconds"] = perf_counter() - started
    # Bounded check only: avoid pretending is_empty is full realizability.
    consistency = consistent(result)
    low, high = (config["N"] - 1) / 2, 100 - (config["N"] - 1) / 2
    row.update(
        status="ok",
        inconsistency_check=str(consistency),
        expected_lower=low,
        expected_upper=high,
        steps_json=json.dumps(steps),
        output_cores=len(result.a.terms) + len(result.g.terms),
        output_z3_dag_nodes=_term_list_z3_size(result.a) + _term_list_z3_size(result.g),
    )
    safety = z3.And(*[t.core.expr for t in result.a.init_terms() + result.a.inv_terms()])
    row["range_scope"] = "conjoined INIT and INV cores at position zero; finite diagnostic"
    # A vacuous composition (assumption false, guarantee empty) still has a timing, but it
    # measures a degenerate result: flag it so reports never present it as a scalability claim.
    row["composed_assumption_false"] = any(z3.is_false(t.core.expr) for t in result.a.terms)
    row["composed_guarantee_empty"] = len(result.g.terms) == 0
    row["degenerate"] = bool(row["composed_assumption_false"] or row["composed_guarantee_empty"])
    present = {variable.decl().name() for variable in get_vars(safety)}
    for position in (0, 1):
        suffix = "current" if position == 0 else "next"
        if f"y0_{position}" not in present:
            # Depth-zero family: the next-position variable is not mentioned at all.
            row.update(
                {
                    f"observed_lower_{suffix}": "absent",
                    f"observed_upper_{suffix}": "absent",
                    f"input_range_check_{suffix}": "not-applicable",
                    f"input_range_contained_{suffix}": "not-applicable",
                }
            )
            continue
        try:
            variable = z3.Real(f"y0_{position}")
            endpoints = []
            for minimize in (True, False):
                optimizer = z3.Optimize()
                optimizer.set(timeout=1000)
                optimizer.add(safety)
                bound = optimizer.minimize(variable) if minimize else optimizer.maximize(variable)
                status = optimizer.check()
                endpoints.append(str(bound.value()) if status == z3.sat else "unknown")
            local = z3.Solver()
            local.set(timeout=500)
            local.add(safety, z3.Not(z3.And(variable >= low, variable <= high)))
            contained = local.check()
            match = (
                "unknown"
                if "unknown" in endpoints
                else str(endpoints == [str(z3.RealVal(low)), str(z3.RealVal(high))]).lower()
            )
            row.update(
                {
                    f"observed_lower_{suffix}": endpoints[0],
                    f"observed_upper_{suffix}": endpoints[1],
                    f"input_range_check_{suffix}": match,
                    f"input_range_contained_{suffix}": (
                        "true" if contained == z3.unsat else "false" if contained == z3.sat else "unknown"
                    ),
                }
            )
        except Exception as error:
            row.update(
                {
                    f"observed_lower_{suffix}": "unknown",
                    f"observed_upper_{suffix}": "unknown",
                    f"input_range_check_{suffix}": "unknown",
                    f"input_range_contained_{suffix}": "unknown",
                    f"diagnostic_error_{suffix}": str(error),
                }
            )
    # Compatibility aliases explicitly refer to the current position.
    row["input_range_check"] = row["input_range_check_current"]
    row["input_range_contained"] = row["input_range_contained_current"]
    if config["N"] <= 4:
        row["result_a_json"] = json.dumps([(t.tag.value, t.core.expr.sexpr()) for t in result.a.terms])
        row["result_g_json"] = json.dumps([(t.tag.value, t.core.expr.sexpr()) for t in result.g.terms])
    return row


def ast_ltl(node: AST) -> str:
    """Render Boolean output AST as LTL, preserving next depths."""
    op = node[0]
    if op == "constant":
        return "1" if node[1] else "0"
    if op == "variable":
        return node[1]
    if op in ("not", "next"):
        return f"{'!' if op == 'not' else 'X'}({ast_ltl(node[1])})"
    if op == "ite":
        a, b, c = (ast_ltl(n) for n in node[1:])
        return f"(({a} & {b}) | (!({a}) & {c}))"
    if len(node) == 1:
        return "1" if op == "and" else "0"
    return (
        "("
        + {"and": " & ", "or": " | ", "eq": " <-> ", "implies": " -> ", "xor": " xor "}[op].join(
            ast_ltl(n) for n in node[1:]
        )
        + ")"
    )


def terms_ltl(terms: gr1.GR1TermList) -> str:
    """Preserve separate GF obligations and persistent G certificates."""
    return (
        " & ".join(
            f"{ {'init': '', 'inv': 'G', 'liv': 'G F'}[t.tag.value]}" f"({ast_ltl(z3_boolean(t.core.expr))})"
            for t in terms.terms
        )
        or "1"
    )


def spot_available() -> bool:
    """Reject the unrelated PyPI spot package as well as missing bindings."""
    try:
        import buddy
        import spot

        return all(hasattr(spot, name) for name in ("translate", "complement", "product", "are_equivalent")) and (
            hasattr(buddy, "bdd_exist")
        )
    except Exception:
        return False


def automata(config: Row) -> Row:
    """Exact projection/complement with Spot; all expensive work is isolated.

    AP registration follows https://spot.lre.epita.fr/tut90.html. Edge merging
    follows https://spot.lre.epita.fr/ipynb/split.html. Version-dependent missing
    methods are error rows, never silently substituted approximations.
    """
    import buddy
    import spot

    instance = synthetic(config)
    target, context = instance.terms()
    cave, row = eliminate(instance, "refinement")
    row["cave_operation_seconds"] = row["seconds"]
    publish_partial({**row, "active_phase": "translate-and-project"})
    source = f"({terms_ltl(context)}) & !({terms_ltl(target)})"
    gc.collect()
    started = perf_counter()
    exists = spot.translate(source, "BA")
    for name in instance.eliminated:
        ap = exists.register_ap(name)
        variable = buddy.bdd_ithvar(ap)
        for edge in exists.edges():
            edge.cond = buddy.bdd_exist(edge.cond, variable)
        exists.unregister_ap(ap)
    exists.merge_edges()
    # Projection can create overlapping guards: do not reuse cached
    # determinism/unambiguity properties when complementing the automaton.
    exists.prop_reset()
    row["exists_seconds"] = perf_counter() - started
    row.update(exists_states=exists.num_states(), exists_acceptance_sets=exists.num_sets())
    publish_partial({**row, "active_phase": "complement"})
    complement_started = perf_counter()
    complement = spot.complement(exists)
    row["complement_seconds"] = perf_counter() - complement_started
    row["seconds"] = perf_counter() - started
    row.update(complement_states=complement.num_states(), complement_acceptance_sets=complement.num_sets())
    publish_partial({**row, "active_phase": "soundness-and-equivalence"})
    cave_automaton = spot.translate(terms_ltl(cave))
    row.update(
        complement_states=complement.num_states(),
        complement_acceptance_sets=complement.num_sets(),
        sound=spot.product(cave_automaton, exists).is_empty(),
        exact=spot.are_equivalent(complement, cave_automaton),
        needs_nonbuchi_or_multiple_sets=not complement.acc().is_buchi() or complement.num_sets() > 1,
        spot_version=str(getattr(spot, "__version__", "unknown")),
        buddy_version=str(getattr(buddy, "__version__", "unknown")),
        acceptance_interpretation="observed representation only; not a GR(1) expressibility test",
    )
    return row


def bucket_certificate(left: gr1.GR1TermList, right: gr1.GR1TermList) -> str:
    """Prove sufficient bucketwise equivalence; unknown is not inequivalence."""

    def equivalent(a: Any, b: Any) -> bool:
        solver = z3.Solver()
        solver.set(timeout=500)
        solver.add(a != b)
        return solver.check() == z3.unsat

    for tag in ("init", "inv"):
        a, b = [z3.And(*[t.core.expr for t in result.terms if t.tag.value == tag]) for result in (left, right)]
        if not equivalent(a, b):
            return "unknown"
    for a, b in ((left.liv_terms(), right.liv_terms()), (right.liv_terms(), left.liv_terms())):
        if any(not any(equivalent(x.core.expr, y.core.expr) for y in b) for x in a):
            return "unknown"
    return "true"


def ablation(config: Row) -> Row:
    """Patch only this spawned benchmark process; restore every patch."""
    name = config["ablation"]
    simplify = name != "ablation_simplify_false"

    def execute(flag: bool) -> Tuple[Any, Row]:
        return aeb_compose(flag) if config["family"] == "aeb" else eliminate(synthetic(config), "refinement", flag)

    with ExitStack() as stack:
        stack.enter_context(patch.object(gr1, "_evaluation_ablation", True, create=True))
        if name == "ablation_synthetic_only":
            # Construct only the synthetic candidate; slicing the original
            # list would still pay for every support projection.
            stack.enter_context(
                patch.object(
                    gr1,
                    "_refinement_liv_candidates",
                    lambda target, context, variables: [gr1._refine_liv_fallback(target, context, variables)],
                )
            )
        if name in ("ablation_qe", "ablation_qe_rec"):
            tactic = name[len("ablation_") :]

            def alternate(expr: Any) -> Any:
                result = z3.Tactic(tactic)(expr)
                if len(result) != 1:
                    raise ValueError(f"{tactic}: expected one subgoal, got {len(result)}")
                simplified = z3.simplify(z3.And(*result[0]))
                if z3.is_and(simplified) and all(
                    z3.is_const(c) and c.sort() == z3.BoolSort() for c in simplified.children()
                ):
                    return z3.And(*sorted(simplified.children(), key=lambda c: c.sexpr()))
                return simplified

            stack.enter_context(patch.object(gr1, "_eliminate_quantifiers", alternate))
        output, row = execute(simplify)
    if not config.get("_warm_call", False):
        return row
    reference, _ = execute(True)  # Diagnostic, after both cold and warm calls.
    pairs = [(reference.a, output.a), (reference.g, output.g)] if config["family"] == "aeb" else [(reference, output)]
    row.update(
        unchanged="true" if all(bucket_certificate(a, b) == "true" for a, b in pairs) else "unknown",
        equivalence_method="sufficient tag-preserving finite-core Z3 equivalence; 500ms/query",
        simplify=simplify,
        qe_tactic=name[len("ablation_") :] if name in ("ablation_qe", "ablation_qe_rec") else "qe2",
    )
    return row


# def aeb_application() -> List[Row]:
#     """Copy the old AEB compose-then-quotient logic, without its repetition loop."""
#     from examples.aeb_gr1_composition import make_supervisor, make_vehicle
#
#     supervisor, vehicle = make_supervisor(), make_vehicle()
#     composition_observer = CaveInstrumentation()
#     gc.collect()
#     started = perf_counter()
#     with composition_observer.observe():
#         composition = supervisor.compose(vehicle, simplify=True)
#     composition_seconds = perf_counter() - started
#     quotient_observer = CaveInstrumentation()
#     gc.collect()
#     started = perf_counter()
#     with quotient_observer.observe():
#         quotient = composition.quotient(vehicle, simplify=True)
#     quotient_seconds = perf_counter() - started
#     combined_observer = CaveInstrumentation()
#     combined_observer.metrics = _combine_metrics(composition_observer.metrics, quotient_observer.metrics)
#     rows = []
#     for scope, observer, seconds, contracts in (
#         ("composition", composition_observer, composition_seconds, [composition]),
#         ("quotient", quotient_observer, quotient_seconds, [quotient]),
#         ("combined", combined_observer, composition_seconds + quotient_seconds, [composition, quotient]),
#     ):
#         row = metric_row(observer, seconds)
#         row.update(scope=scope, end_to_end_seconds=row["seconds"],
#                    output_cores=sum(len(c.a.terms) + len(c.g.terms) for c in contracts),
#                    output_z3_dag_nodes=sum(_term_list_z3_size(c.a) + _term_list_z3_size(c.g) for c in contracts))
#         rows.append(row)
#     return rows


def aeb_application() -> List[Row]:
    """Measure the Table 2 AEB composition and quotient operations."""
    from examples.aeb_gr1_composition import make_supervisor, make_vehicle
    from examples.aeb_predicted_clearance import make_prediction, make_target

    supervisor, vehicle = make_supervisor(), make_vehicle()
    clearance, target = make_prediction(), make_target()
    composition_observer = CaveInstrumentation()
    gc.collect()
    started = perf_counter()
    with composition_observer.observe():
        comp = supervisor.compose(vehicle, simplify=True)
        svd = comp.compose(clearance, simplify=True)
    composition_seconds = perf_counter() - started
    quotient_observer = CaveInstrumentation()
    gc.collect()
    started = perf_counter()
    with quotient_observer.observe():
        q = target.quotient(vehicle, simplify=True)
    quotient_seconds = perf_counter() - started
    combined_observer = CaveInstrumentation()
    combined_observer.metrics = _combine_metrics(composition_observer.metrics, quotient_observer.metrics)
    rows = []
    for scope, observer, seconds, contracts in (
        ("composition", composition_observer, composition_seconds, [svd]),
        ("quotient", quotient_observer, quotient_seconds, [q]),
        ("combined", combined_observer, composition_seconds + quotient_seconds, [svd, q]),
    ):
        row = metric_row(observer, seconds)
        row.update(
            scope=scope,
            end_to_end_seconds=row["seconds"],
            output_cores=sum(len(c.a.terms) + len(c.g.terms) for c in contracts),
            output_z3_dag_nodes=sum(_term_list_z3_size(c.a) + _term_list_z3_size(c.g) for c in contracts),
        )
        rows.append(row)
    return rows


def profile_operation(config: Row) -> Row:
    """Profile once; disjoint self-time groups avoid double counting nesting."""
    import cProfile
    import io
    import pstats

    profiler = cProfile.Profile()
    result: Row = {}
    if config["profile_name"] != "chain_n3":
        from examples.aeb_gr1_composition import make_supervisor, make_vehicle

        supervisor, vehicle = make_supervisor(), make_vehicle()  # construction stays unprofiled
    gc.collect()
    profiler.enable()
    try:
        if config["profile_name"] == "chain_n3":
            result = chain({"N": 3, "order": "left-fold"}, instrument=False)
        else:
            # Production call only: no harness observer, so no harness bookkeeping in the profile.
            supervisor.compose(vehicle, simplify=config["profile_name"] == "aeb_simplify_true")
    finally:
        profiler.disable()
    stream = io.StringIO()
    stats: Any = pstats.Stats(profiler, stream=stream)
    stats.sort_stats("cumulative").print_stats(40)
    stats.sort_stats("tottime").print_stats(40)
    buckets = {
        key: 0.0
        for key in (
            "qe_apply",
            "solver_checks",
            "simplify",
            "selection",
            "parsing_flattening",
            "z3_printing_get_vars",
            "z3_python_wrapper",
            "other",
        )
    }
    get_vars_cumulative = 0.0
    for (filename, _line, function), (_cc, _nc, self_time, cumulative, _callers) in stats.stats.items():
        lower = function.lower()
        base = os.path.basename(filename)
        if function == "get_vars" and base == "z3util.py":
            get_vars_cumulative += cumulative  # recursive; cProfile counts outermost entries only
        if "tactic_apply" in lower or (function == "apply" and "z3" in filename):
            category = "qe_apply"
        elif "solver_check" in lower or "optimize_check" in lower or (function == "check" and "z3" in filename):
            category = "solver_checks"
        elif "simplif" in lower:
            category = "simplify"
        elif "_select_" in lower or "selectliveness" in lower:
            category = "selection"
        elif any(token in lower for token in ("parse", "flatten", "token", "_to_z3", "_shift")):
            category = "parsing_flattening"
        elif base in ("z3printer.py", "z3util.py"):
            category = "z3_printing_get_vars"  # z3util.get_vars de-duplicates by str(expr)
        elif os.sep + "z3" + os.sep in filename:
            category = "z3_python_wrapper"
        else:
            category = "other"
        buckets[category] += self_time
    return {
        "profile_name": config["profile_name"],
        "profile_text": stream.getvalue(),
        **buckets,
        "z3util_get_vars_cumulative_seconds": get_vars_cumulative,
        "profile_note": "no harness observer; categories are disjoint self times, get_vars is cumulative",
        "profile_total_seconds": stats.total_tt,
        "profile_accounting": "disjoint cProfile self time",
        "status": result.get("status", "ok"),
        "error": result.get("error", ""),
        "profile_operation_seconds": result.get("seconds", ""),
    }


def require_api(experiment: str) -> None:
    """Fail inside the worker, producing a clear error row for missing APIs."""
    required = ("_project_liv_terms", "_core_next_depth", "_eliminate_quantifiers")
    missing = [name for name in required if not hasattr(gr1, name)]
    missing += [
        f"GR1TermList.{name}"
        for name in ("to_bucket_dict", "elim_vars_by_refining", "elim_vars_by_relaxing")
        if not hasattr(gr1.GR1TermList, name)
    ]
    if missing:
        raise RuntimeError(f"{experiment}: required production API unavailable: {', '.join(missing)}")


def dispatch(config: Row) -> List[Row]:
    """Dispatch copied experiments inside a measurement worker."""
    experiment = config["experiment"]
    if experiment == "selftest":
        return [selftest()]
    if experiment == "pilot":
        run_structural_pilot()
        return [{"status": "ok"}]
    if experiment == "profile":
        return [profile_operation(config)]
    if experiment == "e4-precheck":
        return [sample_nonblocking(config)]
    if experiment in ("e1", "e2"):
        return [
            eliminate(
                synthetic(config),
                config["direction"],
                enforce_counts=experiment == "e1" and config["direction"] == "refinement",
            )[1]
        ]
    if experiment == "e3":
        return [aeb_compose(config["simplify"])[1] if config["baseline"].startswith("CAVE-") else unrolled(config)]
    if experiment == "e4":
        gc.collect()
        started = perf_counter()
        rows = fuzz(config)
        elapsed = perf_counter() - started
        for row in rows:
            for key in list(row):
                if key.endswith("_seconds") or key in ("seconds", "qe_share"):
                    row[key] = ""
            row.update(
                cold_seconds="",
                seconds="",
                scan_seconds=elapsed,
                timing_scope="non-timing oracle scan shared by both directions",
            )
        return rows
    if experiment == "e5":
        return [chain(config)]
    if experiment == "e6":
        return [automata(config)]
    if experiment == "e8":
        return aeb_application()
    if experiment == "e7":
        return [ablation(config)]
    raise ValueError(f"unknown experiment {experiment}")


def worker(config: Row, connection: Any) -> None:
    """Import dependencies once, run cold then warm in the same fresh process."""
    global _REPORTER
    phase = "setup"

    def report(row: Row) -> None:
        # Cold subphase metrics never masquerade as warm measurements.
        message = {f"cold_{key}": value for key, value in row.items()} if phase == "cold" else dict(row)
        connection.send({"partial": {**message, "active_phase": phase}})

    _REPORTER = report
    cold: List[Row] = []
    try:
        # The supervisor never calls this loader.
        if config["experiment"] != "e4-precheck":
            _load_dependencies()
            require_api(config["experiment"])
            random.seed(config.get("seed", 0))
            z3.set_param("smt.random_seed", int(config.get("seed", 0)) % (1 << 31))
            z3.set_param("sat.random_seed", int(config.get("seed", 0)) % (1 << 31))
        gc.collect()
        if config["experiment"] in ("e4", "e4-precheck", "selftest", "pilot", "profile"):
            phase = "diagnostic" if config["experiment"] != "e4" else "oracle"
            rows = dispatch(config)
        else:
            phase = "cold"
            cold = dispatch({**config, "_warm_call": False})
            connection.send({"partial": {"cold_rows_json": json.dumps(cold), "active_phase": "warm"}})
            if any(row.get("status", "ok") != "ok" for row in cold):
                rows = [
                    {**row, "cold_seconds": row.get("seconds", ""), "seconds": "", "active_phase": "cold"}
                    for row in cold
                ]
            else:
                phase = "warm"
                gc.collect()
                rows = dispatch({**config, "_warm_call": True})
                if len(rows) != len(cold):
                    raise RuntimeError("cold/warm operation returned different numbers of rows")
                for row, first in zip(rows, cold):
                    row.update(
                        {
                            f"cold_{key}": value
                            for key, value in first.items()
                            if key not in ("status", "error", "traceback", "scope", "direction")
                        }
                    )
                    row["cold_seconds"] = first["seconds"]
                    row["active_phase"] = "complete"
        for row in rows:
            row.setdefault("status", "ok")
        connection.send(rows)
    except Exception as error:
        connection.send(
            [
                {
                    "status": "error",
                    "error": f"{config['experiment']} {phase}: {type(error).__name__}: {error}",
                    "traceback": traceback.format_exc(),
                    "active_phase": phase,
                    "cold_rows_json": json.dumps(cold),
                }
            ]
        )
    finally:
        connection.close()


def supervisor(config: Row, timeout: float, connection: Any) -> None:
    """Fresh parent per run: hard timeout and genuine per-child peak RSS."""
    import signal

    def terminate(signum: int, frame: Any) -> None:
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, terminate)
    context = mp.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=worker, args=(config, sender))
    started = perf_counter()
    rows: Optional[List[Row]] = None
    partial: Row = {}
    try:
        process.start()
        sender.close()
        deadline = started + timeout
        while perf_counter() < deadline:
            if receiver.poll(min(0.1, max(0, deadline - perf_counter()))):
                try:
                    message = receiver.recv()
                except EOFError:
                    break
                if isinstance(message, dict) and "partial" in message:
                    partial.update(message["partial"])
                    continue
                rows = [{**partial, **row} for row in message]
                process.join(max(0, deadline - perf_counter()))
                if process.is_alive():
                    rows = None
                break
            if not process.is_alive():
                break
        if rows is None:
            timed_out = process.is_alive() or perf_counter() >= deadline
            rows = [
                {
                    **partial,
                    "status": "timeout" if timed_out else "error",
                    "seconds": timeout if timed_out else perf_counter() - started,
                    "error": "hard child deadline" if timed_out else f"worker exit code {process.exitcode}",
                }
            ]
    finally:
        if process.pid is not None:
            if process.is_alive():
                process.kill()
            process.join()
        receiver.close()
        sender.close()
    rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss if resource is not None else None
    for row in rows or []:
        row["peak_rss_bytes"] = int(rss if sys.platform == "darwin" else rss * 1024) if rss is not None else None
        row["supervisor_seconds"] = perf_counter() - started
        row["rss_method"] = (
            "fresh-supervisor RUSAGE_CHILDREN.ru_maxrss" if rss is not None else "unavailable on this platform"
        )
    connection.send(rows)
    connection.close()


def isolated(config: Row, timeout: float) -> List[Row]:
    """Start an isolated supervisor and clean up on interruption or failure."""
    context = mp.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=supervisor, args=(config, timeout, sender))
    started = perf_counter()
    try:
        process.start()
        sender.close()
        heartbeat = started
        while process.is_alive() or receiver.poll():
            if receiver.poll(0.2):
                try:
                    return receiver.recv()
                except EOFError:
                    break
            now = perf_counter()
            if now - heartbeat >= 30:
                print(f"  still running {config['experiment']} ({now - started:.0f}s including startup)", flush=True)
                heartbeat = now
            if now - started > timeout + 20:
                return [
                    {
                        "status": "timeout",
                        "seconds": timeout,
                        "error": "supervisor startup/cleanup deadline",
                        "rss_method": "unavailable",
                    }
                ]
        return [{"status": "error", "error": f"supervisor exited {process.exitcode}"}]
    finally:
        if process.pid is not None:
            process.join(0.2)
            if process.is_alive():
                process.terminate()  # Supervisor's handler reaps the worker.
                process.join(3)
            if process.is_alive():
                process.kill()
                process.join()
        receiver.close()
        sender.close()


def configurations(experiment: str, args: argparse.Namespace) -> List[Row]:
    """Construct deterministic parameter grids before the seeded shuffle."""
    base = {"n_p": 2, "n_I": 2, "n_J": 2, "D": 1}
    configs: List[Row] = []
    if experiment in ("e1", "e2"):
        families = ["substitution"] if experiment == "e1" else ["bool-bound", "lra"]
        directions = ["refinement", "relaxation"]
        for family, direction in itertools.product(families, directions):
            for parameter in base:
                values: Tuple[int, ...] = (0, 1) if parameter == "D" else (1, 2)
                if not args.quick:
                    values = tuple(range(6)) if parameter == "D" else (1, 2, 4, 6, 8)
                for value in values:
                    configs.append(
                        {
                            **base,
                            parameter: value,
                            "family": family,
                            "direction": direction,
                            "sweep": parameter,
                            "parameter_value": value,
                        }
                    )
        if experiment == "e2":
            for n, depth, direction in itertools.product(
                (1, 2) if args.quick else (1, 2, 4, 6), (0, 1) if args.quick else range(5), directions
            ):
                configs.append(
                    {
                        **base,
                        "n_p": n,
                        "D": depth,
                        "family": "bool-bound",
                        "direction": direction,
                        "sweep": "grid",
                        "parameter_value": f"{n}x{depth}",
                    }
                )
    elif experiment == "e3":
        configs = [
            {"baseline": "unrolled-Z3-qe2", "T": t, "projection": projection, "liveness_dropped": True}
            for t in ((1, 2, 3, 4) if args.quick else (1, 2, 3, 4, 6, 8, 12, 16))
            for projection in ("requested-five", "interface-matched-four")
        ]
        configs.extend(
            {
                "baseline": f"CAVE-simplify-{str(flag).lower()}",
                "simplify": flag,
                "projection": "production-interface",
                "liveness_dropped": False,
            }
            for flag in (True, False)
        )
    elif experiment == "e4":
        sources = ("uniform", "nonblocking") if args.e4_source == "both" else (args.e4_source,)
        for source, n_int in itertools.product(sources, range(1, args.n_int + 1)):
            for index in range(args.instances):
                digest = hashlib.sha256(f"{args.seed}:{n_int}:{index}".encode()).hexdigest()
                config = {"instance_id": index, "n_int": n_int, "ext": args.ext, "quick": args.quick, "source": source}
                if source == "uniform":
                    config.update(
                        instance_seed=int(digest[:16], 16),
                        seed_stream_id=f"{args.seed}:{n_int}:uniform",
                        seed_stream_index=index,
                        rejected_draws=0,
                        nonblocking_checked_on="",
                    )
                configs.append(config)
    elif experiment == "e5":
        configs = [{"N": n, "order": "left-fold"} for n in ((1, 2, 3) if args.quick else (1, 2, 3, 4, 5, 6, 8))]
        configs.extend({"N": n, "order": "balanced"} for n in ((4,) if args.quick else (4, 8)))
    elif experiment == "e6":
        configs = [
            {"family": "bool-bound", "direction": "refinement", "n_p": n, "D": depth, "n_I": 1, "n_J": 1}
            for n, depth in itertools.product((1, 2) if args.quick else (1, 2, 3), (0, 1))
        ]
    elif experiment == "e8":
        configs = [{"family": "aeb", "operation": "compose-clearance-and-target-quotient", "simplify": True}]
    else:
        configs = [
            {**base, "family": family, "direction": "refinement", "ablation": variant}
            for family, variant in itertools.product(
                ("aeb", "bool-bound"),
                (
                    "ablation_production",
                    "ablation_synthetic_only",
                    "ablation_qe",
                    "ablation_qe_rec",
                    "ablation_simplify_false",
                ),
            )
        ]
    for config in configs:
        config.update(experiment=experiment, seed=args.seed)
    rng = random.Random(args.seed + int(experiment[1:]))
    grouped: Dict[str, List[Row]] = defaultdict(list)
    for config in configs:
        key, _escalation_value = escalation_key(config)
        grouped[key or json.dumps(config, sort_keys=True)].append(config)
    batches = list(grouped.values())
    rng.shuffle(batches)
    return [config for batch in batches for config in sorted(batch, key=lambda c: escalation_key(c)[1])]


def escalation_key(config: Row) -> Tuple[str, float]:
    """Order values ascending inside independently randomized sweep groups."""
    experiment = config["experiment"]
    if experiment in ("e1", "e2"):
        sweep = config["sweep"]
        dimensions = [experiment, config["family"], config["direction"], sweep]
        if sweep == "grid":
            dimensions.append(str(config["n_p"]))
        return ":".join(dimensions), float(config["D"] if sweep == "grid" else config[sweep])
    if experiment == "e3" and config["baseline"] == "unrolled-Z3-qe2":
        return f"e3:{config['projection']}", float(config["T"])
    if experiment == "e5":
        return f"e5:{config['order']}", float(config["N"])
    return "", 0.0


def aggregates(raw: List[Row], expected: int) -> List[Row]:
    """Successful-only quantiles, separate E8 scopes, and explicit skipped counts."""
    grouped: Dict[Tuple[str, str, str], List[Row]] = defaultdict(list)
    for row in raw:
        grouped[str(row["config_id"]), str(row.get("direction", "")), str(row.get("scope", ""))].append(row)
    output = list(raw)
    metric_keys = set(vars(CaveMetrics())) - {"selected_supports", "cumulative_cave_seconds"}
    metric_keys |= {
        "seconds",
        "cave_seconds",
        "peak_rss_bytes",
        "supervisor_seconds",
        "diff_fraction",
        "qe_share",
        "output_z3_dag_nodes",
        "output_cores",
        "exists_states",
        "complement_states",
        "exists_acceptance_sets",
        "complement_acceptance_sets",
    }
    metric_keys |= {f"cold_{key}" for key in list(metric_keys)}
    for rows in grouped.values():
        first = rows[0]
        keys = metric_keys | {key for row in rows for key in row if key.endswith("_seconds")}
        aggregate = {
            key: value
            for key, value in first.items()
            if key not in keys
            and key
            not in (
                "traceback",
                "error",
                "witness_json",
                "instance_json",
                "result_json",
                "steps_json",
                "cold_rows_json",
                "result_a_json",
                "result_g_json",
            )
        }
        successes = [row for row in rows if row["status"] == "ok"]
        counts = {
            status: sum(row["status"] == status for row in rows) for status in ("ok", "timeout", "error", "skipped")
        }
        statuses = {row["status"] for row in rows}
        aggregate.update(
            row_type="aggregate",
            repetition="",
            completed_runs=len(rows),
            successful_runs=counts["ok"],
            timeout_runs=counts["timeout"],
            error_runs=counts["error"],
            skipped_runs=counts["skipped"],
            complete=len(rows) == expected,
            status=next(iter(statuses)) if len(statuses) == 1 else "mixed",
        )
        for key in sorted(keys):
            numbers = [float(row[key]) for row in successes if row.get(key, "") not in ("", None)]
            if numbers:
                aggregate.update({f"{key}_{stat}": value for stat, value in _distribution(numbers).items()})
        if first["experiment"] == "e4":
            for classification in ("exact", "conservative", "unsound"):
                aggregate[f"{classification}_count"] = sum(
                    row.get("classification") == classification for row in successes
                )
        output.append(aggregate)
    return output


def atomic_csv(path: Path, rows: Sequence[Row]) -> None:
    """Flush and fsync a replacement in the same directory, then rename."""
    columns = sorted({key for row in rows for key in row})
    temporary = path.with_suffix(".csv.tmp")
    try:
        with temporary.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


class IdentityError(ValueError):
    """Argument/checkpoint incompatibility, distinct from experiment failures."""


def effective_protocol(experiment: str, args: argparse.Namespace) -> Tuple[int, float]:
    """Resolve preset defaults and explicit overrides independently per experiment."""
    repetitions = args.repetitions
    if repetitions is None:
        repetitions = (
            1
            if args.quick
            else (
                5
                if args.preset == "paper" and experiment == "e2"
                else (3 if args.preset == "paper" and experiment == "e5" else 10)
            )
        )
    if experiment == "e4":
        repetitions = 1
    timeout = args.timeout
    if timeout is None:
        timeout = 30.0 if args.quick else 300.0 if args.preset == "paper" and experiment == "e5" else 600.0
    return repetitions, timeout


def row_defaults() -> Row:
    """Keep unavailable fields explicit even in failure-only experiment CSVs."""
    fields = set(vars(CaveMetrics())) - {"cumulative_cave_seconds"}
    fields |= {
        "seconds",
        "cave_seconds",
        "cold_seconds",
        "qe_share",
        "peak_rss_bytes",
        "output_cores",
        "output_z3_dag_nodes",
        "liveness_projections",
        "liveness_projections_expected",
        "liveness_projections_match",
    }
    fields |= {f"cold_{key}" for key in list(fields) if not key.startswith("cold_")}
    return {key: "" for key in fields}


def run_sweep(experiment: str, args: argparse.Namespace, environment: Row) -> Row:
    """One protocol, atomic per-run persistence, adaptive stopping and stable resume."""
    if experiment == "e6" and not spot_available():
        print("SKIPPED: spot not available (requires Spot automata bindings and buddy)", flush=True)
        return {"status": "skipped", "reason": "spot not available"}
    path = args.output_dir / f"{experiment}.csv"
    expected, timeout = effective_protocol(experiment, args)
    identity_base = {
        **environment,
        "schema_version": SCHEMA_VERSION,
        "timing_protocol": TIMING_PROTOCOL,
        "experiment": experiment,
        "seed": args.seed,
        "measured_repetitions": expected,
        "timeout": timeout,
    }
    digest = hashlib.sha256(json.dumps(identity_base, sort_keys=True).encode()).hexdigest()
    raw: List[Row] = []
    if path.exists():
        if not args.resume:
            raise IdentityError(f"{path} exists; use --resume or a fresh --output-dir")
        with path.open(newline="", encoding="utf-8") as stream:
            raw = [dict(row) for row in csv.DictReader(stream) if row["row_type"] == "raw"]
        if any(row.get("run_identity") != digest for row in raw):
            raise IdentityError(f"{path}: incompatible environment, source, seed, timeout or repetitions")
    configs = configurations(experiment, args)
    stopped = set()
    for order_index, requested in enumerate(configs):
        parameters = json.dumps(requested, sort_keys=True)
        config_id = hashlib.sha256(parameters.encode()).hexdigest()[:24]
        existing = [row for row in raw if row["config_id"] == config_id]
        group, _value = escalation_key(requested)
        key = "direction" if experiment == "e4" else "scope" if experiment == "e8" else None
        labels = (
            ("refinement", "relaxation")
            if experiment == "e4"
            else (("composition", "quotient", "combined") if experiment == "e8" else ("",))
        )
        completed = set()
        for repetition in range(1, expected + 1):
            matches = [row for row in existing if int(row["repetition"]) == repetition]
            if matches:
                actual = {row.get(key, "") for row in matches} if key else {""}
                if len(matches) != len(labels) or actual != set(labels):
                    raise IdentityError(f"damaged/duplicate checkpoint {config_id}, repetition {repetition}")
                completed.add(repetition)
        print(f"{experiment} [{order_index + 1}/{len(configs)}] {parameters}", flush=True)
        if len(completed) == expected:
            if group and existing and all(row["status"] == "timeout" for row in existing):
                stopped.add(group)
            print("  complete: skipped", flush=True)
            continue
        config = dict(requested)
        selection_error: Optional[Row] = None
        if experiment == "e4" and config["source"] == "nonblocking":
            try:
                selected = isolated({**config, "experiment": "e4-precheck"}, min(timeout, 60.0))[0]
                if selected["status"] != "ok":
                    selection_error = {**selected, "active_phase": "nonblocking-precheck"}
                else:
                    config.update(
                        {
                            k: v
                            for k, v in selected.items()
                            if k
                            in (
                                "instance_seed",
                                "seed_stream_id",
                                "seed_stream_index",
                                "rejected_draws",
                                "nonblocking_checked_on",
                            )
                        }
                    )
            except Exception as error:
                selection_error = {"status": "error", "error": str(error), "traceback": traceback.format_exc()}
        for repetition in range(1, expected + 1):
            if repetition in completed:
                continue
            print(
                f"  run {repetition}/{expected}: "
                + ("oracle only" if experiment == "e4" else "fresh worker, cold call then warm call"),
                flush=True,
            )
            try:
                if group in stopped:
                    results = [
                        {
                            "status": "skipped",
                            "skip_reason": "smaller configuration timed out",
                            "seconds": "",
                            "cold_seconds": "",
                        }
                    ]
                elif selection_error:
                    results = [selection_error]
                else:
                    results = isolated(config, timeout)
            except Exception as error:
                results = [
                    {
                        "status": "error",
                        "error": f"{experiment}: {type(error).__name__}: {error}",
                        "traceback": traceback.format_exc(),
                    }
                ]
            for result in results:
                # A timeout in the warm call still leaves a completed cold call: keep its time.
                if not key and result.get("status") != "ok" and result.get("cold_seconds", "") in ("", None):
                    try:
                        first = json.loads(result.get("cold_rows_json") or "[]")
                    except ValueError:
                        first = []
                    if len(first) == 1 and first[0].get("status", "ok") == "ok":
                        result["cold_seconds"] = first[0].get("seconds", "")
            if key and len(results) == 1 and key not in results[0]:
                failure = results[0]
                cold = json.loads(failure.get("cold_rows_json") or "[]")
                results = []
                for label in labels:
                    row = {**failure, key: label}
                    first = next((item for item in cold if item.get(key) == label), None)
                    if first is not None:
                        row["cold_seconds"] = first.get("seconds", "")
                    results.append(row)
            common = {
                **row_defaults(),
                **environment,
                **config,
                "schema_version": SCHEMA_VERSION,
                "row_type": "raw",
                "config_id": config_id,
                "run_identity": digest,
                "parameters_json": parameters,
                "cli_json": json.dumps(vars(args), default=str, sort_keys=True),
                "order_index": order_index,
                "repetition": repetition,
                "measured_repetitions": expected,
                "timeout": timeout,
                "timing_protocol": TIMING_PROTOCOL,
                "warmup_count": 0 if experiment == "e4" else 1,
            }
            for result in results:
                if experiment == "e4":
                    result["seconds"] = result["cold_seconds"] = ""
                raw.append({**common, **result})
                if result["status"] != "ok":
                    print(f"  {result['status']}: {result.get('error', result.get('skip_reason', ''))}", flush=True)
            atomic_csv(path, aggregates(raw, expected))
            print(f"  saved {path}", flush=True)
        finished = [row for row in raw if row["config_id"] == config_id]
        if group and len(finished) == expected and all(row["status"] == "timeout" for row in finished):
            stopped.add(group)
    return {
        "status": "complete",
        **{
            f"{status}_rows": sum(row["status"] == status for row in raw)
            for status in ("ok", "timeout", "error", "skipped")
        },
    }


def atomic_json(path: Path, payload: Row) -> None:
    """Atomically update the manifest using the same persistence convention."""
    temporary = path.with_suffix(".json.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True, default=str)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def provenance() -> Row:
    """Copy the old environment metadata and add sources/optional library versions."""
    environment: Row = dict(_environment_metadata())
    paths = (
        Path(__file__),
        ROOT / "examples/aeb_gr1_composition.py",
        Path(gr1.__file__),
        Path(gr1.__file__).with_name("iocontract.py"),
    )

    def label(path: Path) -> str:
        """Repository-relative name when possible, absolute otherwise (e.g. site-packages)."""
        try:
            return str(path.resolve().relative_to(ROOT))
        except ValueError:
            return str(path.resolve())

    digests = {label(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths if path.exists()}
    environment["source_digests_json"] = json.dumps(digests, sort_keys=True)
    environment["source_sha256"] = hashlib.sha256(environment["source_digests_json"].encode()).hexdigest()
    environment["spot_available"] = spot_available()
    for module in ("spot", "buddy"):
        try:
            imported = __import__(module)
            environment[f"{module}_version"] = str(getattr(imported, "__version__", "unknown"))
        except Exception:
            environment[f"{module}_version"] = "unavailable"
    return environment


def resolved_plan(selected: List[str], args: argparse.Namespace) -> Row:
    """Print exact grids, batch sizes, seeds and per-experiment protocol settings."""
    plan: Row = {
        "preset": args.preset or "custom",
        "seed": args.seed,
        "timing_protocol": TIMING_PROTOCOL,
        "order": "seeded sweep order; ascending values inside sweeps",
        "selftest_timeout": max(120.0, args.timeout if args.timeout is not None else 120.0),
        "experiments": {},
    }
    for experiment in selected:
        reps, timeout = effective_protocol(experiment, args)
        configs = configurations(experiment, args)
        details: Row = {
            "configurations": len(configs),
            "repetitions": reps,
            "timeout": timeout,
            "worker_launches_upper_bound": len(configs) * reps
            + (len(configs) if experiment == "e4" and args.e4_source != "uniform" else 0),
        }
        if experiment == "e4":
            details.update(
                instances_per_source_and_batch=args.instances,
                source=args.e4_source,
                external_variables=args.ext,
                internal_batches=list(range(1, args.n_int + 1)),
                lasso_prefix_max=1 if args.quick else 2,
                lasso_cycle_max=2 if args.quick else 3,
                precheck_timeout=min(timeout, 60.0),
                warmup_count=0,
            )
        else:
            details["grid"] = [
                {k: v for k, v in config.items() if k not in ("seed", "experiment")} for config in configs
            ]
            details["warmup_count"] = 1
        plan["experiments"][experiment] = details
    return plan


def main() -> None:
    """Resolve arguments first; help and multiprocessing imports stay import-light."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    labels = [
        "original synthetic, both directions",
        "harder Boolean/LRA families and grid",
        "AEB unrolled baseline",
        "soundness/precision oracle",
        "well-conditioned chain composition",
        "optional exact Spot baseline",
        "local ablations",
        "AEB compose then quotient",
    ]
    for index, label in enumerate(labels, 1):
        parser.add_argument(f"--e{index}", action="store_true", help=label)
    parser.add_argument("--all", action="store_true", help="run E1--E8")
    parser.add_argument("--synthetic", action="store_true", help="legacy alias for --e1")
    parser.add_argument("--aeb", action="store_true", help="legacy alias for --e8")
    parser.add_argument(
        "--selftest", action="store_true", help="known answers and p-free regression; default limit 120s"
    )
    parser.add_argument("--pilot", action="store_true", help="copied structural diagnostic, excluded from CSVs")
    parser.add_argument(
        "--profile", action="store_true", help="three isolated cProfile diagnostics, excluded from eN.csv"
    )
    parser.add_argument("--preset", choices=("quick", "paper"), help="select and print an exact preset; alone runs all")
    parser.add_argument("--quick", action="store_true", help="legacy alias for --preset quick")
    parser.add_argument(
        "--repetitions",
        type=int,
        default=None,
        help="override all timing repetitions (default 10; quick 1; paper E2=5, E5=3; E4 always 1)",
    )
    parser.add_argument(
        "--timeout", type=float, default=None, help="override per-worker limit (default 600s; quick 30s; paper E5 300s)"
    )
    parser.add_argument("--seed", type=int, default=0, help="seed for formulas, solver, hashing and sweep order")
    parser.add_argument(
        "--instances", type=int, default=None, help="E4 kept instances per source/batch (2000; quick 100)"
    )
    parser.add_argument("--ext", type=int, default=2, help="E4 external Boolean variables (default 2)")
    parser.add_argument(
        "--int",
        dest="n_int",
        type=int,
        choices=(1, 2),
        default=None,
        help="maximum E4 hidden-bit batch (default: 2 for --preset paper, otherwise 1)",
    )
    parser.add_argument(
        "--e4-source",
        choices=("uniform", "nonblocking", "both"),
        default="both",
        help="uniform generator, quick-lasso rejection sampling, or both (default)",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("experiment_out"), help="CSV/manifest directory")
    parser.add_argument("--resume", action="store_true", help="validate identities and skip completed configurations")
    args = parser.parse_args()
    if args.quick and args.preset == "paper":
        parser.error("--quick conflicts with --preset paper")
    if args.quick:
        args.preset = "quick"
    args.quick = args.preset == "quick"
    if args.instances is None:
        args.instances = 100 if args.quick else 2000
    if args.n_int is None:
        args.n_int = 2 if args.preset == "paper" else 1
    if args.instances < 1 or args.ext < 1 or (args.repetitions is not None and args.repetitions < 1):
        parser.error("counts must be positive")
    if args.timeout is not None and (not math.isfinite(args.timeout) or args.timeout <= 0):
        parser.error("--timeout must be positive and finite")
    args.e1 |= args.synthetic
    args.e8 |= args.aeb
    selected = [f"e{i}" for i in range(1, 9) if args.all or getattr(args, f"e{i}")]
    if not selected and args.preset and not (args.selftest or args.pilot or args.profile):
        selected = [f"e{i}" for i in range(1, 9)]
    if not selected and not (args.selftest or args.pilot or args.profile):
        parser.error("select a preset, experiment, --all, --selftest, --pilot or --profile")
    os.environ["PYTHONHASHSEED"] = str(args.seed % (1 << 32))
    plan = resolved_plan(selected, args)
    print(json.dumps(plan, indent=2, sort_keys=True), flush=True)
    _load_dependencies()
    environment = provenance()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "MANIFEST.json"
    history = []
    if manifest_path.exists():
        with manifest_path.open(encoding="utf-8") as stream:
            previous = json.load(stream)
        history = previous.get("history", []) + [{k: v for k, v in previous.items() if k != "history"}]
    manifest: Row = {
        **environment,
        "schema_version": SCHEMA_VERSION,
        "command_line": sys.argv,
        "preset": args.preset or "custom",
        "seed": args.seed,
        "plan": plan,
        "start_time_utc": datetime.now(timezone.utc).isoformat(),
        "end_time_utc": None,
        "status": "running",
        "history": history,
        "experiments": {},
    }
    atomic_json(manifest_path, manifest)
    try:
        for diagnostic in ("selftest", "pilot"):
            if getattr(args, diagnostic):
                limit = plan["selftest_timeout"] if diagnostic == "selftest" else effective_protocol("e1", args)[1]
                result = isolated({"experiment": diagnostic, "seed": args.seed}, limit)[0]
                manifest[diagnostic] = result
                if result["status"] != "ok":
                    print(json.dumps(result, indent=2), flush=True)
                    raise RuntimeError(f"{diagnostic} failed; see MANIFEST.json")
        if args.profile:
            profile_rows = []
            for name in ("aeb_simplify_true", "aeb_simplify_false", "chain_n3"):
                result = isolated(
                    {"experiment": "profile", "profile_name": name, "seed": args.seed},
                    args.timeout if args.timeout is not None else 600.0,
                )[0]
                report = result.pop("profile_text", json.dumps(result, indent=2))
                (args.output_dir / f"profile_{name}.txt").write_text(report, encoding="utf-8")
                profile_rows.append({**environment, "profile_name": name, **result})
                atomic_csv(args.output_dir / "profile_summary.csv", profile_rows)
        for experiment in selected:
            manifest["experiments"][experiment] = run_sweep(experiment, args, environment)
            atomic_json(manifest_path, manifest)
        manifest["status"] = "complete"
    except IdentityError as error:
        manifest.update(status="identity-error", error=str(error))
        parser.error(str(error))
    except KeyboardInterrupt:
        manifest["status"] = "interrupted"
        print("Interrupted: completed runs saved. Repeat the command with --resume.", flush=True)
        raise SystemExit(130)
    except Exception as error:
        manifest.update(status="error", error=str(error), traceback=traceback.format_exc())
        raise
    finally:
        manifest["end_time_utc"] = datetime.now(timezone.utc).isoformat()
        atomic_json(manifest_path, manifest)


if __name__ == "__main__":
    main()
