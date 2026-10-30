from typing import Any, Dict, Tuple

import pytest
import z3
from tests.gr1_semantic_assertions import assert_formula_semantically_equal

from pacti.iocontract import Var
from pacti.iocontract.gr1_iocontract import (
    GR1Behavior,
    GR1CoreFormula,
    GR1IoContract,
    GR1Tag,
    GR1Term,
    GR1TermList,
    _associated_liv_supports,
    _core_semantically_depends_on_eliminated_vars,
    _equivalence_guarded_formula,
    _normalize_liv_core_global_shift,
    canonicalize_mixed_linear_formula,
    parse_gr1_core,
)
from pacti.utils.errors import IncompatibleArgsError


def _core(expr: Any) -> GR1CoreFormula:
    return GR1CoreFormula.of_expr(
        str(expr),
        [Var(v.decl().name()) for v in z3.z3util.get_vars(expr)],
        expr,
    )


def _is_equivalent(left: Any, right: Any) -> bool:
    solver = z3.Solver()
    solver.add(left != right)
    return bool(solver.check() == z3.unsat)


@pytest.mark.parametrize(
    ("formula", "expected_bound"),
    [
        ("x >= 1/2", z3.RealVal("1/2")),
        ("x >= -1/2", z3.RealVal("-1/2")),
        ("x >= (-1)/2", z3.RealVal("-1/2")),
        ("x >= -(1/2)", z3.RealVal("-1/2")),
        ("x >= -0.5", z3.RealVal("-1/2")),
        ("x >= -11/2", z3.RealVal("-11/2")),
    ],
)
def test_real_numeric_rational_literals_are_exact(formula: str, expected_bound: Any) -> None:
    core = parse_gr1_core(formula, {"x": "real"})

    assert _is_equivalent(core.expr, z3.Real("x_0") >= expected_bound)


def test_real_numeric_rational_upper_bound_is_exact() -> None:
    core = parse_gr1_core("x <= 3/10", {"x": "real"})

    assert _is_equivalent(core.expr, z3.Real("x_0") <= z3.RealVal("3/10"))


def test_real_fraction_and_decimal_spellings_are_equivalent() -> None:
    half_fraction = parse_gr1_core("x >= 1/2", {"x": "real"})
    half_decimal = parse_gr1_core("x >= 0.5", {"x": "real"})
    tenth_fraction = parse_gr1_core("x >= 1/10", {"x": "real"})
    tenth_decimal = parse_gr1_core("x >= 0.1", {"x": "real"})

    assert _is_equivalent(half_fraction.expr, half_decimal.expr)
    assert _is_equivalent(tenth_fraction.expr, tenth_decimal.expr)


def test_semantic_formula_identity_does_not_require_textual_normalization_identity() -> None:
    direct = parse_gr1_core("x <= 1", {"x": "real"})
    scaled = parse_gr1_core("2*x <= 2", {"x": "real"})

    assert direct.text != scaled.text
    assert_formula_semantically_equal(direct.expr, scaled.expr)


def test_real_rational_serialization_round_trip_is_exact() -> None:
    contract = GR1IoContract.from_dict(
        {
            "input_vars": ["x"],
            "output_vars": [],
            "variable_sorts": {"x": "real"},
            "assumptions": {"init": [], "inv": ["x >= -1/2", "x <= 3/10"], "liv": []},
            "guarantees": {},
        },
        simplify=False,
    )
    restored = GR1IoContract.from_dict(contract.to_dict(), simplify=False)

    assert _is_equivalent(
        z3.And(*[term.core.expr for term in restored.a.inv_terms()]),
        z3.And(z3.Real("x_0") >= z3.RealVal("-1/2"), z3.Real("x_0") <= z3.RealVal("3/10")),
    )


def test_real_variable_division_and_rational_offset_are_exact() -> None:
    envelope = parse_gr1_core("u <= 2 - d/10", {"d": "real", "u": "real"})
    offset = parse_gr1_core("u <= 5/2 - d/10", {"d": "real", "u": "real"})
    d_0, u_0 = z3.Reals("d_0 u_0")

    assert _is_equivalent(envelope.expr, u_0 <= 2 - d_0 / 10)
    assert _is_equivalent(offset.expr, u_0 <= z3.RealVal("5/2") - d_0 / 10)


def test_semantic_dependence_ignores_tautological_eliminated_bool() -> None:
    q_0, s_0 = z3.Bools("q_0 s_0")
    core = _core(z3.And(s_0, z3.Or(q_0, z3.Not(q_0))))

    assert not _core_semantically_depends_on_eliminated_vars(core, [Var("q")])


def test_semantic_dependence_ignores_multiple_shifted_tautologies() -> None:
    q_0, q_1, s_0 = z3.Bools("q_0 q_1 s_0")
    tautology = z3.Or(
        z3.And(q_0, q_1),
        z3.And(q_0, z3.Not(q_1)),
        z3.And(z3.Not(q_0), q_1),
        z3.And(z3.Not(q_0), z3.Not(q_1)),
    )
    core = _core(z3.And(s_0, tautology))

    assert not _core_semantically_depends_on_eliminated_vars(core, [Var("q")])


def test_semantic_dependence_detects_current_and_next_eliminated_bools() -> None:
    q_0, q_1, r_1, s_0 = z3.Bools("q_0 q_1 r_1 s_0")

    assert not _core_semantically_depends_on_eliminated_vars(_core(s_0), [Var("q")])
    assert not _core_semantically_depends_on_eliminated_vars(_core(r_1), [Var("q")])
    assert _core_semantically_depends_on_eliminated_vars(_core(q_0), [Var("q")])
    assert _core_semantically_depends_on_eliminated_vars(_core(q_1), [Var("q")])
    assert _core_semantically_depends_on_eliminated_vars(_core(z3.And(q_0, s_0)), [Var("q")])
    assert _core_semantically_depends_on_eliminated_vars(_core(z3.Or(q_1, s_0)), [Var("q")])


def test_liv_refinement_projects_semantically_q_free_generated_target() -> None:
    q_0, q_1, r_0, s_0 = z3.Bools("q_0 q_1 r_0 s_0")
    tautology = z3.Or(
        z3.And(q_0, q_1),
        z3.And(q_0, z3.Not(q_1)),
        z3.And(z3.Not(q_0), q_1),
        z3.And(z3.Not(q_0), z3.Not(q_1)),
    )
    target = GR1TermList.from_bucket_formulas(liv=[_core(z3.And(s_0, tautology))])
    context = GR1TermList.from_bucket_formulas(
        inv=[_core(r_0 == q_1)],
        liv=[_core(q_0), _core(r_0)],
    )

    result, _ = target.elim_vars_by_refining(
        context=context,
        vars_to_elim=[Var("q")],
        simplify=False,
        tactics_order=[],
    )

    assert result.inv_terms() == []
    assert len(result.liv_terms()) == 1
    assert _is_equivalent(result.liv_terms()[0].core.expr, s_0)
    assert all(not variable.name.startswith("q_") for variable in result.liv_terms()[0].core.vars)


def test_liv_simplification_merges_single_variable_global_shifts() -> None:
    q_0, q_2, q_5 = z3.Bools("q_0 q_2 q_5")
    terms = GR1TermList.from_bucket_formulas(liv=[_core(q_0), _core(q_2), _core(q_5)])

    simplified = terms.simplify()

    assert len(simplified.liv_terms()) == 1
    assert _is_equivalent(simplified.liv_terms()[0].core.expr, q_0)


def test_liv_simplification_merges_uniformly_shifted_compound_cores() -> None:
    p_1, p_3, q_2, q_4 = z3.Bools("p_1 p_3 q_2 q_4")
    terms = GR1TermList.from_bucket_formulas(liv=[_core(z3.And(p_1, q_2)), _core(z3.And(p_3, q_4))])

    simplified = terms.simplify()

    assert len(simplified.liv_terms()) == 1
    assert _is_equivalent(
        simplified.liv_terms()[0].core.expr,
        z3.And(z3.Bool("p_0"), z3.Bool("q_1")),
    )


