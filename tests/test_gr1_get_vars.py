"""Differential checks against the installed Z3 variable collector."""

import itertools
import random
from typing import Any, Dict, Iterator, List, Optional

import pytest
import z3
from z3.z3util import get_vars

from pacti.iocontract import gr1_iocontract as gr1


def _assert_same(expr: Any, rs: Optional[List[Any]] = None) -> None:
    expected = get_vars(expr, rs)
    actual = gr1._z3_get_vars(expr, rs)
    assert [(str(v), v.get_id()) for v in actual] == [(str(v), v.get_id()) for v in expected]


def test_get_vars_constants_sorts_and_sharing() -> None:
    x, y = z3.Ints("x y")
    r = z3.Real("r")
    b = z3.Bool("b")
    enum, values = z3.EnumSort("GetVarsEnum", ["GetVarsOn", "GetVarsOff"])
    array = z3.Array("a", z3.IntSort(), z3.RealSort())
    function = z3.Function("f", z3.IntSort(), z3.IntSort())
    shared = x + y
    expressions = [
        z3.BoolVal(True),
        z3.BoolVal(False),
        z3.IntVal(0),
        z3.RealVal("1/3"),
        z3.BitVecVal(7, 8),
        z3.StringVal("literal"),
        values[0],
        z3.Const("mode", enum),
        x,
        b,
        r,
        z3.And(b, b),
        shared + shared,
        z3.And(x > 0, r > x, b),
        z3.Select(array, x) > r,
        z3.K(z3.IntSort(), r),
        function(x),
        z3.And(z3.Int("collision") > 0, z3.Real("collision") > 0),
        z3.And(z3.Real("collision") > 0, z3.Int("collision") > 0),
    ]
    for expr in expressions:
        _assert_same(expr)


def test_get_vars_quantifiers_and_bound_names() -> None:
    x, y = z3.Ints("x y")
    predicate = z3.Function("pattern_predicate", z3.IntSort(), z3.IntSort(), z3.BoolSort())
    pattern_only = z3.Int("pattern_only")
    expressions = [
        z3.ForAll([x], x > y),
        z3.Exists([x], x == y),
        z3.And(x > 0, z3.ForAll([x], x > y)),
        z3.ForAll([x], z3.Exists([y], x > y)),
        z3.Exists([x], z3.And(z3.ForAll([y], y > x), x > z3.Int("free"))),
        z3.ForAll([x], x > y, patterns=[predicate(x, pattern_only)]),
        z3.Var(0, z3.IntSort()),
    ]
    for expr in expressions:
        _assert_same(expr)


def test_get_vars_odd_names() -> None:
    names = ("y0_1", "x'", "a b", "|a b|", "a|b", "λ", "True", "1", "")
    for name in names:
        integer, real = z3.Int(name), z3.Real(name)
        _assert_same(z3.And(integer > 0, real < 1, z3.Bool(name)))
        _assert_same(z3.And(real < 1, integer > 0))


def test_get_vars_accumulator_semantics() -> None:
    x, y = z3.Ints("x y")
    for expr in (z3.IntVal(3), z3.BoolVal(False), x, x + y, z3.And(), z3.Var(0, z3.IntSort())):
        rs = [z3.Real("x"), x, y, y]
        before = [v.get_id() for v in rs]
        _assert_same(expr, rs)
        assert [v.get_id() for v in rs] == before
        if z3.is_const(expr) and expr.decl().kind() != z3.Z3_OP_UNINTERPRETED:
            assert gr1._z3_get_vars(expr, rs) is rs
    assert gr1._z3_get_vars(z3.IntVal(3)) == []


def test_get_vars_deep_shared_dag(monkeypatch: pytest.MonkeyPatch) -> None:
    # The reference's unfolded tree has 2**2500 leaves; do not execute it here.
    monkeypatch.setattr(gr1, "_USE_FAST_Z3_GET_VARS", True)
    x, y = z3.Ints("deep_x deep_y")
    expr = x
    depth = 2500
    for _ in range(depth):
        expr = expr + expr
    expr = expr > y
    visits: Dict[int, int] = {}
    original_children = z3.ExprRef.children

    def children(node: Any) -> List[Any]:
        identity = node.get_id()
        visits[identity] = visits.get(identity, 0) + 1
        return original_children(node)

    monkeypatch.setattr(z3.ExprRef, "children", children)
    actual = gr1._z3_get_vars(expr)
    assert [v.get_id() for v in actual] == [x.get_id(), y.get_id()]
    assert max(visits.values()) == 1
    assert len(visits) <= depth + 3


