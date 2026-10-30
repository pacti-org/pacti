# pacti/terms/gr1/gr1_iocontract.py
"""Typed GR(1) assume-guarantee contracts with bounded ``next`` formulas.

The public representation separates temporal structure from Boolean/arithmetic
cores.  Each term belongs to one of three buckets:

``INIT(phi)``
    ``phi`` must hold in the first state.
``INV(phi)``
    ``phi`` must hold at every state (the GR(1) formula ``always phi``).
``LIV(phi)``
    ``phi`` must recur infinitely often (``always eventually phi``).

Several terms in a bucket are conjunctive.  Liveness terms deliberately remain
separate: ``LIV(p), LIV(q)`` means that both ``p`` and ``q`` recur, not that
``p`` and ``q`` must recur simultaneously.

Creating a contract from user-facing text
-----------------------------------------
Use :meth:`GR1IoContract.from_dict` and declare every interface variable's
sort.  Formula strings use base interface names; time indices are an internal
implementation detail::

    contract = GR1IoContract.from_dict({
        "input_vars": ["request", "temperature"],
        "output_vars": ["grant"],
        "variable_sorts": {
            "request": "bool",
            "grant": "bool",
            "temperature": "real",
        },
        "assumptions": {
            "init": ["temperature >= 0"],
            "inv": ["temperature <= 100"],
            "liv": ["request"],
        },
        "guarantees": {
            "init": ["!grant"],
            "inv": ["request -> X(grant)"],
            "liv": ["grant"],
        },
    })

User-input naming rule
----------------------
Users must enter and declare **base variable names**, such as ``q``, ``grant``,
and ``temperature``.  Do not enter flattened implementation names such as
``q_0`` or ``q_1`` in ``input_vars``, ``output_vars``, ``variable_sorts``, or
formula strings.  Express temporal depth with the bounded-next operator::

    # Correct user input
    "input_vars": ["q"]
    "variable_sorts": {"q": "bool"}
    "inv": ["r = X(q)", "X(X(q)) -> r"]

    # Incorrect user input: these names are reserved for internal Z3 use
    "input_vars": ["q_0"]
    "variable_sorts": {"q_0": "bool"}
    "inv": ["r_0 = q_1"]

If ``q_0`` is declared as user input, the parser treats the entire string
``q_0`` as a base name and its current-time internal symbol becomes
``q_0_0``.  It does not mean the current value of ``q``.  Therefore always
write ``q`` for the current value, ``X(q)`` for the next value, and
``X(X(q))`` for the value two steps ahead.

Supported core syntax includes ``!``/``not``, ``&``/``and``, ``|``/``or``,
``->``/``=>``, ``<->``, comparisons, exact decimal and rational arithmetic,
parentheses, Boolean
literals, and nested ``X(...)`` or ``next(...)``.  For example,
``X(X(counter)) = counter + 2`` is valid when ``counter`` is an integer.
The outer ``always`` and ``eventually`` operators are supplied by the bucket;
users do not write ``G``, ``F``, or ``U`` inside a core.  Variables must be
declared as ``bool``, ``int``, or ``real`` so parsing and serialization never
guess a sort.

Next-state flattening and names
-------------------------------
The parser retains an immutable :class:`GR1SyntaxNode` tree for structural
renaming and readable serialization, while translating ``p`` to ``p_0``,
``X(p)`` to ``p_1``, and nested next operators to greater depths for Z3.
Contract interfaces always expose the base name ``p``.  Formula bookkeeping,
relevance, elimination, and renaming understand the relationship between a
base name and all of its flattened instances.  Renaming ``p`` to ``r`` thus
renames ``p_0``, ``p_1``, and every other depth without accidental textual
replacement inside unrelated names.

Generated and serialized output follows the same user-facing convention.
For example, a QE result stored internally as ``q_1 == r_0`` is displayed as
``X(q) = r``.  Small mixed Boolean/linear QE formulas additionally undergo a
conservative interval canonicalization: Boolean modes are enumerated, exact
per-mode arithmetic bounds are extracted, and common bounds are factored from
conditioned implications.  A candidate replaces the executable expression
only after Z3 proves it equivalent to the raw QE result. Unsupported formulas
fall back unchanged. ``core.raw_expr`` and :meth:`GR1IoContract.debug_dump`
retain the solver result, while normal printing uses bucket-oriented canonical
formulas and bounded ``X(...)`` syntax. Both forms are preserved in versioned
``gr1_machine`` serialization for lossless restoration.

For programmatic construction, :class:`GR1NextFlattener` provides typed Z3
variables and an ``X`` operation::


    fl = GR1NextFlattener()
    request = fl.Bool("request")
    grant = fl.Bool("grant")
    core = fl.core("request -> X(grant)",
                   z3.Implies(request, fl.X(grant)))

Refinement and relaxation
-------------------------
Variable elimination implements the finite-window CAVE constructions.  INIT
and INV terms are conjoined by bucket before quantifier elimination because
existential quantification does not distribute over conjunction.  Refinement
uses universal implication from the context; relaxation existentially
projects the conjunction of context and target.  Shifted invariant guards are
expanded through the greatest next depth involved, and output variables are
recovered from the resulting Z3 expression itself.  In particular, INV
relaxation uses ``Gamma_inv^[0:h]`` through the target invariant's horizon;
the target and context roles remain distinct so a context relation such as
``p=q`` contributes both ``p_0=q_0`` and ``p_1=q_1`` when needed.

GR(1) composition and quotient operate on canonical bucket obligations.
Generic assumption saturation is contract-redundant when no hidden variable
remains, but conjoining it into generated cores would erase whether a formula
originated as INIT, INV, or a separate LIV liveness term.  A GR(1)-specific algebra
hook therefore preserves those canonical cores in the redundant case, while
falling back to ordinary contextual relaxation whenever assumptions genuinely
aid elimination.  Quotient CAVE similarly keeps divisor guarantees distinct
from system assumptions.

Every target liveness core enters the same complete candidate construction:
``GF psi_i,0`` uses universal implication from the invariant window alone,
and ``G psi_i,j`` uses that window and the j-th context liveness core, for
EVERY j. The synthetic horizon is the target's syntax depth; each genuine
support horizon is the maximum of target and support syntax depths. No
variable-overlap or viability filter precedes projection. Selection prefers a
true core, then a non-false core in canonical synthetic-first order, preserving
temporal tags; it makes no global weakestness or temporal Pareto claim.
Relaxation projects the complete liveness bucket and then removes true,
equivalent, and redundant liveness results. Its standalone decomposed
strongestness applies to the raw construction (``simplify=False``); optional
context-relative simplification is a later representation reduction.
LIV-only simplification also removes a common global next shift,
using ``GF(X^k(phi)) <=> GF(phi)``.  Relative offsets are preserved: liveness
cores ``p_1 & q_2`` and ``p_3 & q_4`` share the canonical core ``p_0 & q_1``,
whereas ``p_1 & q_2`` and ``p_1 & q_3`` remain distinct.  This narrow rule is
not applied to INIT or INV and is not a general LTL simplifier.  Separate
liveness obligations are never merged into one liveness core.

Unicode presentation is intentionally separate from storage. INIT terms may be
displayed as one conjunction, and INV terms may be displayed using
``□phi ∧ □psi = □(phi ∧ psi)``. LIV terms are never placed beneath one shared
``□◇``: in general ``□◇phi ∧ □◇psi`` is not ``□◇(phi ∧ psi)``. These display
choices do not modify :class:`GR1TermList`, serialized text, or machine formulas.
At contract level, the Unicode view may additionally reduce guarantees under
assumptions. Such a display residual is accepted under the contextual condition
``A => (G_internal <=> G_display)``; the full guarantee remains stored and is
used by every semantic operation and serialization API.

Post-CAVE semantic reduction
----------------------------
The six CAVE bounds are evaluated literally before redundancy reduction.  A
separate GR(1)-specific postprocessor may then remove obligations already
established by stronger result buckets.  In particular, ``G(phi)`` establishes
``phi`` at time zero, so an INIT consequence implied by the flattened invariant
bucket can be removed or reduced modulo that context.  Likewise ``G(phi)``
implies ``GF(phi)``; more generally a LIV core is redundant when the finite
shifted invariant closure required by that core implies it.  Every partial INIT
rewrite is guarded by the SMT proof
``Gamma_inv_0 & residual <=> Gamma_inv_0 & original``.  These reductions are
post-processing only, are distinct from assumption-relative guarantee
reduction, and do not constitute a general LTL minimizer.

Operation-produced contracts retain the pre-reduction buckets in an immutable
canonical snapshot.  Later composition, quotient, and CAVE elimination consume
that snapshot, while ``a``/``g`` and Unicode presentation retain the compact
reduced view.  The optional versioned ``gr1_operation_buckets`` serialization
section preserves this distinction across round trips; older dictionaries use
their stored buckets as the canonical fallback.

Persistence and behavior checks
-------------------------------
Human-facing bounded-next text is the primary serialized representation.
Versioned ``gr1_machine`` data preserves Z3-generated QE formulas that no
longer have a parser AST, together with explicit variable sorts, so contracts
round-trip after elimination and renaming.

:class:`GR1Behavior` represents either a finite trace or an ultimately
periodic lasso.  INIT and every complete invariant window can be checked on a
finite trace.  Liveness has trace semantics only when ``loop_start`` identifies
the repeating suffix.  Emptiness is intentionally conservative: inconsistent
initial constraints are detected by SMT, while full infinite-state GR(1)
realizability is outside the scope of :meth:`GR1TermList.is_empty`.
"""

from __future__ import annotations

import copy
import re
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from itertools import product
from typing import (  # noqa: WPS235
    Any,
    Dict,
    FrozenSet,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypedDict,
    Union,
    cast,
)

import z3
from z3.z3util import get_vars

from pacti.iocontract import IoContract, TacticStatistics, Term, TermList, Var
from pacti.utils.errors import IncompatibleArgsError
from pacti.utils.lists import list_union

numeric = Union[int, float]
BehaviorState = Mapping[Union[str, Var], Any]
BehaviorStates = Sequence[BehaviorState]
FormulaVarMap = Dict[str, List[str]]
VariableSortMap = Dict[str, Any]
MachineCorePayload = Optional[Dict[str, Any]]
MachineBucketPayload = Dict[str, List[MachineCorePayload]]
ExactBounds = Tuple[Optional[Any], Optional[Any]]
ValuationBounds = Dict[Any, ExactBounds]
ValuationCase = Tuple[Tuple[bool, ...], Optional[ValuationBounds]]
VariableInput = Union[str, Var]
VariableInputs = Sequence[VariableInput]


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def _conj_text(parts: List[str]) -> str:
    """Render nonempty strings as a parenthesized conjunction, or ``true``.

    Args:
        parts: Formula text fragments to combine.

    Returns:
        The computed str result.
    """
    parts = [p.strip() for p in parts if p and p.strip()]
    if not parts:
        return "true"
    if len(parts) == 1:
        return parts[0]
    return "(" + " & ".join(parts) + ")"


def _implies_text(a: str, b: str) -> str:
    """Render two formula fragments as a parenthesized implication.

    Args:
        a: Left expression or operand.
        b: Right expression or operand.

    Returns:
        The computed str result.
    """
    return f"({_conj_text([a])} -> {_conj_text([b])})"


# ---------------------------------------------------------------------------
# Variable / term helpers
# ---------------------------------------------------------------------------


def _is_shifted_instance(v: Var, base: Var) -> bool:
    """Return True if v is a flattened copy of base.

    Examples:
        p      belongs to base p
        p_0    belongs to base p
        p_1    belongs to base p
        p_12   belongs to base p
        p'     belongs to base p

    But:
        p_aux does not automatically belong to base p.

    Args:
        v: V.
        base: Base variable name.

    Returns:
        The computed bool result.
    """
    name = v.name
    base_name = base.name

    if name == base_name:
        return True

    if name.startswith(base_name + "_"):
        suffix = name[len(base_name) + 1 :]
        return suffix.isdigit()

    return name.startswith(base_name + "'")


# ---------------------------------------------------------------------------
# Z3 helpers
# ---------------------------------------------------------------------------


_USE_FAST_Z3_GET_VARS = True


def _z3_get_vars(f: Any, rs: Optional[List[Any]] = None) -> List[Any]:  # noqa: WPS231
    """Memoize z3.z3util.get_vars with identical output and DFS order.

    Visit each DAG node once by AST identity, but deduplicate constants by
    str(), exactly as the installed collector does (including sort collisions).
    Reversed children preserve its first-occurrence order. Quantifier children
    include the body; bound variables are not constants. Interpreted constants
    are values, matching z3.z3util.is_expr_val. A value root returns rs unchanged.
    Keep these compatibility branches in one traversal (WPS231).

    Args:
        f: Z3 expression whose free constants are collected.
        rs: Optional initial accumulator, preserved without mutation.

    Returns:
        Constants in the same order as z3.z3util.get_vars.
    """
    if not _USE_FAST_Z3_GET_VARS:
        return cast(List[Any], get_vars(f, rs))
    if z3.z3_debug():
        assert z3.is_expr(f)
    initial = [] if rs is None else rs
    if z3.is_const(f) and f.decl().kind() != z3.Z3_OP_UNINTERPRETED:
        return initial
    found: Dict[str, Any] = {}
    for variable in initial:
        found.setdefault(str(variable), variable)
    seen: Set[int] = set()
    stack = [f]
    while stack:
        node = stack.pop()
        identity = node.get_id()
        if identity in seen:
            continue
        seen.add(identity)
        if z3.is_const(node) and node.decl().kind() == z3.Z3_OP_UNINTERPRETED:
            found.setdefault(str(node), node)
        stack.extend(reversed(node.children()))
    return list(found.values())


def _z3_vars_in_expr(expr: Any) -> Dict[str, Any]:
    """Return a name -> Z3 const map for all uninterpreted constants in expr.

        Preserves the Z3 sort, so Bool variables stay Bool, Reals stay Real, etc.

    Args:
        expr: Z3 expression to process.

    Returns:
        The computed Dict[str, Any] result.
    """
    out: Dict[str, Any] = {}
    # GETVARS-PATCH: original (disabled) ---
    # for v in get_vars(expr):
    # GETVARS-PATCH: replacement ---
    for v in _z3_get_vars(expr):
        # GETVARS-PATCH: end ---
        out[v.decl().name()] = v
    return out


def _z3_const_for_name(name: str, *exprs: Any, fallback_sort: Any = None) -> Any:
    """Return a same-named constant using an observed or fallback Z3 sort.

    Args:
        name: Variable name.
        fallback_sort: Sort used when no expression determines the sort.
        *exprs: Z3 expressions to process.

    Returns:
        The computed Any result.
    """
    env: Dict[str, Any] = {}
    for expr in exprs:
        if expr is not None:
            env.update(_z3_vars_in_expr(expr))

    if name in env:
        return env[name]

    if fallback_sort is not None:
        return z3.Const(name, fallback_sort)

    return z3.Real(name)


def _z3_atoms_for_vars(vars_to_elim: List[Var], *exprs: Any) -> List[Any]:
    """Build actual Z3 variables to quantify, preserving the sort used in exprs.

        Variables that do not occur in the expressions are skipped.

    Args:
        vars_to_elim: Variables to eliminate.
        *exprs: Z3 expressions to process.

    Returns:
        The computed List[Any] result.
    """
    env: Dict[str, Any] = {}
    for expr in exprs:
        if expr is not None:
            env.update(_z3_vars_in_expr(expr))

    atoms: List[Any] = []
    for v in vars_to_elim:
        if v.name in env:
            atoms.append(env[v.name])
    return atoms


class GR1SolverError(RuntimeError):
    """A required solver decision or quantifier elimination was unavailable."""


def _contains_quantifier(expr: Any) -> bool:
    """Inspect every subexpression, including nested quantified bodies.

    Args:
        expr: Z3 expression to inspect.

    Returns:
        Whether a quantified subexpression exists.
    """
    pending = [expr]
    seen: Set[int] = set()
    while pending:
        node = pending.pop()
        if node.get_id() in seen:
            continue
        seen.add(node.get_id())
        if z3.is_quantifier(node):
            return True
        pending.extend(node.children())
    return False


def _eliminate_quantifiers(expr: Any) -> Any:
    """Run Z3 quantifier elimination and return one simplified Boolean term.

    Args:
        expr: Z3 expression to process.

    Returns:
        The computed Any result.

    Raises:
        GR1SolverError: The backend fails or does not return one quantifier-free subgoal.
    """
    # Z3's general ``qe`` tactic is stateful for this mixed Boolean/LRA
    # workload: repeated applications to the very same quantified AST can
    # return non-equivalent results.  ``qe2`` implements the required exact
    # finite-window elimination deterministically for these formulas.  This is
    # a solver-backend stability choice; the quantified CAVE bound is unchanged.
    try:
        goals = z3.Tactic("qe2")(expr)
    except z3.Z3Exception as error:
        raise GR1SolverError(f"Quantifier elimination failed: {error}") from error
    if len(goals) != 1:
        raise GR1SolverError(f"Quantifier elimination expected one subgoal, received {len(goals)}")
    simplified = goals[0]
    if any(_contains_quantifier(part) for part in simplified):
        raise GR1SolverError("Quantifier elimination left a residual quantifier; theory may be unsupported")
    if len(simplified) > 0:
        result = z3.simplify(z3.And(*simplified))
        # Keep the established generated-text order for the common projection
        # of a conjunction of Boolean literals.  qe2 emits these literals in
        # reverse AST order compared with qe; sorting this narrow case is
        # semantic no-op and avoids changing the public pretty representation.
        children_are_boolean_constants = all(
            z3.is_const(child) and child.sort() == z3.BoolSort() for child in result.children()
        )
        if z3.is_and(result) and children_are_boolean_constants:
            return z3.And(*sorted(result.children(), key=lambda child: child.sexpr()))
        return result
    return z3.BoolVal(True)


def _qe_forall_refinement(term_expr: Any, context_expr: Any, vars_to_elim: List[Var]) -> Any:
    """Refinement QE:

          ForAll(vars, Implies(context, term))

    Args:
        term_expr: Target term expression.
        context_expr: Context expression guarding the target.
        vars_to_elim: Variables to eliminate.

    Returns:
        The computed Any result.
    """
    atoms = _z3_atoms_for_vars(vars_to_elim, term_expr, context_expr)
    if not atoms:
        return z3.simplify(z3.Implies(context_expr, term_expr))

    full = z3.ForAll(atoms, z3.Implies(context_expr, term_expr))
    return _eliminate_quantifiers(full)


def _qe_exists_relaxation(term_expr: Any, context_expr: Any, vars_to_elim: List[Var]) -> Any:
    """Relaxation QE:

          Exists(vars, And(context, term))

    Args:
        term_expr: Target term expression.
        context_expr: Context expression guarding the target.
        vars_to_elim: Variables to eliminate.

    Returns:
        The computed Any result.
    """
    atoms = _z3_atoms_for_vars(vars_to_elim, term_expr, context_expr)
    if not atoms:
        return z3.simplify(z3.And(context_expr, term_expr))

    full = z3.Exists(atoms, z3.And(context_expr, term_expr))
    return _eliminate_quantifiers(full)


def _is_sat(expr: Any) -> bool:
    """Return whether Z3 can satisfy ``expr``.

    Args:
        expr: Z3 expression to process.

    Returns:
        The computed bool result.

    Raises:
        GR1SolverError: The solver returns unknown or fails.
    """
    try:  # noqa: WPS229 (normalize failures from construction, add and check)
        solver = z3.Solver()
        solver.add(expr)
        result = solver.check()
        if result == z3.unknown:
            raise GR1SolverError(f"Solver could not decide satisfiability: {solver.reason_unknown()}")
        return cast(bool, result == z3.sat)
    except z3.Z3Exception as error:
        raise GR1SolverError(f"Solver satisfiability check failed: {error}") from error


def _implies(a: Any, b: Any) -> bool:
    """Check a => b via UNSAT(a ∧ ¬b).

    Args:
        a: Left expression or operand.
        b: Right expression or operand.

    Returns:
        The computed bool result.

    Raises:
        GR1SolverError: The solver fails; unknown instead returns False.
    """
    try:  # noqa: WPS229 (normalize failures from construction, add and check)
        solver = z3.Solver()
        solver.add(a, z3.Not(b))
        # Unknown means no certificate, never a successful implication.
        return cast(bool, solver.check() == z3.unsat)
    except z3.Z3Exception as error:
        raise GR1SolverError(f"Solver implication check failed: {error}") from error


def _equivalent(a: Any, b: Any) -> bool:
    """Return whether two Z3 formulas imply one another.

    Args:
        a: Left expression or operand.
        b: Right expression or operand.

    Returns:
        The computed bool result.
    """
    return _implies(a, b) and _implies(b, a)


def _expr_semantically_depends_on_bool_var(expr: Any, variable: Any) -> bool:
    """Return whether Boolean ``variable`` can affect the truth of ``expr``.

        Dependence is decided by Boolean cofactors: ``variable`` is irrelevant
        exactly when substituting ``True`` and ``False`` produces equivalent
        formulas.  ``variable`` must be a flattened Z3 Boolean constant such as
        ``q_0`` or ``q_2``.

    Args:
        expr: Z3 expression to process.
        variable: Variable.

    Returns:
        The computed bool result.

    Raises:
        ValueError: If the supplied value is invalid.
    """
    if not z3.is_const(variable) or variable.sort() != z3.BoolSort():
        raise ValueError("Semantic Boolean dependence requires a Boolean Z3 constant")
    when_true = z3.simplify(z3.substitute(expr, (variable, z3.BoolVal(True))))
    when_false = z3.simplify(z3.substitute(expr, (variable, z3.BoolVal(False))))
    return not _equivalent(when_true, when_false)


def _core_semantically_depends_on_eliminated_vars(
    core: "GR1CoreFormula",
    vars_to_elim: List[Var],
) -> bool:
    """Return whether ``core`` depends on an eliminated base at any depth.

    Every actual Z3 variable matching an eliminated base name is inspected.
    Boolean occurrences use exact cofactor equivalence, which ignores merely
    tautological occurrences.  For non-Boolean sorts, syntactic occurrence is
    treated conservatively as dependence; this helper does not claim general
    arithmetic independence checking.

    Args:
        core: GR(1) core formula to process.
        vars_to_elim: Variables to eliminate.

    Returns:
        The computed bool result.
    """
    if core.expr is None:
        return any(_is_shifted_instance(core_var, base_var) for core_var in core.vars for base_var in vars_to_elim)

    for name, variable in _z3_vars_in_expr(core.expr).items():
        if not any(_is_shifted_instance(Var(name), base) for base in vars_to_elim):
            continue
        if variable.sort() != z3.BoolSort():
            return True
        if _expr_semantically_depends_on_bool_var(core.expr, variable):
            return True
    return False


def _drop_irrelevant_eliminated_bool_vars(expr: Any, vars_to_elim: List[Var]) -> Any:
    """Remove irrelevant eliminated Boolean symbols using equivalent cofactors.

        This cleanup is intentionally limited to symbols selected for elimination
        and is used when a LIV target has already been proven semantically free.

    Args:
        expr: Z3 expression to process.
        vars_to_elim: Variables to eliminate.

    Returns:
        The computed Any result.
    """
    current = expr
    for name, variable in list(_z3_vars_in_expr(current).items()):
        if variable.sort() != z3.BoolSort():
            continue
        if not any(_is_shifted_instance(Var(name), base) for base in vars_to_elim):
            continue
        if not _expr_semantically_depends_on_bool_var(current, variable):
            current = z3.simplify(z3.substitute(current, (variable, z3.BoolVal(True))))
    return z3.simplify(current)


def _simplify_expr(expr: Any) -> Any:
    """Equivalence-preserving simplification.

        Do NOT use solve-eqs or goal-based satisfiability tactics here.
        For Boolean formulas like q, solve-eqs can turn q into True by treating
        q as an asserted constraint, which is not formula-equivalent.

    Args:
        expr: Z3 expression to process.

    Returns:
        The computed Any result.
    """
    return z3.simplify(expr)


def _equivalence_guarded_formula(raw_expr: Any, candidate_expr: Any) -> Any:
    """Accept ``candidate_expr`` only after proving equivalence to ``raw_expr``.

    This is the single safety gate for presentation-oriented canonicalization.
    An unsupported, incorrect, or solver-inconclusive candidate can therefore
    never replace the executable formula.

    Args:
        raw_expr: Original formula.
        candidate_expr: Proposed compact formula.

    Returns:
        The simplified candidate when equivalent, otherwise ``raw_expr``.
    """
    candidate = _simplify_expr(candidate_expr)
    return candidate if _equivalent(raw_expr, candidate) else raw_expr


def _exact_bound(expr: Any, variable: Any, minimize: bool) -> Optional[Any]:
    """Return one exact closed Optimize bound, or ``None`` when unsupported.

    Args:
        expr: Formula whose bound is requested.
        variable: Arithmetic variable to optimize.
        minimize: Whether to request the lower rather than upper bound.

    Returns:
        The exact bound when it is closed and finite, otherwise ``None``.
    """
    optimizer = z3.Optimize()
    optimizer.add(expr)
    handle = optimizer.minimize(variable) if minimize else optimizer.maximize(variable)
    if optimizer.check() != z3.sat:
        return None
    bound = optimizer.lower(handle) if minimize else optimizer.upper(handle)
    if isinstance(bound, (z3.IntNumRef, z3.RatNumRef)):
        return bound
    return None


def _bound_key(value: Any) -> Fraction:
    """Convert an exact Z3 numeral to an exact ordering key.

    Args:
        value: Exact integer or rational Z3 numeral.

    Returns:
        Exact fraction suitable for ordering bounds.
    """
    if isinstance(value, z3.IntNumRef):
        return Fraction(value.as_long(), 1)
    return Fraction(value.numerator_as_long(), value.denominator_as_long())


def _valuation_condition(boolean_vars: List[Any], values: Tuple[bool, ...]) -> Any:
    """Build the Boolean cube corresponding to one enumerated valuation.

    Args:
        boolean_vars: Boolean variables in enumeration order.
        values: Truth values matching ``boolean_vars``.

    Returns:
        Conjunction describing the valuation.
    """
    return z3.And(*[variable if value else z3.Not(variable) for variable, value in zip(boolean_vars, values)])