def test_liv_simplification_preserves_different_relative_offsets() -> None:
    p_1, q_2, q_3 = z3.Bools("p_1 q_2 q_3")
    terms = GR1TermList.from_bucket_formulas(liv=[_core(z3.And(p_1, q_2)), _core(z3.And(p_1, q_3))])

    simplified = terms.simplify()

    assert len(simplified.liv_terms()) == 2
    assert any(
        _is_equivalent(term.core.expr, z3.And(z3.Bool("p_0"), z3.Bool("q_1"))) for term in simplified.liv_terms()
    )
    assert any(
        _is_equivalent(term.core.expr, z3.And(z3.Bool("p_0"), z3.Bool("q_2"))) for term in simplified.liv_terms()
    )


def test_liv_global_shift_preserves_boolean_structure_and_sorts() -> None:
    p_2, p_5, q_3, q_6 = z3.Bools("p_2 p_5 q_3 q_6")
    boolean_terms = GR1TermList.from_bucket_formulas(
        liv=[_core(z3.Or(p_2, z3.Not(q_3))), _core(z3.Or(p_5, z3.Not(q_6)))]
    ).simplify()
    assert len(boolean_terms.liv_terms()) == 1
    assert _is_equivalent(
        boolean_terms.liv_terms()[0].core.expr,
        z3.Or(z3.Bool("p_0"), z3.Not(z3.Bool("q_1"))),
    )

    x_2, y_3 = z3.Reals("x_2 y_3")
    normalized = _normalize_liv_core_global_shift(_core(x_2 <= y_3))
    normalized_vars = z3.z3util.get_vars(normalized.expr)
    assert _is_equivalent(normalized.expr, z3.Real("x_0") <= z3.Real("y_1"))
    assert all(variable.sort() == z3.RealSort() for variable in normalized_vars)


def test_global_shift_normalization_is_not_applied_to_init_or_inv() -> None:
    q_0, q_1 = z3.Bools("q_0 q_1")
    init_only = GR1TermList.from_bucket_formulas(init=[_core(q_0), _core(q_1)]).simplify()
    inv_only = GR1TermList.from_bucket_formulas(inv=[_core(q_0), _core(q_1)]).simplify()

    # GF(q) = GF(X(q)), but INIT and INV boundary semantics retain both depths.
    assert _is_equivalent(z3.And(*[term.core.expr for term in init_only.init_terms()]), z3.And(q_0, q_1))
    assert _is_equivalent(z3.And(*[term.core.expr for term in inv_only.inv_terms()]), z3.And(q_0, q_1))


def test_unicode_pretty_prints_one_term_per_bucket() -> None:
    terms = GR1TermList.from_bucket_strings(
        init=["q"],
        inv=["q -> X(q)"],
        liv=["q"],
        variable_sorts={"q": "bool"},
    )

    rendered = terms.to_pretty_string()

    assert rendered == "INIT:\n  q\nINV:\n  □(q → X(q))\nLIV:\n  □◇(q)"


def test_unicode_pretty_lists_init_and_boxes_each_inv_without_mutation() -> None:
    terms = GR1TermList.from_bucket_strings(
        init=["p", "q"],
        inv=["p", "q"],
        variable_sorts={"p": "bool", "q": "bool"},
    )
    before_terms = list(terms.terms)
    before_buckets = terms.to_bucket_dict()

    rendered = terms.to_pretty_string()

    assert rendered == "INIT:\n  p\n  q\nINV:\n  □(p)\n  □(q)"
    assert "□(p ∧ q)" not in rendered
    assert len(terms.init_terms()) == 2
    assert len(terms.inv_terms()) == 2
    assert terms.terms == before_terms
    assert terms.to_bucket_dict() == before_buckets


def test_unicode_pretty_never_collapses_separate_liv_terms() -> None:
    terms = GR1TermList.from_bucket_strings(
        liv=["p", "q"],
        variable_sorts={"p": "bool", "q": "bool"},
    )

    rendered = terms.to_pretty_string()
    compact = terms.to_pretty_string(compact=True)

    assert rendered == "LIV:\n  □◇(p)\n  □◇(q)"
    assert compact == "□◇(p) ∧ □◇(q)"
    assert "□◇(p ∧ q)" not in rendered
    assert "□◇(p ∧ q)" not in compact
    assert len(terms.liv_terms()) == 2


def test_presentation_view_refuses_unproved_safety_candidate() -> None:
    contract = GR1IoContract.from_dict(
        {
            "input_vars": ["x"],
            "output_vars": ["y"],
            "variable_sorts": {"x": "real", "y": "real"},
            "assumptions": {"inv": ["x >= 0"]},
            "guarantees": {"inv": ["y >= x"]},
        },
        simplify=False,
    )
    bad_assumption = GR1TermList.from_bucket_strings(inv=["x >= 1"], variable_sorts={"x": "real", "y": "real"})
    bad_guarantee = GR1TermList.from_bucket_strings(inv=["y >= x + 1"], variable_sorts={"x": "real", "y": "real"})

    displayed_a, displayed_g = contract.presentation_view(bad_assumption, bad_guarantee)

    assert _is_equivalent(z3.And(*[term.core.expr for term in displayed_a.inv_terms()]), z3.Real("x_0") >= 0)
    assert _is_equivalent(
        z3.And(*[term.core.expr for term in displayed_g.inv_terms()]), z3.Real("y_0") >= z3.Real("x_0")
    )


def test_unicode_pretty_unflattens_nested_next_without_machine_names() -> None:
    q_0, s_2 = z3.Bools("q_0 s_2")
    terms = GR1TermList.from_bucket_formulas(inv=[_core(q_0 == s_2)])

    rendered = terms.to_pretty_string()

    assert "q = X(X(s))" in rendered or "X(X(s)) = q" in rendered
    assert "q_0" not in rendered
    assert "s_2" not in rendered


def test_unicode_contract_pretty_is_observational_only() -> None:
    contract = GR1IoContract.from_dict(
        {
            "input_vars": ["q"],
            "output_vars": ["r"],
            "variable_sorts": {"q": "bool", "r": "bool"},
            "assumptions": {"init": ["q"], "inv": ["q -> X(q)"], "liv": ["q"]},
            "guarantees": {"init": ["r = q"], "inv": ["q = X(r)"], "liv": ["r"]},
        },
        simplify=False,
    )
    before = contract.to_machine_dict()
    term_counts = (len(contract.a.terms), len(contract.g.terms))

    rendered = contract.to_pretty_string()

    assert "Inputs:  q" in rendered
    assert "INIT:\n    q" in rendered
    assert "INV:\n    □(q → X(q))" in rendered
    assert "□◇(q)" in rendered
    assert "INIT:\n    r" in rendered
    assert "INV:\n    □(q = X(r))" in rendered
    assert "□◇(r)" in rendered
    assert contract.to_machine_dict() == before
    assert (len(contract.a.terms), len(contract.g.terms)) == term_counts


def test_unicode_contract_compact_prints_true_for_empty_assumptions() -> None:
    contract = GR1IoContract.from_dict(
        {
            "input_vars": ["q"],
            "output_vars": ["r"],
            "variable_sorts": {"q": "bool", "r": "bool"},
            "assumptions": {"init": [], "inv": [], "liv": []},
            "guarantees": {"init": [], "inv": ["q = X(r)"], "liv": ["q", "r"]},
        },
        simplify=False,
    )

    rendered = contract.to_pretty_string(compact=True)

    assert "A = true" in rendered
    assert "G = □(q = X(r)) ∧ □◇(q) ∧ □◇(r)" in rendered


def test_assumption_relative_pretty_hides_fully_implied_init_without_mutation() -> None:
    contract = GR1IoContract.from_dict(
        {
            "input_vars": ["p"],
            "output_vars": [],
            "variable_sorts": {"p": "bool"},
            "assumptions": {"init": ["p"], "inv": [], "liv": []},
            "guarantees": {"init": ["p"], "inv": [], "liv": []},
        },
        simplify=False,
    )

    reduced = contract.to_pretty_string(assumption_relative=True)
    stored = contract.to_pretty_string(assumption_relative=False)

    assert "Guarantees\n  true" in reduced
    assert "Guarantees\n  INIT:\n    p" in stored
    assert len(contract.g.init_terms()) == 1


