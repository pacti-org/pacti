"""Semantic regression audit for the increasing-distance full-bucket AEB."""

import importlib.util
from pathlib import Path

import z3
from tests.gr1_semantic_assertions import assert_gr1_semantically_equal

from pacti.iocontract import Var
from pacti.iocontract.gr1_iocontract import GR1IoContract, _assumption_relative_guarantee_view, _project_liv_terms

_SPEC = importlib.util.spec_from_file_location(
    "gr1_aeb_increasing_distance", Path(__file__).parents[1] / "examples" / "gr1_aeb_increasing_distance.py"
)
assert _SPEC is not None and _SPEC.loader is not None
_EXAMPLE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_EXAMPLE)
conjunction = _EXAMPLE.conjunction
equivalent = _EXAMPLE.equivalent
implies = _EXAMPLE.implies
make_actuator = _EXAMPLE.make_actuator
make_supervisor = _EXAMPLE.make_supervisor
shifted_context = _EXAMPLE.shifted_context
composition_presentation_candidates = _EXAMPLE.composition_presentation_candidates
quotient_presentation_candidates = _EXAMPLE.quotient_presentation_candidates
print_three_views = _EXAMPLE.print_three_views
verified_quotient_init_candidate = _EXAMPLE.verified_quotient_init_candidate


def formulas():
    d, u, a0, a1 = z3.Reals("d_0 u_0 a_0 a_1")
    e = z3.Bool("e_0")
    h = z3.And(z3.Implies(e, d >= -40), z3.Implies(z3.Not(e), d >= 5))
    assumptions = z3.And(
        d >= 0, d <= 30, z3.Implies(d <= 8, e), z3.Implies(d >= 20, z3.Not(e)), z3.Implies(z3.Not(e), d <= 25)
    )
    guarantees = z3.And(
        a1 >= z3.RealVal("-11/2"),
        a1 <= d / 10 - z3.RealVal("1/2"),
        z3.Implies(e, a1 <= z3.RealVal("-5/2")),
        z3.Implies(z3.Not(e), a1 >= -1),
    )
    return d, u, a0, a1, e, h, assumptions, guarantees


def test_exact_rational_parsing_and_next_flattening() -> None:
    supervisor, actuator = make_supervisor(), make_actuator()
    d, u, _, a1, e, _, _, _ = formulas()
    expected_s = [u <= d / 10 - 1, z3.Implies(z3.Not(e), u >= z3.RealVal("-1/2"))]
    expected_a = [u <= z3.RealVal("3/2"), u - z3.RealVal("1/2") <= a1, a1 <= u + z3.RealVal("1/2")]
    assert equivalent(supervisor.g.inv_terms()[1].core.expr, expected_s[0])
    assert equivalent(supervisor.g.inv_terms()[3].core.expr, expected_s[1])
    assert equivalent(actuator.a.inv_terms()[1].core.expr, expected_a[0])
    assert equivalent(actuator.g.inv_terms()[0].core.expr, expected_a[1])
    assert equivalent(actuator.g.inv_terms()[1].core.expr, expected_a[2])


def test_composition_refinement_and_assumption_buckets() -> None:
    supervisor, actuator = make_supervisor(), make_actuator()
    target = supervisor.compose(actuator, simplify=True)
    d, u, _, _, e, _, expected, _ = formulas()
    compatibility = z3.Tactic("qe")(
        z3.ForAll([u], z3.Implies(conjunction(supervisor.g.inv_terms()), conjunction(actuator.a.inv_terms())))
    ).as_expr()
    assert equivalent(compatibility, z3.Or(e, d <= 25))
    assert equivalent(conjunction(target._operation_assumptions.init_terms()), z3.And(d >= 20, z3.Not(e)))
    assert equivalent(conjunction(target._operation_assumptions.inv_terms()), expected)
    assert len(target._operation_assumptions.liv_terms()) == 1
    assert equivalent(target._operation_assumptions.liv_terms()[0].core.expr, d >= 20)


