"""Focused semantic regressions for the exact-rational AEB integration audit."""

import copy

import z3
from tests.gr1_semantic_assertions import assert_formula_semantically_equal, assert_gr1_semantically_equal

from examples.gr1_aeb_full_buckets import (
    conjunction,
    equivalent,
    make_actuator,
    make_supervisor,
    shifted_assumption_context,
    verified_quotient_init_candidate,
)
from pacti.iocontract import Var
from pacti.iocontract.gr1_iocontract import (
    GR1IoContract,
    GR1TermList,
    _assumption_relative_guarantee_view,
    _eliminate_quantifiers,
    _project_liv_terms,
)


def test_aeb_exact_contract_literals_and_input_dependent_envelope() -> None:
    supervisor = make_supervisor()
    actuator = make_actuator()
    d_0, u_0, a_1 = z3.Reals("d_0 u_0 a_1")

    assert equivalent(supervisor.g.liv_terms()[0].core.expr, u_0 >= z3.RealVal("-1/2"))
    assert equivalent(supervisor.g.inv_terms()[1].core.expr, u_0 <= 2 - d_0 / 10)
    assert equivalent(actuator.g.inv_terms()[0].core.expr, a_1 >= u_0 - z3.RealVal("1/2"))


def test_aeb_compatibility_refinement_is_new_nonredundant_assumption() -> None:
    supervisor = make_supervisor()
    actuator = make_actuator()
    d_0, u_0 = z3.Reals("d_0 u_0")
    e_0 = z3.Bool("e_0")
    refinement = z3.Tactic("qe")(
        z3.ForAll(
            [u_0],
            z3.Implies(conjunction(supervisor.g.inv_terms()), conjunction(actuator.a.inv_terms())),
        )
    ).as_expr()
    expected = z3.Or(e_0, d_0 >= 10)

    assert equivalent(refinement, expected)
    # d=9,e=false satisfies the original supervisor invariant but violates compatibility.
    solver = z3.Solver()
    solver.add(conjunction(supervisor.a.inv_terms()), d_0 == 9, z3.Not(e_0), z3.Not(expected))
    assert solver.check() == z3.sat


def test_aeb_composition_contains_expected_compatibility_assumption() -> None:
    supervisor = make_supervisor()
    target = supervisor.compose(make_actuator(), simplify=True)
    d_0 = z3.Real("d_0")
    e_0 = z3.Bool("e_0")
    expected = z3.And(
        d_0 >= 0,
        d_0 <= 20,
        z3.Implies(d_0 <= 8, e_0),
        z3.Implies(d_0 >= 15, z3.Not(e_0)),
        z3.Implies(z3.Not(e_0), d_0 >= 10),
    )

    assert equivalent(conjunction(target.a.inv_terms()), expected)


def test_aeb_projected_supervisor_liveness_is_exact_expected_core() -> None:
    supervisor = make_supervisor()
    projected = _project_liv_terms(supervisor.g.liv_terms(), supervisor.g, [Var("u")])
    d_0 = z3.Real("d_0")
    e_0 = z3.Bool("e_0")

    assert len(projected) == 1
    assert equivalent(projected[0].core.expr, z3.And(z3.Not(e_0), d_0 <= 25))


def test_aeb_independent_tracking_projection_matches_hand_derivation_under_assumptions() -> None:
    supervisor = make_supervisor()
    actuator = make_actuator()
    d_0, u_0, a_1 = z3.Reals("d_0 u_0 a_1")
    e_0 = z3.Bool("e_0")
    projection = z3.Tactic("qe")(
        z3.Exists([u_0], z3.And(conjunction(supervisor.g.inv_terms()), conjunction(actuator.g.inv_terms())))
    ).as_expr()
    expected = z3.And(
        a_1 >= z3.RealVal("-11/2"),
        a_1 <= z3.RealVal("5/2") - d_0 / 10,
        z3.Implies(e_0, a_1 <= z3.RealVal("-5/2")),
        z3.Implies(z3.Not(e_0), a_1 >= -1),
    )
    assumptions = z3.And(
        d_0 >= 0,
        d_0 <= 20,
        z3.Implies(d_0 <= 8, e_0),
        z3.Implies(d_0 >= 15, z3.Not(e_0)),
        z3.Implies(z3.Not(e_0), d_0 >= 10),
    )

    assert equivalent(projection, expected, assumptions)