def test_assumption_relative_pretty_partially_reduces_init() -> None:
    contract = GR1IoContract.from_dict(
        {
            "input_vars": ["p"],
            "output_vars": ["q"],
            "variable_sorts": {"p": "bool", "q": "bool"},
            "assumptions": {"init": ["p"], "inv": [], "liv": []},
            "guarantees": {"init": ["p & q"], "inv": [], "liv": []},
        },
        simplify=False,
    )

    rendered = contract.to_pretty_string()

    assert "INIT:\n    q" in rendered
    assert _is_equivalent(contract.g.init_terms()[0].core.expr, z3.And(z3.Bool("p_0"), z3.Bool("q_0")))


def test_assumption_relative_pretty_reduces_inv_under_shifted_assumptions() -> None:
    contract = GR1IoContract.from_dict(
        {
            "input_vars": ["p"],
            "output_vars": ["q"],
            "variable_sorts": {"p": "bool", "q": "bool"},
            "assumptions": {"init": [], "inv": ["p -> X(p)"], "liv": []},
            "guarantees": {"init": [], "inv": ["(p -> X(p)) & q"], "liv": []},
        },
        simplify=False,
    )

    rendered = contract.to_pretty_string()

    assert "Guarantees\n  INV:\n    □(q)" in rendered
    assert len(contract.g.inv_terms()) == 1
    assert "p -> X(p)" in contract.g.to_bucket_dict()["inv"][0]


def test_assumption_relative_pretty_reduces_pointwise_inv_condition() -> None:
    contract = GR1IoContract.from_dict(
        {
            "input_vars": ["p"],
            "output_vars": ["q"],
            "variable_sorts": {"p": "bool", "q": "bool"},
            "assumptions": {"init": [], "inv": ["p"], "liv": []},
            "guarantees": {"init": [], "inv": ["p & q"], "liv": []},
        },
        simplify=False,
    )

    rendered = contract.to_pretty_string()

    assert "Guarantees\n  INV:\n    □(q)" in rendered
    stored = contract.g.inv_terms()[0].core.expr
    assert _is_equivalent(stored, z3.And(z3.Bool("p_0"), z3.Bool("q_0")))


def test_assumption_relative_pretty_hides_liv_implied_by_inv() -> None:
    contract = GR1IoContract.from_dict(
        {
            "input_vars": ["r"],
            "output_vars": [],
            "variable_sorts": {"r": "bool"},
            "assumptions": {"init": [], "inv": ["r"], "liv": []},
            "guarantees": {"init": [], "inv": [], "liv": ["r"]},
        },
        simplify=False,
    )

    assert "Guarantees\n  true" in contract.to_pretty_string()
    assert len(contract.g.liv_terms()) == 1


def test_assumption_relative_pretty_uses_one_recurring_liv_support() -> None:
    contract = GR1IoContract.from_dict(
        {
            "input_vars": ["d", "e"],
            "output_vars": [],
            "variable_sorts": {"d": "real", "e": "bool"},
            "assumptions": {
                "init": [],
                "inv": ["d >= 15 -> !e", "d <= 20"],
                "liv": ["d >= 15"],
            },
            "guarantees": {"init": [], "inv": [], "liv": ["!e & d <= 25"]},
        },
        simplify=False,
    )

    assert "Guarantees\n  true" in contract.to_pretty_string()
    assert len(contract.g.liv_terms()) == 1


def test_assumption_relative_pretty_never_synchronizes_liv_supports() -> None:
    contract = GR1IoContract.from_dict(
        {
            "input_vars": ["p", "q"],
            "output_vars": [],
            "variable_sorts": {"p": "bool", "q": "bool"},
            "assumptions": {"init": [], "inv": [], "liv": ["p", "q"]},
            "guarantees": {"init": [], "inv": [], "liv": ["p & q"]},
        },
        simplify=False,
    )

    rendered = contract.to_pretty_string()

    assert "□◇(p ∧ q)" in rendered
    assert len(contract.g.liv_terms()) == 1


def test_assumption_relative_pretty_retains_unsupported_liv_and_serialization() -> None:
    contract = GR1IoContract.from_dict(
        {
            "input_vars": ["p"],
            "output_vars": ["q"],
            "variable_sorts": {"p": "bool", "q": "bool"},
            "assumptions": {"init": [], "inv": [], "liv": ["p"]},
            "guarantees": {"init": [], "inv": [], "liv": ["q"]},
        },
        simplify=False,
    )
    before = contract.to_machine_dict()
    before_terms = list(contract.g.terms)

    rendered = contract.to_pretty_string(assumption_relative=True)

    assert "□◇(q)" in rendered
    assert contract.to_machine_dict() == before
    assert contract.g.terms == before_terms


def test_associated_liv_supports_use_target_union_all_invariant_vars() -> None:
    p_1, x_0, y_2, z_0, w_0 = z3.Bools("p_1 x_0 y_2 z_0 w_0")
    target = GR1Term(GR1Tag.LIV, _core(p_1))
    inv_terms = [
        GR1Term(GR1Tag.INV, _core(z3.Or(p_1, x_0))),
        GR1Term(GR1Tag.INV, _core(z3.Or(x_0, y_2))),
        # Disconnected invariant variables still belong to Vars(gamma_inv).
        GR1Term(GR1Tag.INV, _core(w_0)),
    ]
    associated = GR1Term(GR1Tag.LIV, _core(y_2))
    disconnected_but_relevant = GR1Term(GR1Tag.LIV, _core(w_0))
    unrelated = GR1Term(GR1Tag.LIV, _core(z_0))

    assert _associated_liv_supports(
        target,
        inv_terms,
        [unrelated, associated, disconnected_but_relevant],
    ) == [associated, disconnected_but_relevant]


def test_init_relaxation_projects_invariant_when_target_init_is_empty() -> None:
    p_0, q_0, r_1 = z3.Bools("p_0 q_0 r_1")
    target = GR1TermList()
    context = GR1TermList.from_bucket_formulas(inv=[_core(p_0 == q_0), _core(p_0 == r_1)])

    result, _ = target.elim_vars_by_relaxing(context, [Var("p")], simplify=False, tactics_order=[])

    assert len(result.init_terms()) == 1
    assert _is_equivalent(result.init_terms()[0].core.expr, q_0 == r_1)


def test_init_relaxation_omits_true_for_empty_init_buckets() -> None:
    p_0, q_0 = z3.Bools("p_0 q_0")
    target = GR1TermList()
    context = GR1TermList.from_bucket_formulas(inv=[_core(p_0 == q_0)])

    result, _ = target.elim_vars_by_relaxing(context, [Var("p")], simplify=False, tactics_order=[])

    assert result.init_terms() == []


def test_init_refinement_omits_true_when_target_init_is_empty() -> None:
    p_0, q_0 = z3.Bools("p_0 q_0")
    target = GR1TermList()
    context = GR1TermList.from_bucket_formulas(init=[_core(p_0)], inv=[_core(p_0 == q_0)])

    result, _ = target.elim_vars_by_refining(context, [Var("p")], simplify=False, tactics_order=[])

    assert result.init_terms() == []


def test_init_refinement_uses_true_for_empty_context_init() -> None:
    p_0, q_0, r_0 = z3.Bools("p_0 q_0 r_0")
    target = GR1TermList.from_bucket_formulas(init=[_core(r_0 == p_0)])
    context = GR1TermList.from_bucket_formulas(inv=[_core(p_0 == q_0)])

    result, _ = target.elim_vars_by_refining(context, [Var("p")], simplify=False, tactics_order=[])

    assert len(result.init_terms()) == 1
    assert _is_equivalent(result.init_terms()[0].core.expr, r_0 == q_0)