def test_raw_relaxations_and_separate_liveness_projections() -> None:
    supervisor, actuator = make_supervisor(), make_actuator()
    raw = supervisor.compose(actuator, simplify=False)
    d, u, a0, a1, e, h, _, expected_g = formulas()
    raw_init = conjunction(raw.g.init_terms())
    for fact in (a0 == 0, a1 >= z3.RealVal("-1/2"), a1 <= z3.RealVal("1/2"), d >= 10, z3.Not(e)):
        assert implies(raw_init, fact)
    projection = z3.Tactic("qe")(
        z3.Exists([u], z3.And(conjunction(supervisor.g.inv_terms()), conjunction(actuator.g.inv_terms())))
    ).as_expr()
    assert equivalent(projection, z3.And(h, expected_g))
    projected_s = _project_liv_terms(supervisor.g.liv_terms(), supervisor.g, [Var("u")])
    assert len(projected_s) == 1
    assert equivalent(projected_s[0].core.expr, z3.And(z3.Not(e), d >= 5))
    projected_a = z3.Tactic("qe")(z3.Exists([u], z3.And(conjunction(supervisor.g.inv_terms()), a0 >= -1))).as_expr()
    assert equivalent(projected_a, z3.And(a0 >= -1, h))


def test_displayed_composition_is_expected_semantically() -> None:
    target = make_supervisor().compose(make_actuator(), simplify=True)
    display = _assumption_relative_guarantee_view(target)
    d, _, a0, a1, e, _, assumptions, guarantees = formulas()
    init_context = z3.And(d >= 20, z3.Not(e), shifted_context(target, display.init_terms()))
    assert equivalent(
        conjunction(display.init_terms()),
        z3.And(a0 == 0, a1 >= z3.RealVal("-1/2"), a1 <= z3.RealVal("1/2")),
        init_context,
    )
    assert equivalent(conjunction(display.inv_terms()), guarantees, shifted_context(target, display.inv_terms()))
    # The stored display core retains H, but H follows from the composed invariant.
    assert len(display.liv_terms()) == 1
    assert equivalent(display.liv_terms()[0].core.expr, a0 >= -1, assumptions)


def test_system_level_consequences() -> None:
    d, _, _, a1, e, _, assumptions, guarantees = formulas()
    context = z3.And(assumptions, guarantees)
    assert implies(context, z3.Implies(d <= 8, a1 <= z3.RealVal("-5/2")))
    assert implies(context, z3.Implies(d >= 20, a1 >= -1))
    assert implies(context, z3.Implies(z3.Not(e), a1 <= 2))


def test_printing_and_canonical_serialization_are_semantically_non_destructive() -> None:
    target = make_supervisor().compose(make_actuator(), simplify=True)
    before = target.to_dict()
    target.canonical_debug_dump()
    target.debug_dump()
    target.to_pretty_string(assumption_relative=True)
    assert target.to_dict() == before
    restored = GR1IoContract.from_dict(before)
    assert_gr1_semantically_equal(target, restored)
    for left, right in (
        (target._operation_assumptions, restored._operation_assumptions),
        (target._operation_guarantees, restored._operation_guarantees),
        (target.a, restored.a),
        (target.g, restored.g),
    ):
        assert left.refines(right) and right.refines(left)


def test_quotient_assumption_projection_and_liveness_preservation() -> None:
    supervisor = make_supervisor()
    target = supervisor.compose(make_actuator(), simplify=True)
    quotient = target.quotient(supervisor, simplify=True)
    d, u, _, _, e, _, assumptions, _ = formulas()
    projected = z3.Tactic("qe")(z3.Exists([d, e], z3.And(assumptions, conjunction(supervisor.g.inv_terms())))).as_expr()
    assert equivalent(conjunction(quotient._operation_assumptions.inv_terms()), projected)
    assert len(quotient._operation_assumptions.liv_terms()) == 1
    assert equivalent(
        quotient._operation_assumptions.liv_terms()[0].core.expr, z3.And(u >= -5, u >= z3.RealVal("-1/2"))
    )
    # Synthetic recurrence is guarded by context; compare under quotient assumptions.
    assert any(
        equivalent(term.core.expr, z3.Real("a_0") >= -1, conjunction(quotient._operation_assumptions.inv_terms()))
        for term in quotient._operation_guarantees.liv_terms()
    )


