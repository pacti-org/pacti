"""Selection regressions; construction remains the complete R1--R12 family."""

from dataclasses import FrozenInstanceError
from itertools import permutations
from unittest.mock import patch

import pytest
import z3

from pacti.iocontract import Var
from pacti.iocontract import gr1_iocontract as gr1
from tests.test_gr1_final_cave import candidates, expr, terms
from tests.test_aeb_gr1_composition import example


def identity(term):
    return term.branch_id, term.support_id, term.tag


@pytest.mark.parametrize(
    "target,supports,expected",
    [
        ("p | q", ["p", "a", "!p & b"], "true"),
        ("p", ["!p & a", "!p & b"], "!a"),
        ("p | q", ["p", "p | q"], "true"),
    ],
)
def test_repeatability_and_all_support_permutations(target, supports, expected):
    selected_identity = None
    selected_expr = None
    for _ in range(3):
        for order in permutations(supports):
            family = candidates(terms(liv=[target]), terms(liv=list(order)))
            assert len(family) == len(supports) + 1
            assert [term.tag for term in family] == [gr1.GR1Tag.LIV] + [gr1.GR1Tag.INV] * len(supports)
            before = [(identity(term), term.core.expr.sexpr()) for term in family]
            selected = gr1._select_refinement_support(family)
            assert selected is not None
            assert any(selected is term for term in family)
            assert before == [(identity(term), term.core.expr.sexpr()) for term in family]
            assert gr1._equivalent(selected.core.expr, expr(expected))
            if selected_identity is None:
                selected_identity, selected_expr = identity(selected), selected.core.expr
            assert identity(selected) == selected_identity
            assert gr1._equivalent(selected.core.expr, selected_expr)
            # Selection itself is also independent of the candidate-list order.
            for reordered in permutations(family):
                assert gr1._select_refinement_support(list(reordered)) is selected


def test_complete_family_and_source_identity():
    context = terms(liv=["p", "a", "!p & b"])
    family = candidates(terms(liv=["p | q"]), context)
    for term, expected in zip(family, ["q", "true", "a -> q", "b -> q"]):
        assert gr1._equivalent(term.core.expr, expr(expected))
    assert family[0].branch_id == "0" and family[0].support_id is None
    for term, support in zip(family[1:], context.liv_terms()):
        assert term.support_id == (gr1._core_next_depth(support.core), support.core.expr.sexpr())
        assert term.branch_id == "support:{}:{}".format(*term.support_id)
    with pytest.raises(FrozenInstanceError):
        family[0].tag = gr1.GR1Tag.INV
    assert gr1._select_refinement_support(family) is family[1]


@pytest.mark.parametrize(
    "support,wrapper,expected",
    [
        ("a", gr1.GR1Tag.LIV, "q"),
        ("q", gr1.GR1Tag.INV, "true"),
    ],
)
def test_elimination_free_target_keeps_recurrence_unless_tautology(support, wrapper, expected):
    target, context = terms(liv=["q"]), terms(liv=[support])
    family = candidates(target, context)
    assert len(family) == 2
    assert family[0].tag == gr1.GR1Tag.LIV
    assert family[1].tag == gr1.GR1Tag.INV
    chosen = gr1._select_refinement_support(family)
    assert chosen is not None
    assert chosen.tag == wrapper
    assert gr1._equivalent(chosen.core.expr, expr(expected))
    result, _ = target.elim_vars_by_refining(context, [Var("p")], False, [])
    assert result.terms[0].tag == wrapper
    assert gr1._equivalent(result.terms[0].core.expr, expr(expected))