def test_get_vars_random_differential() -> None:
    rng = random.Random(0)
    boolean_leaves = list(z3.Bools("random_b0 random_b1 random_b2")) + [z3.BoolVal(True)]
    numeric_leaves = {
        "int": list(z3.Ints("random_i0 random_i1")) + [z3.IntVal(0), z3.IntVal(-1)],
        "real": list(z3.Reals("random_r0 random_r1")) + [z3.RealVal("1/2"), z3.RealVal(0)],
    }

    def number(depth: int, sort: str) -> Any:
        if not depth:
            return rng.choice(numeric_leaves[sort])
        left = number(depth - 1, sort)
        right = left if rng.random() < 0.4 else number(depth - 1, sort)
        operation = rng.randrange(4)
        if operation == 0:
            return left + right
        if operation == 1:
            return left - right
        if operation == 2:
            return left * 2
        return z3.If(boolean(depth - 1), left, right)

    def boolean(depth: int) -> Any:
        if not depth:
            return rng.choice(boolean_leaves)
        operation = rng.randrange(7)
        if operation < 2:
            sort = rng.choice(("int", "real"))
            left, right = number(depth - 1, sort), number(depth - 1, sort)
            return left < right if operation == 0 else left == right
        left = boolean(depth - 1)
        right = left if rng.random() < 0.4 else boolean(depth - 1)
        if operation == 2:
            return z3.And(left, right)
        if operation == 3:
            return z3.Or(left, right)
        if operation == 4:
            return z3.Not(left)
        if operation == 5:
            return z3.Implies(left, right)
        return z3.If(left, right, boolean(depth - 1))

    for index in range(300):
        expr = boolean(3) if index % 3 == 0 else number(3, "int" if index % 3 == 1 else "real")
        _assert_same(expr)


def _example_terms() -> Iterator[Any]:
    from examples.aeb_gr1_composition import make_supervisor, make_vehicle
    from examples.gr1_cave_scalability import SyntheticParameters, generate_synthetic_instance
    from examples import gr1_cave_experiments as constructors

    constructors._load_dependencies()  # Import bootstrap only; no experiment mode.
    for simplify in (True, False):
        supervisor, vehicle = make_supervisor(), make_vehicle()
        composed = supervisor.compose(vehicle, simplify=simplify)
        quotient = composed.quotient(vehicle, simplify=simplify)
        for contract in (supervisor, vehicle, composed, quotient):
            yield from contract.a.terms
            yield from contract.g.terms
    for np, ni, nj, depth in itertools.product((1, 2), (1, 2), (1, 2), (0, 1)):
        instance = generate_synthetic_instance(SyntheticParameters(np, ni, nj, depth))
        yield from instance.target.terms
        yield from instance.context.terms
        for direction in ("refining", "relaxing"):
            result, _ = getattr(instance.target, f"elim_vars_by_{direction}")(
                context=instance.context, vars_to_elim=list(instance.eliminated), simplify=False, tactics_order=[]
            )
            yield from result.terms
    for n in (2, 3):
        result = constructors.stage(1)
        for i in range(2, n + 1):
            stage = constructors.stage(i)
            yield from stage.a.terms
            yield from stage.g.terms
            result = result.compose(stage, simplify=True)
        yield from result.a.terms
        yield from result.g.terms
    stages = [constructors.stage(i) for i in range(1, 5)]
    for stage in stages:
        yield from stage.a.terms
        yield from stage.g.terms
    result = (
        stages[0].compose(stages[1], simplify=True).compose(stages[2].compose(stages[3], simplify=True), simplify=True)
    )
    yield from result.a.terms
    yield from result.g.terms


def test_get_vars_example_expressions() -> None:
    for term in _example_terms():
        _assert_same(term.core.expr)
        if term.core.raw_expr is not None:
            _assert_same(term.core.raw_expr)


def test_get_vars_fallback_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    x, y = z3.Ints("fallback_x fallback_y")
    expr = z3.And(x > y, z3.Exists([x], x > y), z3.Real("fallback_x") > 0)
    monkeypatch.setattr(gr1, "_USE_FAST_Z3_GET_VARS", True)
    fast = gr1._z3_get_vars(expr)
    monkeypatch.setattr(gr1, "_USE_FAST_Z3_GET_VARS", False)
    slow = gr1._z3_get_vars(expr)
    assert [(str(v), v.get_id()) for v in fast] == [(str(v), v.get_id()) for v in slow]
    _assert_same(expr)