def test_quotient_init_compact_presentation_is_canonical_context_equivalent(capsys) -> None:
    supervisor = make_supervisor()
    quotient = supervisor.compose(make_actuator(), simplify=True).quotient(supervisor, simplify=True)
    candidate_a, candidate_g = quotient_presentation_candidates()
    candidate = verified_quotient_init_candidate(quotient, candidate_g)
    exact = conjunction(quotient._operation_guarantees.init_terms())
    compact = conjunction(candidate.init_terms())
    u_0, u_1, a_0, a_1 = z3.Reals("u_0 u_1 a_0 a_1")
    exact_guarded_compact = z3.Implies(
        z3.And(
            u_0 == 0,
            u_0 >= -5,
            u_0 >= z3.RealVal("-1/2"),
            u_1 >= -5,
            z3.Or(u_1 <= -3, u_1 >= z3.RealVal("-1/2")),
        ),
        z3.And(
            a_0 == u_0,
            a_1 >= z3.RealVal("-1/2"),
            a_1 <= z3.RealVal("1/2"),
        ),
    )
    context = z3.And(
        conjunction(quotient._operation_assumptions.init_terms()),
        shifted_context(
            quotient,
            quotient._operation_guarantees.init_terms() + candidate.init_terms(),
        ),
    )
    before = quotient.to_dict()
    canonical_before = exact.sexpr()
    stored_before = conjunction(quotient.g.init_terms()).sexpr()

    assert equivalent(exact, exact_guarded_compact)
    assert implies(z3.And(context, exact), compact)
    assert implies(z3.And(context, compact), exact)
    assert print_three_views(
        "QUOTIENT",
        quotient,
        (candidate_a, candidate_g),
        omit_verbose_guarantee_init=True,
    )
    rendered = capsys.readouterr().out

    assert "[exact generated condition omitted from concise output]" not in rendered
    assert "a = 0" in rendered
    assert "<=" in rendered and "X(a)" in rendered
    assert quotient.to_dict() == before
    assert conjunction(quotient._operation_guarantees.init_terms()).sexpr() == canonical_before
    assert conjunction(quotient.g.init_terms()).sexpr() == stored_before


def test_round_trip_quotient_and_recomposition_directions() -> None:
    supervisor = make_supervisor()
    target = supervisor.compose(make_actuator(), simplify=True)
    restored = GR1IoContract.from_dict(target.to_dict())
    quotient = target.quotient(supervisor, simplify=True)
    restored_q = restored.quotient(supervisor, simplify=True)
    assert_gr1_semantically_equal(quotient, restored_q)
    assert quotient._operation_assumptions.refines(restored_q._operation_assumptions)
    assert restored_q._operation_assumptions.refines(quotient._operation_assumptions)
    assert quotient._operation_guarantees.refines(restored_q._operation_guarantees)
    assert restored_q._operation_guarantees.refines(quotient._operation_guarantees)
    recomposed = supervisor.compose(quotient, simplify=True)
    assert recomposed.refines(target)
    # Recurrent synthetic certificates now allow both directions.
    assert target.refines(recomposed)


def test_increasing_distance_repeated_operations_are_semantically_stable() -> None:
    supervisor, actuator = make_supervisor(), make_actuator()
    target_1 = supervisor.compose(actuator, simplify=True)
    target_2 = supervisor.compose(actuator, simplify=True)
    assert_gr1_semantically_equal(target_1, target_2)

    for simplify in (False, True):
        first = target_1.quotient(supervisor, simplify=simplify)
        second = target_1.quotient(supervisor, simplify=simplify)
        assert_gr1_semantically_equal(first, second)