def _interval_constraints(variable: Any, lower: Optional[Any], upper: Optional[Any]) -> List[Any]:
    """Render a closed exact interval, preferring equality for a singleton.

    Args:
        variable: Arithmetic variable constrained by the interval.
        lower: Optional inclusive lower bound.
        upper: Optional inclusive upper bound.

    Returns:
        Z3 constraints representing the interval.
    """
    if lower is not None and upper is not None and _bound_key(lower) == _bound_key(upper):
        return [variable == lower]
    constraints = []
    if lower is not None:
        constraints.append(variable >= lower)
    if upper is not None:
        constraints.append(variable <= upper)
    return constraints


def _rectangular_valuation_cases(
    raw_expr: Any, boolean_vars: List[Any], numeric_vars: List[Any]
) -> Optional[List[Any]]:
    """Extract rectangular bounds for every Boolean valuation.

    Args:
        raw_expr: Simplified mixed formula.
        boolean_vars: Boolean variables to enumerate.
        numeric_vars: Arithmetic variables to bound.

    Returns:
        Valuation/bounds pairs, or ``None`` for a non-rectangular case.
    """
    cases: List[ValuationCase] = []
    for values in product((False, True), repeat=len(boolean_vars)):
        substitutions = [(variable, z3.BoolVal(value)) for variable, value in zip(boolean_vars, values)]
        cofactor = _simplify_expr(z3.substitute(raw_expr, *substitutions))
        if not _is_sat(cofactor):
            cases.append((values, None))
            continue
        bounds = {
            variable: (
                _exact_bound(cofactor, variable, minimize=True),
                _exact_bound(cofactor, variable, minimize=False),
            )
            for variable in numeric_vars
        }
        interval_parts = [
            constraint for variable in numeric_vars for constraint in _interval_constraints(variable, *bounds[variable])
        ]
        if not _equivalent(cofactor, z3.And(*interval_parts)):
            return None
        cases.append((values, bounds))
    return cases


def _global_rectangular_bounds(
    numeric_vars: List[Any], satisfiable_bounds: List[Any]
) -> Tuple[Dict[Any, Any], List[Any]]:
    """Compute the common envelope of satisfiable valuation boxes.

    Args:
        numeric_vars: Arithmetic variables in output order.
        satisfiable_bounds: Bounds for satisfiable valuations.

    Returns:
        Global bounds and their interval constraints.
    """
    global_bounds = {}
    common_parts = []
    for variable in numeric_vars:
        lowers = [bounds[variable][0] for bounds in satisfiable_bounds]
        uppers = [bounds[variable][1] for bounds in satisfiable_bounds]
        global_lower = None if any(value is None for value in lowers) else min(lowers, key=_bound_key)
        global_upper = None if any(value is None for value in uppers) else max(uppers, key=_bound_key)
        global_bounds[variable] = (global_lower, global_upper)
        common_parts.extend(_interval_constraints(variable, global_lower, global_upper))
    return global_bounds, common_parts


def _is_tighter_bound(bound: Optional[Any], global_bound: Optional[Any]) -> bool:
    """Return whether one finite bound tightens a global bound.

    Args:
        bound: Candidate valuation bound.
        global_bound: Shared envelope bound.

    Returns:
        Whether the candidate is present and strictly different.
    """
    return bound is not None and (global_bound is None or _bound_key(bound) != _bound_key(global_bound))


def _valuation_refinements(bounds: Dict[Any, Any], global_bounds: Dict[Any, Any], numeric_vars: List[Any]) -> List[Any]:
    """Return valuation bounds tighter than the global envelope.

    Args:
        bounds: Bounds for one valuation.
        global_bounds: Bounds shared by every valuation.
        numeric_vars: Arithmetic variables in output order.

    Returns:
        Per-valuation refinement constraints.
    """
    refinements = []
    for variable in numeric_vars:
        lower, upper = bounds[variable]
        global_lower, global_upper = global_bounds[variable]
        if _is_tighter_bound(lower, global_lower):
            refinements.append(variable >= lower)
        if _is_tighter_bound(upper, global_upper):
            refinements.append(variable <= upper)
    return refinements


def _conditioned_rectangular_parts(
    cases: List[Any], boolean_vars: List[Any], numeric_vars: List[Any], global_bounds: Dict[Any, Any]
) -> List[Any]:
    """Build exclusions and implications for enumerated valuations.

    Args:
        cases: Valuations paired with optional rectangular bounds.
        boolean_vars: Boolean variables in enumeration order.
        numeric_vars: Arithmetic variables in output order.
        global_bounds: Bounds shared by every valuation.

    Returns:
        Formula parts conditioned on Boolean valuations.
    """
    conditioned_parts = []
    for values, bounds in cases:
        condition = _valuation_condition(boolean_vars, values)
        if bounds is None:
            conditioned_parts.append(z3.Not(condition))
            continue
        refinements = _valuation_refinements(bounds, global_bounds, numeric_vars)
        if refinements:
            conditioned_parts.append(z3.Implies(condition, z3.And(*refinements)))
    return conditioned_parts


def canonicalize_mixed_linear_formula(expr: Any, max_boolean_variables: int = 3) -> Any:
    """Canonicalize a small Boolean-conditioned rectangular linear formula.

    Boolean variables are enumerated up to ``max_boolean_variables``.  In each
    satisfiable valuation, exact Optimize bounds are extracted for every
    remaining Int/Real variable.  The valuation is accepted only when the
    resulting conjunction of intervals is equivalent to that cofactor.  Global
    envelope bounds are factored out and tighter per-mode bounds are rebuilt as
    implications.  Finally, the complete candidate is equivalence-checked.

    The deliberately narrow implementation handles the common QE result in
    which every Boolean mode selects an axis-aligned interval or box.  It is not
    a general linear-arithmetic or Boolean minimizer.  Unsupported sorts,
    nonlinear/non-rectangular regions, strict/open bounds, excessive Boolean
    variables, or inconclusive checks return the original expression unchanged.

    Args:
        expr: Quantifier-free Z3 Boolean expression.
        max_boolean_variables: Maximum number of Boolean valuations to enumerate.

    Returns:
        A compact equivalent formula, or the original formula on fallback.
    """
    raw_expr = _simplify_expr(expr)
    # GETVARS-PATCH: original (disabled) ---
    # variables = sorted(get_vars(raw_expr), key=lambda variable: variable.decl().name())
    # GETVARS-PATCH: replacement ---
    variables = sorted(_z3_get_vars(raw_expr), key=lambda variable: variable.decl().name())
    # GETVARS-PATCH: end ---
    boolean_vars = [variable for variable in variables if variable.sort() == z3.BoolSort()]
    numeric_vars = [variable for variable in variables if variable.sort() in {z3.IntSort(), z3.RealSort()}]
    if len(boolean_vars) > max_boolean_variables or not numeric_vars:
        return raw_expr
    if len(boolean_vars) + len(numeric_vars) != len(variables):
        return raw_expr

    cases = _rectangular_valuation_cases(raw_expr, boolean_vars, numeric_vars)
    if cases is None:
        return raw_expr

    satisfiable_bounds = [bounds for _, bounds in cases if bounds is not None]
    if not satisfiable_bounds:
        return _equivalence_guarded_formula(raw_expr, z3.BoolVal(False))

    global_bounds, common_parts = _global_rectangular_bounds(numeric_vars, satisfiable_bounds)
    conditioned_parts = _conditioned_rectangular_parts(cases, boolean_vars, numeric_vars, global_bounds)

    candidate = z3.And(*(common_parts + conditioned_parts))
    return _equivalence_guarded_formula(raw_expr, candidate)


# def _simplify_expr(expr):
#     import z3

#     g = z3.Goal()
#     g.add(expr)

#     tactic = z3.Then(
#         "simplify",
#         "propagate-values",
#         "ctx-solver-simplify",
#         "solve-eqs",
#         "simplify",
#     )

#     r = tactic(g)

#     if len(r) == 0:
#         return z3.BoolVal(True)

#     exprs = []
#     for subgoal in r:
#         if len(subgoal) == 0:
#             exprs.append(z3.BoolVal(True))
#         else:
#             exprs.append(z3.And(*subgoal))

#     return z3.simplify(z3.Or(*exprs)) if len(exprs) > 1 else z3.simplify(exprs[0])


def _and_expr(terms: List["GR1Term"]) -> Any:
    """Conjoin term expressions; by convention the empty conjunction is true.

    Args:
        terms: GR(1) terms to process.

    Returns:
        The computed Any result.
    """
    if not terms:
        return z3.BoolVal(True)
    return z3.And(*[cast(z3.BoolRef, t.core.expr) for t in terms])


def _conjoin_bucket_terms(tag: "GR1Tag", terms: List["GR1Term"]) -> Optional["GR1Term"]:
    """Combine one conjunctive INIT or INV bucket into a single core.

    Args:
        tag: GR(1) temporal bucket tag.
        terms: GR(1) terms to process.

    Returns:
        The computed Optional['GR1Term'] result.

    Raises:
        ValueError: If the supplied value is invalid.
    """
    if not terms:
        return None
    if tag == GR1Tag.LIV:
        raise ValueError("LIV liveness terms must remain separate")
    core = _make_core_from_expr(
        _and_expr(terms),
        text=_conj_text([term.core.text for term in terms]),
        next_depth=max(_core_next_depth(term.core) for term in terms),
    )
    return GR1Term(tag, core)


def _next_text(base: str, depth: int) -> str:
    """Render a base variable at ``depth`` using nested bounded-next syntax.

    Args:
        base: Base variable name.
        depth: Bounded-next depth.

    Returns:
        The computed str result.
    """
    rendered = base
    for _ in range(depth):
        rendered = f"X({rendered})"
    return rendered


def _remove_irrelevant_display_variables(expr: Any) -> Any:
    """Remove Boolean variables with equivalent true and false cofactors.

    Args:
        expr: Simplified Z3 expression.

    Returns:
        The expression without semantically irrelevant Boolean variables.
    """
    current = expr
    # GETVARS-PATCH: original (disabled) ---
    # for variable in list(get_vars(current)):
    # GETVARS-PATCH: replacement ---
    for variable in list(_z3_get_vars(current)):
        # GETVARS-PATCH: end ---
        if variable.sort() == z3.BoolSort():
            when_true = z3.simplify(z3.substitute(current, (variable, z3.BoolVal(True))))
            when_false = z3.simplify(z3.substitute(current, (variable, z3.BoolVal(False))))
            if _equivalent(when_true, when_false):
                current = when_true
    return current


def _display_candidates(expr: Any) -> List[Any]:
    """Return common compact Boolean forms matching an expression's arity.

    Args:
        expr: Z3 expression.

    Returns:
        Candidate compact forms.
    """
    # GETVARS-PATCH: original (disabled) ---
    # all_vars = list(get_vars(expr))
    # GETVARS-PATCH: replacement ---
    all_vars = list(_z3_get_vars(expr))
    # GETVARS-PATCH: end ---
    boolean_vars = [variable for variable in all_vars if variable.sort() == z3.BoolSort()]
    if len(all_vars) == 1 and len(boolean_vars) == 1:
        variable = boolean_vars[0]
        return [variable, z3.Not(variable)]
    if len(all_vars) != 2 or len(boolean_vars) != 2:
        return []
    left, right = boolean_vars
    return [
        left == right,
        left != right,
        z3.Implies(left, right),
        z3.Implies(right, left),
        z3.And(left, right),
        z3.Or(left, right),
    ]


def _minimize_boolean_expr_for_display(expr: Any) -> Any:
    """Find small Boolean display forms without changing the stored formula.

        Quantifier elimination often leaves irrelevant variables in a DNF.  This
        helper removes a Boolean variable when its true and false cofactors are
        equivalent, then recognizes common one- and two-variable formulas.  Every
        rewrite is checked for logical equivalence, so this affects presentation
        only and cannot weaken or strengthen the executable expression.

    Args:
        expr: Z3 expression to process.

    Returns:
        The computed Any result.
    """
    current = _remove_irrelevant_display_variables(z3.simplify(expr))
    for candidate in _display_candidates(current):
        if _equivalent(current, candidate):
            return z3.simplify(candidate)
    return current


def _render_z3_variable(node: Any) -> str:
    """Render one flattened uninterpreted Z3 constant.

    Args:
        node: Z3 variable node.

    Returns:
        User-facing bounded-next variable text.
    """
    base, depth = _parse_flat_name(node.decl().name())
    return _next_text(base, depth)


def _implication_antecedent(literal: Any) -> Optional[Any]:
    """Recover an implication antecedent from an OR literal.

    Args:
        literal: Candidate Boolean literal.

    Returns:
        Antecedent expression, or ``None`` when unsupported.
    """
    if z3.is_const(literal) and literal.sort() == z3.BoolSort():
        return z3.Not(literal)
    if z3.is_not(literal) and z3.is_const(literal.arg(0)) and literal.arg(0).sort() == z3.BoolSort():
        return literal.arg(0)
    return None


def _render_or_implication(node: Any) -> Optional[str]:
    """Render a two-part disjunction as an implication when possible.

    Args:
        node: Candidate Z3 disjunction.

    Returns:
        Implication text, or ``None`` when the shape does not match.
    """
    if not z3.is_or(node) or node.num_args() != 2:
        return None
    left, right = node.children()
    for literal, consequence in ((left, right), (right, left)):
        antecedent = _implication_antecedent(literal)
        if antecedent is None:
            continue
        return f"({_render_z3_user_text(antecedent)} -> {_render_z3_user_text(consequence)})"
    return None


def _render_recognized_z3_node(node: Any) -> Optional[str]:
    """Render a directly recognized Boolean or atomic Z3 node.

    Args:
        node: Z3 syntax node.

    Returns:
        Rendered text, or ``None`` for an operator handled elsewhere.
    """
    renderers = (
        (z3.is_true, lambda value: "true"),
        (z3.is_false, lambda value: "false"),
        (lambda value: z3.is_const(value) and value.decl().kind() == z3.Z3_OP_UNINTERPRETED, _render_z3_variable),
        (lambda value: z3.is_int_value(value) or z3.is_rational_value(value), str),
        (z3.is_not, lambda value: f"!({_render_z3_user_text(value.arg(0))})"),
        (z3.is_and, lambda value: "(" + " & ".join(_render_z3_user_text(child) for child in value.children()) + ")"),
        (z3.is_or, lambda value: "(" + " | ".join(_render_z3_user_text(child) for child in value.children()) + ")"),
        (
            z3.is_implies,
            lambda value: f"({_render_z3_user_text(value.arg(0))} -> {_render_z3_user_text(value.arg(1))})",
        ),
    )
    return next((renderer(node) for predicate, renderer in renderers if predicate(node)), None)


def _render_z3_operator(node: Any) -> Optional[str]:
    """Render a supported arithmetic or comparison operator.

    Args:
        node: Z3 syntax node.

    Returns:
        Rendered operator text, or ``None`` when unsupported.
    """
    operator_by_kind = {
        z3.Z3_OP_EQ: "=",
        z3.Z3_OP_DISTINCT: "!=",
        z3.Z3_OP_LE: "<=",
        z3.Z3_OP_LT: "<",
        z3.Z3_OP_GE: ">=",
        z3.Z3_OP_GT: ">",
        z3.Z3_OP_ADD: "+",
        z3.Z3_OP_SUB: "-",
        z3.Z3_OP_MUL: "*",
        z3.Z3_OP_DIV: "/",
        z3.Z3_OP_IDIV: "/",
    }
    operator = operator_by_kind.get(node.decl().kind())
    if operator is None or node.num_args() < 2:
        return None
    rendered = (_render_z3_user_text(child) for child in node.children())
    return "(" + f" {operator} ".join(rendered) + ")"


def _render_z3_user_text(node: Any) -> str:
    """Render one flattened Z3 syntax node recursively.

    Args:
        node: Z3 syntax node.

    Returns:
        Parseable bounded-next text.
    """
    rendered = _render_or_implication(node)
    if rendered is None:
        rendered = _render_recognized_z3_node(node)
    if rendered is None:
        rendered = _render_z3_operator(node)
    if rendered is not None:
        return rendered
    if node.decl().kind() == z3.Z3_OP_UMINUS:
        return f"-({_render_z3_user_text(node.arg(0))})"
    return str(node)


def _expr_to_user_text(expr: Any) -> str:
    """Render a flattened Z3 expression as parseable bounded-next text.

        ``q_0``, ``q_1``, and ``q_2`` become ``q``, ``X(q)``, and
        ``X(X(q))`` respectively.  The conversion walks the Z3 AST and therefore
        never performs unsafe substring replacement in names such as ``q_aux``.

    Args:
        expr: Z3 expression to process.

    Returns:
        The computed str result.
    """
    readable = _minimize_boolean_expr_for_display(expr)
    return _render_z3_user_text(readable)


def _has_single_outer_parenthesis_pair(text: str) -> bool:
    """Check whether the first parenthesis closes at the end of the text.

    Args:
        text: Parenthesized formula text.

    Returns:
        Whether the outer pair encloses the complete expression.
    """
    depth = 0
    for index, character in enumerate(text):
        depth += int(character == "(")
        depth -= int(character == ")")
        if depth == 0 and index != len(text) - 1:
            return False
    return depth == 0


def _strip_display_outer_parentheses(text: str) -> str:
    """Remove one redundant balanced outer parenthesis pair for display.

    Args:
        text: Formula text to trim.

    Returns:
        Text with a redundant outer pair removed.
    """
    stripped = text.strip()
    if len(stripped) < 2 or stripped[0] != "(" or stripped[-1] != ")":
        return stripped
    if _has_single_outer_parenthesis_pair(stripped):
        return stripped[1:-1].strip()
    return stripped


def _unicode_formula_text(text: str) -> str:
    """Translate parser-style Boolean tokens to Unicode for display only.

    Args:
        text: Formula text to translate.

    Returns:
        Display text using Unicode operators.
    """
    rendered = text
    rendered = rendered.replace("<->", "↔").replace("->", "→")
    rendered = rendered.replace("&&", "∧").replace("||", "∨")
    rendered = re.sub(r"\band\b", "∧", rendered, flags=re.IGNORECASE)
    rendered = re.sub(r"\bor\b", "∨", rendered, flags=re.IGNORECASE)
    rendered = re.sub(r"\bnot\b", "¬", rendered, flags=re.IGNORECASE)
    rendered = re.sub("!(?!=)", "¬", rendered)
    rendered = rendered.replace("&", "∧").replace("|", "∨")
    rendered = rendered.replace("==", "=")
    return _strip_display_outer_parentheses(rendered)


def _unicode_core_text(core: "GR1CoreFormula") -> str:
    """Render one core with bounded-Next syntax and Unicode Boolean operators.

    Args:
        core: Core formula to render.

    Returns:
        Display text for the core.
    """
    if core.syntax is not None or core.expr is None:
        source = core.text
    else:
        source = _expr_to_user_text(core.expr)
    return _unicode_formula_text(source)


def _parenthesized_display_conjunction(parts: List[str]) -> str:
    """Join display-only conjuncts with conservative parentheses.

    Args:
        parts: Conjunct strings to join.

    Returns:
        Parenthesized conjunction text.
    """
    if not parts:
        return "true"
    if len(parts) == 1:
        return parts[0]
    return " ∧ ".join(f"({part})" for part in parts)


def _make_core_from_expr(
    expr: Any,
    text: Optional[str] = None,
    syntax: Optional["GR1SyntaxNode"] = None,
    raw_expr: Optional[Any] = None,
    next_depth: Optional[int] = None,
) -> "GR1CoreFormula":
    """Build a core whose variable metadata exactly matches its Z3 expression.

    Args:
        expr: Z3 expression to process.
        text: Human-readable formula text.
        syntax: Optional parsed syntax tree.
        raw_expr: Original QE expression retained for debugging.
        next_depth: Original finite-window depth before simplification.

    Returns:
        The computed 'GR1CoreFormula' result.
    """
    if next_depth is None:
        # GETVARS-PATCH: original (disabled) ---
        # next_depth = max((_parse_flat_name(v.decl().name())[1] for v in get_vars(expr)), default=0)
        # GETVARS-PATCH: replacement ---
        next_depth = max((_parse_flat_name(v.decl().name())[1] for v in _z3_get_vars(expr)), default=0)
        # GETVARS-PATCH: end ---
    simp_expr = _simplify_expr(expr)
    # GETVARS-PATCH: original (disabled) ---
    # vars_ = [Var(v.decl().name()) for v in get_vars(simp_expr)]
    # GETVARS-PATCH: replacement ---
    vars_ = [Var(v.decl().name()) for v in _z3_get_vars(simp_expr)]
    # GETVARS-PATCH: end ---
    return GR1CoreFormula.of_expr(
        text if text is not None else _expr_to_user_text(simp_expr),
        vars_,
        expr=simp_expr,
        syntax=syntax,
        raw_expr=raw_expr,
        next_depth=next_depth,
    )


def _make_qe_core(raw_expr: Any) -> "GR1CoreFormula":
    """Build a core from QE output while retaining its raw solver formula.

    Args:
        raw_expr: Raw solver expression produced by quantifier elimination.

    Returns:
        Core containing the canonical and raw expressions.
    """
    raw = _simplify_expr(raw_expr)
    canonical = canonicalize_mixed_linear_formula(raw)
    return _make_core_from_expr(canonical, raw_expr=raw)


def _normalize_liv_core_global_shift(core: "GR1CoreFormula") -> "GR1CoreFormula":
    """Canonicalize one liveness core modulo a uniform global Next shift.

        If the minimum flattened depth in ``phi`` is ``k``, every variable
        ``base_d`` is replaced by ``base_(d-k)``.  Z3 sorts are preserved exactly.
        This operation is sound specifically beneath LIV because
        ``GF(X^k(phi))`` and ``GF(phi)`` are equivalent on infinite traces.  It
        must not be used for INIT or INV cores.

    Args:
        core: GR(1) core formula to process.

    Returns:
        The computed 'GR1CoreFormula' result.
    """
    if core.expr is None:
        return core
    # QE may leave a lower-depth Boolean symbol only in a tautological wrapper.
    # Remove such symbols by exact cofactor equivalence before finding d_min.
    expr = core.expr
    for candidate_variable in list(_z3_vars_in_expr(expr).values()):
        if candidate_variable.sort() != z3.BoolSort():
            continue
        if not _expr_semantically_depends_on_bool_var(expr, candidate_variable):
            expr = z3.simplify(z3.substitute(expr, (candidate_variable, z3.BoolVal(True))))

    variables = list(_z3_vars_in_expr(expr).values())
    if not variables:
        return _make_core_from_expr(expr, raw_expr=core.raw_expr)
    parsed = [(_parse_flat_name(item.decl().name()), item) for item in variables]
    min_depth = min(depth for ((_, depth), _) in parsed)
    if min_depth == 0:
        if set(_z3_vars_in_expr(expr)) == set(_z3_vars_in_expr(core.expr)):
            return core
        return _make_core_from_expr(expr, raw_expr=core.raw_expr)
    substitutions = [
        (
            parsed_variable,
            z3.Const(_shifted_name(base, depth - min_depth), parsed_variable.sort()),
        )
        for ((base, depth), parsed_variable) in parsed
    ]
    return _make_core_from_expr(z3.substitute(expr, *substitutions), raw_expr=core.raw_expr)


def _support_viable(gamma_inv_expr: Any, support_expr: Any, target_expr: Any) -> bool:
    """Historical diagnostic SAT check, unused by final Algorithm 1:

          SAT(gamma_inv ∧ gamma_liv,j ∧ phi_i)

        If UNSAT, the context liveness event cannot coincide with the target event
        under the invariant context, but final Algorithm 1 still projects this support.

    Args:
        gamma_inv_expr: Invariant context expression.
        support_expr: Candidate liveness-support expression.
        target_expr: Target expression being supported.

    Returns:
        The computed bool result.
    """
    return _is_sat(z3.And(gamma_inv_expr, support_expr, target_expr))


def _refinement_term_is_dominated(index: int, terms: List["GR1Term"]) -> bool:
    """Check whether one refinement term is strictly stronger than a peer.

    Args:
        index: Candidate index.
        terms: Refinement terms.

    Returns:
        Whether the indexed term is dominated.
    """
    candidate_expr = cast(Any, terms[index].core.expr)
    for other_index, other in enumerate(terms):
        if index == other_index:
            continue
        other_expr = cast(Any, other.core.expr)
        if _implies(candidate_expr, other_expr) and not _implies(other_expr, candidate_expr):
            return True
    return False


def _remove_dominated_refinement_terms(terms: List["GR1Term"]) -> List["GR1Term"]:
    """Historical same-wrapper INV dominance helper, unused by final Algorithm 1.

        If psi_j => psi_k and not psi_k => psi_j, then psi_k is weaker and
        therefore less conservative, so psi_j is dominated and removed.

        If multiple incomparable supports remain, they are kept for the subsequent
        liveness-index selection step.

    Args:
        terms: GR(1) terms to process.

    Returns:
        The computed List['GR1Term'] result.
    """
    return [term for index, term in enumerate(terms) if not _refinement_term_is_dominated(index, terms)]


def _base_var_name(v: Var) -> str:
    """Return the unshifted base name of a flattened GR(1) variable.

    Examples:
        p     -> p
        p_0   -> p
        p_3   -> p
        q_12  -> q

    Args:
        v: V.

    Returns:
        The computed str result.
    """
    base, _ = _parse_flat_name(v.name)
    return base


def _base_var_names_in_core(core: "GR1CoreFormula") -> Set[str]:
    """Return the set of unshifted base-variable names appearing in a core.

    Args:
        core: GR(1) core formula to process.

    Returns:
        The computed Set[str] result.
    """
    return {_base_var_name(v) for v in core.vars}


def _support_relevance_variables(target: "GR1Term", inv_terms: List["GR1Term"]) -> Set[str]:
    """Return the historical overlap diagnostic, unused by final Algorithm 1.

        The historical diagnostic uses

            W_i = Vars(phi_i) union Vars(gamma_inv)

        directly. It does not compute a transitive graph closure through
        overlapping invariant terms.

    Args:
        target: Liveness target term.
        inv_terms: Context invariant terms.

    Returns:
        The base-variable relevance set ``W_i``.
    """
    relevant = set(_base_var_names_in_core(target.core))
    for inv_term in inv_terms:
        relevant.update(_base_var_names_in_core(inv_term.core))
    return relevant


def _associated_liv_supports(
    target: "GR1Term",
    inv_terms: List["GR1Term"],
    liv_terms: List["GR1Term"],
) -> List["GR1Term"]:
    """Compute the syntactically associated context liveness terms for one target

    liveness term.

    Form ``W_i = Vars(phi_i) union Vars(gamma_inv)`` and retain exactly the
    context LIV terms whose variables intersect ``W_i``.
    This historical diagnostic does not filter final Algorithm 1 candidates.

    Args:
        target: Target variable, name, or obligation.
        inv_terms: Invariant terms supplying the context.
        liv_terms: Liveness terms supplying candidate support.

    Returns:
        The computed List['GR1Term'] result.
    """
    relevant = _support_relevance_variables(target, inv_terms)
    return [term for term in liv_terms if relevant.intersection(_base_var_names_in_core(term.core))]