def test_post_cave_removes_init_implied_by_invariant() -> None:
    q_0, r_1 = z3.Bools("q_0 r_1")
    terms = GR1TermList.from_bucket_formulas(init=[_core(q_0 == r_1)], inv=[_core(q_0 == r_1)])

    simplified = terms.simplify()

    assert simplified.init_terms() == []
    assert len(simplified.inv_terms()) == 1


def test_post_cave_partially_reduces_init_under_invariant() -> None:
    q_0, r_0, r_1 = z3.Bools("q_0 r_0 r_1")
    original_init = z3.And(r_0 == q_0, q_0 == r_1)
    terms = GR1TermList.from_bucket_formulas(init=[_core(original_init)], inv=[_core(q_0 == r_1)])

    simplified = terms.simplify()

    assert len(simplified.init_terms()) == 1
    residual = simplified.init_terms()[0].core.expr
    assert _is_equivalent(residual, r_0 == q_0)
    assert _is_equivalent(z3.And(q_0 == r_1, residual), z3.And(q_0 == r_1, original_init))


def test_post_cave_removes_liv_implied_by_invariant() -> None:
    r_0 = z3.Bool("r_0")
    terms = GR1TermList.from_bucket_formulas(inv=[_core(r_0)], liv=[_core(r_0)])

    assert terms.simplify().liv_terms() == []


def test_post_cave_shifted_invariant_removes_liv() -> None:
    p_0, p_1, q_0, q_1 = z3.Bools("p_0 p_1 q_0 q_1")
    terms = GR1TermList.from_bucket_formulas(
        inv=[_core(z3.Implies(p_0, q_0))],
        liv=[_core(z3.Implies(p_1, q_1))],
    )

    assert terms.simplify().liv_terms() == []


def test_post_cave_does_not_remove_unforced_liv() -> None:
    p_0, q_0 = z3.Bools("p_0 q_0")
    terms = GR1TermList.from_bucket_formulas(inv=[_core(z3.Implies(p_0, q_0))], liv=[_core(q_0)])

    simplified = terms.simplify()

    assert len(simplified.liv_terms()) == 1
    assert _is_equivalent(simplified.liv_terms()[0].core.expr, q_0)


def test_post_cave_reduces_equivalent_and_weaker_invariants() -> None:
    p_0, q_0 = z3.Bools("p_0 q_0")
    terms = GR1TermList.from_bucket_formulas(
        inv=[_core(p_0), _core(p_0), _core(z3.Or(p_0, q_0))],
    )

    simplified = terms.simplify()

    assert len(simplified.inv_terms()) == 1
    assert _is_equivalent(simplified.inv_terms()[0].core.expr, p_0)


def test_liv_refinement_selects_first_incomparable_support() -> None:
    p_0, q_0, r_0 = z3.Bools("p_0 q_0 r_0")
    target = GR1TermList.from_bucket_formulas(liv=[_core(p_0)])
    context = GR1TermList.from_bucket_formulas(liv=[_core(z3.Or(p_0, q_0)), _core(z3.Or(p_0, r_0))])

    result, _ = target.elim_vars_by_refining(
        context=context,
        vars_to_elim=[Var("p")],
        simplify=False,
        tactics_order=[],
    )

    assert len(result.terms) == 1
    selected = result.inv_terms()[0]
    assert z3.is_true(z3.simplify(selected.core.expr == z3.Not(q_0)))


def test_liv_relaxation_reduces_combined_context_and_target_projections() -> None:
    p_0, q_0, r_0 = z3.Bools("p_0 q_0 r_0")
    target = GR1TermList.from_bucket_formulas(liv=[_core(z3.And(p_0, z3.Or(q_0, r_0))), _core(z3.And(p_0, r_0))])
    context = GR1TermList.from_bucket_formulas(liv=[_core(z3.Or(p_0, q_0)), _core(z3.And(p_0, q_0))])

    result, _ = target.elim_vars_by_relaxing(
        context=context,
        vars_to_elim=[Var("p")],
        simplify=False,
        tactics_order=[],
    )

    projected = [term.core.expr for term in result.liv_terms()]
    assert len(projected) == 2
    assert z3.is_true(z3.simplify(projected[0] == q_0))
    assert z3.is_true(z3.simplify(projected[1] == r_0))


def test_liv_relaxation_projects_context_without_target_liveness() -> None:
    p_0, q_0 = z3.Bools("p_0 q_0")
    target = GR1TermList()
    context = GR1TermList.from_bucket_formulas(liv=[_core(z3.And(p_0, q_0))])

    result, _ = target.elim_vars_by_relaxing(
        context=context,
        vars_to_elim=[Var("p")],
        simplify=False,
        tactics_order=[],
    )

    assert len(result.liv_terms()) == 1
    assert z3.is_true(z3.simplify(result.liv_terms()[0].core.expr == q_0))


def test_generated_core_vars_include_shifted_invariant_variables() -> None:
    p_0, p_1, q_0 = z3.Bools("p_0 p_1 q_0")
    target = GR1TermList.from_bucket_formulas(inv=[_core(p_1)])
    context = GR1TermList.from_bucket_formulas(inv=[_core(p_0 == q_0)])

    result, _ = target.elim_vars_by_relaxing(
        context=context,
        vars_to_elim=[Var("p")],
        simplify=False,
        tactics_order=[],
    )

    core = result.inv_terms()[0].core
    solver = z3.Solver()
    solver.add(core.expr != z3.Bool("q_1"))
    assert solver.check() == z3.unsat

    expression_vars = frozenset(Var(v.decl().name()) for v in z3.z3util.get_vars(core.expr))
    assert Var("q_1") in core.vars
    assert frozenset(core.vars) == expression_vars


def test_inv_relaxation_shift_closes_context_through_target_horizon() -> None:
    p_0, q_0, q_1 = z3.Bools("p_0 q_0 q_1")
    target = GR1TermList.from_bucket_formulas(inv=[_core(z3.Implies(q_0, q_1))])
    context = GR1TermList.from_bucket_formulas(inv=[_core(p_0 == q_0)])

    result, _ = target.elim_vars_by_relaxing(
        context=context,
        vars_to_elim=[Var("q")],
        simplify=False,
        tactics_order=[],
    )

    assert len(result.inv_terms()) == 1
    assert _is_equivalent(
        result.inv_terms()[0].core.expr,
        z3.Implies(z3.Bool("p_0"), z3.Bool("p_1")),
    )


def test_inv_relaxation_shift_closes_context_through_nested_next() -> None:
    p_0, q_0, q_1, q_2 = z3.Bools("p_0 q_0 q_1 q_2")
    target = GR1TermList.from_bucket_formulas(inv=[_core(z3.Implies(q_1, q_2))])
    context = GR1TermList.from_bucket_formulas(inv=[_core(p_0 == q_0)])

    result, _ = target.elim_vars_by_relaxing(
        context=context,
        vars_to_elim=[Var("q")],
        simplify=False,
        tactics_order=[],
    )

    assert _is_equivalent(
        result.inv_terms()[0].core.expr,
        z3.Implies(z3.Bool("p_1"), z3.Bool("p_2")),
    )


def test_inv_relaxation_depth_zero_is_unchanged() -> None:
    p_0, q_0 = z3.Bools("p_0 q_0")
    target = GR1TermList.from_bucket_formulas(inv=[_core(q_0)])
    context = GR1TermList.from_bucket_formulas(inv=[_core(p_0 == q_0)])

    result, _ = target.elim_vars_by_relaxing(
        context=context,
        vars_to_elim=[Var("q")],
        simplify=False,
        tactics_order=[],
    )

    assert _is_equivalent(result.inv_terms()[0].core.expr, p_0)


def test_parse_gr1_core_flattens_nested_next_and_boolean_logic() -> None:
    core = parse_gr1_core(
        "request -> X(grant & next(!failed))",
        {"request": "bool", "grant": "bool", "failed": "bool"},
    )
    expected = z3.Implies(
        z3.Bool("request_0"),
        z3.And(z3.Bool("grant_1"), z3.Not(z3.Bool("failed_2"))),
    )

    solver = z3.Solver()
    solver.add(core.expr != expected)
    assert solver.check() == z3.unsat
    assert frozenset(core.vars) == frozenset({Var("request_0"), Var("grant_1"), Var("failed_2")})


