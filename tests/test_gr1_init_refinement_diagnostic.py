"""Diagnostic tests for contextual INIT refinement; production code is unchanged."""

import importlib.util
from pathlib import Path

import z3

from pacti.iocontract import gr1_iocontract as gr1


def core(expr):
    return gr1._make_core_from_expr(expr)


def terms(init=None, inv=None):
    return gr1.GR1TermList.from_bucket_formulas(
        init=[core(expr) for expr in (init or [])],
        inv=[core(expr) for expr in (inv or [])],
    )


def implies(left, right):
    return gr1._implies(left, right)


def expr(bucket):
    return gr1._bucket_expr(bucket)


def contextual_init_refines(source, target, horizon=0):
    guard = z3.And(expr(source.init_terms()), gr1._shift_closed_inv_expr(source.inv_terms(), horizon))
    return implies(guard, expr(target.init_terms()))


def test_plain_init_implication_without_invariants():
    p_0, q_0 = z3.Bools("p_0 q_0")
    source = terms(init=[z3.And(p_0, q_0)])
    target = terms(init=[p_0])

    assert implies(expr(source.init_terms()), expr(target.init_terms()))
    assert contextual_init_refines(source, target)
    assert gr1._init_terms_refine(source.init_terms(), source.inv_terms(), target.init_terms())
    assert source.refines(target)


def test_source_invariant_context_soundly_establishes_target_init():
    p_0 = z3.Bool("p_0")
    source = terms(inv=[p_0])
    target = terms(init=[p_0])

    assert not implies(expr(source.init_terms()), expr(target.init_terms()))
    assert contextual_init_refines(source, target)
    assert gr1._init_terms_refine(source.init_terms(), source.inv_terms(), target.init_terms())
    assert source.refines(target)


def test_target_invariant_context_would_be_unsound():
    p_0 = z3.Bool("p_0")
    source = terms()
    target = terms(init=[p_0], inv=[p_0])

    assert implies(z3.And(expr(source.init_terms()), expr(target.inv_terms())), expr(target.init_terms()))
    assert not contextual_init_refines(source, target)
    assert not gr1._init_terms_refine(source.init_terms(), source.inv_terms(), target.init_terms())
    assert not source.refines(target)
    # The constant p=False source trace violates both target INIT and target INV.
    assert z3.is_false(z3.simplify(z3.substitute(p_0, (p_0, z3.BoolVal(False)))))


def test_bounded_next_init_can_require_shifted_source_invariants():
    p_0, q_0, q_1, r_0, r_1 = z3.Bools("p_0 q_0 q_1 r_0 r_1")
    source = terms(inv=[z3.Implies(p_0, q_1), z3.Implies(q_0, r_1), z3.Not(r_0)])
    target = terms(init=[z3.Not(p_0)])

    assert not contextual_init_refines(source, target, horizon=0)
    assert not contextual_init_refines(source, target, horizon=1)
    assert contextual_init_refines(source, target, horizon=2)
    assert not gr1._init_terms_refine(source.init_terms(), source.inv_terms(), target.init_terms(), max_horizon=0)
    assert not gr1._init_terms_refine(source.init_terms(), source.inv_terms(), target.init_terms(), max_horizon=1)
    assert gr1._init_terms_refine(source.init_terms(), source.inv_terms(), target.init_terms(), max_horizon=2)
    assert source.refines(target)


def test_countdown_family_requires_arbitrary_finite_init_horizons():
    for length in (2, 3, 4):
        variables = [z3.Bool(f"count_{length}_{index}_0") for index in range(length + 1)]
        next_variables = [z3.Bool(f"count_{length}_{index}_1") for index in range(length + 1)]
        source_inv = [z3.Not(variables[-1])]
        source_inv.extend(z3.Implies(variables[index], next_variables[index + 1]) for index in range(length))
        source = terms(inv=source_inv)
        target = terms(init=[z3.Not(variables[0])])

        assert not contextual_init_refines(source, target, horizon=length - 1)
        assert contextual_init_refines(source, target, horizon=length)
        assert not gr1._init_terms_refine(
            source.init_terms(), source.inv_terms(), target.init_terms(), max_horizon=length - 1
        )
        assert gr1._init_terms_refine(source.init_terms(), source.inv_terms(), target.init_terms(), max_horizon=length)


def test_valid_init_consequence_can_lack_a_finite_shift_certificate():
    p_0, p_1 = z3.Bools("p_drift_0 p_drift_1")
    x_0, x_1 = z3.Reals("x_drift_0 x_drift_1")
    source = terms(
        inv=[
            z3.Implies(p_0, p_1),
            z3.Implies(z3.Not(p_0), z3.Not(p_1)),
            z3.Implies(p_0, x_0 == 0),
            z3.Implies(z3.Not(p_0), x_0 <= 0),
            z3.Implies(z3.Not(p_0), x_1 >= x_0 + 1),
        ]
    )
    target = terms(init=[p_0])

    # Semantically, an infinite !p trace would increase x forever while x<=0.
    # Every tested finite closure survives by choosing a sufficiently negative x_0.
    for horizon in range(6):
        assert not contextual_init_refines(source, target, horizon=horizon)
        assert not gr1._init_terms_refine(
            source.init_terms(), source.inv_terms(), target.init_terms(), max_horizon=horizon
        )