def _select_refinement_support(terms: List["GR1Term"]) -> Optional["GR1Term"]:
    """Select a certificate without comparing mixed temporal wrappers.

        Prefer a provably true core, then a core not proved false, then any
        candidate. Within each tier use synthetic-first canonical support order,
        independent of input order. Return the original tagged candidate with
        its branch provenance. This is not a temporal optimality claim.

    Args:
        terms: GR(1) terms to process.

    Returns:
        The computed Optional['GR1Term'] result.
    """
    if not terms:
        return None
    ordered = sorted(terms, key=_refinement_selection_key)
    for term in ordered:
        if _equivalent(term.core.expr, z3.BoolVal(True)):
            return term
    for term in ordered:
        if not _equivalent(term.core.expr, z3.BoolVal(False)):
            return term
    return ordered[0]


# NEW: Helper class to flatten formulas:
class GR1NextFlattener:
    """
    Helper for constructing GR(1) core formulas with a syntactic next operator X.

    Standard flattened naming convention:
        p      is internally treated as p_0
        X(p)  becomes p_1
        X(X(p)) becomes p_2

    Example:
        fl = GR1NextFlattener()
        P = fl.Bool("p")
        Q = fl.Bool("q")

        expr = fl.X(z3.And(P, fl.X(Q)))
        core = fl.core("X(p & X(q))", expr)

    The expression above is flattened as:
        And(p_1, q_2)

    Notes:
        - X only shifts uninterpreted constants appearing in the Z3 expression.
        - It preserves the Z3 sort of each variable.
        - The result is a normal GR1CoreFormula with explicit flattened Vars.
    """

    def __init__(self, *, current_suffix: str = "_0", next_separator: str = "_"):
        """Create a flattener with configurable current and depth separators.

        Args:
            current_suffix: Suffix representing the current state.
            next_separator: Separator used before a next-state index.
        """
        self.current_suffix = current_suffix
        self.next_separator = next_separator

        # Maps flattened variable name -> Z3 variable.
        self._z3_vars: Dict[str, Any] = {}

        # Maps flattened variable name -> Pacti Var.
        self._vars: Dict[str, Var] = {}

        # Maps original base variable name -> sort.
        self._sorts: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Variable constructors
    # ------------------------------------------------------------------

    def Bool(self, name: str) -> Any:  # noqa: N802
        """Create and return the current-time Boolean ``name_0``.

        Args:
            name: Variable name.

        Returns:
            The computed Any result.
        """
        return self._mk_base_var(name, z3.BoolSort())

    def Real(self, name: str) -> Any:  # noqa: N802
        """Create and return the current-time real ``name_0``.

        Args:
            name: Variable name.

        Returns:
            The computed Any result.
        """
        return self._mk_base_var(name, z3.RealSort())

    def Int(self, name: str) -> Any:  # noqa: N802
        """Create and return the current-time integer ``name_0``.

        Args:
            name: Variable name.

        Returns:
            The computed Any result.
        """
        return self._mk_base_var(name, z3.IntSort())

    # ------------------------------------------------------------------
    # Next operator
    # ------------------------------------------------------------------

    def X(self, expr: Any) -> Any:  # noqa: N802
        """Syntactic next operator.

        Shifts every flattened variable in expr forward by one time step.

        Examples:
            X(p_0) = p_1
            X(q_1) = q_2
            X(p_0 & q_1) = p_1 & q_2

        Args:
            expr: Z3 expression to process.

        Returns:
            The computed Any result.
        """
        substitutions = []

        # GETVARS-PATCH: original (disabled) ---
        # for v in get_vars(expr):
        # GETVARS-PATCH: replacement ---
        for v in _z3_get_vars(expr):
            # GETVARS-PATCH: end ---
            old_name = v.decl().name()
            base, depth = self._parse_flat_name(old_name)
            new_name = self._shifted_name(base, depth + 1)
            new_var = self._mk_flat_var(new_name, v.sort())
            substitutions.append((v, new_var))

        if not substitutions:
            return expr

        return z3.simplify(z3.substitute(expr, *substitutions))

    # ------------------------------------------------------------------
    # Core construction
    # ------------------------------------------------------------------

    def core(self, text: str, expr: Any) -> "GR1CoreFormula":
        """Build a GR1CoreFormula from a flattened Z3 expression.

        Args:
            text: Human-readable formula text.
            expr: Z3 expression to process.

        Returns:
            The computed 'GR1CoreFormula' result.
        """
        vars_ = []
        # GETVARS-PATCH: original (disabled) ---
        # for v in get_vars(expr):
        # GETVARS-PATCH: replacement ---
        for v in _z3_get_vars(expr):
            # GETVARS-PATCH: end ---
            name = v.decl().name()
            vars_.append(Var(name))
            self._vars[name] = Var(name)
            self._z3_vars[name] = v

        return GR1CoreFormula.of_expr(
            text=text,
            vars=vars_,
            expr=expr,
        )

    # ------------------------------------------------------------------
    # Naming helpers
    # ------------------------------------------------------------------

    def _mk_base_var(self, name: str, sort: Any) -> Any:
        """Create the current-time version of a variable.

                User-facing name:
                    p

                Internal flattened name:
                    p_0

        Args:
            name: Variable name.
            sort: Z3 sort of the variable.

        Returns:
            The computed Any result.

        Raises:
            ValueError: The name already has a different sort.
        """
        if name in self._sorts and self._sorts[name] != sort:
            raise ValueError(f"Variable {name!r} already has sort {self._sorts[name]}, not {sort}")
        flat_name = self._shifted_name(name, 0)
        variable = self._mk_flat_var(flat_name, sort)
        self._sorts[name] = sort
        return variable

    def _mk_flat_var(self, flat_name: str, sort: Any) -> Any:
        """Intern one flattened Z3 constant while preserving its sort.

        Args:
            flat_name: Flattened internal variable name.
            sort: Z3 sort of the variable.

        Returns:
            The computed Any result.

        Raises:
            ValueError: The cached constant has a different sort.
        """
        if flat_name in self._z3_vars and self._z3_vars[flat_name].sort() != sort:
            raise ValueError(f"Variable {flat_name!r} already has a conflicting sort")
        if flat_name not in self._z3_vars:
            self._z3_vars[flat_name] = z3.Const(flat_name, sort)
            self._vars[flat_name] = Var(flat_name)
        return self._z3_vars[flat_name]

    def _shifted_name(self, base: str, depth: int) -> str:
        """Construct this flattener's internal name for ``depth``.

        Args:
            base: Base variable name.
            depth: Bounded-next depth.

        Returns:
            The computed str result.
        """
        return f"{base}{self.next_separator}{depth}"

    def _parse_flat_name(self, name: str) -> Tuple[str, int]:
        """Parse flattened variable names.

                Supports:
                    p       -> (p, 0)
                    p_0     -> (p, 0)
                    p_1     -> (p, 1)
                    q_12    -> (q, 12)

                If the name is not in flattened form, treat it as depth 0.

        Args:
            name: Variable name.

        Returns:
            The computed Tuple[str, int] result.
        """
        if self.next_separator not in name:
            return name, 0

        base, maybe_depth = name.rsplit(self.next_separator, 1)

        if maybe_depth.isdigit():
            return base, int(maybe_depth)

        return name, 0


def _parse_flat_name(name: str) -> Tuple[str, int]:
    """Parse flattened variable names.

        Supports:
            p       -> (p, 0)
            p_0     -> (p, 0)
            p_1     -> (p, 1)
            q_12    -> (q, 12)

        If the name is not in flattened form, treat it as depth 0.

    Args:
        name: Variable name.

    Returns:
        The computed Tuple[str, int] result.
    """
    if "_" not in name:
        return name, 0

    base, maybe_depth = name.rsplit("_", 1)

    if maybe_depth.isdigit():
        return base, int(maybe_depth)

    return name, 0


def _shifted_name(base: str, depth: int) -> str:
    """Return the canonical flattened name ``base_depth``.

    Args:
        base: Base variable name.
        depth: Bounded-next depth.

    Returns:
        The computed str result.
    """
    return f"{base}_{depth}"


def _compile_variable_node(
    node: Any, variable_sorts: VariableSortMap, depth: int, expected_sort: Optional[Any] = None
) -> Any:
    del expected_sort

    name = cast(str, node.value)
    return z3.Const(_shifted_name(name, depth), variable_sorts[name])


def _compile_number_node(
    node: Any, variable_sorts: VariableSortMap, depth: int, expected_sort: Optional[Any] = None
) -> Any:
    del variable_sorts, depth

    value = cast(str, node.value)
    is_real = expected_sort == z3.RealSort() or any(marker in value.lower() for marker in (".", "e"))
    return z3.RealVal(value) if is_real else z3.IntVal(value)


def _compile_boolean_node(
    node: Any, variable_sorts: VariableSortMap, depth: int, expected_sort: Optional[Any] = None
) -> Any:
    del expected_sort
    del variable_sorts, depth

    return z3.BoolVal(node.value == "true")


def _compile_next_node(
    node: Any, variable_sorts: VariableSortMap, depth: int, expected_sort: Optional[Any] = None
) -> Any:
    return node.children[0].to_z3(variable_sorts, depth + 1, expected_sort)


def _compile_unary_node(
    node: Any, variable_sorts: VariableSortMap, depth: int, expected_sort: Optional[Any] = None
) -> Any:

    operand = node.children[0].to_z3(variable_sorts, depth, expected_sort)
    if node.value == "not":
        return z3.Not(operand)
    return operand if node.value == "+" else -operand


def _binary_numeric_sort(node: Any, variable_sorts: VariableSortMap) -> Optional[Any]:
    """Infer the numeric sort of a binary arithmetic node.

    Args:
        node: Binary syntax node.
        variable_sorts: Declared variable sorts.

    Returns:
        Inferred numeric sort, if available.
    """
    child_sorts = [_syntax_numeric_sort(child, variable_sorts) for child in node.children]
    if z3.RealSort() in child_sorts:
        return z3.RealSort()
    if z3.IntSort() in child_sorts:
        return z3.IntSort()
    return None


def _leaf_numeric_sort(node: Any, variable_sorts: VariableSortMap) -> Optional[Any]:
    """Infer a variable or number leaf's numeric sort.

    Args:
        node: Variable or number syntax node.
        variable_sorts: Declared variable sorts.

    Returns:
        Inferred numeric sort, if available.
    """
    if node.kind == "variable":
        sort = variable_sorts[cast(str, node.value)]
        return sort if sort in {z3.IntSort(), z3.RealSort()} else None
    value = cast(str, node.value).lower()
    return z3.RealSort() if any(marker in value for marker in (".", "e")) else None


def _syntax_numeric_sort(node: Any, variable_sorts: VariableSortMap) -> Optional[Any]:
    """Infer an arithmetic node's concrete sort without fixing bare numerals.

    Args:
        node: Syntax node to inspect.
        variable_sorts: Declared variable sorts.

    Returns:
        Inferred numeric sort, if available.
    """
    if node.kind in {"variable", "number"}:
        return _leaf_numeric_sort(node, variable_sorts)
    if node.kind in {"next", "unary"}:
        return _syntax_numeric_sort(node.children[0], variable_sorts)
    is_arithmetic = node.kind == "binary" and node.value in {"+", "-", "*", "/"}
    return _binary_numeric_sort(node, variable_sorts) if is_arithmetic else None


def _compile_binary_node(
    node: Any, variable_sorts: VariableSortMap, depth: int, expected_sort: Optional[Any] = None
) -> Any:

    operand_sort = expected_sort
    if node.value in {"=", "!=", "<", "<=", ">", ">=", "+", "-", "*", "/"}:
        inferred = [_syntax_numeric_sort(child, variable_sorts) for child in node.children]
        if z3.RealSort() in inferred:
            operand_sort = z3.RealSort()
        elif operand_sort is None and z3.IntSort() in inferred:
            operand_sort = z3.IntSort()
    left = node.children[0].to_z3(variable_sorts, depth, operand_sort)
    right = node.children[1].to_z3(variable_sorts, depth, operand_sort)
    operations = {
        "and": lambda: z3.And(left, right),
        "or": lambda: z3.Or(left, right),
        "->": lambda: z3.Implies(left, right),
        "<->": lambda: left == right,
        "=": lambda: left == right,
        "!=": lambda: left != right,
        "<": lambda: left < right,
        "<=": lambda: left <= right,
        ">": lambda: left > right,
        ">=": lambda: left >= right,
        "+": lambda: left + right,
        "-": lambda: left - right,
        "*": lambda: left * right,
        "/": lambda: left / right,
    }
    operation = operations.get(cast(str, node.value))
    if operation is None:
        raise ValueError(f"Unknown GR(1) syntax operator: {node.value}")
    return operation()


@dataclass(frozen=True)
class GR1SyntaxNode:
    """Immutable user-facing AST for a bounded-next GR(1) core."""

    kind: str
    value: Optional[str] = None
    children: Tuple["GR1SyntaxNode", ...] = ()

    def next_depth(self, depth: int = 0) -> int:
        """Return the greatest Next nesting preceding a variable leaf.

        Args:
            depth: Current nesting depth.

        Returns:
            Maximum Next depth.
        """
        if self.kind == "variable":
            return depth
        return max(
            (child.next_depth(depth + (self.kind == "next")) for child in self.children),
            default=0,
        )

    def rename(self, source: str, target: str) -> "GR1SyntaxNode":
        """Structurally rename exact variable leaves, including below ``X``.

        Args:
            source: Source variable or name.
            target: Target variable, name, or obligation.

        Returns:
            The computed 'GR1SyntaxNode' result.
        """
        value = target if self.kind == "variable" and self.value == source else self.value
        return GR1SyntaxNode(
            self.kind,
            value,
            tuple(child.rename(source, target) for child in self.children),
        )

    def to_text(self) -> str:
        """Render canonical, user-facing bounded-next formula text.

        Returns:
            The computed str result.

        Raises:
            ValueError: If the supplied value is invalid.
        """
        if self.kind in {"variable", "number", "boolean"}:
            return cast(str, self.value)
        if self.kind == "next":
            return f"X({self.children[0].to_text()})"
        if self.kind == "unary":
            operator = "!" if self.value == "not" else cast(str, self.value)
            return f"{operator}({self.children[0].to_text()})"
        if self.kind == "binary":
            return f"({self.children[0].to_text()} {self.value} {self.children[1].to_text()})"
        raise ValueError(f"Unknown GR(1) syntax-node kind: {self.kind}")

    def to_z3(self, variable_sorts: Dict[str, Any], depth: int = 0, expected_sort: Optional[Any] = None) -> Any:
        """Compile to Z3, flattening variables relative to ``depth``.

        Args:
            variable_sorts: Declared sort for each base variable.
            depth: Bounded-next depth.
            expected_sort: Expected sort inherited from the parent expression.

        Returns:
            The computed Any result.

        Raises:
            ValueError: If the supplied value is invalid.
        """
        compilers = {
            "variable": _compile_variable_node,
            "number": _compile_number_node,
            "boolean": _compile_boolean_node,
            "next": _compile_next_node,
            "unary": _compile_unary_node,
            "binary": _compile_binary_node,
        }
        compiler = compilers.get(self.kind)
        if compiler is None:
            raise ValueError(f"Unknown GR(1) syntax-node kind: {self.kind}")
        return compiler(self, variable_sorts, depth, expected_sort)


@dataclass(frozen=True)
class GR1Behavior:
    """A finite trace or an ultimately-periodic lasso used for behavior checks."""

    states: BehaviorStates
    loop_start: Optional[int] = None

    def __post_init__(self) -> None:
        """Validate the nonempty trace and optional repeating-suffix index.

        Raises:
            ValueError: If the supplied value is invalid.
        """
        if not self.states:
            raise ValueError("A GR(1) behavior must contain at least one state")
        if self.loop_start is not None and (self.loop_start < 0 or self.loop_start >= len(self.states)):
            raise ValueError("loop_start must index a state in the behavior")


def _validated_variable_sort(name: str, declared_sort: Any) -> Any:
    """Validate one base-variable name and normalize its declared Z3 sort.

    Args:
        name: Base-variable name.
        declared_sort: String or Z3 sort declaration.

    Returns:
        The normalized Z3 sort.

    Raises:
        TypeError: If the declaration has an unsupported type.
        ValueError: If the name or sort is unsupported.
    """
    if not re.fullmatch("[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Invalid GR(1) variable name: {name!r}")
    if isinstance(declared_sort, str):
        sort_by_name = {
            "bool": z3.BoolSort(),
            "boolean": z3.BoolSort(),
            "int": z3.IntSort(),
            "integer": z3.IntSort(),
            "real": z3.RealSort(),
        }
        normalized = sort_by_name.get(declared_sort.lower())
        if normalized is None:
            raise ValueError(f"Unsupported sort {declared_sort!r} for {name!r}; expected bool, int, or real")
        return normalized
    if not isinstance(declared_sort, z3.SortRef):
        raise TypeError(f"Sort for {name!r} must be a string or Z3 sort")
    if declared_sort not in {z3.BoolSort(), z3.IntSort(), z3.RealSort()}:
        raise ValueError(f"Unsupported Z3 sort for {name!r}: {declared_sort}")
    return declared_sort


def _compile_parser_syntax(syntax: GR1SyntaxNode, variable_sorts: VariableSortMap, formula_text: str) -> Any:
    """Compile parsed syntax and normalize Z3 type errors to ``ValueError``.

    Args:
        syntax: Parsed core syntax.
        variable_sorts: Declared variable sorts.
        formula_text: Original formula text for diagnostics.

    Returns:
        A Boolean Z3 expression.

    Raises:
        ValueError: If compilation fails or produces a non-Boolean expression.
    """
    try:
        expr = syntax.to_z3(variable_sorts)
    except z3.Z3Exception as error:
        raise ValueError(f"Invalid typed GR(1) formula {formula_text!r}: {error}") from error
    if not z3.is_bool(expr):
        raise ValueError("A GR(1) core must be a Boolean formula")
    return expr


def _parse_identifier_primary(parser: Any, value: str, position: int) -> GR1SyntaxNode:
    """Parse a Boolean literal, next call, or declared variable identifier.

    Args:
        parser: Active recursive-descent parser.
        value: Identifier spelling.
        position: Source position for diagnostics.

    Returns:
        The parsed syntax node.

    Raises:
        ValueError: If the identifier denotes an unsupported call or variable.
    """
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return GR1SyntaxNode("boolean", lowered)
    if lowered in {"x", "next"} and parser._accept("("):
        expr = parser._parse_iff()
        parser._expect(")")
        return GR1SyntaxNode("next", children=(expr,))
    if parser._peek("("):
        raise ValueError(f"Unsupported function {value!r} at position {position}")
    if value not in parser._sorts:
        raise ValueError(f"Undeclared variable {value!r} at position {position}")
    return GR1SyntaxNode("variable", value)


class GR1CoreParser:
    """Parse typed bounded-next core formulas into flattened Z3 expressions."""

    _TOKEN_RE = re.compile(  # noqa: WPS115
        r"\s*(?:(?P<number>(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
        "|(?P<identifier>[A-Za-z_][A-Za-z0-9_]*)"
        r"|(?P<operator><->|->|=>|<=|>=|==|!=|&&|\|\||[()!&|+\-*/<>=]))"
    )

    def __init__(self, variable_sorts: Dict[str, Any]):
        """Initialize from explicit ``name -> bool/int/real`` declarations.

        Args:
            variable_sorts: Declared sort for each base variable.
        """
        self._sorts = {name: _validated_variable_sort(name, sort) for name, sort in variable_sorts.items()}
        self._tokens: List[Tuple[str, str, int]] = []
        self._index = 0

    def parse(self, formula_text: str) -> "GR1CoreFormula":
        """Parse one Boolean core, flattening nested X/next applications.

        Args:
            formula_text: User-facing bounded-next formula.

        Returns:
            The computed 'GR1CoreFormula' result.

        Raises:
            ValueError: If the supplied value is invalid.
        """
        self._tokens = self._tokenize(formula_text)
        self._index = 0
        if not self._tokens:
            raise ValueError("GR(1) core formula must not be empty")

        syntax = self._parse_iff()
        if self._index != len(self._tokens):
            _, value, position = self._tokens[self._index]
            raise ValueError(f"Unexpected token {value!r} at position {position}")
        expr = _compile_parser_syntax(syntax, self._sorts, formula_text)
        return _make_core_from_expr(expr, text=syntax.to_text(), syntax=syntax, next_depth=syntax.next_depth())

    def _tokenize(self, formula_text: str) -> List[Tuple[str, str, int]]:
        """Split text into tokens while retaining source positions for errors.

        Args:
            formula_text: User-facing bounded-next formula.

        Returns:
            The computed List[Tuple[str, str, int]] result.

        Raises:
            ValueError: If the supplied value is invalid.
        """
        text = formula_text.strip()
        tokens: List[Tuple[str, str, int]] = []
        position = 0
        while position < len(text):
            match = self._TOKEN_RE.match(text, position)
            if match is None:
                raise ValueError(f"Unexpected character {text[position]!r} at position {position}")
            kind = cast(str, match.lastgroup)
            tokens.append((kind, match.group(kind), match.start(kind)))
            position = match.end()
        return tokens

    def _peek(self, *values: str) -> bool:
        """Return whether the next token matches any supplied spelling.

        Args:
            *values: Values to process.

        Returns:
            The computed bool result.
        """
        return self._index < len(self._tokens) and self._tokens[self._index][1].lower() in values

    def _take(self) -> Tuple[str, str, int]:
        """Consume the next token or reject unexpected end of input.

        Returns:
            The computed Tuple[str, str, int] result.

        Raises:
            ValueError: If the supplied value is invalid.
        """
        if self._index >= len(self._tokens):
            raise ValueError("Unexpected end of GR(1) formula")
        token = self._tokens[self._index]
        self._index += 1
        return token

    def _accept(self, *values: str) -> bool:
        """Consume a matching token and report whether one was present.

        Args:
            *values: Values to process.

        Returns:
            The computed bool result.
        """
        if self._peek(*values):
            self._index += 1
            return True
        return False

    def _expect(self, value: str) -> None:
        """Require and consume ``value`` with a position-aware error.

        Args:
            value: Value to process.

        Raises:
            ValueError: If the supplied value is invalid.
        """
        if not self._accept(value):
            position = self._tokens[self._index][2] if self._index < len(self._tokens) else "end"
            raise ValueError(f"Expected {value!r} at position {position}")

    def _parse_iff(self) -> GR1SyntaxNode:
        """Parse the equivalence precedence level.

        Returns:
            The computed GR1SyntaxNode result.
        """
        left = self._parse_implies()
        while self._accept("<->"):
            left = GR1SyntaxNode("binary", "<->", (left, self._parse_implies()))
        return left

    def _parse_implies(self) -> GR1SyntaxNode:
        """Parse right-associative implication.

        Returns:
            The computed GR1SyntaxNode result.
        """
        left = self._parse_or()
        if self._accept("->", "=>"):
            return GR1SyntaxNode("binary", "->", (left, self._parse_implies()))
        return left

    def _parse_or(self) -> GR1SyntaxNode:
        """Parse Boolean disjunction.

        Returns:
            The computed GR1SyntaxNode result.
        """
        left = self._parse_and()
        while self._accept("|", "||", "or"):
            left = GR1SyntaxNode("binary", "or", (left, self._parse_and()))
        return left

    def _parse_and(self) -> GR1SyntaxNode:
        """Parse Boolean conjunction.

        Returns:
            The computed GR1SyntaxNode result.
        """
        left = self._parse_not()
        while self._accept("&", "&&", "and"):
            left = GR1SyntaxNode("binary", "and", (left, self._parse_not()))
        return left

    def _parse_not(self) -> GR1SyntaxNode:
        """Parse Boolean negation.

        Returns:
            The computed GR1SyntaxNode result.
        """
        if self._accept("!", "not"):
            return GR1SyntaxNode("unary", "not", (self._parse_not(),))
        return self._parse_comparison()

    def _parse_comparison(self) -> GR1SyntaxNode:
        """Parse at most one equality or ordered comparison.

        Returns:
            The computed GR1SyntaxNode result.
        """
        left = self._parse_additive()
        if self._peek("=", "==", "!=", "<", "<=", ">", ">="):
            operator = self._take()[1]
            normalized = "=" if operator == "==" else operator
            return GR1SyntaxNode("binary", normalized, (left, self._parse_additive()))
        return left

    def _parse_additive(self) -> GR1SyntaxNode:
        """Parse left-associative addition and subtraction.

        Returns:
            The computed GR1SyntaxNode result.
        """
        left = self._parse_multiplicative()
        while self._peek("+", "-"):
            operator = self._take()[1]
            left = GR1SyntaxNode("binary", operator, (left, self._parse_multiplicative()))
        return left

    def _parse_multiplicative(self) -> GR1SyntaxNode:
        """Parse left-associative multiplication and division.

        Returns:
            The computed GR1SyntaxNode result.
        """
        left = self._parse_unary()
        while self._peek("*", "/"):
            operator = self._take()[1]
            left = GR1SyntaxNode("binary", operator, (left, self._parse_unary()))
        return left

    def _parse_unary(self) -> GR1SyntaxNode:
        """Parse unary numeric signs.

        Returns:
            The computed GR1SyntaxNode result.
        """
        if self._accept("+"):
            return GR1SyntaxNode("unary", "+", (self._parse_unary(),))
        if self._accept("-"):
            return GR1SyntaxNode("unary", "-", (self._parse_unary(),))
        return self._parse_primary()

    def _parse_primary(self) -> GR1SyntaxNode:
        """Parse literals, variables, grouping, and ``X``/``next`` calls.

        Returns:
            The computed GR1SyntaxNode result.

        Raises:
            ValueError: If the supplied value is invalid.
        """
        if self._accept("("):
            expr = self._parse_iff()
            self._expect(")")
            return expr

        kind, value, position = self._take()
        if kind == "number":
            return GR1SyntaxNode("number", value)
        if kind != "identifier":
            raise ValueError(f"Expected an expression at position {position}, got {value!r}")
        return _parse_identifier_primary(self, value, position)