def test_parse_gr1_core_supports_typed_arithmetic() -> None:
    core = parse_gr1_core(
        "counter >= 0 & X(temperature) <= temperature + 2.5",
        {"counter": "int", "temperature": "real"},
    )
    expected = z3.And(
        z3.Int("counter_0") >= 0,
        z3.Real("temperature_1") <= z3.Real("temperature_0") + z3.RealVal("2.5"),
    )

    solver = z3.Solver()
    solver.add(core.expr != expected)
    assert solver.check() == z3.unsat


def test_from_bucket_strings_builds_z3_backed_parsed_cores() -> None:
    terms = GR1TermList.from_bucket_strings(
        inv=["request -> X(grant)"],
        liv=["grant"],
        variable_sorts={"request": "bool", "grant": "bool"},
    )

    assert terms.inv_terms()[0].core.expr is not None
    assert terms.liv_terms()[0].core.expr is not None
    assert terms.inv_terms()[0].core.vars == [Var("grant_1"), Var("request_0")]


def test_parse_gr1_core_rejects_undeclared_variables() -> None:
    try:
        parse_gr1_core("known & unknown", {"known": "bool"})
    except ValueError as error:
        assert "Undeclared variable 'unknown'" in str(error)
    else:
        raise AssertionError("Expected undeclared variable to be rejected")


def test_gr1_contract_from_dict_parses_typed_formulas_with_base_interfaces() -> None:
    contract = GR1IoContract.from_dict(
        {
            "input_vars": ["request"],
            "output_vars": ["grant"],
            "variable_sorts": {"request": "bool", "grant": "bool"},
            "assumptions": {"init": [], "inv": ["request"], "liv": []},
            "guarantees": {
                "init": [],
                "inv": ["request -> X(grant)"],
                "liv": ["grant"],
            },
        },
        simplify=False,
    )

    assert contract.inputvars == [Var("request")]
    assert contract.outputvars == [Var("grant")]
    assert contract.g.vars == [Var("grant"), Var("request")]
    assert contract.g.inv_terms()[0].core.vars == [Var("grant_1"), Var("request_0")]
    assert len(contract.g.get_terms_with_vars([Var("grant")]).terms) == 2


def test_gr1_contract_typed_dictionary_round_trip() -> None:
    source = {
        "input_vars": ["temperature"],
        "output_vars": ["alarm"],
        "variable_sorts": {"temperature": "real", "alarm": "bool"},
        "assumptions": {"init": [], "inv": ["temperature >= 0"], "liv": []},
        "guarantees": {"init": [], "inv": ["temperature > 10 -> X(alarm)"], "liv": []},
    }

    restored = GR1IoContract.from_dict(
        GR1IoContract.from_dict(source, simplify=False).to_dict(),
        simplify=False,
    )

    assert restored.variable_sorts == {"alarm": "bool", "temperature": "real"}
    assert restored.g.inv_terms()[0].core.expr is not None
    assert restored.g.inv_terms()[0].core.vars == [Var("alarm_1"), Var("temperature_0")]


def test_gr1_contract_rename_updates_every_flattened_depth() -> None:
    contract = GR1IoContract.from_dict(
        {
            "input_vars": ["request"],
            "output_vars": ["grant"],
            "variable_sorts": {"request": "bool", "grant": "bool"},
            "assumptions": {"init": [], "inv": [], "liv": []},
            "guarantees": {"init": [], "inv": ["grant & X(grant)"], "liv": []},
        },
        simplify=False,
    )

    renamed = contract.rename_variables([("grant", "ack")])

    assert renamed.outputvars == [Var("ack")]
    assert renamed.g.inv_terms()[0].core.vars == [Var("ack_0"), Var("ack_1")]
    assert renamed.variable_sorts == {"request": "bool", "ack": "bool"}
    assert renamed.to_dict()["variable_sorts"] == {"ack": "bool", "request": "bool"}


def test_relaxation_conjoins_invariant_bucket_before_existential_qe() -> None:
    p_0, q_0 = z3.Bools("p_0 q_0")
    target = GR1TermList.from_bucket_formulas(inv=[_core(p_0), _core(p_0 == q_0)])

    result, _ = target.elim_vars_by_relaxing(
        context=GR1TermList(),
        vars_to_elim=[Var("p")],
        simplify=False,
        tactics_order=[],
    )

    assert len(result.inv_terms()) == 1
    solver = z3.Solver()
    solver.add(result.inv_terms()[0].core.expr != q_0)
    assert solver.check() == z3.unsat


def test_relaxation_conjoins_initial_bucket_before_existential_qe() -> None:
    p_0, q_0 = z3.Bools("p_0 q_0")
    target = GR1TermList.from_bucket_formulas(init=[_core(p_0), _core(p_0 == q_0)])

    result, _ = target.elim_vars_by_relaxing(
        context=GR1TermList(),
        vars_to_elim=[Var("p")],
        simplify=False,
        tactics_order=[],
    )

    assert len(result.init_terms()) == 1
    solver = z3.Solver()
    solver.add(result.init_terms()[0].core.expr != q_0)
    assert solver.check() == z3.unsat


def test_refinement_conjoins_invariant_bucket_before_universal_qe() -> None:
    p_0, q_0, r_0 = z3.Bools("p_0 q_0 r_0")
    target = GR1TermList.from_bucket_formulas(inv=[_core(z3.Or(p_0, q_0)), _core(z3.Or(z3.Not(p_0), r_0))])

    result, _ = target.elim_vars_by_refining(
        context=GR1TermList(),
        vars_to_elim=[Var("p")],
        simplify=False,
        tactics_order=[],
    )

    assert len(result.inv_terms()) == 1
    expected = z3.And(q_0, r_0)
    solver = z3.Solver()
    solver.add(result.inv_terms()[0].core.expr != expected)
    assert solver.check() == z3.unsat


def test_ast_rename_is_structural_and_regenerates_user_text() -> None:
    terms = GR1TermList.from_bucket_strings(
        inv=["p & X(p) & p_aux"],
        variable_sorts={"p": "bool", "p_aux": "bool"},
    )

    renamed = terms.rename_variable(Var("p"), Var("r"))
    core = renamed.inv_terms()[0].core

    assert core.syntax is not None
    assert core.text == "((r and X(r)) and p_aux)"
    assert core.vars == [Var("p_aux_0"), Var("r_0"), Var("r_1")]


def test_relaxation_result_round_trips_through_machine_serialization() -> None:
    p_0, q_0 = z3.Bools("p_0 q_0")
    target = GR1TermList.from_bucket_formulas(inv=[_core(p_0), _core(p_0 == q_0)])
    relaxed, _ = target.elim_vars_by_relaxing(
        context=GR1TermList(),
        vars_to_elim=[Var("p")],
        simplify=False,
        tactics_order=[],
    )
    contract = GR1IoContract(
        assumptions=GR1TermList(),
        guarantees=relaxed,
        input_vars=[],
        output_vars=[Var("q")],
        simplify=False,
        variable_sorts={"q": "bool"},
    )

    serialized = contract.to_dict()
    restored = GR1IoContract.from_dict(serialized, simplify=False)

    assert serialized["gr1_machine"]["version"] == 1
    solver = z3.Solver()
    solver.add(restored.g.inv_terms()[0].core.expr != relaxed.inv_terms()[0].core.expr)
    assert solver.check() == z3.unsat


def test_refinement_result_round_trips_through_machine_serialization() -> None:
    p_0, q_0, r_0 = z3.Bools("p_0 q_0 r_0")
    target = GR1TermList.from_bucket_formulas(inv=[_core(z3.Or(p_0, q_0)), _core(z3.Or(z3.Not(p_0), r_0))])
    refined, _ = target.elim_vars_by_refining(
        context=GR1TermList(),
        vars_to_elim=[Var("p")],
        simplify=False,
        tactics_order=[],
    )
    contract = GR1IoContract(
        assumptions=GR1TermList(),
        guarantees=refined,
        input_vars=[],
        output_vars=[Var("q"), Var("r")],
        simplify=False,
        variable_sorts={"q": "bool", "r": "bool"},
    )

    restored = GR1IoContract.from_dict(contract.to_dict(), simplify=False)

    solver = z3.Solver()
    solver.add(restored.g.inv_terms()[0].core.expr != refined.inv_terms()[0].core.expr)
    assert solver.check() == z3.unsat