def test_aeb_assumption_relative_display_hides_supported_liv_without_mutation() -> None:
    target = make_supervisor().compose(make_actuator(), simplify=True)
    before = target.to_machine_dict()
    before_terms = list(target.g.terms)
    display = _assumption_relative_guarantee_view(target)
    a_0, d_0 = z3.Reals("a_0 d_0")
    e_0 = z3.Bool("e_0")

    # The generic display reducer may retain assumption-feasibility predicates
    # conjoined with the actuator liveness, but every displayed liveness must
    # still entail the actuator's recurring output obligation.
    assert display.liv_terms()
    assert all(z3.Solver().check(term.core.expr, z3.Not(a_0 >= -1)) == z3.unsat for term in display.liv_terms())
    assert not any(equivalent(term.core.expr, z3.And(z3.Not(e_0), d_0 <= 25)) for term in display.liv_terms())
    target.to_pretty_string(assumption_relative=True)
    assert target.to_machine_dict() == before
    assert target.g.terms == before_terms


def test_aeb_canonical_snapshot_restores_quotient_context_and_free_liveness() -> None:
    supervisor = make_supervisor()
    target = supervisor.compose(make_actuator(), simplify=True)
    d_0, u_0, a_0 = z3.Reals("d_0 u_0 a_0")
    e_0 = z3.Bool("e_0")
    expected_inv = z3.And(
        u_0 >= -5,
        u_0 <= 1,
        z3.Or(u_0 <= -3, u_0 >= z3.RealVal("-1/2")),
    )

    assert target._operation_assumptions.refines(supervisor._operation_assumptions)
    assert equivalent(
        conjunction(target._operation_assumptions.init_terms()),
        z3.And(d_0 >= 15, z3.Not(e_0)),
    )
    assert equivalent(conjunction(target.a.init_terms()), d_0 >= 15)
    assert any(equivalent(term.core.expr, a_0 >= -1) for term in target._operation_guarantees.liv_terms())

    quotient = target.quotient(supervisor, simplify=True)

    assert equivalent(conjunction(quotient._operation_assumptions.inv_terms()), expected_inv)
    # Synthetic recurrence is guarded by context; compare under quotient assumptions.
    assert any(
        equivalent(term.core.expr, z3.Real("a_0") >= -1, conjunction(quotient._operation_assumptions.inv_terms()))
        for term in quotient._operation_guarantees.liv_terms()
    )


def test_old_aeb_quotient_init_compact_presentation_is_context_equivalent() -> None:
    supervisor = make_supervisor()
    quotient = supervisor.compose(make_actuator(), simplify=True).quotient(supervisor, simplify=True)
    candidate = verified_quotient_init_candidate(quotient)
    exact = conjunction(quotient._operation_guarantees.init_terms())
    compact = conjunction(candidate.init_terms())
    context = z3.And(
        conjunction(quotient._operation_assumptions.init_terms()),
        shifted_assumption_context(
            quotient,
            quotient._operation_guarantees.init_terms() + candidate.init_terms(),
        ),
    )
    before = quotient.to_dict()
    canonical_before = exact.sexpr()
    stored_before = conjunction(quotient.g.init_terms()).sexpr()

    assert equivalent(exact, compact, context)
    assert "a = 0" in candidate.to_pretty_string()
    assert "X(a)" in candidate.to_pretty_string()
    assert quotient.to_dict() == before
    assert conjunction(quotient._operation_guarantees.init_terms()).sexpr() == canonical_before
    assert conjunction(quotient.g.init_terms()).sexpr() == stored_before