def parse_gr1_core(formula_text: str, variable_sorts: Dict[str, Any]) -> "GR1CoreFormula":
    """Parse a user-facing bounded-next formula into a Z3-backed GR(1) core.

    Args:
        formula_text: User-facing bounded-next formula.
        variable_sorts: Declared sort for each base variable.

    Returns:
        The computed 'GR1CoreFormula' result.
    """
    return GR1CoreParser(variable_sorts).parse(formula_text)


def _shift_expr_by(expr: Any, amount: int) -> Any:
    """Shift every flattened variable in expr forward by `amount`.

        Example:
            p_0 => q_0 shifted by 1 becomes p_1 => q_1.

    Args:
        expr: Z3 expression to process.
        amount: Number of next-state shifts to apply.

    Returns:
        The computed Any result.
    """
    if amount == 0:
        return expr

    substitutions = []

    # GETVARS-PATCH: original (disabled) ---
    # for v in get_vars(expr):
    # GETVARS-PATCH: replacement ---
    for v in _z3_get_vars(expr):
        # GETVARS-PATCH: end ---
        old_name = v.decl().name()
        base, depth = _parse_flat_name(old_name)
        new_name = _shifted_name(base, depth + amount)
        new_var = z3.Const(new_name, v.sort())
        substitutions.append((v, new_var))

    if not substitutions:
        return expr

    return z3.simplify(z3.substitute(expr, *substitutions))


def _core_next_depth(core: "GR1CoreFormula") -> int:
    """Return syntax-defined next depth, including occurrences simplified away.

        Example:
            p_0, q_0 -> 0
            p_1, q_0 -> 1
            p_1, q_2 -> 2

    Args:
        core: GR(1) core formula to process.

    Returns:
        The computed int result.
    """
    max_depth = core.next_depth

    for v in core.vars:
        _, depth = _parse_flat_name(v.name)
        max_depth = max(max_depth, depth)

    return max_depth


def _shift_closed_inv_expr(inv_terms: List["GR1Term"], h: int) -> Any:
    """Build the shifted invariant guard:

            Gamma_inv^[0:h] = gamma_inv ∧ X gamma_inv ∧ ... ∧ X^h gamma_inv.

        If gamma_inv is represented by multiple INV terms, all are shifted.

    Args:
        inv_terms: Invariant terms supplying the context.
        h: Maximum bounded-next horizon.

    Returns:
        The computed Any result.
    """
    if not inv_terms:
        return z3.BoolVal(True)

    shifted_parts = []

    for k in range(h + 1):
        for term in inv_terms:
            shifted_parts.append(_shift_expr_by(cast(z3.BoolRef, term.core.expr), k))

    return z3.simplify(z3.And(*shifted_parts))


def _shifted_inv_guard_for_cores(
    inv_terms: List["GR1Term"],
    cores: List["GR1CoreFormula"],
) -> Any:
    """Build Gamma_inv^[0:h_B], where

        h_B = max_{chi in cores} d(chi).

    This is the shifted invariant guard required by the GR(1) CAVE bounds.

    Args:
        inv_terms: Invariant terms supplying the context.
        cores: Core formulas whose horizons are considered.

    Returns:
        The computed Any result.
    """
    # Preserve the prescribed syntax depth even when simplification made a
    # core true or removed its deepest variables. Empty buckets have depth zero.
    h = max((_core_next_depth(core) for core in cores), default=0)

    return _shift_closed_inv_expr(inv_terms, h)


def _expand_elim_vars_from_exprs(vars_to_elim: List[Var], *exprs: Any) -> List[Var]:
    """Expand base variables p into all shifted copies appearing in the given

        Z3 expressions, e.g. p_0, p_1, p_2.

    Args:
        vars_to_elim: Variables to eliminate.
        *exprs: Z3 expressions to process.

    Returns:
        The computed List[Var] result.
    """
    all_names: Set[str] = set()
    for expr in exprs:
        # GETVARS-PATCH: original (disabled) ---
        # for z3_var in get_vars(expr):
        # GETVARS-PATCH: replacement ---
        for z3_var in _z3_get_vars(expr):
            # GETVARS-PATCH: end ---
            all_names.add(z3_var.decl().name())

    out: Set[Var] = set(vars_to_elim)

    for name in all_names:
        v = Var(name)
        if any(_is_shifted_instance(v, base) for base in vars_to_elim):
            out.add(v)

    return sorted(out, key=lambda x: x.name)


def _liv_term_is_redundant(index: int, terms: List[GR1Term]) -> bool:
    """Check whether one liveness term is implied by a preferred peer.

    Args:
        index: Candidate index.
        terms: Nontrivial liveness terms.

    Returns:
        Whether the indexed term is redundant.
    """
    candidate_expr = cast(Any, terms[index].core.expr)
    for other_index, other in enumerate(terms):
        if index == other_index:
            continue
        other_expr = cast(Any, other.core.expr)
        other_implies = _implies(other_expr, candidate_expr)
        candidate_implies = _implies(candidate_expr, other_expr)
        if other_implies and (not candidate_implies or other_index < index):
            return True
    return False


def _pointwise_reduce_liv_terms(candidates: List[GR1Term]) -> List[GR1Term]:
    """Apply same-time implication reduction to liveness terms.

    Args:
        candidates: Candidate liveness terms.

    Returns:
        Nontrivial, non-redundant liveness terms.
    """
    nontrivial = [term for term in candidates if not _equivalent(cast(Any, term.core.expr), b=True)]
    return [term for index, term in enumerate(nontrivial) if not _liv_term_is_redundant(index, nontrivial)]


def _remove_redundant_liv_terms(terms: List[GR1Term]) -> List[GR1Term]:
    """Reduce projected liveness terms without changing their conjunction.

        First canonicalize uniform global shifts using GF(X^k(phi)) = GF(phi).
        Terms equivalent to True are trivial. Of equivalent normalized terms, the
        first is retained. A term b is redundant when another term a strictly
        implies it, because □◇a then implies □◇b. Liveness terms remain separate;
        their cores are never conjoined inside one GF.

    Args:
        terms: GR(1) terms to process.

    Returns:
        The computed List[GR1Term] result.
    """
    # Preserve implications visible at the original common time origin before
    # independently removing each core's semantically irrelevant global shift.
    reduced = _pointwise_reduce_liv_terms(terms)
    normalized = [GR1Term(GR1Tag.LIV, _normalize_liv_core_global_shift(term.core)) for term in reduced]
    return _pointwise_reduce_liv_terms(normalized)


# ---------------------------------------------------------------------------
# Core propositional formula
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GR1CoreFormula:
    """
    Non-temporal core formula φ.

    Use:
    - of(...)       -> text-only formulas
    - of_expr(...)  -> Z3-backed formulas, required for elimination
    - parse_gr1_core(...) -> parse a typed user-facing bounded-next formula

    The only temporal operator allowed inside cores is Next, and it should be
    flattened before manually creating a Z3 expression. GR1CoreParser performs
    this flattening for string input.  User text uses ``q`` and ``X(q)``;
    ``q_0`` and ``q_1`` are reserved for the corresponding internal Z3
    constants.  Generated ``text`` is unflattened again for presentation while
    ``expr`` and ``vars`` retain the exact machine-level symbols.
    """

    text: str
    _vars: FrozenSet[Var]
    expr: Optional[Any] = None
    syntax: Optional[GR1SyntaxNode] = None
    raw_expr: Optional[Any] = field(default=None, compare=False, repr=False)
    serialized_machine: Optional[Dict[str, Any]] = field(default=None, compare=False, repr=False)
    next_depth: int = field(default=0, compare=False)

    @staticmethod
    def of(
        text: str,
        vars: Iterable[Var],  # noqa: A002, VNE003
        expr: Optional[Any] = None,
        syntax: Optional[GR1SyntaxNode] = None,
        raw_expr: Optional[Any] = None,
        serialized_machine: Optional[Dict[str, Any]] = None,
        next_depth: int = 0,
    ) -> "GR1CoreFormula":
        """Build a core, optionally attaching an expression and parser AST.

        Args:
            text: Human-readable formula text.
            vars: Variables occurring in the formula.
            expr: Z3 expression to process.
            syntax: Optional parsed syntax tree.
            raw_expr: Original solver/QE expression retained for debugging.
            serialized_machine: Optional serialized machine representation.
            next_depth: Original finite-window depth before simplification.

        Returns:
            The computed 'GR1CoreFormula' result.
        """
        return GR1CoreFormula(
            text=text,
            _vars=frozenset(vars),
            expr=expr,
            syntax=syntax,
            raw_expr=raw_expr,
            serialized_machine=serialized_machine,
            next_depth=next_depth,
        )

    @staticmethod
    def of_expr(
        text: str,
        vars: Iterable[Var],  # noqa: A002, VNE003
        expr: Any,
        syntax: Optional[GR1SyntaxNode] = None,
        raw_expr: Optional[Any] = None,
        serialized_machine: Optional[Dict[str, Any]] = None,
        next_depth: int = 0,
    ) -> "GR1CoreFormula":
        """Build a core that is guaranteed to have a Z3 expression.

        Args:
            text: Human-readable formula text.
            vars: Variables occurring in the formula.
            expr: Z3 expression to process.
            syntax: Optional parsed syntax tree.
            raw_expr: Original solver/QE expression retained for debugging.
            serialized_machine: Optional serialized machine representation.
            next_depth: Original finite-window depth before simplification.

        Returns:
            The computed 'GR1CoreFormula' result.

        Raises:
            ValueError: If the supplied value is invalid.
        """
        if expr is None:
            raise ValueError("expr must not be None")
        return GR1CoreFormula(
            text=text,
            _vars=frozenset(vars),
            expr=expr,
            syntax=syntax,
            raw_expr=raw_expr,
            serialized_machine=serialized_machine,
            next_depth=next_depth,
        )

    @staticmethod
    def false() -> "GR1CoreFormula":  # noqa: WPS605
        """Return the variable-free unsatisfiable core.

        Returns:
            The computed 'GR1CoreFormula' result.
        """
        return GR1CoreFormula.of_expr("False", [], expr=z3.BoolVal(False))

    @staticmethod
    def true() -> "GR1CoreFormula":  # noqa: WPS605
        """Return the variable-free tautological core.

        Returns:
            The computed 'GR1CoreFormula' result.
        """
        return GR1CoreFormula.of_expr("True", [], expr=z3.BoolVal(True))

    @property
    def vars(self) -> List[Var]:  # noqa: A003
        """Return flattened variables in deterministic name order.

        Returns:
            The computed List[Var] result.
        """
        return sorted(self._vars, key=lambda v: v.name)

    def contains_var(self, v: Var) -> bool:
        """Return whether the exact flattened variable occurs in this core.

        Args:
            v: V.

        Returns:
            The computed bool result.
        """
        return v in self._vars

    def rename_variable(self, source: Var, target: Var) -> "GR1CoreFormula":
        """Rename a base variable structurally in text, AST, and every Z3 depth.

        Args:
            source: Source variable or name.
            target: Target variable, name, or obligation.

        Returns:
            The computed 'GR1CoreFormula' result.
        """
        if source == target:
            return self

        renamed_syntax = self.syntax.rename(source.name, target.name) if self.syntax is not None else None
        if renamed_syntax is not None:
            new_text = renamed_syntax.to_text()
        else:
            new_text = re.sub(
                rf"(?<![A-Za-z0-9_]){re.escape(source.name)}_(\d+)(?![A-Za-z0-9_])",
                lambda match: f"{target.name}_{match.group(1)}",
                self.text,
            )
            new_text = re.sub(
                f"(?<![A-Za-z0-9_]){re.escape(source.name)}(?![A-Za-z0-9_])",
                target.name,
                new_text,
            )
        if self.expr is None:
            new_vars = {target if v == source else v for v in self._vars}
            return GR1CoreFormula(text=new_text, _vars=frozenset(new_vars), expr=None)

        substitutions = []
        # GETVARS-PATCH: original (disabled) ---
        # for z3_var in get_vars(self.expr):
        # GETVARS-PATCH: replacement ---
        for z3_var in _z3_get_vars(self.expr):
            # GETVARS-PATCH: end ---
            base, depth = _parse_flat_name(z3_var.decl().name())
            if base == source.name:
                substitutions.append((z3_var, z3.Const(_shifted_name(target.name, depth), z3_var.sort())))

        new_expr = z3.substitute(self.expr, *substitutions) if substitutions else self.expr
        renamed_raw = self.raw_expr
        if renamed_raw is not None and substitutions:
            renamed_raw = z3.substitute(renamed_raw, *substitutions)
        return _make_core_from_expr(
            new_expr,
            text=new_text,
            syntax=renamed_syntax,
            raw_expr=renamed_raw,
            next_depth=_core_next_depth(self),
        )

    def __str__(self) -> str:
        """Return the readable core formula.

        Returns:
            The computed str result.
        """
        return self.text


class GR1Tag(str, Enum):  # noqa: WPS600
    """Temporal bucket tags for initial, invariant, and liveness formulas."""

    INIT = "init"  # noqa: WPS115
    INV = "inv"  # noqa: WPS115  # □φ
    LIV = "liv"  # noqa: WPS115  # □◇φ


@dataclass(frozen=True)
class GR1Term(Term):
    """
    A single GR(1) term = (tag, core).

    Semantics:
      INIT:  φ
      INV:   □φ
      LIV:   □◇φ
    """

    tag: GR1Tag
    core: GR1CoreFormula

    def __eq__(self, other: object) -> bool:
        """Compare both temporal tag and core formula.

        Args:
            other: Other term list or contract.

        Returns:
            The computed Any result.
        """
        if not isinstance(other, GR1Term):
            return False
        return self.tag == other.tag and self.core == other.core

    def __hash__(self) -> int:
        """Hash consistently with structural term equality.

        Returns:
            The computed Any result.
        """
        return hash((self.tag, self.core))

    @property
    def vars(self) -> List[Var]:  # noqa: A003
        """Expose base interface variables rather than flattened instances.

        Returns:
            The computed List[Var] result.
        """
        return sorted({Var(_base_var_name(v)) for v in self.core.vars}, key=lambda v: v.name)

    def contains_var(self, var_to_seek: Var) -> bool:
        """Test relevance by exact or base-variable name.

        Args:
            var_to_seek: Var to seek.

        Returns:
            The computed bool result.
        """
        return any(
            variable == var_to_seek or _base_var_name(variable) == var_to_seek.name for variable in self.core.vars
        )

    def rename_variable(self, source_var: Var, target_var: Var) -> "GR1Term":
        """Rename one base variable throughout the term's core.

        Args:
            source_var: Source var.
            target_var: Target var.

        Returns:
            The computed 'GR1Term' result.
        """
        if source_var == target_var:
            return self
        return GR1Term(self.tag, self.core.rename_variable(source_var, target_var))

    def copy(self) -> "GR1Term":
        """Copy the immutable term while preserving AST and Z3 data.

        Returns:
            The computed 'GR1Term' result.
        """
        return GR1Term(
            self.tag,
            (
                GR1CoreFormula.of_expr(
                    self.core.text,
                    self.core.vars,
                    self.core.expr,
                    syntax=self.core.syntax,
                    raw_expr=self.core.raw_expr,
                    serialized_machine=copy.deepcopy(self.core.serialized_machine),
                    next_depth=_core_next_depth(self.core),
                )
                if self.core.expr is not None
                else GR1CoreFormula.of(self.core.text, self.core.vars)
            ),
        )

    def __str__(self) -> str:
        """Render the core together with its implicit temporal operator.

        Returns:
            The computed str result.
        """
        if self.tag == GR1Tag.INIT:
            return f"INIT({self.core})"
        if self.tag == GR1Tag.INV:
            return f"INV(□ {self.core})"
        return f"LIV(□◇ {self.core})"

    def __repr__(self) -> str:
        """Return a concise debugging representation.

        Returns:
            The computed str result.
        """
        return f"<GR1Term {self}>"


def _behavior_value(state: Mapping[Union[str, Var], Any], base: str) -> Any:
    """Read a base variable from a behavior state keyed by string or ``Var``.

    Args:
        state: State.
        base: Base variable name.

    Returns:
        The computed Any result.

    Raises:
        ValueError: If the supplied value is invalid.
    """
    if base in state:
        return state[base]
    variable = Var(base)
    if variable in state:
        return state[variable]
    raise ValueError(f"Behavior does not assign variable {base!r}")


def _behavior_state_index(behavior: GR1Behavior, index: int) -> int:
    """Map an absolute index into a finite trace or its repeating lasso suffix.

    Args:
        behavior: Behavior or trace to check.
        index: Index.

    Returns:
        The computed int result.

    Raises:
        ValueError: If the supplied value is invalid.
    """
    if index < len(behavior.states):
        return index
    if behavior.loop_start is None:
        raise ValueError("Behavior is too short for the formula's next depth")
    loop_length = len(behavior.states) - behavior.loop_start
    return behavior.loop_start + ((index - behavior.loop_start) % loop_length)


def _behavior_z3_value(z3_var: Any, value: Any) -> Any:
    """Convert one behavior value to the variable's exact Z3 sort.

    Args:
        z3_var: Typed Z3 variable.
        value: Concrete behavior value.

    Returns:
        The corresponding Z3 literal.

    Raises:
        ValueError: If the variable sort is unsupported.
    """
    converters = {
        z3.BoolSort(): lambda: z3.BoolVal(bool(value)),
        z3.IntSort(): lambda: z3.IntVal(value),
        z3.RealSort(): lambda: z3.RealVal(value),
    }
    converter = converters.get(z3_var.sort())
    if converter is None:
        raise ValueError(f"Unsupported behavior variable sort: {z3_var.sort()}")
    return converter()


def _behavior_substitution(name: str, z3_var: Any, behavior: GR1Behavior, time: int) -> Tuple[Any, Any]:
    """Build one typed substitution for behavior evaluation.

    Args:
        name: Flattened variable name.
        z3_var: Typed Z3 variable.
        behavior: Behavior trace.
        time: Evaluation time.

    Returns:
        The variable and concrete Z3 replacement pair.
    """
    base, depth = _parse_flat_name(name)
    state_index = _behavior_state_index(behavior, time + depth)
    value = _behavior_value(behavior.states[state_index], base)
    return z3_var, _behavior_z3_value(z3_var, value)


def _evaluated_core_result(core: GR1CoreFormula, result: Any) -> bool:
    """Convert a fully simplified Z3 result to a Python Boolean.

    Args:
        core: Evaluated core formula.
        result: Simplified Z3 result.

    Returns:
        The concrete Boolean result.

    Raises:
        ValueError: If variables remain after evaluation.
    """
    if z3.is_true(result):
        return True
    if z3.is_false(result):
        return False
    raise ValueError(f"Behavior did not fully evaluate core {core.text!r}: {result}")


def _evaluate_core_at(core: GR1CoreFormula, behavior: GR1Behavior, time: int) -> bool:
    """Evaluate a flattened core at ``time`` using the behavior's future states.

    Args:
        core: GR(1) core formula to process.
        behavior: Behavior or trace to check.
        time: Time.

    Returns:
        The computed bool result.

    Raises:
        NotImplementedError: If the supplied value is invalid.
    """
    if core.expr is None:
        raise NotImplementedError("Behavior checking requires Z3-backed GR(1) cores")
    substitutions = [
        _behavior_substitution(name, z3_var, behavior, time) for name, z3_var in _z3_vars_in_expr(core.expr).items()
    ]
    result = z3.simplify(z3.substitute(core.expr, *substitutions))
    return _evaluated_core_result(core, result)


def _deduplicate_text_terms(terms: List[Term]) -> "GR1TermList":
    """Deduplicate text-only terms while preserving their original order.

    Args:
        terms: Terms to deduplicate.

    Returns:
        A term list containing the first occurrence of every structural key.
    """
    seen = set()
    unique: List[GR1Term] = []
    for term_any in terms:
        term = cast(GR1Term, term_any)
        key = (term.tag, term.core.text, tuple(term.core.vars))
        if key not in seen:
            unique.append(term)
            seen.add(key)
    return GR1TermList(unique)


def _usable_simplification_context(context: Optional["GR1TermList"]) -> Optional["GR1TermList"]:
    """Discard a context that contains non-executable text-only terms.

    Args:
        context: Candidate semantic simplification context.

    Returns:
        The executable context, or ``None`` when it cannot be used semantically.
    """
    if context is None:
        return None
    if any(cast(GR1Term, term).core.expr is None for term in context.terms):
        return None
    return context


def _context_implies_term(
    candidate: GR1Term,
    context_init: Optional[Any],
    context_inv: Optional[Any],
    context_liv: List[GR1Term],
) -> bool:
    """Check whether the matching context bucket implies a candidate term.

    Args:
        candidate: Candidate term.
        context_init: Conjoined initial context, when available.
        context_inv: Conjoined invariant context, when available.
        context_liv: Separate liveness context terms.

    Returns:
        Whether the candidate is redundant in the context.
    """
    expr = cast(Any, candidate.core.expr)
    if candidate.tag == GR1Tag.INIT and context_init is not None:
        guard = context_init
        if context_inv is not None:

            guard = z3.And(guard, context_inv)
        return _implies(guard, expr)
    if candidate.tag == GR1Tag.INV and context_inv is not None:
        return _implies(context_inv, expr)
    if candidate.tag != GR1Tag.LIV:
        return False
    if context_inv is not None and _implies(context_inv, expr):
        return True
    return any(_implies(cast(Any, source.core.expr), expr) for source in context_liv)


def _simplification_candidates(
    bucket: List[GR1Term],
    context_init: Optional[Any],
    context_inv: Optional[Any],
    context_liv: List[GR1Term],
) -> Tuple[List[GR1Term], bool]:
    """Simplify one bucket and report whether it contains false.

    Args:
        bucket: Terms from one temporal bucket.
        context_init: Conjoined initial context, when available.
        context_inv: Conjoined invariant context, when available.
        context_liv: Separate liveness context terms.

    Returns:
        Simplified candidates and whether a false term was encountered.
    """
    candidates: List[GR1Term] = []
    for term in bucket:
        expr = _simplify_expr(cast(Any, term.core.expr))
        if _equivalent(expr, b=True) or _context_implies_term(term, context_init, context_inv, context_liv):
            continue
        if _equivalent(expr, b=False):
            return [], True
        candidates.append(
            GR1Term(
                term.tag,
                _make_core_from_expr(
                    expr,
                    text=term.core.text,
                    syntax=term.core.syntax,
                    raw_expr=term.core.raw_expr,
                    next_depth=_core_next_depth(term.core),
                ),
            )
        )
    return candidates, False


def _safety_term_is_redundant(index: int, candidates: List[GR1Term]) -> bool:
    """Check whether one safety candidate is implied by a preferred peer.

    Args:
        index: Candidate index.
        candidates: Safety candidates.

    Returns:
        Whether the indexed candidate is redundant.
    """
    candidate_expr = cast(Any, candidates[index].core.expr)
    for other_index, other in enumerate(candidates):
        if index == other_index:
            continue
        other_expr = cast(Any, other.core.expr)
        other_implies = _implies(other_expr, candidate_expr)
        candidate_implies = _implies(candidate_expr, other_expr)
        if other_implies and (not candidate_implies or other_index < index):
            return True
    return False


def _remove_redundant_safety_terms(candidates: List[GR1Term]) -> List[GR1Term]:
    """Remove conjunction-redundant INIT or INV candidates.

        Candidates are considered from last to first. A candidate is removed
        only when the conjunction of the terms that remain implies it. The
        iterative order avoids unsound simultaneous removal of mutually
        supporting constraints.

    Args:
        candidates: Candidate safety terms.

    Returns:
        The non-redundant candidates in their original order.
    """
    reduced = list(candidates)
    for index in range(len(reduced) - 1, -1, -1):
        others = reduced[:index] + reduced[index + 1 :]
        if others and _implies(_and_expr(others), cast(Any, reduced[index].core.expr)):
            del reduced[index]
    return reduced


def _z3_nodes(expr: Any) -> List[Any]:
    """Collect distinct nodes from a Z3 expression.

    Args:
        expr: Expression to traverse.

    Returns:
        Distinct expression nodes.
    """
    nodes = []
    pending = [expr]
    seen: Set[int] = set()
    while pending:
        node = pending.pop()
        node_id = node.get_id()
        if node_id not in seen:
            seen.add(node_id)
            nodes.append(node)
            pending.extend(node.children())
    return nodes


def _z3_ast_size(expr: Any) -> int:
    """Count distinct nodes in a Z3 expression for conservative candidate ranking.

    Args:
        expr: Expression whose nodes are counted.

    Returns:
        Number of distinct AST nodes.
    """
    return len(_z3_nodes(expr))


def _expr_next_depth(expr: Any) -> int:
    """Return the greatest flattened Next depth occurring in an expression.

    Args:
        expr: Expression to inspect.

    Returns:
        Greatest flattened Next depth.
    """
    # GETVARS-PATCH: original (disabled) ---
    # return max((_parse_flat_name(variable.decl().name())[1] for variable in get_vars(expr)), default=0)
    # GETVARS-PATCH: replacement ---
    return max((_parse_flat_name(variable.decl().name())[1] for variable in _z3_get_vars(expr)), default=0)
    # GETVARS-PATCH: end ---


def _variable_pair_residuals(left: Any, right: Any) -> List[Any]:
    """Construct residual candidates for a same-sort variable pair.

    Args:
        left: First variable.
        right: Second variable.

    Returns:
        Equality and Boolean implication candidates.
    """
    candidates = [left == right, left != right]
    if left.sort() == z3.BoolSort():
        candidates.extend([z3.Implies(left, right), z3.Implies(right, left)])
    return candidates


def _init_residual_candidates(expr: Any) -> List[Any]:
    """Construct small candidate residuals; every accepted rewrite is SMT checked.

    Args:
        expr: Expression from which to construct candidates.

    Returns:
        Unique simplified residual candidates.
    """
    candidates = _flatten_boolean_operator(expr, z3.is_and)
    # GETVARS-PATCH: original (disabled) ---
    # variables = list(get_vars(expr))
    # GETVARS-PATCH: replacement ---
    variables = list(_z3_get_vars(expr))
    # GETVARS-PATCH: end ---
    for index, left in enumerate(variables):
        if left.sort() == z3.BoolSort():
            candidates.extend([left, z3.Not(left)])
        for right in variables[index + 1 :]:
            if left.sort() == right.sort():
                candidates.extend(_variable_pair_residuals(left, right))
    return _unique_equivalent_exprs([z3.simplify(candidate) for candidate in candidates])