def test_renamed_ast_contract_round_trips_with_user_facing_next_text() -> None:
    contract = GR1IoContract.from_dict(
        {
            "input_vars": [],
            "output_vars": ["p"],
            "variable_sorts": {"p": "bool"},
            "assumptions": {"init": [], "inv": [], "liv": []},
            "guarantees": {"init": [], "inv": ["p -> X(p)"], "liv": []},
        },
        simplify=False,
    ).rename_variables([("p", "r")])

    serialized = contract.to_dict()
    restored = GR1IoContract.from_dict(serialized, simplify=False)

    assert "X(r)" in serialized["guarantees"]["inv"][0]
    assert restored.g.inv_terms()[0].core.syntax is not None
    assert restored.g.inv_terms()[0].core.vars == [Var("r_0"), Var("r_1")]


def test_simplify_removes_true_equivalent_and_implied_terms() -> None:
    p_0, q_0 = z3.Bools("p_0 q_0")
    terms = GR1TermList.from_bucket_formulas(
        inv=[_core(z3.BoolVal(True)), _core(p_0), _core(z3.Or(p_0, q_0)), _core(p_0)],
        liv=[_core(p_0), _core(z3.Or(p_0, q_0)), _core(p_0)],
    )

    simplified = terms.simplify()

    assert len(simplified.inv_terms()) == 1
    assert len(simplified.liv_terms()) == 0
    assert z3.eq(simplified.inv_terms()[0].core.expr, p_0)


def test_simplify_uses_context_and_detects_false_bucket() -> None:
    p_0, q_0 = z3.Bools("p_0 q_0")
    context = GR1TermList.from_bucket_formulas(inv=[_core(p_0)])
    target = GR1TermList.from_bucket_formulas(
        inv=[_core(z3.Or(p_0, q_0))],
        liv=[_core(p_0)],
    )

    assert target.simplify(context).terms == []
    false_terms = GR1TermList.from_bucket_formulas(init=[_core(q_0), _core(z3.Not(q_0))]).simplify()
    assert len(false_terms.terms) == 1
    assert z3.is_false(false_terms.init_terms()[0].core.expr)


def test_is_empty_detects_inconsistent_initial_invariant_and_liveness() -> None:
    p_0 = z3.Bool("p_0")

    assert GR1TermList.from_bucket_formulas(init=[_core(p_0), _core(z3.Not(p_0))]).is_empty()
    assert GR1TermList.from_bucket_formulas(inv=[_core(z3.BoolVal(False))]).is_empty()
    assert GR1TermList.from_bucket_formulas(inv=[_core(p_0)], liv=[_core(z3.Not(p_0))]).is_empty()
    assert not GR1TermList.from_bucket_formulas(inv=[_core(p_0)]).is_empty()


def test_contains_behavior_checks_finite_windows_and_lasso_liveness() -> None:
    terms = GR1TermList.from_bucket_strings(
        init=["p"],
        inv=["p -> X(p)"],
        liv=["q"],
        variable_sorts={"p": "bool", "q": "bool"},
    )
    satisfying = GR1Behavior(
        states=[{"p": True, "q": False}, {"p": True, "q": True}],
        loop_start=0,
    )
    no_liveness = GR1Behavior(
        states=[{"p": True, "q": False}],
        loop_start=0,
    )

    assert terms.contains_behavior(satisfying)
    assert not terms.contains_behavior(no_liveness)

    try:
        terms.contains_behavior([{"p": True, "q": True}])
    except ValueError as error:
        assert "loop_start" in str(error)
    else:
        raise AssertionError("Finite prefixes must not establish liveness")


def test_parser_supports_boolean_integer_and_real_variables_together() -> None:
    core = parse_gr1_core(
        "enabled & count >= 1 & X(level) < level + 0.5",
        {"enabled": "bool", "count": "int", "level": "real"},
    )

    assert core.vars == [Var("count_0"), Var("enabled_0"), Var("level_0"), Var("level_1")]


def test_nested_next_mixed_depth_and_numeric_suffix_names() -> None:
    core = parse_gr1_core(
        "sensor_1 & X(sensor_1) & X(X(flag))",
        {"sensor_1": "bool", "flag": "bool"},
    )

    assert core.vars == [Var("flag_2"), Var("sensor_1_0"), Var("sensor_1_1")]


def test_elimination_handles_multiple_base_variables_and_next_in_invariant() -> None:
    p_0, p_1, r_0, r_1, q_0, q_1 = z3.Bools("p_0 p_1 r_0 r_1 q_0 q_1")
    context = GR1TermList.from_bucket_formulas(inv=[_core(z3.And(p_0 == q_0, r_0 == q_0))])
    target = GR1TermList.from_bucket_formulas(inv=[_core(z3.And(p_1, r_1))])

    result, _ = target.elim_vars_by_relaxing(
        context=context,
        vars_to_elim=[Var("p"), Var("r")],
        simplify=False,
        tactics_order=[],
    )

    solver = z3.Solver()
    solver.add(result.inv_terms()[0].core.expr != q_1)
    assert solver.check() == z3.unsat


def test_unsatisfiable_and_equivalent_projected_liveness_terms_reduce() -> None:
    p_0, q_0 = z3.Bools("p_0 q_0")
    target = GR1TermList.from_bucket_formulas(liv=[_core(z3.And(p_0, z3.Not(p_0)))])
    context = GR1TermList.from_bucket_formulas(liv=[_core(z3.And(p_0, q_0)), _core(z3.And(q_0, p_0))])

    result, _ = target.elim_vars_by_relaxing(
        context=context,
        vars_to_elim=[Var("p")],
        simplify=False,
        tactics_order=[],
    )

    assert len(result.liv_terms()) == 1
    assert z3.is_false(result.liv_terms()[0].core.expr)


def _bounded_next_liveness_contracts() -> Tuple[GR1IoContract, GR1IoContract]:
    producer = GR1IoContract.from_dict(
        {
            "input_vars": ["q"],
            "output_vars": ["p"],
            "variable_sorts": {"q": "bool", "p": "bool"},
            "assumptions": {"init": [], "inv": [], "liv": []},
            "guarantees": {"init": [], "inv": ["p = q"], "liv": ["p"]},
        },
        simplify=False,
    )
    consumer = GR1IoContract.from_dict(
        {
            "input_vars": ["p"],
            "output_vars": ["r"],
            "variable_sorts": {"p": "bool", "r": "bool"},
            "assumptions": {"init": [], "inv": [], "liv": []},
            "guarantees": {"init": [], "inv": ["p = X(r)"], "liv": ["r"]},
        },
        simplify=False,
    )
    return producer, consumer


def test_compose_eliminates_internal_variable_with_next_and_liveness() -> None:
    producer, consumer = _bounded_next_liveness_contracts()

    composed = producer.compose(consumer, simplify=True)

    assert composed.inputvars == [Var("q")]
    assert composed.outputvars == [Var("r")]
    assert Var("p") not in composed.a.vars + composed.g.vars
    expected_inv = z3.Bool("q_0") == z3.Bool("r_1")
    solver = z3.Solver()
    solver.add(composed.g.inv_terms()[0].core.expr != expected_inv)
    assert solver.check() == z3.unsat
    assert {tuple(term.core.vars) for term in composed.g.liv_terms()} == {
        (Var("q_0"),),
        (Var("r_0"),),
    }