def test_minimal_raw_stored_reproducer_is_contextually_equivalent():
    p_0, q_0 = z3.Bools("p_0 q_0")
    raw = terms(
        init=[z3.And(z3.Not(p_0), z3.Not(q_0))],
        inv=[z3.Or(z3.Not(q_0), z3.And(z3.Not(p_0), q_0))],
    )
    stored = raw.simplify()
    raw_init = expr(raw.init_terms())
    stored_init = expr(stored.init_terms())
    invariant = expr(stored.inv_terms())

    assert z3.eq(z3.simplify(stored_init), p_0 == q_0)
    assert not gr1._equivalent(raw_init, stored_init)
    assert gr1._equivalent(z3.And(invariant, raw_init), z3.And(invariant, stored_init))
    assert raw.refines(stored)
    assert stored.refines(raw)


def test_unrelated_init_and_irrelevant_source_invariant_remain_unproved():
    p_0, q_0 = z3.Bools("p_unrelated_0 q_unrelated_0")
    target = terms(init=[p_0])

    assert not terms().refines(target)
    assert not terms(inv=[q_0]).refines(target)


def test_bounded_next_source_with_infinite_countertrace_remains_unproved():
    p_0, p_1 = z3.Bools("p_counter_0 p_counter_1")
    source = terms(inv=[p_1 == p_0])
    target = terms(init=[p_0])

    assert not source.refines(target)
    # The constant p=False trace satisfies the source and violates target INIT.
    assert z3.is_true(z3.simplify(z3.substitute(p_1 == p_0, (p_0, z3.BoolVal(False)), (p_1, z3.BoolVal(False)))))


def test_arithmetic_source_with_infinite_countertrace_remains_unproved():
    x_0, x_1 = z3.Reals("x_counter_0 x_counter_1")
    source = terms(inv=[x_1 == x_0])
    target = terms(init=[x_0 >= 0])

    assert not source.refines(target)


def _load_aeb():
    path = Path(__file__).parents[1] / "examples" / "aeb_gr1_composition.py"
    spec = importlib.util.spec_from_file_location("aeb_init_diagnostic", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_final_aeb_stored_guarantee_init_uses_contextual_fallback():
    aeb = _load_aeb()
    vehicle = aeb.make_vehicle()
    target = aeb.make_supervisor().compose(vehicle, simplify=True)
    quotient = target.quotient(vehicle, simplify=True)
    recomposed = vehicle.compose(quotient, simplify=True)

    assert implies(expr(target.a.init_terms()), expr(recomposed.a.init_terms()))
    assert contextual_init_refines(target.a, recomposed.a)
    assert gr1._init_terms_refine(target.a.init_terms(), target.a.inv_terms(), recomposed.a.init_terms())

    guarantee_source = recomposed.g | target.a
    guarantee_target = target.g | target.a
    assert not implies(expr(guarantee_source.init_terms()), expr(guarantee_target.init_terms()))
    assert contextual_init_refines(guarantee_source, guarantee_target)
    assert gr1._init_terms_refine(
        guarantee_source.init_terms(), guarantee_source.inv_terms(), guarantee_target.init_terms()
    )
    assert recomposed.refines(target)


def test_final_aeb_raw_and_stored_safety_is_contextually_equivalent():
    aeb = _load_aeb()
    vehicle = aeb.make_vehicle()
    composed = aeb.make_supervisor().compose(vehicle, simplify=True)
    quotient = composed.quotient(vehicle, simplify=True)
    recomposed = vehicle.compose(quotient, simplify=True)

    for contract in (composed, quotient, recomposed):
        for raw, stored in (
            (contract._operation_assumptions, contract.a),
            (contract._operation_guarantees, contract.g),
        ):
            raw_inv = expr(raw.inv_terms())
            stored_inv = expr(stored.inv_terms())
            assert gr1._equivalent(raw_inv, stored_inv)
            assert gr1._equivalent(
                z3.And(raw_inv, expr(raw.init_terms())),
                z3.And(stored_inv, expr(stored.init_terms())),
            )
            assert gr1._liv_terms_refine(raw.inv_terms(), raw.liv_terms(), stored.liv_terms())


def test_first_aeb_init_divergence_is_post_cave_reduction():
    aeb = _load_aeb()
    vehicle = aeb.make_vehicle()
    composed = aeb.make_supervisor().compose(vehicle, simplify=True)
    quotient = composed.quotient(vehicle, simplify=True)
    raw = quotient._operation_assumptions

    buckets = (
        (gr1.GR1Tag.INIT, raw.init_terms()),
        (gr1.GR1Tag.INV, raw.inv_terms()),
        (gr1.GR1Tag.LIV, raw.liv_terms()),
    )
    reduced, contradiction = gr1._reduce_simplification_buckets(buckets, None, None, [])
    assert contradiction is None
    before_post_cave = gr1.GR1TermList(reduced)
    after_post_cave = gr1._post_cave_bucket_reduction(before_post_cave)

    assert gr1._equivalent(expr(before_post_cave.init_terms()), expr(raw.init_terms()))
    assert not gr1._equivalent(expr(after_post_cave.init_terms()), expr(raw.init_terms()))
    assert gr1._equivalent(expr(after_post_cave.init_terms()), expr(quotient.a.init_terms()))