def test_composition_liv_projection_and_display_residuals_are_exact() -> None:
    target = make_supervisor().compose(make_actuator(), simplify=True)
    d, _, a0, _, e, h, assumptions, _ = formulas()
    expected_first = z3.And(a0 >= -1, h)
    expected_second = z3.And(z3.Not(e), d >= 5)
    stored = target.g.liv_terms()

    assert len(target._operation_guarantees.liv_terms()) == 3
    assert len(stored) == 2
    assert equivalent(stored[0].core.expr, expected_first)
    assert equivalent(expected_first, stored[0].core.expr)
    assert equivalent(stored[1].core.expr, expected_second)
    assert equivalent(expected_second, stored[1].core.expr)
    assert implies(assumptions, h)

    support = target.a.liv_terms()[0].core.expr
    support_guard = shifted_context(target, [target.a.liv_terms()[0], stored[1]])
    assert implies(z3.And(support_guard, support), expected_second)

    _, displayed = target.presentation_view()
    assert len(displayed.liv_terms()) == 1
    assert equivalent(displayed.liv_terms()[0].core.expr, a0 >= -1)


def test_verified_compact_composition_presentation_is_contextually_exact() -> None:
    target = make_supervisor().compose(make_actuator(), simplify=True)
    candidate_a, candidate_g = composition_presentation_candidates()
    displayed_a, displayed_g = target.presentation_view(candidate_a, candidate_g)
    d, _, a0, a1, e, _, assumptions, guarantees = formulas()

    assert equivalent(conjunction(displayed_a.inv_terms()), assumptions)
    assert equivalent(
        conjunction(displayed_g.init_terms()),
        z3.And(a0 == 0, a1 >= z3.RealVal("-1/2"), a1 <= z3.RealVal("1/2")),
        z3.And(conjunction(target.a.init_terms()), shifted_context(target, displayed_g.init_terms())),
    )
    assert equivalent(
        conjunction(displayed_g.inv_terms()), guarantees, shifted_context(target, displayed_g.inv_terms())
    )


def test_verified_compact_quotient_presentation_is_contextually_exact() -> None:
    supervisor = make_supervisor()
    quotient = supervisor.compose(make_actuator(), simplify=True).quotient(supervisor, simplify=True)
    candidate_a, candidate_g = quotient_presentation_candidates()
    displayed_a, displayed_g = quotient.presentation_view(candidate_a, candidate_g)
    u0, u1, a0, a1 = z3.Reals("u_0 u_1 a_0 a_1")
    half = z3.RealVal("1/2")
    f0 = z3.And(u0 >= -5, u0 <= z3.RealVal("3/2"), z3.Or(u0 <= -3, u0 >= -half))
    f1 = z3.And(u1 >= -5, u1 <= z3.RealVal("3/2"), z3.Or(u1 <= -3, u1 >= -half))
    expected_g = z3.And(
        z3.Implies(u0 <= -3, z3.And(a1 >= z3.RealVal("-11/2"), a1 <= u0 + half)),
        z3.Implies(u0 >= -half, z3.And(a1 >= -1, a1 <= u0 + half)),
    )

    assert equivalent(conjunction(displayed_a.inv_terms()), f0)
    assert equivalent(conjunction(displayed_g.inv_terms()), expected_g, z3.And(f0, f1))


def test_rendering_is_non_mutating_and_operations_are_unchanged() -> None:
    supervisor = make_supervisor()
    target = supervisor.compose(make_actuator(), simplify=True)
    before = target.to_dict()
    before_q = target.quotient(supervisor, simplify=True)
    candidate_a, candidate_g = composition_presentation_candidates()

    target.to_pretty_string(candidate_assumptions=candidate_a, candidate_guarantees=candidate_g)

    assert target.to_dict() == before
    after_q = target.quotient(supervisor, simplify=True)
    assert before_q._operation_assumptions.refines(after_q._operation_assumptions)
    assert after_q._operation_assumptions.refines(before_q._operation_assumptions)
    assert before_q._operation_guarantees.refines(after_q._operation_guarantees)
    assert after_q._operation_guarantees.refines(before_q._operation_guarantees)