def test_quotient_eliminates_hidden_variable_and_round_trips() -> None:
    producer, consumer = _bounded_next_liveness_contracts()
    system = producer.compose(consumer, simplify=True)
    quotient = system.quotient(producer, simplify=True)
    restored = GR1IoContract.from_dict(quotient.to_dict(), simplify=False)

    assert quotient.inputvars == [Var("p")]
    assert quotient.outputvars == [Var("r")]
    assert Var("q") not in quotient.a.vars + quotient.g.vars
    assert len(quotient.a.liv_terms()) == 1
    assert _is_equivalent(quotient.a.liv_terms()[0].core.expr, z3.Bool("p_0"))
    assert len(quotient.g.inv_terms()) == 1
    assert _is_equivalent(
        quotient.g.inv_terms()[0].core.expr,
        z3.Bool("p_0") == z3.Bool("r_1"),
    )
    assert len(quotient.g.liv_terms()) == 1
    assert _is_equivalent(quotient.g.liv_terms()[0].core.expr, z3.Bool("r_0"))
    assert not any(_is_equivalent(term.core.expr, z3.Bool("r_0")) for term in quotient.g.inv_terms())
    assert restored.inputvars == quotient.inputvars
    assert restored.outputvars == quotient.outputvars
    assert restored.a.refines(quotient.a) and quotient.a.refines(restored.a)
    assert restored.g.refines(quotient.g) and quotient.g.refines(restored.g)


def test_full_bucket_quotient_preserves_canonical_liv_and_recovers_consumer() -> None:
    producer = GR1IoContract.from_dict(
        {
            "input_vars": ["q"],
            "output_vars": ["p"],
            "variable_sorts": {"q": "bool", "p": "bool"},
            "assumptions": {"init": ["q"], "inv": ["q -> X(q)"], "liv": ["q"]},
            "guarantees": {"init": ["p = q"], "inv": ["p = q"], "liv": ["p"]},
        },
        simplify=False,
    )
    consumer = GR1IoContract.from_dict(
        {
            "input_vars": ["p"],
            "output_vars": ["r"],
            "variable_sorts": {"p": "bool", "r": "bool"},
            "assumptions": {"init": ["p"], "inv": ["p -> X(p)"], "liv": ["p"]},
            "guarantees": {"init": ["r = p"], "inv": ["p = X(r)"], "liv": ["r"]},
        },
        simplify=False,
    )

    composed = producer.compose(consumer, simplify=True)
    quotient = composed.quotient(producer, simplify=True)

    # Final assumption saturation must not replace canonical LIV(r) by a core
    # containing q; its synthetic projection remains equivalent to the free core.
    assert len(composed.g.liv_terms()) == 1
    assert _is_equivalent(composed.g.liv_terms()[0].core.expr, z3.Bool("r_0"))
    assert len(quotient.g.liv_terms()) == 1
    assert _is_equivalent(quotient.g.liv_terms()[0].core.expr, z3.Bool("r_0"))
    assert quotient.a.refines(consumer.a) and consumer.a.refines(quotient.a)
    assert quotient.g.refines(consumer.g)
    # Post-CAVE reduction removes the invariant's redundant time-zero instance.
    assert consumer.g.refines(quotient.g)
    assert producer.compose(quotient, simplify=True).refines(composed)


def test_generated_text_uses_bounded_next_instead_of_flat_names() -> None:
    p_0, q_0, q_2 = z3.Bools("p_0 q_0 q_2")
    target = GR1TermList.from_bucket_formulas(inv=[_core(z3.And(p_0, q_0, q_2))])

    projected, _ = target.elim_vars_by_relaxing(
        context=GR1TermList(),
        vars_to_elim=[Var("p")],
        simplify=False,
        tactics_order=[],
    )

    generated = projected.inv_terms()[0].core
    assert generated.text == "(q & X(X(q)))"
    assert {variable.name for variable in generated.vars} == {"q_0", "q_2"}


def test_composition_generated_text_is_compact_user_syntax() -> None:
    producer, consumer = _bounded_next_liveness_contracts()

    composed = producer.compose(consumer, simplify=True)

    assert composed.g.inv_terms()[0].core.text in {"(q = X(r))", "(X(r) = q)"}
    assert composed.g.to_bucket_dict()["liv"] == ["q", "r"]


def test_liv_refinement_preserves_target_free_of_eliminated_variable() -> None:
    p_0, q_0, r_0, r_1 = z3.Bools("p_0 q_0 r_0 r_1")
    context = GR1TermList.from_bucket_formulas(
        inv=[_core(p_0 == q_0)],
        liv=[_core(p_0)],
    )

    for target_expr in (r_0, r_1):
        target = GR1TermList.from_bucket_formulas(liv=[_core(target_expr)])
        result, _ = target.elim_vars_by_refining(
            context=context,
            vars_to_elim=[Var("q")],
            simplify=True,
            tactics_order=[],
        )

        assert not result.inv_terms()
        assert len(result.liv_terms()) == 1
        # LIV(r_1) is retained as liveness but canonically represented by r_0,
        # using GF(X(r)) = GF(r).
        assert _is_equivalent(result.liv_terms()[0].core.expr, r_0)


def test_liv_refinement_still_processes_dependent_target() -> None:
    p_0, q_0, q_1 = z3.Bools("p_0 q_0 q_1")
    context = GR1TermList.from_bucket_formulas(
        inv=[_core(p_0 == q_0)],
        liv=[_core(p_0)],
    )
    target = GR1TermList.from_bucket_formulas(liv=[_core(q_0)])

    result, _ = target.elim_vars_by_refining(
        context=context,
        vars_to_elim=[Var("q")],
        simplify=True,
        tactics_order=[],
    )

    assert result.terms == []

    next_target = GR1TermList.from_bucket_formulas(liv=[_core(q_1)])
    next_result, _ = next_target.elim_vars_by_refining(
        context=context,
        vars_to_elim=[Var("q")],
        simplify=True,
        tactics_order=[],
    )

    # The synthetic GF(p_1) normalizes to GF(p_0), already in the context.
    assert next_result.terms == []
    raw_next, _ = next_target.elim_vars_by_refining(context, [Var("q")], False, [])
    assert len(raw_next.liv_terms()) == 1
    assert _is_equivalent(raw_next.liv_terms()[0].core.expr, z3.Bool("p_1"))


def test_refines_allows_invariant_to_discharge_liveness() -> None:
    r_0 = z3.Bool("r_0")
    source = GR1TermList.from_bucket_formulas(inv=[_core(r_0)])
    target = GR1TermList.from_bucket_formulas(liv=[_core(r_0)])

    assert source.refines(target)


def test_refines_uses_shifted_invariant_for_next_liveness() -> None:
    p_0, q_0, p_1, q_1 = z3.Bools("p_0 q_0 p_1 q_1")
    source = GR1TermList.from_bucket_formulas(inv=[_core(z3.Implies(p_0, q_0))])
    target = GR1TermList.from_bucket_formulas(liv=[_core(z3.Implies(p_1, q_1))])

    assert source.refines(target)


def test_refines_does_not_infer_next_liveness_from_nonforcing_invariant() -> None:
    p_0, q_0, q_1 = z3.Bools("p_0 q_0 q_1")
    source = GR1TermList.from_bucket_formulas(inv=[_core(z3.Implies(p_0, q_0))])
    target = GR1TermList.from_bucket_formulas(liv=[_core(q_1)])

    assert not source.refines(target)


def test_refines_keeps_separate_liveness_supports_separate() -> None:
    p_0 = z3.Bool("p_0")
    source = GR1TermList.from_bucket_formulas(liv=[_core(p_0), _core(z3.Not(p_0))])
    target = GR1TermList.from_bucket_formulas(liv=[_core(p_0)])

    assert source.refines(target)
    assert not target.refines(source)


def test_canonicalize_boolean_conditioned_real_interval() -> None:
    e_0 = z3.Bool("e_0")
    a_1 = z3.Real("a_1")
    raw = z3.Or(
        z3.And(e_0, a_1 >= z3.RealVal("-11/2"), a_1 <= z3.RealVal("-5/2")),
        z3.And(z3.Not(e_0), a_1 >= -1, a_1 <= z3.RealVal("5/2")),
    )
    expected = z3.And(
        a_1 >= z3.RealVal("-11/2"),
        a_1 <= z3.RealVal("5/2"),
        z3.Implies(e_0, a_1 <= z3.RealVal("-5/2")),
        z3.Implies(z3.Not(e_0), a_1 >= -1),
    )

    canonical = canonicalize_mixed_linear_formula(raw)

    assert _is_equivalent(raw, canonical)
    assert _is_equivalent(canonical, expected)
    assert z3.is_and(canonical)