def test_total_on_empty_and_all_false_and_same_core_different_wrappers():
    assert gr1._select_refinement_support([]) is None
    family = candidates(terms(liv=["p"]), terms(liv=["true"]))
    assert all(gr1._equivalent(term.core.expr, expr("false")) for term in family)
    assert gr1._select_refinement_support(family[::-1]) is family[0]
    family = candidates(terms(liv=["q"]), terms(liv=["true"]))
    assert all(gr1._equivalent(term.core.expr, expr("q")) for term in family)
    assert gr1._select_refinement_support(family[::-1]) is family[0]
    assert family[0] is not None
    trace = gr1.GR1Behavior(states=[{"q": False}, {"q": True}], loop_start=0)
    assert gr1.GR1TermList([family[0]]).contains_behavior(trace)
    assert not gr1.GR1TermList([family[1]]).contains_behavior(trace)


def test_support_syntax_depth_is_part_of_identity():
    family = candidates(terms(liv=["q"]), terms(liv=["a", "a & (X(b) | !X(b))"]))
    assert family[1].support_id[0] == 0
    assert family[2].support_id[0] == 1
    assert family[1].branch_id != family[2].branch_id


def test_aeb_actual_composition_mov_selection_and_compact_result():
    supervisor, vehicle = example.make_supervisor(), example.make_vehicle()
    original = gr1._refine_liv_term
    observed = []

    def observe(target, context, eliminated):
        if not gr1._equivalent(target.core.expr, example.parsed("MOV")):
            return original(target, context, eliminated)
        events = []
        original_qe = gr1._qe_forall_refinement

        def qe(target_expr, guard, variables):
            result = original_qe(target_expr, guard, variables)
            events.append((target_expr, guard, variables, result))
            return result

        with patch.object(gr1, "_qe_forall_refinement", qe):
            family = gr1._refinement_liv_candidates(target, context, eliminated)
        assert {v.name for v in eliminated} == {"MOV", "DCL", "STP", "u", "v"}
        assert context.to_bucket_dict() == (supervisor.a | supervisor.g).to_bucket_dict()
        assert len(family) == len(events) == 3
        assert [term.tag for term in family] == [gr1.GR1Tag.LIV, gr1.GR1Tag.INV, gr1.GR1Tag.INV]
        inv = gr1._and_expr(context.inv_terms())
        for index, ((target_expr, guard, variables, result), term) in enumerate(zip(events, family)):
            support = None if index == 0 else context.liv_terms()[index - 1]
            assert (
                max(gr1._core_next_depth(target.core), 0 if support is None else gr1._core_next_depth(support.core))
                == 0
            )
            expected_guard = inv if support is None else z3.And(inv, support.core.expr)
            assert gr1._equivalent(guard, expected_guard)
            atoms = gr1._z3_atoms_for_vars(variables, target_expr, guard)
            assert {str(atom) for atom in atoms} == {"MOV_0", "MOV_1", "DCL_0", "DCL_1", "STP_0", "STP_1", "u_0"}
            assert gr1._equivalent(result, term.core.expr)
        supervisor_inv = gr1._and_expr(supervisor.a.inv_terms())
        assert gr1._equivalent(family[0].core.expr, z3.Not(supervisor_inv))
        solver = z3.Solver()
        solver.add(supervisor_inv, family[0].core.expr)
        assert solver.check() == z3.unsat
        assert gr1._equivalent(family[1].core.expr, z3.Not(z3.And(supervisor_inv, example.parsed("!URG & !WRN"))))
        assert gr1._equivalent(family[2].core.expr, expr("true"))
        chosen = gr1._select_refinement_support(family)
        assert chosen is family[2]
        assert isinstance(chosen, gr1._RefinementLivCandidate)
        assert chosen.support_id == (0, example.parsed("MOV").sexpr())
        observed.append(chosen)
        return chosen

    with patch.object(gr1, "_refine_liv_term", observe):
        composition = supervisor.compose(vehicle, simplify=True)
    assert len(observed) == 1
    checks = example._compact_bucket_equivalence(
        composition, example._compact_environment_terms(), example._compact_external_guarantees()
    )
    assert all(forward and backward for forward, backward in checks.values())
    assert [term.core.text for term in composition.a.liv_terms()] == ["(!(URG) and !(WRN))"]
