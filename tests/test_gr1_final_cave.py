"""Regressions for the final finite-subproblem CAVE construction (R1--R12)."""

from unittest.mock import patch

import pytest
import z3

from pacti.iocontract import Var
from pacti.iocontract import gr1_iocontract as gr1

SORTS = {name: "bool" for name in ("p", "q", "a", "b", "s")}


def terms(**buckets):
    return gr1.GR1TermList.from_bucket_strings(variable_sorts=SORTS, **buckets)


def expr(text):
    return gr1.parse_gr1_core(text, SORTS).expr


def candidates(target, context):
    return gr1._refinement_liv_candidates(target.liv_terms()[0], context, [Var("p")])


def test_r1_synthetic_is_recurrent_not_persistent():
    result, _ = terms(liv=["p | q"]).elim_vars_by_refining(terms(), [Var("p")], False, [])
    assert not result.inv_terms()
    assert len(result.liv_terms()) == 1
    assert gr1._equivalent(result.liv_terms()[0].core.expr, expr("q"))
    trace = gr1.GR1Behavior(states=[{"q": False}, {"q": True}], loop_start=0)
    assert result.contains_behavior(trace)
    assert not terms(inv=["q"]).contains_behavior(trace)


def test_r2_p_free_target_constructs_both_branches():
    family = candidates(terms(liv=["a"]), terms(liv=["a"]))
    assert [term.tag for term in family] == [gr1.GR1Tag.LIV, gr1.GR1Tag.INV]
    assert gr1._equivalent(family[0].core.expr, expr("a"))
    assert gr1._equivalent(family[1].core.expr, z3.BoolVal(True))


def test_r3_fixed_support_certificate_is_persistent():
    family = candidates(terms(liv=["p"]), terms(liv=["p | a"]))
    assert family[1].tag == gr1.GR1Tag.INV
    assert gr1._equivalent(family[1].core.expr, expr("!a"))


def test_r4_all_candidates_exist_before_non_mutating_selection():
    target, context = terms(liv=["p | q"]), terms(liv=["p", "a", "!p & b"])
    original = gr1._select_refinement_support
    observed = []

    def select(family):
        before = [(term.tag, term.core.expr.sexpr()) for term in family]
        assert len(family) == 4
        assert [term.tag for term in family] == [gr1.GR1Tag.LIV] + [gr1.GR1Tag.INV] * 3
        selected = original(family)
        assert any(selected is term for term in family)
        assert before == [(term.tag, term.core.expr.sexpr()) for term in family]
        observed.extend(before)
        return selected

    with patch.object(gr1, "_select_refinement_support", select):
        target.elim_vars_by_refining(context, [Var("p")], False, [])
    assert len(observed) == 4


def test_r5_disconnected_support_reaches_projection():
    with patch.object(gr1, "_associated_liv_supports", side_effect=AssertionError("historical filter")):
        family = candidates(terms(liv=["p | q"]), terms(liv=["a"]))
    assert gr1._equivalent(family[1].core.expr, expr("a -> q"))


def test_r6_incompatible_support_reaches_projection():
    with patch.object(gr1, "_support_viable", side_effect=AssertionError("historical filter")):
        family = candidates(terms(liv=["p & q"]), terms(liv=["!p & a"]))
    assert gr1._equivalent(family[1].core.expr, expr("!a"))


def test_r7_w8_combines_one_recurrence_with_invariant_context():
    source, target = terms(inv=["a -> b"], liv=["a"]), terms(liv=["b"])
    assert not gr1._implies(expr("a"), expr("b"))
    assert not gr1._implies(expr("a -> b"), expr("b"))
    assert gr1._implies(expr("(a -> b) & a"), expr("b"))
    assert source.refines(target)
    assert not terms(liv=["a", "b"]).refines(terms(liv=["a & b"]))


@pytest.mark.parametrize(
    "cores, expected",
    [
        (["true", "a"], ["a"]),
        (["a", "a"], ["a"]),
        (["a", "a & (b | !b)"], ["a"]),
        (["a & b", "a"], ["a & b"]),
        (["a", "b"], ["a", "b"]),
    ],
)
def test_r8_select_liveness_preserves_conjunction(cores, expected):
    reduced = gr1._remove_redundant_liv_terms(terms(liv=cores).liv_terms())
    assert len(reduced) == len(expected)
    assert all(gr1._equivalent(term.core.expr, expr(want)) for term, want in zip(reduced, expected))