def test_canonicalize_factors_bounds_common_to_boolean_cases() -> None:
    mode_0 = z3.Bool("mode_0")
    x_0 = z3.Real("x_0")
    raw = z3.Or(
        z3.And(mode_0, x_0 >= 0, x_0 <= 3),
        z3.And(z3.Not(mode_0), x_0 >= 0, x_0 <= 7),
    )

    canonical = canonicalize_mixed_linear_formula(raw)

    assert _is_equivalent(raw, canonical)
    assert _is_equivalent(canonical, z3.And(x_0 >= 0, x_0 <= 7, z3.Implies(mode_0, x_0 <= 3)))


def test_canonicalize_unsupported_nonrectangular_formula_is_noop() -> None:
    x_0, y_0 = z3.Reals("x_0 y_0")
    raw = x_0 + y_0 <= 1

    canonical = canonicalize_mixed_linear_formula(raw)

    assert canonical.eq(z3.simplify(raw))


def test_canonicalization_equivalence_guard_rejects_wrong_candidate() -> None:
    x_0 = z3.Real("x_0")
    raw = z3.And(x_0 >= 0, x_0 <= 2)
    wrong = z3.And(x_0 >= 0, x_0 <= 1)

    guarded = _equivalence_guarded_formula(raw, wrong)

    assert _is_equivalent(guarded, raw)
    assert not _is_equivalent(guarded, wrong)


def _contract_from_merge_data(data: Dict[str, Any]) -> GR1IoContract:
    return GR1IoContract.from_dict(data, simplify=False)


def test_merge_preserves_all_six_gr1_buckets() -> None:
    first = _contract_from_merge_data(
        {
            "input_vars": ["p"],
            "output_vars": ["r"],
            "variable_sorts": {"p": "bool", "r": "bool"},
            "assumptions": {"init": ["p"], "inv": ["p -> X(p)"], "liv": ["p"]},
            "guarantees": {"init": ["!r"], "inv": ["p -> X(r)"], "liv": ["r"]},
        }
    )
    second = _contract_from_merge_data(
        {
            "input_vars": ["q"],
            "output_vars": ["s"],
            "variable_sorts": {"q": "bool", "s": "bool"},
            "assumptions": {"init": ["q"], "inv": ["q -> X(q)"], "liv": ["q"]},
            "guarantees": {"init": ["!s"], "inv": ["q -> X(s)"], "liv": ["s"]},
        }
    )

    merged = first.merge(second)

    assert merged.a.to_bucket_dict() == {
        "init": ["p", "q"],
        "inv": ["(p -> X(p))", "(q -> X(q))"],
        "liv": ["p", "q"],
    }
    assert merged.g.to_bucket_dict() == {
        "init": ["!(r)", "!(s)"],
        "inv": ["(p -> X(r))", "(q -> X(s))"],
        "liv": ["r", "s"],
    }


def test_merge_keeps_liveness_guarantees_separate() -> None:
    first = GR1IoContract.from_buckets(input_vars=[], output_vars=["p"], g_liv=[_core(z3.Bool("p_0"))], simplify=False)
    second = GR1IoContract.from_buckets(input_vars=[], output_vars=["q"], g_liv=[_core(z3.Bool("q_0"))], simplify=False)

    merged = first.merge(second)

    liveness = merged.g.liv_terms()
    assert len(liveness) == 2
    assert _is_equivalent(liveness[0].core.expr, z3.Bool("p_0"))
    assert _is_equivalent(liveness[1].core.expr, z3.Bool("q_0"))
    assert not any(_is_equivalent(term.core.expr, z3.And(z3.Bool("p_0"), z3.Bool("q_0"))) for term in liveness)


def test_merge_keeps_liveness_assumptions_separate() -> None:
    first = GR1IoContract.from_buckets(input_vars=["p"], output_vars=[], a_liv=[_core(z3.Bool("p_0"))], simplify=False)
    second = GR1IoContract.from_buckets(input_vars=["q"], output_vars=[], a_liv=[_core(z3.Bool("q_0"))], simplify=False)

    merged = first.merge(second)

    liveness = merged.a.liv_terms()
    assert len(liveness) == 2
    assert _is_equivalent(liveness[0].core.expr, z3.Bool("p_0"))
    assert _is_equivalent(liveness[1].core.expr, z3.Bool("q_0"))
    assert not any(_is_equivalent(term.core.expr, z3.And(z3.Bool("p_0"), z3.Bool("q_0"))) for term in liveness)


def test_merge_with_empty_contract_preserves_meaningful_contract() -> None:
    meaningful = _contract_from_merge_data(
        {
            "input_vars": ["p"],
            "output_vars": ["q"],
            "variable_sorts": {"p": "bool", "q": "bool"},
            "assumptions": {"init": ["p"], "inv": [], "liv": ["p"]},
            "guarantees": {"init": [], "inv": ["p -> X(q)"], "liv": ["q"]},
        }
    )
    empty = GR1IoContract(GR1TermList(), GR1TermList(), [], [], simplify=False)

    merged = meaningful.merge(empty)

    assert merged.inputvars == meaningful.inputvars
    assert merged.outputvars == meaningful.outputvars
    assert merged.variable_sorts == meaningful.variable_sorts
    assert merged.a.to_bucket_dict() == meaningful.a.to_bucket_dict()
    assert merged.g.to_bucket_dict() == meaningful.g.to_bucket_dict()


def test_merge_uses_generic_interface_union_order() -> None:
    first = GR1IoContract(GR1TermList(), GR1TermList(), [Var("shared"), Var("left_in")], [Var("left_out")], False)
    second = GR1IoContract(
        GR1TermList(),
        GR1TermList(),
        [Var("shared"), Var("right_in")],
        [Var("right_out")],
        False,
    )

    merged = first.merge(second)

    assert merged.inputvars == [Var("shared"), Var("left_in"), Var("right_in")]
    assert merged.outputvars == [Var("left_out"), Var("right_out")]


def test_merge_rejects_input_output_classification_conflict() -> None:
    input_contract = GR1IoContract(GR1TermList(), GR1TermList(), [Var("shared")], [], False)
    output_contract = GR1IoContract(GR1TermList(), GR1TermList(), [], [Var("shared")], False)

    with pytest.raises(IncompatibleArgsError):
        input_contract.merge(output_contract)


def test_merge_mutually_refines_manually_constructed_contract() -> None:
    first = _contract_from_merge_data(
        {
            "input_vars": ["p"],
            "output_vars": ["r"],
            "variable_sorts": {"p": "bool", "r": "bool"},
            "assumptions": {"init": ["p"], "inv": [], "liv": ["p"]},
            "guarantees": {"init": [], "inv": ["p -> X(r)"], "liv": ["r"]},
        }
    )
    second = _contract_from_merge_data(
        {
            "input_vars": ["q"],
            "output_vars": ["s"],
            "variable_sorts": {"q": "bool", "s": "bool"},
            "assumptions": {"init": ["q"], "inv": [], "liv": ["q"]},
            "guarantees": {"init": [], "inv": ["q -> X(s)"], "liv": ["s"]},
        }
    )
    expected = _contract_from_merge_data(
        {
            "input_vars": ["p", "q"],
            "output_vars": ["r", "s"],
            "variable_sorts": {"p": "bool", "q": "bool", "r": "bool", "s": "bool"},
            "assumptions": {"init": ["p", "q"], "inv": [], "liv": ["p", "q"]},
            "guarantees": {"init": [], "inv": ["p -> X(r)", "q -> X(s)"], "liv": ["r", "s"]},
        }
    )

    merged = first.merge(second)

    assert merged <= expected
    assert expected <= merged