def _reduce_init_expr_under_invariant(init_expr: Any, inv_at_zero: Any) -> Any:
    """Reduce an INIT formula modulo the time-zero invariant context.

    A replacement ``delta`` is accepted only after proving

        inv_at_zero & delta  <=>  inv_at_zero & init_expr.

    Top-level conjuncts are removed semantically first. For solver-produced
    Boolean DNF, compact atomic candidates are then considered and ranked by
    bounded-Next depth and AST size. If no strictly smaller verified
    residual is found, the original expression is retained.

    Args:
        init_expr: Initial expression to reduce.
        inv_at_zero: Invariant context at time zero.

    Returns:
        Equivalent reduced initial expression.
    """
    if _implies(inv_at_zero, init_expr):
        return z3.BoolVal(True)

    conjuncts = _flatten_boolean_operator(init_expr, z3.is_and)
    reduced = list(conjuncts)
    for index in range(len(reduced) - 1, -1, -1):
        others = reduced[:index] + reduced[index + 1 :]
        guard = z3.And(inv_at_zero, *others)
        if _implies(guard, reduced[index]):
            del reduced[index]
    conjunctive_residual = z3.simplify(z3.And(*reduced)) if reduced else z3.BoolVal(True)

    original_guarded = z3.And(inv_at_zero, init_expr)
    verified = [
        candidate
        for candidate in _init_residual_candidates(conjunctive_residual)
        if _equivalent(z3.And(inv_at_zero, candidate), original_guarded)
    ]
    if verified:
        verified.sort(key=lambda candidate: (_expr_next_depth(candidate), _z3_ast_size(candidate), str(candidate)))
        best = verified[0]
        if _z3_ast_size(best) < _z3_ast_size(init_expr):
            return best
    if _equivalent(z3.And(inv_at_zero, conjunctive_residual), original_guarded):
        return conjunctive_residual
    return init_expr


def _post_cave_bucket_reduction(terms: "GR1TermList") -> "GR1TermList":
    """Apply semantic GR(1) redundancy reduction after exact finite-window CAVE projection.

    This is not part of any CAVE bound and is not a general LTL minimizer.
    It uses only: invariant truth at time zero for INIT, shifted invariant
    closure for LIV, and conjunction implication inside safety buckets.

    Args:
        terms: Terms to reduce.

    Returns:
        Reduced term list.
    """
    inv_terms = _remove_redundant_safety_terms(terms.inv_terms())
    if len(inv_terms) > 1:
        inv_terms = [GR1Term(GR1Tag.INV, _make_core_from_expr(_and_expr(inv_terms)))]
    inv_at_zero = _and_expr(inv_terms)

    init_terms = _remove_redundant_safety_terms(terms.init_terms())
    reduced_init: List[GR1Term] = []
    if init_terms:
        original_init = _and_expr(init_terms)
        residual = _reduce_init_expr_under_invariant(original_init, inv_at_zero)
        if not _equivalent(residual, b=True):
            reduced_init.append(GR1Term(GR1Tag.INIT, _make_core_from_expr(residual)))

    liv_terms = []
    for term in terms.liv_terms():
        shifted_inv = _shifted_inv_guard_for_cores(inv_terms, [term.core])
        if not _implies(shifted_inv, cast(Any, term.core.expr)):
            liv_terms.append(term)
    liv_terms = _remove_redundant_liv_terms(liv_terms)

    return GR1TermList(reduced_init + inv_terms + liv_terms)


def _reduce_simplification_bucket(
    tag: GR1Tag,
    bucket: List[GR1Term],
    context_init: Optional[Any],
    context_inv: Optional[Any],
    context_liv: List[GR1Term],
) -> Tuple[List[GR1Term], Optional[GR1Term]]:
    """Reduce one temporal bucket and return any contradiction separately.

    Args:
        tag: Temporal bucket tag.
        bucket: Terms in that bucket.
        context_init: Conjoined initial context, when available.
        context_inv: Conjoined invariant context, when available.
        context_liv: Separate liveness context terms.

    Returns:
        Reduced terms and an optional false term.
    """
    candidates, contains_false = _simplification_candidates(bucket, context_init, context_inv, context_liv)
    if contains_false or (tag != GR1Tag.LIV and candidates and not _is_sat(_and_expr(candidates))):
        return [], GR1Term(tag, GR1CoreFormula.false())
    if tag == GR1Tag.LIV:
        return _remove_redundant_liv_terms(candidates), None
    return _remove_redundant_safety_terms(candidates), None


TaggedBuckets = Tuple[Tuple[GR1Tag, List[GR1Term]], ...]


def _reduce_simplification_buckets(
    buckets: TaggedBuckets,
    context_init: Optional[Any],
    context_inv: Optional[Any],
    context_liv: List[GR1Term],
) -> Tuple[List[GR1Term], Optional[GR1Term]]:
    """Reduce an ordered collection of temporal buckets.

    Args:
        buckets: Tagged buckets to reduce.
        context_init: Conjoined initial context, when available.
        context_inv: Conjoined invariant context, when available.
        context_liv: Separate liveness context terms.

    Returns:
        Reduced terms and the first contradiction, if present.
    """
    reduced = []
    contradiction = None
    for tag, bucket in buckets:
        bucket_terms, contradiction = _reduce_simplification_bucket(tag, bucket, context_init, context_inv, context_liv)
        if contradiction is not None:
            break
        reduced.extend(bucket_terms)
    return reduced, contradiction


def _simplify_expression_terms(terms: "GR1TermList", semantic_context: Optional["GR1TermList"]) -> "GR1TermList":
    """Simplify an expression-backed term list with optional context.

    Args:
        terms: Term list to simplify.
        semantic_context: Usable simplification context, when supplied.

    Returns:
        Simplified term list.
    """
    if semantic_context is not None and semantic_context.is_empty():
        return GR1TermList()
    context_init = _and_expr(semantic_context.init_terms()) if semantic_context is not None else None
    context_inv = _and_expr(semantic_context.inv_terms()) if semantic_context is not None else None
    context_liv = semantic_context.liv_terms() if semantic_context is not None else []
    buckets = (
        (GR1Tag.INIT, terms.init_terms()),
        (GR1Tag.INV, terms.inv_terms()),
        (GR1Tag.LIV, terms.liv_terms()),
    )
    reduced, contradiction = _reduce_simplification_buckets(buckets, context_init, context_inv, context_liv)
    if contradiction is not None:
        return GR1TermList([contradiction])
    internally_reduced = _post_cave_bucket_reduction(GR1TermList(reduced))
    if semantic_context is None:
        return internally_reduced
    context_buckets = (
        (GR1Tag.INIT, internally_reduced.init_terms()),
        (GR1Tag.INV, internally_reduced.inv_terms()),
        (GR1Tag.LIV, internally_reduced.liv_terms()),
    )
    context_reduced, contradiction = _reduce_simplification_buckets(
        context_buckets, context_init, context_inv, context_liv
    )
    if contradiction is not None:
        return GR1TermList([contradiction])
    return _post_cave_bucket_reduction(GR1TermList(context_reduced))


def _refined_term(tag: GR1Tag, reference_expr: Any) -> GR1Term:
    """Build a refined term, preserving an explicit false result.

    Args:
        tag: Result bucket tag.
        reference_expr: Quantifier-eliminated refinement expression.

    Returns:
        The refined term.
    """
    new_core = _make_qe_core(reference_expr)
    if _is_sat(cast(Any, new_core.expr)):
        return GR1Term(tag, new_core)
    return GR1Term(tag, GR1CoreFormula.false())


def _true_bucket_term(tag: GR1Tag) -> GR1Term:
    """Represent an empty conjunctive INIT/INV bucket by semantic True.

    Args:
        tag: Bucket tag for the true term.

    Returns:
        True term carrying the requested tag.
    """
    return GR1Term(tag, _make_core_from_expr(z3.BoolVal(True)))


def _append_nontrivial_init(terms: List[GR1Term], term: GR1Term) -> None:
    """Append a CAVE INIT result unless it is equivalent to True.

    Args:
        terms: Destination term list.
        term: Candidate initial term.
    """
    if not _equivalent(cast(Any, term.core.expr), b=True):
        terms.append(term)


def _refine_init_term(
    term: GR1Term,
    context: "GR1TermList",
    gamma_init_expr: Any,
    vars_to_elim: List[Var],
) -> GR1Term:
    """Refine one conjoined initial obligation.

    Args:
        term: Initial target term.
        context: Refinement context.
        gamma_init_expr: Conjoined initial context expression.
        vars_to_elim: Base variables to eliminate.

    Returns:
        The refined initial term.
    """
    term_expr = cast(z3.BoolRef, term.core.expr)
    init_cores = [candidate.core for candidate in context.init_terms()]
    shifted_inv = _shifted_inv_guard_for_cores(context.inv_terms(), init_cores + [term.core])
    guard_expr = z3.And(gamma_init_expr, shifted_inv)
    local_vars = _expand_elim_vars_from_exprs(vars_to_elim, guard_expr, term_expr)
    return _refined_term(GR1Tag.INIT, _qe_forall_refinement(term_expr, guard_expr, local_vars))


def _refine_inv_term(term: GR1Term, context: "GR1TermList", vars_to_elim: List[Var]) -> GR1Term:
    """Refine one conjoined invariant obligation.

    Args:
        term: Invariant target term.
        context: Refinement context.
        vars_to_elim: Base variables to eliminate.

    Returns:
        The refined invariant term.
    """
    term_expr = cast(Any, term.core.expr)
    shifted_inv = _shifted_inv_guard_for_cores(context.inv_terms(), [term.core])
    local_vars = _expand_elim_vars_from_exprs(vars_to_elim, shifted_inv, term_expr)
    return _refined_term(GR1Tag.INV, _qe_forall_refinement(term_expr, shifted_inv, local_vars))


def _retain_elimination_free_liv(term: GR1Term, vars_to_elim: List[Var]) -> GR1Term:
    """Historical Boolean cleanup helper, unused by final Algorithm 1.

    Args:
        term: Elimination-free liveness target.
        vars_to_elim: Base variables nominally being eliminated.

    Returns:
        The original or cleaned liveness term.
    """
    term_expr = cast(Any, term.core.expr)
    cleaned_expr = _drop_irrelevant_eliminated_bool_vars(term_expr, vars_to_elim)
    if set(_z3_vars_in_expr(cleaned_expr)) == set(_z3_vars_in_expr(term_expr)):
        return term
    return GR1Term(GR1Tag.LIV, _make_core_from_expr(cleaned_expr))


def _refine_liv_with_support(
    target: GR1Term,
    support: GR1Term,
    context: "GR1TermList",
    vars_to_elim: List[Var],
) -> GR1Term:
    """Project one fixed recurring support into a persistent certificate.

    Args:
        target: Liveness target term.
        support: Candidate context liveness support.
        context: Refinement context.
        vars_to_elim: Base variables to eliminate.

    Returns:
        The fixed-support invariant certificate, including extreme cores.
    """
    target_expr = cast(z3.BoolRef, target.core.expr)
    support_expr = cast(z3.BoolRef, support.core.expr)
    shifted_inv = _shifted_inv_guard_for_cores(context.inv_terms(), [support.core, target.core])
    local_vars = _expand_elim_vars_from_exprs(vars_to_elim, shifted_inv, support_expr, target_expr)
    guard_expr = z3.And(shifted_inv, support_expr)
    reference_expr = _qe_forall_refinement(target_expr, guard_expr, local_vars)
    return _refined_term(GR1Tag.INV, reference_expr)


def _refine_liv_fallback(
    target: GR1Term,
    context: "GR1TermList",
    vars_to_elim: List[Var],
) -> GR1Term:
    """Construct the synthetic recurrent certificate (historical helper name).

    Args:
        target: Liveness target.
        context: Refinement context.
        vars_to_elim: Base variables to eliminate.

    Returns:
        The synthetic LIV obligation, constructed for every target.
    """
    target_expr = cast(Any, target.core.expr)
    shifted_inv = _shifted_inv_guard_for_cores(context.inv_terms(), [target.core])
    local_vars = _expand_elim_vars_from_exprs(vars_to_elim, shifted_inv, target_expr)
    reference_expr = _qe_forall_refinement(target_expr, shifted_inv, local_vars)
    return GR1Term(GR1Tag.LIV, _make_qe_core(reference_expr))


@dataclass(frozen=True, eq=False, repr=False)
class _RefinementLivCandidate(GR1Term):
    """Tagged certificate with selection-local provenance (not contract syntax).

    Branch 0 is synthetic. Genuine branch IDs use the support's syntax depth
    and SMT-LIB core, rather than its incidental input-list index. Identical
    supports share an ID but still each generate a candidate. Ordinary bucket
    simplification may subsequently remove certificates or discard provenance.
    """

    branch_id: str
    support_id: Optional[Tuple[int, str]]


def _refinement_selection_key(term: GR1Term) -> Tuple[int, int, str, str]:
    """Order certificates by source, never by solver-dependent QE printing.

    Plain tagged terms are supported for private diagnostic callers; production
    always supplies candidates with source provenance. Canonical here means
    stable syntax ordering, not canonicalization modulo logical equivalence.

    Args:
        term: Candidate certificate.

    Returns:
        A stable ordering key.

    Raises:
        ValueError: The candidate has no Z3 expression.
    """
    if isinstance(term, _RefinementLivCandidate):
        if term.support_id is None:
            return (0, 0, "", term.tag.value)
        depth, support = term.support_id
        return (1, depth, support, term.tag.value)
    if term.core.expr is None:
        raise ValueError("Selection requires a Z3-backed core")
    return (0 if term.tag == GR1Tag.LIV else 1, _core_next_depth(term.core), term.core.expr.sexpr(), term.tag.value)


def _refinement_liv_candidates(target: GR1Term, context: "GR1TermList", vars_to_elim: List[Var]) -> List[GR1Term]:
    """Construct branch 0 followed by every fixed support before selection.

    Position zero is GF(psi_i,0); position j+1 is G(psi_i,j) for the
    corresponding context LIV term. No relevance or viability filter applies.

    Args:
        target: Target obligation to project.
        context: Context constraining the elimination.
        vars_to_elim: Variables to eliminate.

    Returns:
        All finite liveness certificates.

    Raises:
        ValueError: A support has no Z3 expression.
    """
    synthetic = _refine_liv_fallback(target, context, vars_to_elim)
    candidates: List[GR1Term] = [_RefinementLivCandidate(synthetic.tag, synthetic.core, "0", None)]
    for support in context.liv_terms():
        term = _refine_liv_with_support(target, support, context, vars_to_elim)
        if support.core.expr is None:
            raise ValueError("Liveness support requires a Z3-backed core")
        support_id = (_core_next_depth(support.core), support.core.expr.sexpr())
        branch_id = "support:{}:{}".format(*support_id)
        candidates.append(_RefinementLivCandidate(term.tag, term.core, branch_id, support_id))
    return candidates


def _refine_liv_term(
    target: GR1Term,
    context: "GR1TermList",
    vars_to_elim: List[Var],
) -> GR1Term:
    """Construct every theoretical branch, then select one certificate.

    Args:
        target: Liveness target term.
        context: Refinement context.
        vars_to_elim: Base variables to eliminate.

    Returns:
        The selected recurrent or persistent certificate.
    """
    candidates = _refinement_liv_candidates(target, context, vars_to_elim)
    return cast(GR1Term, _select_refinement_support(candidates))


def _refine_gr1_term(
    term: GR1Term,
    context: "GR1TermList",
    gamma_init_expr: Any,
    vars_to_elim: List[Var],
) -> GR1Term:
    """Dispatch one canonical target term to its bucket refinement rule.

    Args:
        term: Canonical target term.
        context: Refinement context.
        gamma_init_expr: Conjoined initial context expression.
        vars_to_elim: Base variables to eliminate.

    Returns:
        The refined target term.

    Raises:
        ValueError: If the term has an unknown temporal tag.
    """
    if term.tag == GR1Tag.INIT:
        return _refine_init_term(term, context, gamma_init_expr, vars_to_elim)
    if term.tag == GR1Tag.INV:
        return _refine_inv_term(term, context, vars_to_elim)
    if term.tag == GR1Tag.LIV:
        return _refine_liv_term(term, context, vars_to_elim)
    raise ValueError(f"Unknown GR1Tag: {term.tag}")


def _coerce_gr1_behavior(behavior: Any) -> GR1Behavior:
    """Normalize supported behavior inputs to ``GR1Behavior``.

    Args:
        behavior: State mapping, trace sequence, or behavior object.

    Returns:
        The normalized behavior.

    Raises:
        TypeError: If the value is not a supported behavior representation.
    """
    if isinstance(behavior, GR1Behavior):
        return behavior
    if isinstance(behavior, Mapping):
        return GR1Behavior([behavior])
    if isinstance(behavior, Sequence) and not isinstance(behavior, (str, bytes)):
        return GR1Behavior(cast(BehaviorStates, behavior))
    raise TypeError("GR(1) behavior must be a state mapping, trace sequence, or GR1Behavior")


def _contains_init_behavior(terms: List[GR1Term], trace: GR1Behavior) -> bool:
    """Check all initial terms at the first state.

    Args:
        terms: Initial terms.
        trace: Normalized behavior trace.

    Returns:
        Whether every initial term holds.
    """
    return all(_evaluate_core_at(term.core, trace, 0) for term in terms)


def _contains_inv_behavior(terms: List[GR1Term], trace: GR1Behavior) -> bool:
    """Check every complete invariant window in a behavior.

    Args:
        terms: Invariant terms.
        trace: Normalized behavior trace.

    Returns:
        Whether all required invariant windows hold.
    """
    for term in terms:
        if trace.loop_start is not None:
            invariant_times: Iterable[int] = range(len(trace.states))
        else:
            invariant_times = range(max(0, len(trace.states) - _core_next_depth(term.core)))
        if any(not _evaluate_core_at(term.core, trace, time) for time in invariant_times):
            return False
    return True


def _contains_liv_behavior(terms: List[GR1Term], trace: GR1Behavior) -> bool:
    """Check that every liveness term occurs in the repeating suffix.

    Args:
        terms: Liveness terms.
        trace: Normalized behavior trace.

    Returns:
        Whether all liveness terms recur in the loop.

    Raises:
        ValueError: If liveness is requested for a finite trace.
    """
    if not terms:
        return True
    if trace.loop_start is None:
        raise ValueError("LIV behavior checking requires an ultimately-periodic trace with loop_start")
    loop_times = range(trace.loop_start, len(trace.states))
    return all(any(_evaluate_core_at(term.core, trace, time) for time in loop_times) for term in terms)


def _parse_bucket_core(
    formula_text: str,
    parser: Optional[GR1CoreParser],
    var_map: FormulaVarMap,
) -> GR1CoreFormula:
    """Parse typed bucket text or construct a legacy text-only core.

    Args:
        formula_text: User-facing bounded-next formula.
        parser: Optional typed parser.
        var_map: Legacy mapping from formula text to variable names.

    Returns:
        The constructed core formula.

    Raises:
        ValueError: If legacy variable metadata is missing.
    """
    if parser is not None:
        return parser.parse(formula_text)
    if formula_text not in var_map:
        raise ValueError(
            f"Missing var_map entry for formula: {formula_text!r}. "
            "Provide var_map[formula_text] = [list of variable names]."
        )
    return GR1CoreFormula.of(formula_text, [Var(variable) for variable in var_map[formula_text]])


def _bucket_expr(terms: List[GR1Term]) -> Any:
    """Conjoin one non-liveness bucket for implication checking.

    Args:
        terms: Terms in the bucket.

    Returns:
        The conjoined Z3 expression, or true for an empty bucket.
    """
    if not terms:
        return z3.BoolVal(True)
    return z3.And(*[cast(z3.BoolRef, term.core.expr) for term in terms])


# This is a proof-search budget, not a completeness bound. Horizon two
# discharges useful bounded-NEXT residuals while keeping ordinary refinement
# checks small. Some valid invariant implications require larger horizons or
# have no finite shift certificate at all.
_DEFAULT_INV_REFINEMENT_MAX_HORIZON = 2


def _init_terms_refine(  # noqa: WPS231
    source_init: List[GR1Term],
    source_inv: List[GR1Term],
    target_init: List[GR1Term],
    max_horizon: int = _DEFAULT_INV_REFINEMENT_MAX_HORIZON,
) -> bool:
    """Soundly prove INIT refinement, optionally using source invariants.

    INIT may have been reduced modulo its own invariant context.  If the
    pointwise INIT implication fails, a finite shifted closure of only the
    antecedent/source invariant may prove the target INIT.  Every source trace
    satisfying ``G(source_inv)`` satisfies that closure, so an UNSAT finite
    certificate is sound.  The horizon is an incomplete proof-search budget;
    SAT, UNKNOWN, or budget exhaustion means only that refinement was not proved.

    Args:
        source_init: Antecedent initial terms.
        source_inv: Antecedent globally invariant terms.
        target_init: Consequent initial terms.
        max_horizon: Inclusive finite proof-search budget.

    Returns:
        True when the local or a contextual finite implication is proved.

    Raises:
        ValueError: If ``max_horizon`` is negative.
    """
    if max_horizon < 0:
        raise ValueError("INIT refinement horizon must be nonnegative")

    source_init_expr = _bucket_expr(source_init)
    target_init_expr = _bucket_expr(target_init)
    if _implies(source_init_expr, target_init_expr):
        return True

    for horizon in range(max_horizon + 1):
        source_inv_closure = _shift_closed_inv_expr(source_inv, horizon)
        if _implies(z3.And(source_init_expr, source_inv_closure), target_init_expr):
            return True
    return False


def _inv_terms_refine(  # noqa: WPS231
    source_inv: List[GR1Term],
    target_inv: List[GR1Term],
    max_horizon: int = _DEFAULT_INV_REFINEMENT_MAX_HORIZON,
) -> bool:
    """Soundly prove invariant refinement by bounded source shift closure.

    For each target core ``phi``, search for a finite horizon ``h`` such that
    ``source_inv^[0:h] and not phi`` is unsatisfiable. Such an UNSAT result
    proves ``G(source_inv) => G(phi)`` because every globally invariant source
    trace satisfies every selected shifted copy. SAT or UNKNOWN means only
    that refinement was not proved at that horizon. This procedure is
    intentionally sufficient and incomplete.

    Args:
        source_inv: Globally repeated source invariant terms.
        target_inv: Target invariant terms proved independently.
        max_horizon: Inclusive finite proof-search budget.

    Returns:
        True exactly when every target term receives a finite UNSAT certificate.

    Raises:
        ValueError: If ``max_horizon`` is negative.
    """
    if max_horizon < 0:
        raise ValueError("Invariant refinement horizon must be nonnegative")

    for target in target_inv:
        target_expr = cast(Any, target.core.expr)
        proved = False
        for horizon in range(max_horizon + 1):
            source_closure = _shift_closed_inv_expr(source_inv, horizon)
            if _implies(source_closure, target_expr):
                proved = True
                break
        if not proved:
            return False
    return True


def _liv_terms_refine(  # noqa: WPS231 (explicit finite certificate search)
    invariant_terms: List[GR1Term],
    source_liv: List[GR1Term],
    target_liv: List[GR1Term],
) -> bool:
    """Discharge target liveness from source liveness or invariants.

    A target ``GF(phi)`` is soundly established when finite shifted source
    invariant closure proves ``phi``: this proves ``G(phi)``, hence ``GF(phi)``.
    W8 also combines that closure with each separate source liveness core.
    The finite horizon is only a proof-search budget; failure to find a
    certificate means not proved, rather than a semantic counterexample.

    Args:
        invariant_terms: Source invariant terms.
        source_liv: Source liveness terms.
        target_liv: Target liveness terms.

    Returns:
        Whether every target liveness obligation is discharged.
    """
    for target in target_liv:
        target_expr = cast(Any, target.core.expr)
        liveness_support = any(_implies(cast(Any, source.core.expr), target_expr) for source in source_liv)
        if liveness_support:
            continue
        proved = False
        for horizon in range(_DEFAULT_INV_REFINEMENT_MAX_HORIZON + 1):
            closure = _shift_closed_inv_expr(invariant_terms, horizon)
            supported = _implies(closure, target_expr) or any(
                _implies(z3.And(closure, source.core.expr), target_expr) for source in source_liv
            )
            if supported:
                proved = True
                break
        if not proved:
            return False
    return True


def _relax_non_liv_term(
    term: GR1Term,
    context: "GR1TermList",
    gamma_init_expr: Any,
    vars_to_elim: List[Var],
) -> GR1Term:
    """Relax one canonical INIT or INV term.

    Args:
        term: Canonical target term.
        context: Relaxation context.
        gamma_init_expr: Conjoined initial context expression.
        vars_to_elim: Base variables to eliminate.

    Returns:
        The projected term.

    Raises:
        AssertionError: If passed a liveness term.
        ValueError: If passed an unknown temporal tag.
    """
    term_expr = cast(z3.BoolRef, term.core.expr)
    if term.tag == GR1Tag.INIT:
        init_cores = [candidate.core for candidate in context.init_terms()]
        shifted_inv = _shifted_inv_guard_for_cores(context.inv_terms(), init_cores + [term.core])
        guard_expr = z3.And(gamma_init_expr, shifted_inv)
    elif term.tag == GR1Tag.INV:
        guard_expr = _shifted_inv_guard_for_cores(context.inv_terms(), [term.core])
    elif term.tag == GR1Tag.LIV:
        raise AssertionError("LIV terms are projected together after bucket transformation")
    else:
        raise ValueError(f"Unknown GR1Tag: {term.tag}")
    local_vars = _expand_elim_vars_from_exprs(vars_to_elim, guard_expr, term_expr)
    projected_expr = _qe_exists_relaxation(term_expr, guard_expr, local_vars)
    return _refined_term(term.tag, projected_expr)


def _project_liv_terms(
    terms: List[GR1Term],
    context: "GR1TermList",
    vars_to_elim: List[Var],
) -> List[GR1Term]:
    """Project and globally reduce a collection of liveness terms.

    Args:
        terms: Context and target liveness terms.
        context: Relaxation context.
        vars_to_elim: Base variables to eliminate.

    Returns:
        Reduced projected liveness terms.
    """
    projected: List[GR1Term] = []
    for term in terms:
        term_expr = cast(Any, term.core.expr)
        shifted_inv = _shifted_inv_guard_for_cores(context.inv_terms(), [term.core])
        local_vars = _expand_elim_vars_from_exprs(vars_to_elim, shifted_inv, term_expr)
        projection = _qe_exists_relaxation(term_expr, shifted_inv, local_vars)
        projected.append(GR1Term(GR1Tag.LIV, _make_qe_core(projection)))
    return _remove_redundant_liv_terms(projected)