def test_r9_empty_inv_is_projected_as_true():
    context = terms(inv=["q"])
    empty, _ = terms().elim_vars_by_relaxing(context, [Var("p")], False, [])
    explicit, _ = terms(inv=["true"]).elim_vars_by_relaxing(context, [Var("p")], False, [])
    assert gr1._equivalent(gr1._and_expr(empty.inv_terms()), expr("q"))
    assert empty.refines(explicit) and explicit.refines(empty)


def test_r10_mixed_typed_indexed_projection():
    sorts = {"p": "bool", "b": "bool", "x": "int", "y": "int", "r": "real", "s": "real"}
    target = gr1.GR1TermList.from_bucket_strings(inv=["X(p) & X(x)=y & X(r)=s"], variable_sorts=sorts)
    context = gr1.GR1TermList.from_bucket_strings(inv=["p=b", "x>=2", "r>=1/2"], variable_sorts=sorts)
    result, _ = target.elim_vars_by_relaxing(context, [Var("p"), Var("x"), Var("r")], False, [])
    expected = gr1.parse_gr1_core("X(b) & y>=2 & s>=1/2", sorts).expr
    assert gr1._equivalent(gr1._and_expr(result.inv_terms()), expected)
    assert {str(v.sort()) for v in z3.z3util.get_vars(expected)} == {"Bool", "Int", "Real"}


@pytest.mark.parametrize("bucket", ["init", "inv", "liv"])
def test_r11_syntax_depth_survives_boolean_simplification(bucket):
    target = terms(**{bucket: ["q & (X(X(b)) | !X(X(b)))"]})
    context = terms(inv=["a"])
    assert gr1._core_next_depth(target.terms[0].core) == 2
    result, _ = target.elim_vars_by_refining(context, [Var("p")], False, [])
    expected = expr("(a & X(a) & X(X(a))) -> q")
    output = getattr(result, bucket + "_terms")()
    assert len(output) == 1
    assert gr1._equivalent(output[0].core.expr, expected)
    assert not gr1._equivalent(output[0].core.expr, expr("a -> q"))


def test_r11_true_support_and_context_init_keep_their_depth():
    context = terms(init=["X(X(b)) | !X(X(b))"], inv=["a"], liv=["X(X(b)) | !X(X(b))"])
    target = terms(init=["q"], liv=["q"])
    result, _ = target.elim_vars_by_refining(context, [Var("p")], False, [])
    expected = expr("(a & X(a) & X(X(a))) -> q")
    assert gr1._equivalent(result.init_terms()[0].core.expr, expected)
    assert gr1._equivalent(candidates(target, context)[1].core.expr, expected)


def test_r11_depth_survives_copy_rename_and_serialization():
    core = terms(init=["q & (X(X(b)) | !X(X(b)))"]).terms[0].core
    combined = gr1._conjoin_bucket_terms(gr1.GR1Tag.INIT, [gr1.GR1Term(gr1.GR1Tag.INIT, core)])
    assert combined is not None
    assert gr1._core_next_depth(combined.copy().core.rename_variable(Var("q"), Var("a"))) == 2
    payload = gr1._machine_core_payload(combined.core)
    assert payload is not None
    restored = gr1._core_from_machine_payload(combined.core.text, payload)
    assert gr1._core_next_depth(restored) == 2


def test_r12_raw_result_precedes_context_relative_reduction():
    target, context = terms(inv=["q"]), terms(inv=["q"])
    raw, _ = target.elim_vars_by_relaxing(context, [Var("p")], False, [])
    reduced, _ = target.elim_vars_by_relaxing(context, [Var("p")], True, [])
    assert gr1._equivalent(gr1._and_expr(raw.inv_terms()), expr("q"))
    assert not reduced.terms
    assert not reduced.refines(raw)
    assert (context | reduced).refines(context | raw)
    assert (context | raw).refines(context | reduced)
