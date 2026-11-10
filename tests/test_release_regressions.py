"""Public-release regressions for interfaces, declarations and solver evidence."""

import importlib
import ssl
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest
import z3

from pacti.iocontract import Var
from pacti.iocontract import gr1_iocontract as gr1
from pacti.utils.errors import IncompatibleArgsError


def test_release_tasks_preserve_https_certificate_verification() -> None:
    pytest.importorskip("duty")
    original = ssl._create_default_https_context
    importlib.import_module("duties")
    assert ssl._create_default_https_context is original
    context = ssl._create_default_https_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname


def contract(
    inputs: List[str], outputs: List[str], sorts: Dict[str, str], guarantees: Optional[Dict[str, List[str]]] = None
) -> gr1.GR1IoContract:
    return gr1.GR1IoContract.from_dict(
        {
            "input_vars": inputs,
            "output_vars": outputs,
            "variable_sorts": sorts,
            "assumptions": {},
            "guarantees": guarantees or {},
        },
        simplify=False,
    )


def test_contract_equality_and_hash_containers() -> None:
    first = contract(["i"], ["o"], {"i": "bool", "o": "bool"})
    same = first.copy()
    other_input = contract(["j"], ["o"], {"j": "bool", "o": "bool"})
    other_output = contract(["i"], ["p"], {"i": "bool", "p": "bool"})
    assert first == same
    assert hash(first) == hash(same)
    assert first != other_input
    assert first != other_output
    assert len({first, same, other_input, other_output}) == 3
    lookup = {first: "first", other_input: "input", other_output: "output"}
    assert lookup[same] == "first"
    assert lookup[other_output] == "output"


@pytest.mark.parametrize("left,right", [("bool", "real"), ("bool", "int"), ("int", "real")])
@pytest.mark.parametrize("operation", ["compose", "quotient"])
def test_conflicting_unused_declarations(left: str, right: str, operation: str) -> None:
    # Both operations are IO-compatible; the shared input is deliberately unused.
    a = contract(["shared"], ["a"], {"shared": left, "a": "bool"})
    b = contract(["shared"], ["b"], {"shared": right, "b": "bool"})
    with pytest.raises(IncompatibleArgsError, match="conflicting sorts"):
        getattr(a, operation)(b)


@pytest.mark.parametrize("simplify", [False, True])
@pytest.mark.parametrize("sort", ["bool", "int", "real"])
def test_composition_preserves_unused_sorts_and_hides_internal(sort: str, simplify: bool) -> None:
    a = contract(["i"], ["p"], {"i": "int", "p": sort})
    b = contract(["p"], ["o"], {"p": sort, "o": "real"})
    result = a.compose(b, simplify=simplify)
    assert result.variable_sorts == {"i": "int", "o": "real"}
    kept = a.compose(b, vars_to_keep=["p"], simplify=simplify)
    assert kept.variable_sorts == {"i": "int", "p": sort, "o": "real"}
    restored = gr1.GR1IoContract.from_dict(kept.to_dict())
    assert restored.variable_sorts == kept.variable_sorts
    assert restored.copy().variable_sorts == kept.variable_sorts


@pytest.mark.parametrize("simplify", [False, True])
@pytest.mark.parametrize("sort", ["bool", "int", "real"])
def test_quotient_preserves_unused_sorts_and_additional_inputs(sort: str, simplify: bool) -> None:
    target = contract(["i"], ["o"], {"i": sort, "o": "real"})
    known = contract(["i"], ["p"], {"i": sort, "p": "bool"})
    residual = target.quotient(known, simplify=simplify)
    assert residual.variable_sorts == {"p": "bool", "o": "real"}
    kept = target.quotient(known, additional_inputs=["i"], simplify=simplify)
    assert kept.variable_sorts == {"i": sort, "p": "bool", "o": "real"}
    restored = gr1.GR1IoContract.from_dict(kept.to_dict())
    assert restored.variable_sorts == kept.variable_sorts
    assert known.compose(residual).refines(target)


def test_compatible_used_sort_and_serialized_operation() -> None:
    a = contract(["i"], ["p"], {"i": "bool", "p": "bool"}, {"inv": ["p = i"]})
    b = contract(["p"], ["o"], {"p": "bool", "o": "bool"}, {"inv": ["o = p"]})
    result = a.compose(b)
    assert result.variable_sorts == {"i": "bool", "o": "bool"}
    restored = gr1.GR1IoContract.from_dict(result.to_dict())
    assert restored.refines(result) and result.refines(restored)
    assert result.g.vars == [Var("i"), Var("o")] or set(result.g.vars) == {Var("i"), Var("o")}


@pytest.mark.parametrize("first,second", [("Bool", "Real"), ("Real", "Int"), ("Int", "Bool")])
def test_flattener_rejects_sort_conflict_without_poisoning_cache(first: str, second: str) -> None:
    fl = gr1.GR1NextFlattener()
    original = getattr(fl, first)("p")
    with pytest.raises(ValueError, match="sort"):
        getattr(fl, second)("p")
    assert getattr(fl, first)("p").eq(original)
    assert fl.X(original).sort() == original.sort()


