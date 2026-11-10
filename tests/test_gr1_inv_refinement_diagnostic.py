"""Diagnostic characterizations for bounded-NEXT invariant refinement.

These tests do not change the refinement implementation.  They distinguish
sound finite proof certificates from completeness of finite unrolling.
"""

import z3

from pacti.iocontract import gr1_iocontract as gr1


def shift(expr, variables, amount):
    substitutions = []
    for name, sort in variables.items():
        for index in range(20):
            old = z3.Const(f"{name}_{index}", sort)
            new = z3.Const(f"{name}_{index + amount}", sort)
            substitutions.append((old, new))
    return z3.substitute(expr, *substitutions)


def closure(source, variables, horizon):
    return z3.And(*[shift(source, variables, index) for index in range(horizon + 1)])


def proves(source, target, variables, horizon):
    solver = z3.Solver()
    solver.add(closure(source, variables, horizon), z3.Not(target))
    return solver.check() == z3.unsat


def boolean_countdown(length):
    variables = {f"q{index}": z3.BoolSort() for index in range(length + 1)}
    transitions = [z3.Implies(z3.Bool(f"q{index}_0"), z3.Bool(f"q{index + 1}_1")) for index in range(length)]
    source = z3.And(*transitions, z3.Not(z3.Bool(f"q{length}_0")))
    target = z3.Not(z3.Bool("q0_0"))
    return source, target, variables


def term_list(source, target):
    source_terms = gr1.GR1TermList.from_bucket_formulas(inv=[gr1._make_core_from_expr(source)])
    target_terms = gr1.GR1TermList.from_bucket_formulas(inv=[gr1._make_core_from_expr(target)])
    return source_terms, target_terms


def test_horizon_zero_preserves_old_pointwise_inv_behavior():
    p_0, q_0 = z3.Bools("p_0 q_0")
    source, target = term_list(z3.And(p_0, z3.Implies(p_0, q_0)), q_0)
    assert gr1._inv_terms_refine(source.inv_terms(), target.inv_terms(), max_horizon=0)

    invalid_source, invalid_target = term_list(p_0, q_0)
    assert not gr1._inv_terms_refine(invalid_source.inv_terms(), invalid_target.inv_terms(), max_horizon=0)


def test_depth_one_boolean_source_can_require_arbitrarily_many_shifts():
    for length in range(1, 7):
        source, target, variables = boolean_countdown(length)
        assert not proves(source, target, variables, length - 1)
        assert proves(source, target, variables, length)
        source_terms, target_terms = term_list(source, target)
        assert not gr1._inv_terms_refine(source_terms.inv_terms(), target_terms.inv_terms(), max_horizon=length - 1)
        assert gr1._inv_terms_refine(source_terms.inv_terms(), target_terms.inv_terms(), max_horizon=length)


def test_named_syntactic_horizon_rules_are_incomplete():
    source, target, variables = boolean_countdown(4)
    source_depth = 1
    target_depth = 0
    candidates = {
        "local": 0,
        "target_depth": target_depth,
        "source_depth": source_depth,
        "maximum_depth": max(source_depth, target_depth),
        "sum_of_depths": source_depth + target_depth,
    }
    assert all(not proves(source, target, variables, horizon) for horizon in candidates.values())
    assert proves(source, target, variables, 4)


def test_realisable_boolean_real_source_has_no_complete_finite_unrolling():
    p_0, p_1 = z3.Bools("p_0 p_1")
    x_0, x_1 = z3.Reals("x_0 x_1")
    source = z3.And(
        z3.Implies(p_0, p_1),
        z3.Implies(z3.Not(p_0), z3.Not(p_1)),
        z3.Implies(p_0, x_0 == 0),
        z3.Implies(z3.Not(p_0), x_0 <= 0),
        z3.Implies(z3.Not(p_0), x_1 >= x_0 + 1),
    )
    variables = {"p": z3.BoolSort(), "x": z3.RealSort()}

    # The p=true, x=0 trace establishes that G(source) is realizable.  Every
    # finite window nevertheless admits a p=false prefix with a sufficiently
    # negative initial x.  The p=false branch has no infinite real trace.
    for horizon in range(10):
        assert not proves(source, p_0, variables, horizon)
        source_terms, target_terms = term_list(source, p_0)
        assert not gr1._inv_terms_refine(source_terms.inv_terms(), target_terms.inv_terms(), max_horizon=horizon)


def test_candidate_windows_reject_explicit_invalid_refinements():
    p_0, p_1, p_2 = z3.Bools("p_0 p_1 p_2")
    m_0, m_1 = z3.Bools("m_0 m_1")
    x_0, x_1 = z3.Reals("x_0 x_1")
    cases = [
        (z3.BoolVal(True), p_1, {"p": z3.BoolSort()}),
        (p_1 == z3.Not(p_0), p_0, {"p": z3.BoolSort()}),
        (p_2 == p_0, p_1 == p_0, {"p": z3.BoolSort()}),
        (x_1 >= x_0 + 1, x_0 >= 0, {"x": z3.RealSort()}),
        (
            z3.And(
                m_1 == m_0,
                z3.Implies(m_0, x_1 == x_0 + 1),
                z3.Implies(z3.Not(m_0), x_1 == x_0),
            ),
            z3.Implies(m_0, x_0 <= 0),
            {"m": z3.BoolSort(), "x": z3.RealSort()},
        ),
    ]
    for source, target, variables in cases:
        for horizon in range(6):
            assert not proves(source, target, variables, horizon)
            source_terms, target_terms = term_list(source, target)
            assert not gr1._inv_terms_refine(source_terms.inv_terms(), target_terms.inv_terms(), max_horizon=horizon)


def test_larger_finite_closures_are_monotone_proof_certificates():
    source, target, variables = boolean_countdown(4)
    results = [proves(source, target, variables, horizon) for horizon in range(8)]
    assert results == [False, False, False, False, True, True, True, True]