def _raw_relaxation_cave(target: "GR1TermList", context: "GR1TermList", vars_to_elim: List[Var]) -> "GR1TermList":
    """Construct Algorithm 2's standalone decomposed finite projection.

    Both empty safety buckets denote true. Context-relative simplification is
    deliberately outside this boundary: strongestness applies to this result.

    Args:
        target: Target obligation to project.
        context: Context constraining the elimination.
        vars_to_elim: Variables to eliminate.

    Returns:
        The projected term list.
    """
    gamma_init_expr = _and_expr(context.init_terms())
    terms: List[GR1Term] = []
    for tag, bucket in ((GR1Tag.INIT, target.init_terms()), (GR1Tag.INV, target.inv_terms())):
        combined = _conjoin_bucket_terms(tag, bucket) or _true_bucket_term(tag)
        projected = _relax_non_liv_term(combined, context, gamma_init_expr, vars_to_elim)
        if tag == GR1Tag.INIT:
            _append_nontrivial_init(terms, projected)
        elif not _equivalent(projected.core.expr, z3.BoolVal(True)):
            terms.append(projected)
    terms.extend(_project_liv_terms(context.liv_terms() + target.liv_terms(), context, vars_to_elim))
    return GR1TermList(terms)


class GR1TermList(TermList):
    """
    A conjunction of GR(1) terms.

    Multiple LIV terms remain separate:
      LIV(φ1), LIV(φ2) means □◇φ1 ∧ □◇φ2,
    not □◇(φ1 ∧ φ2).

    Simplification canonicalizes only uniform global Next shifts of LIV cores;
    INIT and INV retain their original depths.
    """

    def __init__(self, term_list: Optional[List[GR1Term]] = None):
        """Initialize from tagged terms; an omitted list denotes true.

        Args:
            term_list: Term list.
        """
        super().__init__(term_list=term_list or [])

    def init_terms(self) -> List[GR1Term]:
        """Return initial-state terms in their existing order.

        Returns:
            The computed List[GR1Term] result.
        """
        return [cast(GR1Term, t) for t in self.terms if cast(GR1Term, t).tag == GR1Tag.INIT]

    def inv_terms(self) -> List[GR1Term]:
        """Return invariant terms in their existing order.

        Returns:
            The computed List[GR1Term] result.
        """
        return [cast(GR1Term, t) for t in self.terms if cast(GR1Term, t).tag == GR1Tag.INV]

    def liv_terms(self) -> List[GR1Term]:
        """Return separate liveness terms in their existing order.

        Returns:
            The computed List[GR1Term] result.
        """
        return [cast(GR1Term, t) for t in self.terms if cast(GR1Term, t).tag == GR1Tag.LIV]

    def to_bucket_dict(self) -> Dict[str, List[str]]:
        """Serialize readable formula text grouped by temporal bucket.

        Returns:
            The computed Dict[str, List[str]] result.
        """
        return {
            "init": [t.core.text for t in self.init_terms()],
            "inv": [t.core.text for t in self.inv_terms()],
            "liv": [t.core.text for t in self.liv_terms()],
        }

    def copy(self) -> "GR1TermList":
        """Copy every term while preserving bucket order.

        Returns:
            The computed 'GR1TermList' result.
        """
        return GR1TermList([cast(GR1Term, t).copy() for t in self.terms])

    @staticmethod
    def from_bucket_formulas(
        *,
        init: Optional[List[GR1CoreFormula]] = None,
        inv: Optional[List[GR1CoreFormula]] = None,
        liv: Optional[List[GR1CoreFormula]] = None,
    ) -> "GR1TermList":
        """Construct a GR1TermList from formulas grouped by bucket.

        Multiple formulas in each bucket are conjunctive. In particular,
        multiple liveness formulas remain separate liveness terms:
          ∧_i □◇φ_i.

        Args:
            init: Initial-condition formulas.
            inv: Invariant formulas.
            liv: Liveness formulas.

        Returns:
            The computed 'GR1TermList' result.
        """
        terms: List[GR1Term] = []
        for f in init or []:
            terms.append(GR1Term(GR1Tag.INIT, f))
        for f in inv or []:
            terms.append(GR1Term(GR1Tag.INV, f))
        for f in liv or []:
            terms.append(GR1Term(GR1Tag.LIV, f))
        return GR1TermList(terms)

    @staticmethod
    def from_bucket_strings(
        *,
        init: Optional[List[str]] = None,
        inv: Optional[List[str]] = None,
        liv: Optional[List[str]] = None,
        var_map: Optional[FormulaVarMap] = None,
        variable_sorts: Optional[VariableSortMap] = None,
    ) -> "GR1TermList":
        """Convenience constructor when formulas are strings.

        With ``variable_sorts``, formulas are parsed into Z3-backed bounded-next
        cores. Without it, ``var_map`` preserves the legacy text-only behavior.

        Args:
            init: Initial-condition formulas.
            inv: Invariant formulas.
            liv: Liveness formulas.
            var_map: Mapping from formula text to variable names.
            variable_sorts: Declared sort for each base variable.

        Returns:
            The computed 'GR1TermList' result.

        Raises:
            ValueError: If the supplied value is invalid.
        """
        if variable_sorts is not None and var_map is not None:
            raise ValueError("Provide either variable_sorts or var_map, not both")

        parser = GR1CoreParser(variable_sorts) if variable_sorts is not None else None
        var_map = var_map or {}

        return GR1TermList.from_bucket_formulas(
            init=[_parse_bucket_core(text, parser, var_map) for text in (init or [])],
            inv=[_parse_bucket_core(text, parser, var_map) for text in (inv or [])],
            liv=[_parse_bucket_core(text, parser, var_map) for text in (liv or [])],
        )

    def __hash__(self) -> int:
        """Hash the ordered conjunction of terms.

        Returns:
            The computed int result.
        """
        return hash(tuple(self.terms))

    def contains_behavior(self, behavior: Any) -> bool:
        """Check a finite trace or ultimately-periodic lasso against this GR(1) list.

                A plain sequence is interpreted as a finite prefix and can check INIT
                and every complete INV window. LIV requires ``GR1Behavior`` with a
                ``loop_start``, because recurrence cannot be established by a finite
                prefix. On a lasso, each liveness core must occur in the repeating loop.

        Args:
            behavior: Behavior or trace to check.

        Returns:
            The computed bool result.

        """
        trace = _coerce_gr1_behavior(behavior)
        return (
            _contains_init_behavior(self.init_terms(), trace)
            and _contains_inv_behavior(self.inv_terms(), trace)
            and _contains_liv_behavior(self.liv_terms(), trace)
        )

    def simplify(self, context: Optional["GR1TermList"] = None) -> "GR1TermList":
        """Apply post-CAVE redundancy and optional assumption-relative reduction.

        Exact CAVE evaluation precedes this method. Internal reduction first
        removes redundancies within and across this term list's GR(1) buckets;
        a supplied context is then used separately for assume-guarantee
        redundancy. Neither stage changes the six CAVE formulas.

        Args:
            context: Context used by the operation.

        Returns:
            The computed 'GR1TermList' result.
        """
        if any(cast(GR1Term, term).core.expr is None for term in self.terms):
            return _deduplicate_text_terms(self.terms)
        semantic_context = _usable_simplification_context(context)
        return _simplify_expression_terms(self, semantic_context)

    def to_pretty_string(self, compact: bool = False) -> str:
        """Return a read-only Unicode rendering of this GR(1) term list.

        Every INIT core is listed separately, every INV core receives its own
        ``□``, and every LIV core retains its own ``□◇`` operator. Empty
        bucket-view sections are omitted; a completely empty list renders as
        ``true``. No terms, formulas, metadata, or serialization are changed.

        Args:
            compact: Return one semantic conjunction instead of bucket lines.

        Returns:
            Unicode user-facing GR(1) text.
        """
        init = [_unicode_core_text(term.core) for term in self.init_terms()]
        inv = [_unicode_core_text(term.core) for term in self.inv_terms()]
        liv = [_unicode_core_text(term.core) for term in self.liv_terms()]

        if compact:
            clauses: List[str] = []
            clauses.extend(f"({core})" for core in init)
            clauses.extend(f"□({core})" for core in inv)
            # Always delimit the complete justice core.  Without these outer
            # parentheses, a conjunctive core such as ``p ∧ q`` is rendered as
            # ``□◇p ∧ q``, which misleadingly places only ``p`` in the scope
            # of the temporal operator.
            clauses.extend(f"□◇({core})" for core in liv)
            return " ∧ ".join(clauses) if clauses else "true"

        if not init and not inv and not liv:
            return "true"
        lines: List[str] = []
        if init:
            lines.append("INIT:")
            lines.extend(f"  {core}" for core in init)
        if inv:
            lines.append("INV:")
            lines.extend(f"  □({core})" for core in inv)
        if liv:
            lines.append("LIV:")
            lines.extend(f"  □◇({core})" for core in liv)
        return "\n".join(lines)

    def refines(self, other: "GR1TermList") -> bool:
        """Sufficient GR(1) refinement check using Z3 expressions.

                INIT first uses pointwise implication, then a bounded iterative
                shift-closure of only the antecedent/source invariant terms.
                INV uses the same bounded source-closure proof strategy. An UNSAT
                finite-window certificate is sound; SAT means only that refinement
                was not proved within the budget.

                LIV is checked separately.  Every target liveness term must be
                established either by a pointwise-stronger source liveness core or by
                a bounded iterative shift-closure of the source invariant bucket.
                It also combines that closure with each source LIV core (W8).
                Closure alone proves the target globally and therefore recurrently.
                Its finite horizon is a proof-search budget, not a completeness bound.

                This remains a structured sufficient GR(1) check, not a general LTL
                implication solver.  In particular, separate source liveness terms are
                never conjoined inside one ``GF`` obligation.

        Args:
            other: Other term list or contract.

        Returns:
            The computed bool result.
        """
        self._require_exprs("self")
        other._require_exprs("other")

        checks = [
            _init_terms_refine(self.init_terms(), self.inv_terms(), other.init_terms()),
            _inv_terms_refine(self.inv_terms(), other.inv_terms()),
            _liv_terms_refine(self.inv_terms(), self.liv_terms(), other.liv_terms()),
        ]

        return all(checks)

    def is_empty(self) -> bool:
        """Return True when finite-window SMT checks prove no infinite behavior.

                The checks cover inconsistent initial/invariant cores and liveness cores
                that cannot occur under the invariant. False is conservative for harder
                overlap-consistency cases not decided by these finite checks.

        Returns:
            The computed bool result.
        """
        self._require_exprs("self")

        init_expr = _and_expr(self.init_terms())
        if self.init_terms():
            init_guard = _shifted_inv_guard_for_cores(
                self.inv_terms(),
                [term.core for term in self.init_terms()],
            )
            if not _is_sat(z3.And(init_expr, init_guard)):
                return True

        if self.inv_terms() and not _is_sat(_and_expr(self.inv_terms())):
            return True

        for liv_term in self.liv_terms():
            inv_guard = _shifted_inv_guard_for_cores(self.inv_terms(), [liv_term.core])
            if not _is_sat(z3.And(inv_guard, cast(Any, liv_term.core.expr))):
                return True
        return False

    def get_terms_with_vars(self, vars_to_seek: List[Var]) -> "GR1TermList":
        """Return terms mentioning any sought base variable.

        Args:
            vars_to_seek: Vars to seek.

        Returns:
            The computed 'GR1TermList' result.
        """
        return GR1TermList(
            [
                cast(GR1Term, term)
                for term in self.terms
                if any(cast(GR1Term, term).contains_var(variable) for variable in vars_to_seek)
            ]
        )

    def elim_vars_by_refining(
        self,
        context: "GR1TermList",
        vars_to_elim: List[Var],
        simplify: bool,
        tactics_order: List[int],
    ) -> Tuple["GR1TermList", TacticStatistics]:
        """SMT-style refinement elimination for GR(1).

        INIT:
            forall p. [gamma_init ∧ Gamma_inv^[0:h_B] => phi_init],
            B={gamma_init, phi_init}

        INV:
            forall p. [Gamma_inv^[0:h_B] => phi_inv], B={phi_inv}

        Every LIV target, including elimination-free targets:
            construct GF(psi_i,0) from the invariant window alone, and
            G(psi_i,j) from the window and each context liveness core j.
            Synthetic horizon: d(phi_i); genuine: max(d(phi_i), d(gamma_liv,j)).
            Project every branch before deterministic tag-preserving selection.
            No relevance, viability, or mixed-wrapper dominance filtering occurs.

        Context liveness terms are processed separately and are not conjoined.

        Args:
            context: Context used by the operation.
            vars_to_elim: Variables to eliminate.
            simplify: Whether to simplify the resulting formulas.
            tactics_order: Preferred quantifier-elimination tactic order.

        Returns:
            The computed Tuple['GR1TermList', TacticStatistics] result.
        """
        self._require_exprs("self")
        context._require_exprs("context")
        gamma_init_expr = _and_expr(context.init_terms())
        new_terms: List[GR1Term] = []
        combined_init = _conjoin_bucket_terms(GR1Tag.INIT, self.init_terms()) or _true_bucket_term(GR1Tag.INIT)
        combined_inv = _conjoin_bucket_terms(GR1Tag.INV, self.inv_terms())
        refined_init = _refine_gr1_term(combined_init, context, gamma_init_expr, vars_to_elim)
        _append_nontrivial_init(new_terms, refined_init)
        if combined_inv is not None:
            new_terms.append(_refine_gr1_term(combined_inv, context, gamma_init_expr, vars_to_elim))
        for liv_term in self.liv_terms():
            new_terms.append(_refine_gr1_term(liv_term, context, gamma_init_expr, vars_to_elim))

        res = GR1TermList(new_terms)
        if simplify:
            res = res.simplify(context=context)

        stats: TacticStatistics = []
        return res, stats

    def elim_vars_by_relaxing(
        self,
        context: "GR1TermList",
        vars_to_elim: List[Var],
        simplify: bool,
        tactics_order: List[int],
    ) -> Tuple["GR1TermList", TacticStatistics]:
        """SMT-style relaxation elimination for GR(1).

        INIT:
            exists p. [gamma_init ∧ Gamma_inv^[0:h_B] ∧ phi_init],
            B={gamma_init, phi_init}

        INV:
            exists p. [Gamma_inv^[0:h_B] ∧ phi_inv], B={phi_inv}, stored as INV

        LIV:
            project every context and target liveness core separately, discard
            trivial projections, and remove equivalent or implied cores.

        The remaining projected liveness terms remain separate LIV conjuncts.
        An empty INV bucket is true and still projects the invariant context.
        With simplify=False this returns the raw independently decomposed CAVE
        construction. With simplify=True it subsequently reduces obligations
        relative to context; standalone strongestness concerns the raw result.

        Args:
            context: Context used by the operation.
            vars_to_elim: Variables to eliminate.
            simplify: Whether to simplify the resulting formulas.
            tactics_order: Preferred quantifier-elimination tactic order.

        Returns:
            The computed Tuple['GR1TermList', TacticStatistics] result.
        """
        self._require_exprs("self")
        context._require_exprs("context")
        res = _raw_relaxation_cave(self, context, vars_to_elim)
        if simplify:
            res = res.simplify(context=context)

        stats: TacticStatistics = []
        return res, stats

    def elim_vars_by_relaxing_assumptions(
        self,
        context: "GR1TermList",
        vars_to_elim: List[Var],
        simplify: bool,
        tactics_order: List[int],
    ) -> Tuple["GR1TermList", TacticStatistics]:
        """Preserve canonical buckets across redundant assumption saturation.

        Generic composition performs a final guarantee relaxation in the
        composed assumption context. If neither the target nor context still
        mentions a variable to hide, conjoining that context is redundant at
        contract level but replaces canonical GR(1) cores with saturated
        Boolean encodings. Keep the canonical cores in that case. If hiding is
        still required, use ordinary GR(1) relaxation because assumptions may
        be essential to the projection.

        Args:
            context: Context used by the operation.
            vars_to_elim: Variables to eliminate.
            simplify: Whether to simplify the resulting formulas.
            tactics_order: Preferred quantifier-elimination tactic order.

        Returns:
            The computed Tuple['GR1TermList', TacticStatistics] result.

        Args:
            context: Context constraining the elimination.
            vars_to_elim: Variables to eliminate.
            simplify: Whether to simplify before elimination.
            tactics_order: Ordered tactic identifiers.

        Returns:
            The projected terms and tactic statistics.
        """
        target_needs_elimination = bool(self.get_terms_with_vars(vars_to_elim).terms)
        context_aids_elimination = bool(context.get_terms_with_vars(vars_to_elim).terms)
        if not target_needs_elimination and not context_aids_elimination:
            result = self.copy()
            if not result.init_terms():
                # At this point composition has already combined the two raw
                # CAVE guarantee projections. With an empty target INIT, the
                # paper still evaluates its existential bound against that
                # combined invariant context. Materialize this raw boundary
                # consequence before any later cross-bucket presentation pass.
                empty_init = _true_bucket_term(GR1Tag.INIT)
                projected_init = _relax_non_liv_term(
                    empty_init,
                    result,
                    z3.BoolVal(True),
                    vars_to_elim,
                )
                augmented_terms = list(cast(List[GR1Term], result.terms))
                _append_nontrivial_init(augmented_terms, projected_init)
                result = GR1TermList(augmented_terms)
            if simplify:
                result = result.simplify()
            return result, []
        return self.elim_vars_by_relaxing(
            context,
            vars_to_elim,
            simplify,
            tactics_order,
        )

    def elim_vars_by_relaxing_quotient_context(
        self,
        context: "GR1TermList",
        vars_to_elim: List[Var],
        simplify: bool,
        tactics_order: List[int],
    ) -> Tuple["GR1TermList", TacticStatistics]:
        """Project quotient assumptions with shift-closed divisor guarantees.

        Keeping ``self`` as the target and divisor guarantees as ``context``
        lets the ordinary GR(1) INV rule construct Gamma_inv^[0:h] through the
        target horizon instead of losing provenance in a prior TermList union.
        INIT and separate LIV projection use the same canonical buckets.

        Args:
            context: Context used by the operation.
            vars_to_elim: Variables to eliminate.
            simplify: Whether to simplify the resulting formulas.
            tactics_order: Preferred quantifier-elimination tactic order.

        Returns:
            The computed Tuple['GR1TermList', TacticStatistics] result.

        Args:
            context: Context constraining the elimination.
            vars_to_elim: Variables to eliminate.
            simplify: Whether to simplify before elimination.
            tactics_order: Ordered tactic identifiers.

        Returns:
            The projected terms and tactic statistics.
        """
        result, stats = self.elim_vars_by_relaxing(
            context,
            vars_to_elim,
            simplify=False,
            tactics_order=tactics_order,
        )
        # Divisor guarantees aid projection but are not assumptions of the
        # quotient result. Simplifying in that context would incorrectly erase
        # projected obligations such as LIV(p) merely because context has p.
        return (result.simplify() if simplify else result), stats

    def elim_vars_by_refining_quotient_context(
        self,
        divisor_guarantees: "GR1TermList",
        system_assumptions: "GR1TermList",
        vars_to_elim: List[Var],
        simplify: bool,
        tactics_order: List[int],
    ) -> Tuple["GR1TermList", TacticStatistics]:
        """Refine canonical targets using canonical divisor guarantees.

        System assumptions are deliberately not merged into this first CAVE
        context: generic quotient processes them in its following refinement
        pass. Merging them here changes canonical cores (for example ``r=q``)
        into guarded predicates (``p -> r``) before GR(1) bucket rules run.

        Args:
            divisor_guarantees: Divisor guarantees.
            system_assumptions: System assumptions.
            vars_to_elim: Variables to eliminate.
            simplify: Whether to simplify the resulting formulas.
            tactics_order: Preferred quantifier-elimination tactic order.

        Returns:
            The computed Tuple['GR1TermList', TacticStatistics] result.

        Args:
            divisor_guarantees: Guarantees of the known component.
            system_assumptions: Assumptions of the target system.
            vars_to_elim: Variables to eliminate.
            simplify: Whether to simplify before elimination.
            tactics_order: Ordered tactic identifiers.

        Returns:
            The projected terms and tactic statistics.
        """
        del system_assumptions
        return self.elim_vars_by_refining(
            divisor_guarantees,
            vars_to_elim,
            simplify,
            tactics_order,
        )

    def _require_exprs(self, where: str) -> None:
        """Reject operations whose terms lack executable Z3 expressions.

        Args:
            where: Label identifying the checked expression collection.

        Raises:
            NotImplementedError: If the supplied value is invalid.
        """
        missing = []
        for i, t_any in enumerate(self.terms):
            t = cast(GR1Term, t_any)
            if t.core.expr is None:
                missing.append(f"{where}[{i}] {t.tag.value}: {t.core.text}")
        if missing:
            raise NotImplementedError(
                "Z3-based GR(1) elimination requires core.expr for every term.\n"
                + "Missing expressions in:\n- "
                + "\n- ".join(missing)
            )


# ---------------------------------------------------------------------------
# GR(1) contract wrapper
# ---------------------------------------------------------------------------

ser_gr1_termlist = TypedDict(
    "ser_gr1_termlist",
    {"init": List[str], "inv": List[str], "liv": List[str]},
)

ser_gr1_contract = TypedDict(
    "ser_gr1_contract",
    {
        "input_vars": List[str],
        "output_vars": List[str],
        "assumptions": ser_gr1_termlist,
        "guarantees": ser_gr1_termlist,
    },
)


def _z3_sort_name(sort: Any) -> str:
    """Return the portable name of a supported Z3 sort.

    Args:
        sort: Z3 sort of the variable.

    Returns:
        The computed str result.

    Raises:
        ValueError: If the supplied value is invalid.
    """
    if sort == z3.BoolSort():
        return "bool"
    if sort == z3.IntSort():
        return "int"
    if sort == z3.RealSort():
        return "real"
    raise ValueError(f"Unsupported GR(1) variable sort: {sort}")


def _record_inferred_sort(inferred: Dict[str, str], name: str, z3_var: Any) -> None:
    """Record one flattened variable's base sort consistently.

    Args:
        inferred: Sorts accumulated by base name.
        name: Flattened variable name.
        z3_var: Typed Z3 variable.

    Raises:
        ValueError: If the base already has a different sort.
    """
    base, _ = _parse_flat_name(name)
    sort_name = _z3_sort_name(z3_var.sort())
    if base in inferred and inferred[base] != sort_name:
        raise ValueError(f"Variable {base!r} has inconsistent sorts: {inferred[base]} and {sort_name}")
    inferred[base] = sort_name


def _infer_termlist_sorts(termlist: GR1TermList, inferred: Dict[str, str]) -> None:
    """Add all executable core sorts from one term list.

    Args:
        termlist: Source term list.
        inferred: Sorts accumulated by base name.
    """
    for term_any in termlist.terms:
        term = cast(GR1Term, term_any)
        if term.core.expr is not None:
            for name, z3_var in _z3_vars_in_expr(term.core.expr).items():
                _record_inferred_sort(inferred, name, z3_var)


def _infer_variable_sorts(*termlists: GR1TermList) -> Dict[str, str]:
    """Infer and validate base-variable sorts from Z3-backed cores.

    Args:
        *termlists: Termlists.

    Returns:
        The computed Dict[str, str] result.
    """
    inferred: Dict[str, str] = {}
    for termlist in termlists:
        _infer_termlist_sorts(termlist, inferred)
    return inferred


def _machine_core_payload(core: GR1CoreFormula) -> Optional[Dict[str, Any]]:
    """Serialize an exact Z3 core alongside its user-facing source text.

    Args:
        core: GR(1) core formula to process.

    Returns:
        The computed Optional[Dict[str, Any]] result.
    """
    if core.expr is None:
        return None
    if core.serialized_machine is not None:
        return copy.deepcopy(core.serialized_machine)
    variable_exprs = [core.expr]
    if core.raw_expr is not None:
        variable_exprs.append(core.raw_expr)
    variables = {}
    for expr in variable_exprs:
        variables.update(
            {name: _z3_sort_name(z3_var.sort()) for name, z3_var in sorted(_z3_vars_in_expr(expr).items())}
        )
    payload = {
        "smt2": core.expr.sexpr(),
        "variables": variables,
        "generated": core.syntax is None,
    }
    if core.next_depth > _expr_next_depth(core.expr):
        payload["next_depth"] = core.next_depth
    if core.raw_expr is not None:
        payload["raw_smt2"] = core.raw_expr.sexpr()
    return payload


def _core_from_machine_payload(text: str, payload: Dict[str, Any]) -> GR1CoreFormula:
    """Restore an exact generated core from the versioned machine payload.

    Args:
        text: Human-readable formula text.
        payload: Payload.

    Returns:
        The computed GR1CoreFormula result.

    Raises:
        ValueError: If the supplied value is invalid.
    """
    smt2 = payload.get("smt2")
    variables = payload.get("variables")
    if not isinstance(smt2, str) or not isinstance(variables, dict):
        raise ValueError("Invalid serialized GR(1) machine expression")

    parser = GR1CoreParser(cast(Dict[str, Any], variables))
    declarations = {name: z3.Const(name, sort) for name, sort in parser._sorts.items()}
    parsed = z3.parse_smt2_string(f"(assert {smt2})", decls=declarations)
    if len(parsed) != 1:
        raise ValueError("Serialized GR(1) machine expression must contain one assertion")
    raw_expr = None
    raw_smt2 = payload.get("raw_smt2")
    if isinstance(raw_smt2, str):
        raw_parsed = z3.parse_smt2_string(f"(assert {raw_smt2})", decls=declarations)
        if len(raw_parsed) == 1:
            raw_expr = raw_parsed[0]
    next_depth = payload.get("next_depth", _expr_next_depth(parsed[0]))
    if not isinstance(next_depth, int) or next_depth < 0:
        raise ValueError("Invalid serialized GR(1) next depth")
    restored = _make_core_from_expr(parsed[0], text=text, raw_expr=raw_expr, next_depth=next_depth)
    return GR1CoreFormula(
        text=restored.text,
        _vars=restored._vars,
        expr=restored.expr,
        syntax=restored.syntax,
        raw_expr=restored.raw_expr,
        serialized_machine=copy.deepcopy(payload),
        next_depth=restored.next_depth,
    )


def _machine_bucket_payload(termlist: GR1TermList) -> MachineBucketPayload:
    """Serialize machine expressions in the same order as the user buckets.

    Args:
        termlist: Termlist.

    Returns:
        The computed Dict[str, List[Optional[Dict[str, Any]]]] result.
    """
    return {
        "init": [_machine_core_payload(term.core) for term in termlist.init_terms()],
        "inv": [_machine_core_payload(term.core) for term in termlist.inv_terms()],
        "liv": [_machine_core_payload(term.core) for term in termlist.liv_terms()],
    }