def test_canonical_snapshot_round_trip_copy_deepcopy_and_rename() -> None:
    target = make_supervisor().compose(make_actuator(), simplify=True)
    supervisor = make_supervisor()
    serialized = target.to_dict()
    restored = GR1IoContract.from_dict(serialized)

    assert_gr1_semantically_equal(target, restored)
    original_raw = target.g.inv_terms()[0].core.raw_expr
    restored_raw = restored.g.inv_terms()[0].core.raw_expr
    assert original_raw is not None and restored_raw is not None
    assert_formula_semantically_equal(original_raw, restored_raw)
    assert_gr1_semantically_equal(target, copy.copy(target))
    assert_gr1_semantically_equal(target, copy.deepcopy(target))

    quotient = target.quotient(supervisor, simplify=True)
    restored_quotient = restored.quotient(supervisor, simplify=True)
    assert_gr1_semantically_equal(quotient, restored_quotient)

    renamed = target.rename_variable(Var("a"), Var("accel"))

    assert Var("a") not in renamed._operation_guarantees.vars
    assert Var("accel") in renamed._operation_guarantees.vars
    assert_gr1_semantically_equal(target, renamed.rename_variable(Var("accel"), Var("a")))


def _private_semantic_snapshot(contract: GR1IoContract):
    """Capture public and private bucket identities plus executable formulas."""
    termlists = (contract.a, contract.g, contract._operation_assumptions, contract._operation_guarantees)
    return (
        tuple(sorted(contract.__dict__)),
        tuple(id(termlist) for termlist in termlists),
        tuple(
            tuple(
                (
                    id(term),
                    term.tag,
                    term.core.expr.sexpr(),
                    None if term.core.raw_expr is None else term.core.raw_expr.sexpr(),
                )
                for term in termlist.terms
            )
            for termlist in termlists
        ),
        contract.to_dict(),
    )


def test_old_aeb_quotient_is_repeatable_and_non_mutating() -> None:
    target = make_supervisor().compose(make_actuator(), simplify=True)
    supervisor = make_supervisor()
    target_before = _private_semantic_snapshot(target)
    supervisor_before = _private_semantic_snapshot(supervisor)

    for simplify in (False, True):
        first = target.quotient(supervisor, simplify=simplify)
        first_before_second = first.canonical_debug_dump()
        second = target.quotient(supervisor, simplify=simplify)
        assert_gr1_semantically_equal(first, second)
        assert first.canonical_debug_dump() == first_before_second

        source_term_ids = {
            id(term)
            for termlist in (
                target.a,
                target.g,
                target._operation_assumptions,
                target._operation_guarantees,
                supervisor.a,
                supervisor.g,
                supervisor._operation_assumptions,
                supervisor._operation_guarantees,
            )
            for term in termlist.terms
        }
        first_canonical_ids = {
            id(term)
            for termlist in (first._operation_assumptions, first._operation_guarantees)
            for term in termlist.terms
        }
        first_stored_ids = {id(term) for termlist in (first.a, first.g) for term in termlist.terms}
        second_ids = {
            id(term)
            for termlist in (
                second.a,
                second.g,
                second._operation_assumptions,
                second._operation_guarantees,
            )
            for term in termlist.terms
        }
        assert first_canonical_ids.isdisjoint(first_stored_ids)
        assert first_canonical_ids.isdisjoint(source_term_ids)
        assert first_stored_ids.isdisjoint(source_term_ids)
        assert first_canonical_ids.isdisjoint(second_ids)
        assert first_stored_ids.isdisjoint(second_ids)

    for simplify_order in ((False, True, False, True), (True, False, True, False)):
        results = [target.quotient(supervisor, simplify=value) for value in simplify_order]
        assert_gr1_semantically_equal(results[0], results[2])
        assert_gr1_semantically_equal(results[1], results[3])

    assert _private_semantic_snapshot(target) == target_before
    assert _private_semantic_snapshot(supervisor) == supervisor_before


