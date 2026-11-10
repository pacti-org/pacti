"""Diagnostic characterizations for GR(1) liveness refinement.

These tests compare the current structured checker with sound finite
certificates. They intentionally do not modify the implementation.
"""

import z3

from pacti.iocontract import gr1_iocontract as gr1


def core(expr):
    return gr1._make_core_from_expr(expr)


def term(tag, expr):
    return gr1.GR1Term(tag, core(expr))


def occurrence_certificate(source_inv, support, target, horizon, delay=0):
    guard = gr1._shift_closed_inv_expr(source_inv, horizon)
    delayed_target = gr1._shift_expr_by(target.core.expr, delay)
    return gr1._implies(z3.And(guard, support.core.expr), delayed_target)


def test_invariant_directly_establishes_liveness():
    p_0 = z3.Bool("p_0")
    source_inv = [term(gr1.GR1Tag.INV, p_0)]
    target_liv = [term(gr1.GR1Tag.LIV, p_0)]
    assert gr1._liv_terms_refine(source_inv, [], target_liv)


def test_direct_liveness_support_still_establishes_target():
    a_0, b_0 = z3.Bools("a_0 b_0")
    source_liv = [term(gr1.GR1Tag.LIV, z3.And(a_0, b_0))]
    target_liv = [term(gr1.GR1Tag.LIV, a_0)]

    assert gr1._liv_terms_refine([], source_liv, target_liv)


def test_recurring_support_requires_invariant_context():
    a_0, b_0 = z3.Bools("a_0 b_0")
    source_inv = [term(gr1.GR1Tag.INV, z3.Implies(a_0, b_0))]
    source_liv = [term(gr1.GR1Tag.LIV, a_0)]
    target = term(gr1.GR1Tag.LIV, b_0)

    assert gr1._liv_terms_refine(source_inv, source_liv, [target])
    assert occurrence_certificate(source_inv, source_liv[0], target, horizon=0)


def test_independent_recurring_events_cannot_be_conjoined():
    a_0, b_0 = z3.Bools("a_0 b_0")
    source_liv = [term(gr1.GR1Tag.LIV, a_0), term(gr1.GR1Tag.LIV, b_0)]
    target = term(gr1.GR1Tag.LIV, z3.And(a_0, b_0))

    assert not gr1._liv_terms_refine([], source_liv, [target])
    # Alternation is an infinite countertrace: A at even positions, B at odd
    # positions, so both recur but their conjunction never occurs.
    loop = [(True, False), (False, True)]
    assert all(any(state[index] for state in loop) for index in (0, 1))
    assert not any(a and b for a, b in loop)


def test_next_support_needs_bounded_delay_alignment():
    a_0, b_0, b_1 = z3.Bools("a_0 b_0 b_1")
    source_inv = [term(gr1.GR1Tag.INV, z3.Implies(a_0, b_1))]
    source_liv = [term(gr1.GR1Tag.LIV, a_0)]
    target = term(gr1.GR1Tag.LIV, b_0)

    assert not gr1._liv_terms_refine(source_inv, source_liv, [target])
    assert not occurrence_certificate(source_inv, source_liv[0], target, horizon=0, delay=0)
    assert occurrence_certificate(source_inv, source_liv[0], target, horizon=0, delay=1)


def test_shifted_liveness_is_semantically_alignment_invariant():
    p_0, p_1 = z3.Bools("p_0 p_1")
    current = term(gr1.GR1Tag.LIV, p_0)
    shifted = term(gr1.GR1Tag.LIV, p_1)

    # The current pointwise-core checker does not normalize finite shifts.
    assert not gr1._liv_terms_refine([], [shifted], [current])
    assert not gr1._liv_terms_refine([], [current], [shifted])
    # Occurrences {0,2,4,...} and their one-step shift {1,3,5,...} are both
    # infinite, illustrating GF X(p) <=> GF p on infinite traces.
    occurrences = set(range(0, 20, 2))
    assert len(occurrences) == len({index + 1 for index in occurrences})


def test_two_shift_invariant_certificate_matches_aeb_mechanism():
    p_0, q_0, q_1, r_0, r_1 = z3.Bools("p_0 q_0 q_1 r_0 r_1")
    source_inv = [
        term(gr1.GR1Tag.INV, z3.Implies(p_0, q_1)),
        term(gr1.GR1Tag.INV, z3.Implies(q_0, r_1)),
        term(gr1.GR1Tag.INV, z3.Not(r_0)),
    ]
    target = term(gr1.GR1Tag.LIV, z3.Not(p_0))

    assert not gr1._inv_terms_refine(source_inv, [target], max_horizon=0)
    assert not gr1._inv_terms_refine(source_inv, [target], max_horizon=1)
    assert gr1._inv_terms_refine(source_inv, [target], max_horizon=2)
    assert gr1._liv_terms_refine(source_inv, [], [target])

    source_terms = gr1.GR1TermList(source_inv)
    target_terms = gr1.GR1TermList([target])
    assert source_terms.refines(target_terms)


def test_alternating_invariant_does_not_establish_target_liveness():
    p_0, p_1 = z3.Bools("p_0 p_1")
    source_inv = [term(gr1.GR1Tag.INV, p_1 == z3.Not(p_0))]
    target = term(gr1.GR1Tag.LIV, p_0)

    assert not gr1._liv_terms_refine(source_inv, [], [target])


def test_arithmetic_drift_does_not_establish_nonnegative_liveness():
    x_0, x_1 = z3.Reals("x_0 x_1")
    source_inv = [term(gr1.GR1Tag.INV, x_1 == x_0 - 1)]
    target = term(gr1.GR1Tag.LIV, x_0 >= 0)

    assert not gr1._liv_terms_refine(source_inv, [], [target])


def test_genuine_invalid_liveness_has_infinite_countertrace():
    a_0, b_0 = z3.Bools("a_0 b_0")
    source = [term(gr1.GR1Tag.LIV, a_0)]
    target = [term(gr1.GR1Tag.LIV, b_0)]
    assert not gr1._liv_terms_refine([], source, target)
    # The constant trace A=true, B=false satisfies GF A and violates GF B.
    loop = [(True, False)]
    assert any(a for a, _ in loop)
    assert not any(b for _, b in loop)
