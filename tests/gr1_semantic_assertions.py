"""Semantic assertions shared by GR(1) serialization regression tests."""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Tuple

import z3
from z3.z3util import get_vars

from pacti.iocontract.gr1_iocontract import GR1IoContract, GR1Term, GR1TermList


def conjunction(terms: Iterable[GR1Term]) -> z3.BoolRef:
    """Conjoin one safety bucket without adding contract context."""
    return z3.And(*(term.core.expr for term in terms))


def implies(left: z3.BoolRef, right: z3.BoolRef) -> bool:
    """Return whether an unconditional implication is valid."""
    solver = z3.Solver()
    solver.add(left, z3.Not(right))
    return solver.check() == z3.unsat


def equivalent(left: z3.BoolRef, right: z3.BoolRef) -> bool:
    """Return whether both unconditional implications are valid."""
    return implies(left, right) and implies(right, left)


def expression_signature(expr: z3.BoolRef) -> Tuple[Tuple[str, str], ...]:
    """Return flattened free-variable names and exact Z3 sorts."""
    return tuple(sorted((str(variable), str(variable.sort())) for variable in get_vars(expr)))


def flattened_indices(expr: z3.BoolRef) -> Tuple[Tuple[str, int], ...]:
    """Return every flattened base/index pair in an expression."""
    indices: List[Tuple[str, int]] = []
    for variable in get_vars(expr):
        match = re.fullmatch("(.+)_([0-9]+)", str(variable))
        if match is not None:
            indices.append((match.group(1), int(match.group(2))))
    return tuple(sorted(indices))


def assert_formula_semantically_equal(left: z3.BoolRef, right: z3.BoolRef) -> None:
    """Assert equivalence and an identical finite-window variable shape."""
    assert implies(left, right), f"left does not imply right:\n{left}\n!=\n{right}"
    assert implies(right, left), f"right does not imply left:\n{right}\n!=\n{left}"
    assert expression_signature(left) == expression_signature(right)
    assert flattened_indices(left) == flattened_indices(right)


def _liveness_bijection(left: Sequence[GR1Term], right: Sequence[GR1Term]) -> bool:
    """Match separate liveness cores one-to-one, allowing reordering."""
    if len(left) != len(right):
        return False
    edges = [
        [index for index, candidate in enumerate(right) if equivalent(term.core.expr, candidate.core.expr)]
        for term in left
    ]

    def search(position: int, used: set[int]) -> bool:
        if position == len(edges):
            return True
        return any(candidate not in used and search(position + 1, used | {candidate}) for candidate in edges[position])

    return search(0, set())


def assert_term_lists_semantically_equal(left: GR1TermList, right: GR1TermList) -> None:
    """Compare safety conjunctions and separate liveness collections."""
    for accessor in ("init_terms", "inv_terms"):
        assert_formula_semantically_equal(
            conjunction(getattr(left, accessor)()), conjunction(getattr(right, accessor)())
        )

    assert _liveness_bijection(left.liv_terms(), right.liv_terms()), (
        "LIV collections lack a bijection of equivalent liveness cores:\n"
        f"left={[term.core.expr for term in left.liv_terms()]}\n"
        f"right={[term.core.expr for term in right.liv_terms()]}"
    )


def assert_gr1_semantically_equal(
    left: GR1IoContract,
    right: GR1IoContract,
    *,
    compare_stored: bool = True,
    compare_canonical: bool = True,
) -> None:
    """Assert the semantic round-trip contract for two GR(1) contracts."""
    assert [variable.name for variable in left.inputvars] == [variable.name for variable in right.inputvars]
    assert [variable.name for variable in left.outputvars] == [variable.name for variable in right.outputvars]
    assert left.variable_sorts == right.variable_sorts
    left_dict, right_dict = left.to_dict(), right.to_dict()
    assert left_dict["gr1_machine"]["version"] == right_dict["gr1_machine"]["version"]
    assert left_dict["gr1_operation_buckets"]["version"] == right_dict["gr1_operation_buckets"]["version"]

    if compare_stored:
        assert_term_lists_semantically_equal(left.a, right.a)
        assert_term_lists_semantically_equal(left.g, right.g)
    if compare_canonical:
        assert_term_lists_semantically_equal(left._operation_assumptions, right._operation_assumptions)
        assert_term_lists_semantically_equal(left._operation_guarantees, right._operation_guarantees)