def _contract_bucket_dicts(contract: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Validate and return serialized assumption and guarantee buckets.

    Args:
        contract: Serialized contract dictionary.

    Returns:
        The assumption and guarantee bucket dictionaries.

    Raises:
        ValueError: If required keys or bucket dictionaries are missing.
    """
    for key in ("assumptions", "guarantees", "input_vars", "output_vars"):
        if key not in contract:
            raise ValueError(f"Passed dictionary does not have key {key}.")
    assumptions = contract["assumptions"]
    guarantees = contract["guarantees"]
    if not isinstance(assumptions, dict) or not isinstance(guarantees, dict):
        raise ValueError("assumptions/guarantees must be dicts with keys: init, inv, liv")
    return assumptions, guarantees


def _serialized_variable_sorts(
    contract: Dict[str, Any],
    var_map: Optional[FormulaVarMap],
    variable_sorts: Optional[VariableSortMap],
) -> Optional[VariableSortMap]:
    """Resolve explicit or embedded sort declarations.

    Args:
        contract: Serialized contract dictionary.
        var_map: Optional legacy variable map.
        variable_sorts: Explicit sort declarations.

    Returns:
        The explicit or embedded declarations, when available.

    Raises:
        ValueError: If embedded declarations are not a dictionary.
    """
    if variable_sorts is not None or var_map is not None:
        return variable_sorts
    embedded_sorts = contract.get("variable_sorts")
    if embedded_sorts is None:
        return None
    if not isinstance(embedded_sorts, dict):
        raise ValueError("variable_sorts must be a name-to-sort dictionary")
    return cast(VariableSortMap, embedded_sorts)


def _serialized_machine(contract: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate and return the optional versioned machine payload.

    Args:
        contract: Serialized contract dictionary.

    Returns:
        The validated machine dictionary, when present.

    Raises:
        ValueError: If the payload has an unsupported shape or version.
    """
    machine = contract.get("gr1_machine")
    if machine is None:
        return None
    if not isinstance(machine, dict) or machine.get("version") != 1:
        raise ValueError("Unsupported or invalid GR(1) machine serialization version")
    return machine


def _load_serialized_core(
    parser: GR1CoreParser,
    machine_section: Dict[str, Any],
    tag: str,
    text: str,
    index: int,
) -> GR1CoreFormula:
    """Restore exact machine data when present, otherwise parse readable text.

    Args:
        parser: Typed GR(1) core parser.
        machine_section: Machine payload for one contract side.
        tag: Temporal bucket tag.
        text: Human-readable formula text.
        index: Formula position in the bucket.

    Returns:
        The restored core formula.

    Raises:
        ValueError: If neither representation can be restored.
    """
    payloads = machine_section.get(tag, [])
    payload = payloads[index] if isinstance(payloads, list) and index < len(payloads) else None
    # QE-generated cores carry raw_smt2 and must use exact machine data (their
    # generated rational text may be parseable yet lose sort context). Parsed
    # user formulas keep their AST by preferring readable text.
    if isinstance(payload, dict) and (isinstance(payload.get("raw_smt2"), str) or payload.get("generated") is True):
        return _core_from_machine_payload(text, payload)
    try:
        return parser.parse(text)
    except ValueError:
        if isinstance(payload, dict):
            return _core_from_machine_payload(text, payload)
        raise


def _load_serialized_buckets(
    bucket_text: Dict[str, Any],
    machine_section: Optional[Dict[str, Any]],
    var_map: Optional[FormulaVarMap],
    variable_sorts: Optional[VariableSortMap],
) -> GR1TermList:
    """Restore one serialized assumption or guarantee bucket collection.

    Args:
        bucket_text: Human-readable temporal buckets.
        machine_section: Optional machine payload for the same contract side.
        var_map: Optional legacy variable map.
        variable_sorts: Optional sort declarations.

    Returns:
        The restored term list.

    Raises:
        ValueError: If a bucket is not a list of formula strings.
    """
    if machine_section is None or var_map is not None:
        return GR1TermList.from_bucket_strings(
            init=cast(List[str], bucket_text.get("init", [])),
            inv=cast(List[str], bucket_text.get("inv", [])),
            liv=cast(List[str], bucket_text.get("liv", [])),
            var_map=var_map,
            variable_sorts=variable_sorts,
        )
    parser = GR1CoreParser(variable_sorts or {})
    cores: Dict[str, List[GR1CoreFormula]] = {}
    for tag in ("init", "inv", "liv"):
        texts = bucket_text.get(tag, [])
        if not isinstance(texts, list) or not all(isinstance(item, str) for item in texts):
            raise ValueError(f"{tag} bucket must be a list of strings")
        cores[tag] = [
            _load_serialized_core(parser, machine_section, tag, text, index) for index, text in enumerate(texts)
        ]
    return GR1TermList.from_bucket_formulas(init=cores["init"], inv=cores["inv"], liv=cores["liv"])


def _flatten_boolean_operator(expr: Any, predicate: Any) -> List[Any]:
    """Flatten one associative Boolean operator without changing its atoms.

    Args:
        expr: Expression to flatten.
        predicate: Test identifying the associative operator.

    Returns:
        Flattened expression atoms.
    """
    if predicate(expr):
        flattened = []
        for child in expr.children():
            flattened.extend(_flatten_boolean_operator(child, predicate))
        return flattened
    return [expr]


def _unique_equivalent_exprs(exprs: List[Any]) -> List[Any]:
    """Remove semantically equivalent expressions while preserving order.

    Args:
        exprs: Expressions to deduplicate.

    Returns:
        First representative of each equivalence class.
    """
    unique: List[Any] = []
    for expr in exprs:
        if not any(_equivalent(expr, existing) for existing in unique):
            unique.append(expr)
    return unique


def _pretty_core_lines(core: GR1CoreFormula) -> List[str]:
    """Render one core as compact conjunction lines in bounded-Next syntax.

    Args:
        core: Core formula to render.

    Returns:
        User-facing conjunction lines.
    """
    if core.expr is None:
        return [core.text]
    if core.raw_expr is None and core.syntax is not None:
        return [core.text]
    atoms = _flatten_boolean_operator(core.expr, z3.is_and)
    return [_expr_to_user_text(atom) for atom in _unique_equivalent_exprs(atoms)]


def _effective_init_guarantee_exprs(contract: "GR1IoContract") -> List[Any]:
    """Return display-only INIT guarantee atoms reduced under assumptions.

    Stored formulas are untouched. An atom is hidden only when the composed
    INIT/INV assumption context proves it.

    Args:
        contract: Contract providing assumptions and guarantees.

    Returns:
        Non-redundant INIT guarantee atoms.
    """
    guarantee_expr = _and_expr(contract.g.init_terms())
    atoms = _flatten_boolean_operator(guarantee_expr, z3.is_and)
    assumption_guard = z3.And(_and_expr(contract.a.init_terms()), _and_expr(contract.a.inv_terms()))
    retained = [atom for atom in atoms if not _implies(assumption_guard, atom)]
    return _unique_equivalent_exprs(retained)


def _assumptions_establish_liv(contract: "GR1IoContract", target: GR1Term) -> bool:
    """Check ``GF(support) and G(inv) => GF(target)`` for assumption supports.

    Args:
        contract: Contract providing assumption support.
        target: Liveness guarantee to check.

    Returns:
        Whether assumptions establish the target.
    """
    for support in contract.a.liv_terms():
        shifted_inv = _shifted_inv_guard_for_cores(contract.a.inv_terms(), [support.core, target.core])
        if _implies(z3.And(shifted_inv, support.core.expr), target.core.expr):
            return True
    return False


def _assumption_context_for_guarantee_bucket(
    assumptions: GR1TermList,
    guarantee_terms: List[GR1Term],
    include_init: bool,
) -> Any:
    """Build the shifted assumption context valid for a displayed safety bucket.

    Args:
        assumptions: Assumption terms providing context.
        guarantee_terms: Guarantee terms whose horizon is required.
        include_init: Whether to include initial assumptions.

    Returns:
        Shifted assumption context expression.
    """
    horizon = max((_core_next_depth(term.core) for term in guarantee_terms), default=0)
    invariant_context = _shift_closed_inv_expr(assumptions.inv_terms(), horizon)
    if include_init:
        return z3.simplify(z3.And(_and_expr(assumptions.init_terms()), invariant_context))
    return invariant_context


def _assumption_relative_safety_view(
    tag: GR1Tag,
    guarantee_terms: List[GR1Term],
    context: Any,
) -> List[GR1Term]:
    """Return an SMT-verified display residual for one guarantee safety bucket.

    The stored terms are only read. A residual is returned exactly when the
    shared reducer proves ``context & residual <=> context & original``.

    Args:
        tag: Safety bucket tag.
        guarantee_terms: Guarantee terms to reduce.
        context: Assumption context for equivalence checks.

    Returns:
        Display-only residual terms.
    """
    if not guarantee_terms:
        return []
    original = _and_expr(guarantee_terms)
    residual = _reduce_init_expr_under_invariant(original, context)
    if not _equivalent(z3.And(context, residual), z3.And(context, original)):
        return [term.copy() for term in guarantee_terms]
    if _equivalent(residual, b=True):
        return []
    return [GR1Term(tag, _make_core_from_expr(residual))]


def _assumption_implies_liv_target(assumptions: GR1TermList, target: GR1Term) -> bool:
    """Check the two structured rules for assumption-established guarantee LIV.

    First, shifted assumption invariants alone may imply the target core.
    Otherwise each assumption justice ``alpha`` is considered independently:
    ``Gamma_A_inv^[0:max(h_alpha,h_rho)] & alpha => rho``. Distinct assumption
    justices are never synchronized or conjoined to prove one target.

    Args:
        assumptions: Assumption terms providing support.
        target: Liveness target to check.

    Returns:
        Whether the assumptions establish the target.
    """
    target_expr = cast(Any, target.core.expr)
    invariant_guard = _shifted_inv_guard_for_cores(assumptions.inv_terms(), [target.core])
    if _implies(invariant_guard, target_expr):
        return True
    for support in assumptions.liv_terms():
        support_guard = _shifted_inv_guard_for_cores(
            assumptions.inv_terms(),
            [support.core, target.core],
        )
        if _implies(z3.And(support_guard, cast(Any, support.core.expr)), target_expr):
            return True
    return False


def _assumption_relative_guarantee_view(contract: "GR1IoContract") -> GR1TermList:
    """Compute a presentation-only guarantee list reduced under assumptions.

    INIT uses ``A_init`` and shifted ``A_inv``; INV uses shifted ``A_inv``.
    LIV uses invariant implication or one recurring assumption support at a
    time. The returned list is newly allocated and never replaces ``contract.g``.

    Args:
        contract: Contract whose guarantees are displayed.

    Returns:
        Assumption-relative guarantee view.
    """
    init_context = _assumption_context_for_guarantee_bucket(
        contract.a,
        contract.g.init_terms(),
        include_init=True,
    )
    inv_context = _assumption_context_for_guarantee_bucket(
        contract.a,
        contract.g.inv_terms(),
        include_init=False,
    )
    displayed_init = _assumption_relative_safety_view(GR1Tag.INIT, contract.g.init_terms(), init_context)
    displayed_inv = _assumption_relative_safety_view(GR1Tag.INV, contract.g.inv_terms(), inv_context)
    displayed_liv = []
    for term in contract.g.liv_terms():
        if _assumption_implies_liv_target(contract.a, term):
            continue
        original = cast(Any, term.core.expr)
        invariant_guard = _shifted_inv_guard_for_cores(contract.a.inv_terms(), [term.core])
        conjuncts = _flatten_boolean_operator(original, z3.is_and)
        residual = [conjunct for conjunct in conjuncts if not _implies(invariant_guard, conjunct)]
        candidate = z3.simplify(z3.And(*residual)) if residual else z3.BoolVal(True)
        if _equivalent(z3.And(invariant_guard, candidate), z3.And(invariant_guard, original)):
            displayed_liv.append(GR1Term(GR1Tag.LIV, _make_core_from_expr(candidate)))
        else:
            displayed_liv.append(term.copy())
    return GR1TermList(displayed_init + displayed_inv + displayed_liv)


def _apply_presentation_tactic(expr: Any, tactic_names: Tuple[str, ...]) -> Any:
    """Apply one configured Z3 presentation tactic.

    Args:
        expr: Expression to simplify.
        tactic_names: Tactics to compose.

    Returns:
        Simplified tactic result.
    """
    tactic = z3.Then(*tactic_names) if len(tactic_names) > 1 else z3.Tactic(tactic_names[0])
    goal = z3.Goal()
    goal.add(expr)
    result = tactic(goal)
    return z3.simplify(z3.And(*[z3.And(*subgoal) for subgoal in result]))


def _try_presentation_tactic(expr: Any, tactic_names: Tuple[str, ...]) -> Optional[Any]:
    """Apply a presentation tactic, ignoring unsupported combinations.

    Args:
        expr: Expression to simplify.
        tactic_names: Tactics to compose.

    Returns:
        Simplified result, or ``None`` when Z3 rejects the tactic.
    """
    try:
        return _apply_presentation_tactic(expr, tactic_names)
    except z3.Z3Exception:
        return None


def _presentation_tactic_candidates(expr: Any) -> List[Any]:
    """Return inexpensive quantifier-free display candidates.

    Tactics run on copies of the expression.  Callers must still prove a
    candidate equivalent before selecting it.

    Args:
        expr: Expression to simplify for presentation.

    Returns:
        Candidate presentation expressions.
    """
    candidates = [z3.simplify(expr)]
    tactic_sequences = (
        ("ctx-solver-simplify",),
        ("propagate-values",),
        ("simplify", "ctx-solver-simplify"),
        ("simplify", "propagate-values", "solve-eqs"),
    )
    for tactic_names in tactic_sequences:
        candidate = _try_presentation_tactic(expr, tactic_names)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _boolean_mode_implications(mode: Any, atom: Any) -> List[Any]:
    """Build directional implication candidates for one Boolean mode and atom.

    Args:
        mode: Boolean mode variable.
        atom: Existing Boolean atom.

    Returns:
        Directional implication candidates.
    """
    return [
        z3.Implies(mode, atom),
        z3.Implies(z3.Not(mode), atom),
        z3.Implies(atom, mode),
        z3.Implies(atom, z3.Not(mode)),
    ]


def _remove_implied_candidates(candidates: List[Any], context: Any) -> List[Any]:
    """Remove candidates implied by the remaining candidates.

    Args:
        candidates: Consequence candidates.
        context: Context for implication checks.

    Returns:
        Non-redundant candidates.
    """
    reduced = list(candidates)
    for index in range(len(reduced) - 1, -1, -1):
        others = reduced[:index] + reduced[index + 1 :]
        if others and _implies(z3.And(context, *others), reduced[index]):
            del reduced[index]
    return reduced


def _boolean_mode_candidates(nodes: List[Any], boolean_vars: List[Any]) -> List[Any]:
    """Build small Boolean-mode presentation candidates.

    Args:
        nodes: Existing expression nodes.
        boolean_vars: Boolean variables in the expression.

    Returns:
        Existing nodes and implication candidates.
    """
    atom_kinds = {z3.Z3_OP_LE, z3.Z3_OP_GE, z3.Z3_OP_EQ, z3.Z3_OP_DISTINCT}
    atoms = [
        node
        for node in nodes
        if node.sort() == z3.BoolSort()
        and (z3.is_const(node) or node.decl().kind() in atom_kinds)
        and _z3_ast_size(node) <= 8
    ]
    candidates = [node for node in nodes if node.sort() == z3.BoolSort() and _z3_ast_size(node) <= 8]
    for mode in boolean_vars:
        for atom in atoms:
            if not mode.eq(atom):
                candidates.extend(_boolean_mode_implications(mode, atom))
    return candidates


def _unique_simplified_expressions(candidates: List[Any]) -> List[Any]:
    """Simplify and deduplicate expressions by their S-expression.

    Args:
        candidates: Expressions to simplify.

    Returns:
        Unique simplified expressions.
    """
    unique: Dict[str, Any] = {}
    for candidate in candidates:
        simplified = z3.simplify(candidate)
        unique.setdefault(simplified.sexpr(), simplified)
    return list(unique.values())


def _presentation_boolean_mode_candidate(expr: Any, context: Any) -> Optional[Any]:
    """Mine a compact conjunction of verified consequences by Boolean mode.

    The search uses only existing small Boolean subexpressions, arithmetic
    atoms, and implications between a Boolean variable and an existing atom.
    It never invents arithmetic constants.  The result is returned only when
    its conjunction is equivalent to ``expr`` in ``context``.

    Args:
        expr: Expression to simplify.
        context: Context for equivalence checks.

    Returns:
        Verified compact candidate, if one is found.
    """
    nodes = _z3_nodes(expr)
    # GETVARS-PATCH: original (disabled) ---
    # boolean_vars = [variable for variable in get_vars(expr) if variable.sort() == z3.BoolSort()]
    # GETVARS-PATCH: replacement ---
    boolean_vars = [variable for variable in _z3_get_vars(expr) if variable.sort() == z3.BoolSort()]
    # GETVARS-PATCH: end ---
    if not boolean_vars:
        return None
    candidates = _boolean_mode_candidates(nodes, boolean_vars)
    consequences = [
        consequence
        for consequence in _unique_simplified_expressions(candidates)
        if _implies(z3.And(context, expr), consequence) and not _implies(context, consequence)
    ]
    reduced = _remove_implied_candidates(consequences, context)
    if not reduced:
        return None
    result = z3.simplify(z3.And(*reduced))
    if _equivalent(z3.And(context, result), z3.And(context, expr)):
        return result
    return None


def _presentation_safety_expr(expr: Any, context: Any) -> Any:
    """Select the smallest SMT-certified automatic display candidate.

    Args:
        expr: Expression to simplify.
        context: Context for equivalence checks.

    Returns:
        Smallest verified display expression.
    """
    candidates = _presentation_tactic_candidates(expr)
    mode_candidate = _presentation_boolean_mode_candidate(expr, context)
    if mode_candidate is not None:
        candidates.append(mode_candidate)
    verified = [candidate for candidate in candidates if _equivalent(z3.And(context, candidate), z3.And(context, expr))]
    if not verified:
        return expr
    return min(verified, key=lambda candidate: (_z3_ast_size(candidate), len(str(candidate)), str(candidate)))


def _presentation_safety_view(
    terms: GR1TermList,
    init_context: Any,
    inv_context: Any,
) -> GR1TermList:
    """Automatically simplify INIT/INV cores while retaining separate LIV terms.

    Args:
        terms: Terms to simplify for display.
        init_context: Context for initial terms.
        inv_context: Context for invariant terms.

    Returns:
        Simplified presentation term list.
    """
    init_terms = terms.init_terms()
    inv_terms = terms.inv_terms()
    displayed: List[GR1Term] = []
    if init_terms:
        if len(init_terms) == 1 and init_terms[0].core.syntax is not None and init_terms[0].core.raw_expr is None:
            displayed.append(init_terms[0].copy())
        else:
            displayed.append(
                GR1Term(
                    GR1Tag.INIT, _make_core_from_expr(_presentation_safety_expr(_and_expr(init_terms), init_context))
                )
            )
    if inv_terms:
        if len(inv_terms) == 1 and inv_terms[0].core.syntax is not None and inv_terms[0].core.raw_expr is None:
            displayed.append(inv_terms[0].copy())
        else:
            displayed.append(
                GR1Term(GR1Tag.INV, _make_core_from_expr(_presentation_safety_expr(_and_expr(inv_terms), inv_context)))
            )
    displayed.extend(term.copy() for term in terms.liv_terms())
    return GR1TermList(displayed)


def _verified_presentation_bucket_candidate(
    original: List[GR1Term], candidate: List[GR1Term], context: Any
) -> Optional[List[GR1Term]]:
    """Accept a proposed display bucket only after contextual equivalence.

    Args:
        original: Original bucket terms.
        candidate: Proposed replacement terms.
        context: Context for equivalence checks.

    Returns:
        Copied candidate when verified, otherwise ``None``.
    """
    original_expr = _and_expr(original)
    candidate_expr = _and_expr(candidate)
    if _equivalent(z3.And(context, original_expr), z3.And(context, candidate_expr)):
        return [term.copy() for term in candidate]
    return None


def _pretty_liv_term_lines(
    contract: "GR1IoContract",
    term: GR1Term,
    guarantees: bool,
    annotate_redundancy: bool,
) -> List[str]:
    """Render one liveness term for the pretty view.

    Args:
        contract: Contract providing redundancy context.
        term: Liveness term to render.
        guarantees: Whether the term belongs to guarantees.
        annotate_redundancy: Whether to append redundancy annotations.

    Returns:
        Indented liveness lines.
    """
    if term.core.expr is None or (term.core.raw_expr is None and term.core.syntax is not None):
        rendered = [term.core.text]
    else:
        rendered = [_expr_to_user_text(term.core.expr)]
    suffix = ""
    if guarantees and annotate_redundancy and _assumptions_establish_liv(contract, term):
        suffix = "  [redundant under assumptions]"
    return [f"    GF({text}){suffix}" for text in rendered]


def _pretty_bucket_lines(
    contract: "GR1IoContract",
    tag: GR1Tag,
    terms: List[GR1Term],
    guarantees: bool,
    annotate_redundancy: bool,
) -> List[str]:
    """Render one GR(1) bucket for the pretty view.

    Args:
        contract: Contract being rendered.
        tag: Bucket tag.
        terms: Terms in the bucket.
        guarantees: Whether the bucket belongs to guarantees.
        annotate_redundancy: Whether to append redundancy annotations.

    Returns:
        Indented bucket lines.
    """
    lines = [f"  {tag.value.upper()}"]
    if guarantees and tag == GR1Tag.INIT:
        rendered = [_expr_to_user_text(expr) for expr in _effective_init_guarantee_exprs(contract)]
        return lines + [f"    {text}" for text in rendered]
    if not terms:
        return lines + ["    true"]
    if tag == GR1Tag.LIV:
        for term in terms:
            lines.extend(_pretty_liv_term_lines(contract, term, guarantees, annotate_redundancy))
        return lines
    prefix = "G" if tag == GR1Tag.INV else ""
    for term in terms:
        rendered = _pretty_core_lines(term.core)
        lines.extend(f"    {prefix}({text})" if prefix else f"    {text}" for text in rendered)
    return lines


def _pretty_side_lines(
    contract: "GR1IoContract",
    label: str,
    term_list: GR1TermList,
    guarantees: bool,
    annotate_redundancy: bool,
) -> List[str]:
    """Render one assumptions or guarantees side.

    Args:
        contract: Contract being rendered.
        label: Section heading.
        term_list: GR(1) terms for the section.
        guarantees: Whether this is the guarantee side.
        annotate_redundancy: Whether to append redundancy annotations.

    Returns:
        Heading and bucket lines.
    """
    lines = [label]
    buckets = (
        (GR1Tag.INIT, term_list.init_terms()),
        (GR1Tag.INV, term_list.inv_terms()),
        (GR1Tag.LIV, term_list.liv_terms()),
    )
    for tag, terms in buckets:
        lines.extend(_pretty_bucket_lines(contract, tag, terms, guarantees, annotate_redundancy))
    return lines


def _debug_side_lines(label: str, term_list: GR1TermList) -> List[str]:
    """Render one diagnostic assumptions or guarantees side.

    Args:
        label: Section heading.
        term_list: GR(1) terms for the section.

    Returns:
        Heading and raw formula lines.
    """
    lines = [label]
    for raw_term in term_list.terms:
        term = cast(GR1Term, raw_term)
        raw = term.core.raw_expr if term.core.raw_expr is not None else term.core.expr
        lines.append(f"  {term.tag.value.upper():4} {raw if raw is not None else term.core.text}")
    return lines


def _merge_gr1_term_lists(left: GR1TermList, right: GR1TermList) -> GR1TermList:
    """Concatenate matching GR(1) buckets using copied terms.

    Args:
        left: First bucketed term list.
        right: Second bucketed term list.

    Returns:
        Bucket-preserving conjunction of both term lists.
    """
    terms = [term.copy() for term in left.init_terms() + right.init_terms()]
    terms.extend(term.copy() for term in left.inv_terms() + right.inv_terms())
    terms.extend(term.copy() for term in left.liv_terms() + right.liv_terms())
    return GR1TermList(terms)


def _merge_variable_sort_maps(left: Dict[str, str], right: Dict[str, str]) -> Dict[str, str]:
    """Merge persistent sort declarations and reject disagreements.

    Args:
        left: First contract's normalized sort declarations.
        right: Second contract's normalized sort declarations.

    Returns:
        Combined sort declarations.

    Raises:
        IncompatibleArgsError: If one variable has conflicting declarations.
    """
    merged = dict(left)
    for name, sort_name in right.items():
        if name in merged and merged[name] != sort_name:
            raise IncompatibleArgsError(
                f"Cannot merge variable {name!r} with conflicting sorts " f"{merged[name]!r} and {sort_name!r}",
            )
        merged[name] = sort_name
    return merged


_GR1_OPERATION_SIMPLIFY: ContextVar[bool] = ContextVar("gr1_operation_simplify", default=True)


def _normalized_variable_sorts(variable_sorts: Optional[Dict[str, Any]], inferred: Dict[str, str]) -> Dict[str, str]:
    """Normalize declared sorts and validate them against inferred sorts.

    Args:
        variable_sorts: Optional declared variable sorts.
        inferred: Sorts inferred from formulas.

    Returns:
        Combined normalized sort declarations.

    Raises:
        ValueError: If a declared sort conflicts with an inferred sort.
    """
    declared: Dict[str, str] = {}
    if variable_sorts is not None:
        parser = GR1CoreParser(variable_sorts)
        declared = {name: _z3_sort_name(sort) for name, sort in parser._sorts.items()}
        for name, sort_name in inferred.items():
            if name in declared and declared[name] != sort_name:
                raise ValueError(f"Declared sort for {name!r} is {declared[name]}, but formulas use {sort_name}")
    return {**declared, **inferred}


def _presentation_replacement_context(
    assumptions: GR1TermList,
    tag: GR1Tag,
    original_bucket: List[GR1Term],
    proposed_bucket: List[GR1Term],
) -> Any:
    """Build the assumption context for a proposed guarantee replacement.

    Args:
        assumptions: Contract assumption terms.
        tag: Replaced safety bucket tag.
        original_bucket: Original bucket terms.
        proposed_bucket: Proposed bucket terms.

    Returns:
        Shifted context for equivalence checking.
    """
    cores = [term.core for term in original_bucket + proposed_bucket]
    context = _shifted_inv_guard_for_cores(assumptions.inv_terms(), cores)
    if tag == GR1Tag.INIT:
        context = z3.And(_and_expr(assumptions.init_terms()), context)
    return context


def _replace_presentation_safety_buckets(
    assumptions: GR1TermList,
    original: GR1TermList,
    proposed: Optional[GR1TermList],
    guarantee_side: bool,
) -> GR1TermList:
    """Replace verified safety buckets in a presentation term list.

    Args:
        assumptions: Contract assumption terms.
        original: Original presentation term list.
        proposed: Optional proposed presentation term list.
        guarantee_side: Whether assumption-relative context is required.

    Returns:
        Presentation list with verified replacements.
    """
    if proposed is None:
        return original
    buckets: Dict[GR1Tag, List[GR1Term]] = {
        GR1Tag.INIT: original.init_terms(),
        GR1Tag.INV: original.inv_terms(),
        GR1Tag.LIV: original.liv_terms(),
    }
    proposed_buckets = (
        (GR1Tag.INIT, proposed.init_terms()),
        (GR1Tag.INV, proposed.inv_terms()),
    )
    for tag, proposed_bucket in proposed_buckets:
        if proposed_bucket:
            original_bucket = buckets[tag]
            context = z3.BoolVal(True)
            if guarantee_side:
                context = _presentation_replacement_context(assumptions, tag, original_bucket, proposed_bucket)
            replacement = _verified_presentation_bucket_candidate(original_bucket, proposed_bucket, context)
            if replacement is not None:
                buckets[tag] = replacement
    return GR1TermList(buckets[GR1Tag.INIT] + buckets[GR1Tag.INV] + buckets[GR1Tag.LIV])


def _serialized_operation_side(
    operation_payload: Dict[str, Any],
    side: str,
    var_map: Optional[FormulaVarMap],
    variable_sorts: Optional[VariableSortMap],
) -> GR1TermList:
    """Load one canonical operation side from serialized data.

    Args:
        operation_payload: Serialized operation buckets.
        side: Side name to load.
        var_map: Optional legacy variable map.
        variable_sorts: Normalized variable sorts.

    Returns:
        Restored operation-side term list.

    Raises:
        ValueError: If the serialized side is invalid.
    """
    section = operation_payload.get(side)
    if not isinstance(section, dict):
        raise ValueError(f"Invalid canonical GR(1) {side} serialization")
    text_section = section.get("text")
    machine_section = section.get("machine")
    if not isinstance(text_section, dict) or not isinstance(machine_section, dict):
        raise ValueError(f"Invalid canonical GR(1) {side} buckets")
    return _load_serialized_buckets(text_section, machine_section, var_map, variable_sorts)


class _OperationSimplifyContext:
    """Temporarily override operation simplification with guaranteed cleanup."""

    def __init__(self, simplify: bool) -> None:
        self.simplify = simplify
        self.token: Optional[Any] = None

    def __enter__(self) -> None:
        self.token = _GR1_OPERATION_SIMPLIFY.set(self.simplify)

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        del exc_type, exc_value, traceback
        if self.token is not None:
            _GR1_OPERATION_SIMPLIFY.reset(self.token)


class GR1IoContract(IoContract[GR1TermList]):  # noqa: WPS124
    """GR(1) IO contract whose assumptions and guarantees are GR1TermLists."""

    def __init__(
        self,
        assumptions: GR1TermList,
        guarantees: GR1TermList,
        input_vars: List[Var],
        output_vars: List[Var],
        simplify: Optional[bool] = None,
        variable_sorts: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Build a contract and validate or infer its persistent sort table.

        Args:
            assumptions: Assumptions.
            guarantees: Guarantees.
            input_vars: Input vars.
            output_vars: Output vars.
            simplify: Whether to simplify the supplied formulas. Internal
                operation construction inherits the operation's explicit raw
                versus final setting.
            variable_sorts: Declared sort for each base variable.
        """
        effective_simplify = _GR1_OPERATION_SIMPLIFY.get() if simplify is None else simplify
        operation_assumptions = assumptions.copy()
        operation_guarantees = guarantees.copy()
        super().__init__(assumptions, guarantees, input_vars, output_vars, effective_simplify)
        self._operation_assumptions = operation_assumptions
        self._operation_guarantees = operation_guarantees

        inferred = _infer_variable_sorts(self.a, self.g)
        self.variable_sorts = _normalized_variable_sorts(variable_sorts, inferred)

    def __copy__(self) -> "GR1IoContract":
        """Return an independent copy including canonical operation buckets.

        Returns:
            Independent contract copy.
        """
        return self.copy()

    def __deepcopy__(self, memo: Dict[int, Any]) -> "GR1IoContract":
        """Return an independent deep copy including canonical operation buckets.

        Args:
            memo: Deep-copy memoization dictionary.

        Returns:
            Independent contract copy.
        """
        del memo
        return self.copy()

    def copy(self) -> "GR1IoContract":
        """Copy the contract while preserving declarations for unused variables.

        Returns:
            The computed 'GR1IoContract' result.
        """
        copied = GR1IoContract(
            assumptions=self.a.copy(),
            guarantees=self.g.copy(),
            input_vars=self.inputvars.copy(),
            output_vars=self.outputvars.copy(),
            simplify=False,
            variable_sorts=self.variable_sorts,
        )
        copied._set_operation_buckets(self._operation_assumptions, self._operation_guarantees)
        return copied

    def canonical_debug_dump(self) -> str:
        """Return canonical operation buckets without changing stored buckets.

        Returns:
            Canonical debug representation.
        """
        canonical = self._operation_copy()
        return canonical.debug_dump()

    def merge(self, other: "GR1IoContract") -> "GR1IoContract":
        """Merge two contracts while preserving every GR(1) bucket.

        GR(1) is closed under contract merge: assumptions and guarantees are
        conjoined bucket by bucket. INIT and INV terms are concatenated as
        ordinary conjunctions. LIV terms are also concatenated as distinct
        clauses, so ``GF(phi) & GF(psi)`` never becomes ``GF(phi & psi)``.
        No abstraction, projection, quantifier elimination, or CAVE machinery
        is invoked.

        Interface variables follow :meth:`IoContract.merge`: inputs and outputs
        are stable unions, and the constructor rejects variables classified as
        both input and output.

        Args:
            other: GR(1) contract to merge with this contract.

        Returns:
            Exact bucket-preserving conjunction of both contracts.

        Raises:
            IncompatibleArgsError: If contract types, interfaces, or sorts are incompatible.
        """
        if not isinstance(self, type(other)):
            raise IncompatibleArgsError("Asked to merge incompatible contracts")
        merged = GR1IoContract(
            assumptions=_merge_gr1_term_lists(self.a, other.a),
            guarantees=_merge_gr1_term_lists(self.g, other.g),
            input_vars=list_union(self.inputvars, other.inputvars),
            output_vars=list_union(self.outputvars, other.outputvars),
            simplify=False,
            variable_sorts=_merge_variable_sort_maps(self.variable_sorts, other.variable_sorts),
        )
        merged._set_operation_buckets(
            _merge_gr1_term_lists(self._operation_assumptions, other._operation_assumptions),
            _merge_gr1_term_lists(self._operation_guarantees, other._operation_guarantees),
        )
        return merged

    def pretty(self, annotate_redundancy: bool = True) -> str:
        """Return a sectioned bucket view using explicit ``G`` and ``GF``.

        Canonical expressions are split into readable conjunction lines. INIT
        guarantee atoms already implied by assumptions are omitted from this
        view only. Stored semantics and serialization remain unchanged. A LIV
        guarantee established by assumption INV/LIV support is retained but may
        be annotated as redundant.

        Args:
            annotate_redundancy: Mark assumption-established liveness terms.

        Returns:
            Human-readable contract text.
        """
        lines = [
            f"inputs:  [{', '.join(variable.name for variable in self.inputvars)}]",
            f"outputs: [{', '.join(variable.name for variable in self.outputvars)}]",
        ]
        lines.extend(
            _pretty_side_lines(
                self,
                "ASSUMPTIONS",
                self.a,
                guarantees=False,
                annotate_redundancy=annotate_redundancy,
            )
        )
        lines.extend(
            _pretty_side_lines(
                self,
                "GUARANTEES",
                self.g,
                guarantees=True,
                annotate_redundancy=annotate_redundancy,
            )
        )
        return "\n".join(lines)

    def presentation_view(
        self,
        candidate_assumptions: Optional[GR1TermList] = None,
        candidate_guarantees: Optional[GR1TermList] = None,
        assumption_relative: bool = True,
    ) -> Tuple[GR1TermList, GR1TermList]:
        """Return detached, SMT-certified buckets intended only for rendering.

        Automatic candidates use inexpensive Z3 tactics and Boolean-mode
        consequence mining. Optional caller candidates are hints, not trusted
        replacements: assumption safety buckets require unconditional
        equivalence, and guarantee safety buckets require equivalence under the
        appropriate shifted contract assumptions. LIV hints are deliberately
        ignored so distinct justice obligations cannot be synchronized.

        Args:
            candidate_assumptions: Optional proposed assumption presentation.
            candidate_guarantees: Optional proposed guarantee presentation.
            assumption_relative: Whether guarantees are reduced under assumptions.

        Returns:
            Detached assumption and guarantee presentation lists.
        """
        true_context = z3.BoolVal(True)
        assumptions = _presentation_safety_view(self.a.copy(), true_context, true_context)
        guarantees = _assumption_relative_guarantee_view(self) if assumption_relative else self.g.copy()
        guarantee_init_context = _assumption_context_for_guarantee_bucket(
            self.a, guarantees.init_terms(), include_init=True
        )
        guarantee_inv_context = _assumption_context_for_guarantee_bucket(
            self.a, guarantees.inv_terms(), include_init=False
        )
        guarantees = _presentation_safety_view(guarantees, guarantee_init_context, guarantee_inv_context)

        assumptions = _replace_presentation_safety_buckets(
            self.a, assumptions, candidate_assumptions, guarantee_side=False
        )
        guarantees = _replace_presentation_safety_buckets(self.a, guarantees, candidate_guarantees, guarantee_side=True)
        return assumptions, guarantees

    def to_pretty_string(
        self,
        compact: bool = False,
        assumption_relative: bool = True,
        candidate_assumptions: Optional[GR1TermList] = None,
        candidate_guarantees: Optional[GR1TermList] = None,
    ) -> str:
        """Return an observational Unicode assume-guarantee contract view.

        This is an additional presentation API. The existing ASCII
        :meth:`pretty`, :meth:`debug_dump`, serialization, and ``__str__``
        behavior remain unchanged.

        Args:
            compact: Render ``A = ...`` and ``G = ...`` instead of bucket views.
            assumption_relative: Reduce only the displayed guarantees under
                assumptions using SMT-verified GR(1) rules. Set to ``False``
                to display every internally stored guarantee.
            candidate_assumptions: Optional presentation-only safety formulas.
                They are accepted only when unconditionally equivalent.
            candidate_guarantees: Optional presentation-only safety formulas.
                They are accepted only when equivalent under shifted assumptions.

                These are formatting settings only. In contrast, the
                ``simplify`` parameter on construction, composition, and
                quotient controls the formulas stored in the returned
                contract. ``print(contract)`` continues to use the compatible
                ASCII :meth:`pretty` view; call this method explicitly for
                Unicode output.

        Returns:
            Unicode user-facing contract text.
        """
        inputs = ", ".join(variable.name for variable in self.inputvars) or "none"
        outputs = ", ".join(variable.name for variable in self.outputvars) or "none"
        assumption_view, guarantee_view = self.presentation_view(
            candidate_assumptions=candidate_assumptions,
            candidate_guarantees=candidate_guarantees,
            assumption_relative=assumption_relative,
        )
        assumption_text = assumption_view.to_pretty_string(compact=compact)
        guarantee_text = guarantee_view.to_pretty_string(compact=compact)
        if compact:
            return "\n".join(
                [
                    f"Inputs:  {inputs}",
                    f"Outputs: {outputs}",
                    "",
                    f"A = {assumption_text}",
                    f"G = {guarantee_text}",
                ]
            )
        assumption_lines = assumption_text.splitlines()
        guarantee_lines = guarantee_text.splitlines()
        return "\n".join(
            [
                f"Inputs:  {inputs}",
                f"Outputs: {outputs}",
                "",
                "Assumptions",
                *[f"  {line}" for line in assumption_lines],
                "",
                "Guarantees",
                *[f"  {line}" for line in guarantee_lines],
            ]
        )

    def debug_dump(self) -> str:
        """Return bucketed raw solver/QE expressions for diagnostics.

        Returns:
            Diagnostic contract text.
        """
        lines = [
            f"inputs:  [{', '.join(variable.name for variable in self.inputvars)}]",
            f"outputs: [{', '.join(variable.name for variable in self.outputvars)}]",
        ]
        for label, term_list in (("ASSUMPTIONS", self.a), ("GUARANTEES", self.g)):
            lines.extend(_debug_side_lines(label, term_list))
        return "\n".join(lines)

    def __str__(self) -> str:
        """Return the normal bucket-oriented user-facing representation.

        Returns:
            User-facing contract text.
        """
        return self.pretty()

    @staticmethod
    def from_buckets(
        *,
        input_vars: List[str],
        output_vars: List[str],
        a_init: Optional[List[GR1CoreFormula]] = None,
        a_inv: Optional[List[GR1CoreFormula]] = None,
        a_liv: Optional[List[GR1CoreFormula]] = None,
        g_init: Optional[List[GR1CoreFormula]] = None,
        g_inv: Optional[List[GR1CoreFormula]] = None,
        g_liv: Optional[List[GR1CoreFormula]] = None,
        simplify: bool = True,
    ) -> "GR1IoContract":
        """Construct a contract from pre-built cores grouped by GR(1) bucket.

        Args:
            input_vars: Input vars.
            output_vars: Output vars.
            a_init: A init.
            a_inv: A inv.
            a_liv: A liv.
            g_init: G init.
            g_inv: G inv.
            g_liv: G liv.
            simplify: Whether to simplify the resulting formulas.

        Returns:
            The computed 'GR1IoContract' result.
        """
        assumptions = GR1TermList.from_bucket_formulas(
            init=a_init,
            inv=a_inv,
            liv=a_liv,
        )
        guarantees = GR1TermList.from_bucket_formulas(
            init=g_init,
            inv=g_inv,
            liv=g_liv,
        )

        return GR1IoContract(
            assumptions=assumptions,
            guarantees=guarantees,
            input_vars=[Var(x) for x in input_vars],
            output_vars=[Var(x) for x in output_vars],
            simplify=simplify,
        )

    @staticmethod
    def from_dict(
        contract: Dict[str, Any],
        var_map: Optional[FormulaVarMap] = None,
        simplify: bool = True,
        variable_sorts: Optional[VariableSortMap] = None,
    ) -> "GR1IoContract":
        """Restore typed user text, falling back to versioned machine formulas.

                ``variable_sorts`` may be passed explicitly or embedded in ``contract``.
                Legacy ``var_map`` input creates text-only cores and cannot support QE.

        Args:
            contract: Contract.
            var_map: Mapping from formula text to variable names.
            simplify: Whether to simplify the resulting formulas.
            variable_sorts: Declared sort for each base variable.

        Returns:
            The computed 'GR1IoContract' result.

        Raises:
            ValueError: If serialized data or variable sorts are invalid.
        """
        assumptions_text, guarantees_text = _contract_bucket_dicts(contract)
        variable_sorts = _serialized_variable_sorts(contract, var_map, variable_sorts)
        machine = _serialized_machine(contract)
        assumptions_machine = None
        guarantees_machine = None
        if machine is not None:
            assumptions_machine = cast(Optional[Dict[str, Any]], machine.get("assumptions"))
            guarantees_machine = cast(Optional[Dict[str, Any]], machine.get("guarantees"))

        assumptions = _load_serialized_buckets(assumptions_text, assumptions_machine, var_map, variable_sorts)
        guarantees = _load_serialized_buckets(guarantees_text, guarantees_machine, var_map, variable_sorts)

        restored = GR1IoContract(
            assumptions=assumptions,
            guarantees=guarantees,
            input_vars=[Var(x) for x in cast(List[str], contract["input_vars"])],
            output_vars=[Var(x) for x in cast(List[str], contract["output_vars"])],
            simplify=simplify,
            variable_sorts=variable_sorts,
        )
        operation_payload = contract.get("gr1_operation_buckets")
        if operation_payload is not None:
            if not isinstance(operation_payload, dict) or operation_payload.get("version") != 1:
                raise ValueError("Unsupported or invalid GR(1) operation-bucket serialization version")
            operation_assumptions = _serialized_operation_side(
                operation_payload, "assumptions", var_map, variable_sorts
            )
            operation_guarantees = _serialized_operation_side(operation_payload, "guarantees", var_map, variable_sorts)
            restored._set_operation_buckets(operation_assumptions, operation_guarantees)
        else:
            restored._set_operation_buckets(restored.a, restored.g)
        return restored

    def rename_variables(self, variable_mappings: List[Tuple[str, str]]) -> "GR1IoContract":
        """Apply a sequence of base-variable renamings to a copied contract.

        Args:
            variable_mappings: Variable mappings.

        Returns:
            The computed 'GR1IoContract' result.
        """
        new_contract: GR1IoContract = self.copy()
        for src, dst in variable_mappings:
            new_contract = new_contract.rename_variable(Var(src), Var(dst))
        return new_contract

    def rename_variable(self, source_var: Var, target_var: Var) -> "GR1IoContract":
        """Rename one base interface variable and all of its flattened copies.

        Args:
            source_var: Source var.
            target_var: Target var.

        Returns:
            The computed 'GR1IoContract' result.

        Raises:
            ValueError: If serialized data or variable sorts are invalid.
        """
        renamed = super().rename_variable(source_var, target_var)
        renamed._set_operation_buckets(
            self._operation_assumptions.rename_variable(source_var, target_var),
            self._operation_guarantees.rename_variable(source_var, target_var),
        )
        renamed.variable_sorts = dict(self.variable_sorts)
        if source_var.name in renamed.variable_sorts:
            source_sort = renamed.variable_sorts.pop(source_var.name)
            existing_sort = renamed.variable_sorts.get(target_var.name)
            if existing_sort is not None and existing_sort != source_sort:
                raise ValueError(
                    f"Cannot rename {source_var.name!r} to {target_var.name!r}: "
                    f"sorts {source_sort} and {existing_sort} conflict"
                )
            renamed.variable_sorts[target_var.name] = source_sort
        return renamed

    def to_dict(self) -> Dict[str, Any]:
        """Serialize readable buckets, sorts, and versioned generated expressions.

        Returns:
            The computed Dict[str, Any] result.
        """
        contract: Dict[str, Any] = {
            "input_vars": [str(x) for x in self.inputvars],
            "output_vars": [str(x) for x in self.outputvars],
            "assumptions": self.a.to_bucket_dict(),
            "guarantees": self.g.to_bucket_dict(),
        }
        if self.variable_sorts:
            contract["variable_sorts"] = dict(sorted(self.variable_sorts.items()))
        contract["gr1_machine"] = {
            "version": 1,
            "assumptions": _machine_bucket_payload(self.a),
            "guarantees": _machine_bucket_payload(self.g),
        }
        contract["gr1_operation_buckets"] = {
            "version": 1,
            "assumptions": {
                "text": self._operation_assumptions.to_bucket_dict(),
                "machine": _machine_bucket_payload(self._operation_assumptions),
            },
            "guarantees": {
                "text": self._operation_guarantees.to_bucket_dict(),
                "machine": _machine_bucket_payload(self._operation_guarantees),
            },
        }
        return contract

    def to_machine_dict(self) -> ser_gr1_contract:
        """Return :meth:`to_dict` with the public serialized-contract type.

        Returns:
            The computed ser_gr1_contract result.
        """
        return cast(ser_gr1_contract, self.to_dict())

    def compose(
        self,
        other: "GR1IoContract",
        vars_to_keep: Optional[List[str]] = None,
        simplify: bool = True,
    ) -> "GR1IoContract":
        """Compose contracts, optionally preserving named internal variables.

        Args:
            other: Other term list or contract.
            vars_to_keep: Vars to keep.
            simplify: Whether to simplify the resulting formulas.

        Returns:
            The computed 'GR1IoContract' result.
        """
        if vars_to_keep is None:
            vars_to_keep = []
        result, _ = self.compose_tactics(other, vars_to_keep, simplify)
        return result

    def compose_tactics(
        self,
        other: "GR1IoContract",
        vars_to_keep: Optional[List[str]] = None,
        simplify: bool = True,
        tactics_order: Optional[List[int]] = None,
    ) -> Tuple["GR1IoContract", List[TacticStatistics]]:
        """Compose while exposing elimination tactic statistics.

        Args:
            other: Other term list or contract.
            vars_to_keep: Vars to keep.
            simplify: Whether to simplify the resulting formulas.
            tactics_order: Preferred quantifier-elimination tactic order.

        Returns:
            The computed Any result.
        """
        if vars_to_keep is None:
            vars_to_keep = []
        if tactics_order is None:
            tactics_order = []
        merged_sorts = _merge_variable_sort_maps(self.variable_sorts, other.variable_sorts)
        with _OperationSimplifyContext(False):
            raw, stats = IoContract.compose_tactics(
                self._operation_copy(),
                other._operation_copy(),
                [Var(x) for x in vars_to_keep],
                simplify=False,
                tactics_order=tactics_order,
            )
            raw.variable_sorts = _normalized_variable_sorts(
                {var.name: merged_sorts[var.name] for var in raw.vars if var.name in merged_sorts},
                _infer_variable_sorts(raw.a, raw.g),
            )
            return self._finalize_operation_result(raw, simplify), stats

    def quotient(
        self,
        other: "GR1IoContract",
        additional_inputs: Optional[VariableInputs] = None,
        simplify: bool = True,
    ) -> "GR1IoContract":
        """Compute a quotient with optional additional input names.

        Args:
            other: Other term list or contract.
            additional_inputs: Additional inputs.
            simplify: Whether to simplify the resulting formulas.

        Returns:
            The computed 'GR1IoContract' result.
        """
        if additional_inputs is None:
            additional_inputs = []

        result, _ = self.quotient_tactics(other, additional_inputs, simplify)
        return result

    def quotient_tactics(
        self,
        other: "GR1IoContract",
        additional_inputs: Optional[VariableInputs] = None,
        simplify: bool = True,
        tactics_order: Optional[List[int]] = None,
    ) -> Tuple["GR1IoContract", List[TacticStatistics]]:
        """Compute a quotient while exposing tactic statistics.

        Args:
            other: Other term list or contract.
            additional_inputs: Additional inputs.
            simplify: Whether to simplify the resulting formulas.
            tactics_order: Preferred quantifier-elimination tactic order.

        Returns:
            The computed Tuple['GR1IoContract', List[TacticStatistics]] result.
        """
        if additional_inputs is None:
            additional_inputs = []

        if tactics_order is None:
            tactics_order = []

        merged_sorts = _merge_variable_sort_maps(self.variable_sorts, other.variable_sorts)
        with _OperationSimplifyContext(False):
            raw, stats = IoContract.quotient_tactics(
                self._operation_copy(),
                other._operation_copy(),
                [item if isinstance(item, Var) else Var(item) for item in additional_inputs],
                simplify=False,
                tactics_order=tactics_order,
            )
            raw.variable_sorts = _normalized_variable_sorts(
                {var.name: merged_sorts[var.name] for var in raw.vars if var.name in merged_sorts},
                _infer_variable_sorts(raw.a, raw.g),
            )
            return self._finalize_operation_result(raw, simplify), stats

    def _set_operation_buckets(self, assumptions: GR1TermList, guarantees: GR1TermList) -> None:
        """Store independent canonical buckets used by future GR(1) operations.

        Args:
            assumptions: Canonical assumption buckets.
            guarantees: Canonical guarantee buckets.
        """
        self._operation_assumptions = assumptions.copy()
        self._operation_guarantees = guarantees.copy()

    def _operation_copy(self) -> "GR1IoContract":
        """Build a contract exposing canonical buckets to generic algebra.

        Returns:
            Contract containing canonical operation buckets.
        """
        return GR1IoContract(
            assumptions=self._operation_assumptions,
            guarantees=self._operation_guarantees,
            input_vars=self.inputvars,
            output_vars=self.outputvars,
            simplify=False,
            variable_sorts=self.variable_sorts,
        )

    @staticmethod
    def _finalize_operation_result(raw: "GR1IoContract", simplify: bool) -> "GR1IoContract":
        """Attach raw CAVE buckets and optionally construct their reduced view.

        Args:
            raw: Raw operation result.
            simplify: Whether to construct the reduced view.

        Returns:
            Finalized operation result.
        """
        if not simplify:
            return raw
        reduced_assumptions = raw.a.simplify()
        reduced_guarantees = raw.g.simplify(reduced_assumptions)
        reduced_guarantees = GR1TermList(
            reduced_guarantees.init_terms()
            + reduced_guarantees.inv_terms()
            + sorted(reduced_guarantees.liv_terms(), key=lambda term: term.core.text)
        )
        reduced = GR1IoContract(
            assumptions=reduced_assumptions,
            guarantees=reduced_guarantees,
            input_vars=raw.inputvars,
            output_vars=raw.outputvars,
            simplify=False,
            variable_sorts=raw.variable_sorts,
        )
        reduced._set_operation_buckets(raw.a, raw.g)
        return reduced


if __name__ == "__main__":

    p = Var("p")
    q = Var("q")

    P = z3.Real("p")
    Q = z3.Real("q")

    ctx1 = GR1CoreFormula.of_expr("p >= 0", [p], expr=(P >= 0))
    ctx2 = GR1CoreFormula.of_expr("p <= 5", [p], expr=(P <= 5))
    goal = GR1CoreFormula.of_expr("p <= q", [p, q], expr=(P <= Q))

    context = GR1TermList.from_bucket_formulas(inv=[ctx1, ctx2])
    target = GR1TermList.from_bucket_formulas(inv=[goal])

    res, _ = target.elim_vars_by_refining(
        context=context,
        vars_to_elim=[p],
        simplify=False,
        tactics_order=[],
    )

    print("Result:")
    print(res.to_bucket_dict())
    print("Z3 expr:")
    print(res.inv_terms()[0].core.expr)