class SolverResult:
    def __init__(self, result: Any):
        self.result = result

    def add(self, *expressions: Any) -> None:
        pass

    def check(self) -> Any:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    def reason_unknown(self) -> str:
        return "injected timeout"


@pytest.mark.parametrize("result", [z3.unknown, z3.Z3Exception("injected failure")])
def test_inconclusive_solver_never_certifies_empty_or_false(result: Any) -> None:
    terms = gr1.GR1TermList.from_bucket_strings(inv=["true"], variable_sorts={})
    with patch.object(gr1.z3, "Solver", return_value=SolverResult(result)):
        with pytest.raises(RuntimeError, match="solver|Solver"):
            terms.is_empty()
        with pytest.raises(RuntimeError, match="solver|Solver"):
            gr1._refined_term(gr1.GR1Tag.INV, z3.BoolVal(True))


def test_sat_unsat_and_unknown_implication() -> None:
    assert gr1._is_sat(z3.BoolVal(True))
    assert not gr1._is_sat(z3.BoolVal(False))
    with patch.object(gr1.z3, "Solver", return_value=SolverResult(z3.unknown)):
        assert not gr1._implies(z3.BoolVal(True), z3.BoolVal(False))


@pytest.mark.parametrize("goals", [[], [[z3.BoolVal(True)], [z3.BoolVal(False)]]])
def test_qe_rejects_unexpected_subgoal_shape(goals: List[List[Any]]) -> None:
    with patch.object(gr1.z3, "Tactic", return_value=lambda _: goals):
        with pytest.raises(RuntimeError, match="subgoal"):
            gr1._eliminate_quantifiers(z3.BoolVal(True))


def test_qe_rejects_residual_quantifier_and_solver_error() -> None:
    p = z3.Bool("p")
    with patch.object(gr1.z3, "Tactic", return_value=lambda _: [[z3.Exists([p], p)]]):
        with pytest.raises(RuntimeError, match="quantifier"):
            gr1._eliminate_quantifiers(z3.Exists([p], p))
    with patch.object(gr1.z3, "Tactic", side_effect=z3.Z3Exception("unsupported")):
        with pytest.raises(RuntimeError, match="elimination"):
            gr1._eliminate_quantifiers(z3.Exists([p], p))


def test_qe_supported_boolean_real_and_integer_projections() -> None:
    p, q = z3.Bools("p q")
    x, y = z3.Reals("x y")
    i = z3.Int("i")
    for formula, expected in [
        (z3.Exists([p], z3.And(p, q)), q),
        (z3.Exists([x], z3.And(x >= 0, x <= y)), y >= 0),
        (z3.Exists([i], z3.And(i >= 0, i < 1)), z3.BoolVal(True)),
    ]:
        assert gr1._equivalent(gr1._eliminate_quantifiers(formula), expected)


def test_feedback_amplifier_quotient_uses_tactic_fallback() -> None:
    from pacti.contracts import PolyhedralIoContract

    target = PolyhedralIoContract.from_strings(
        input_vars=["u1"], output_vars=["y"], assumptions=["u1 <= 5"], guarantees=["y = 2*u1"]
    )
    known = PolyhedralIoContract.from_strings(
        input_vars=["u1", "u2"],
        output_vars=["y"],
        assumptions=["u1 <= 10"],
        guarantees=["y <= 10000*u1 - 10000*u2"],
    )
    residual = target.quotient(known, additional_inputs=known.outputvars)
    expected = PolyhedralIoContract.from_strings(
        input_vars=["y"],
        output_vars=["u2"],
        assumptions=[],
        guarantees=["2*u2 >= 0.9998*y", "y >= 10"],
    )
    assert residual.refines(expected)
    assert expected.refines(residual)
    assert not residual.g.is_empty()


def test_context_tactic_rejects_unconstrained_elimination_variable() -> None:
    from pacti.terms.polyhedra.polyhedra import PolyhedralTerm, PolyhedralTermList

    u1, u2, y = Var("u1"), Var("u2"), Var("y")
    term = PolyhedralTerm({u1: -10000, u2: 10000, y: 1}, 0)
    context = PolyhedralTermList([PolyhedralTerm({u1: 1}, 5)])
    with pytest.raises(ValueError, match="does not constrain"):
        PolyhedralTermList._get_tlp_context(term, context, [u1, u2], False)


def test_context_tactic_handles_insufficient_active_constraints() -> None:
    from pacti.terms.polyhedra.polyhedra import PolyhedralTerm, PolyhedralTermList

    x, y = Var("x"), Var("y")
    term = PolyhedralTerm({x: 1, y: 1}, 0)
    context = PolyhedralTermList([term])
    # A bounded optimum need not expose one active constraint per variable.
    with pytest.raises(ValueError, match="insufficient active constraints"):
        PolyhedralTermList._get_tlp_context(term, context, [x, y], True)