def test_old_aeb_quotient_matches_exact_invariant_theory() -> None:
    supervisor = make_supervisor()
    target = supervisor.compose(make_actuator(), simplify=True)
    quotient = target.quotient(supervisor, simplify=True)
    d_0, d_1, u_0, u_1 = z3.Reals("d_0 d_1 u_0 u_1")
    e_0, e_1 = z3.Bools("e_0 e_1")
    del u_0, u_1
    first_pass, _ = target._operation_guarantees.elim_vars_by_refining_quotient_context(
        supervisor._operation_guarantees,
        target._operation_assumptions,
        [Var("d"), Var("e")],
        simplify=False,
        tactics_order=[],
    )
    second_pass_target = z3.And(
        conjunction(first_pass.inv_terms()),
        conjunction(supervisor._operation_assumptions.inv_terms()),
    )
    target_assumptions_0 = conjunction(target._operation_assumptions.inv_terms())
    substitutions = []
    for variable in z3.z3util.get_vars(target_assumptions_0):
        name = variable.decl().name()
        if name.endswith("_0"):
            substitutions.append((variable, z3.Const(name[:-2] + "_1", variable.sort())))
    target_assumptions_1 = z3.substitute(target_assumptions_0, *substitutions)
    exact_cave_theory = z3.ForAll(
        [d_0, d_1, e_0, e_1],
        z3.Implies(z3.And(target_assumptions_0, target_assumptions_1), second_pass_target),
    )

    repeated_qe = [_eliminate_quantifiers(exact_cave_theory) for _ in range(3)]
    assert all(equivalent(repeated_qe[0], candidate) for candidate in repeated_qe[1:])
    assert equivalent(conjunction(quotient._operation_guarantees.inv_terms()), exact_cave_theory)


def test_old_aeb_repeated_composition_and_copy_quotients_are_stable() -> None:
    supervisor, actuator = make_supervisor(), make_actuator()
    first_target = supervisor.compose(actuator, simplify=True)
    second_target = supervisor.compose(actuator, simplify=True)
    assert_gr1_semantically_equal(first_target, second_target)
    assert_gr1_semantically_equal(
        first_target.quotient(supervisor, simplify=True),
        copy.deepcopy(first_target).quotient(copy.copy(supervisor), simplify=True),
    )


def test_old_aeb_quotient_is_semantically_independent_of_term_order() -> None:
    supervisor = make_supervisor()
    target = supervisor.compose(make_actuator(), simplify=True)
    reordered = target.copy()
    reordered._set_operation_buckets(
        GR1TermList(list(reversed(target._operation_assumptions.terms))),
        GR1TermList(list(reversed(target._operation_guarantees.terms))),
    )

    assert_gr1_semantically_equal(
        target.quotient(supervisor, simplify=True),
        reordered.quotient(supervisor, simplify=True),
    )


def test_old_serialization_uses_stored_buckets_as_canonical_fallback() -> None:
    source = make_actuator().to_dict()
    source.pop("gr1_operation_buckets")

    restored = GR1IoContract.from_dict(source, simplify=False)

    assert restored._operation_assumptions.to_bucket_dict() == restored.a.to_bucket_dict()
    assert restored._operation_guarantees.to_bucket_dict() == restored.g.to_bucket_dict()
    assert "gr1_operation_buckets" in restored.to_dict()


def test_liveness_snapshot_preserves_weaker_free_liveness_after_reduction() -> None:
    contract = GR1IoContract.from_dict(
        {
            "input_vars": ["s"],
            "output_vars": ["r"],
            "variable_sorts": {"r": "bool", "s": "bool"},
            "assumptions": {},
            "guarantees": {"liv": ["r", "r & s"]},
        },
        simplify=False,
    )
    reduced = GR1IoContract(
        assumptions=contract.a,
        guarantees=contract.g.simplify(),
        input_vars=contract.inputvars,
        output_vars=contract.outputvars,
        simplify=False,
        variable_sorts=contract.variable_sorts,
    )
    reduced._set_operation_buckets(contract.a, contract.g)

    assert len(reduced.g.liv_terms()) == 1
    assert len(reduced._operation_guarantees.liv_terms()) == 2
    projected, _ = reduced._operation_guarantees.elim_vars_by_refining(
        reduced._operation_assumptions,
        [Var("s")],
        simplify=False,
        tactics_order=[],
    )
    assert any(equivalent(term.core.expr, z3.Bool("r_0")) for term in projected.liv_terms())
