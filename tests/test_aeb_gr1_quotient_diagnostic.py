"""Diagnostic regressions for AEB quotient/recomposition refinement.

These tests characterize current behavior.  They do not modify the AEB
contracts and do not assert that a finite-core liveness rejection is an LTL
counterexample.
"""

import importlib.util
from pathlib import Path

import pytest
import z3

from pacti.iocontract import gr1_iocontract as gr1

_SPEC = importlib.util.spec_from_file_location(
    "aeb_gr1_composition_diagnostic",
    Path(__file__).parents[1] / "examples" / "aeb_gr1_composition.py",
)
assert _SPEC is not None and _SPEC.loader is not None
example = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(example)


def _conjunction(terms):
    return z3.And(*[term.core.expr for term in terms])


def _implies(left, right):
    solver = z3.Solver()
    solver.add(left, z3.Not(right))
    return solver.check() == z3.unsat


def _representation_refinement(source, target, canonical):
    source_a = source._operation_assumptions if canonical else source.a
    source_g = source._operation_guarantees if canonical else source.g
    target_a = target._operation_assumptions if canonical else target.a
    target_g = target._operation_guarantees if canonical else target.g
    assumptions = {
        "init": gr1._init_terms_refine(target_a.init_terms(), target_a.inv_terms(), source_a.init_terms()),
        "inv": gr1._inv_terms_refine(target_a.inv_terms(), source_a.inv_terms()),
    }
    guarantee_source = source_g | target_a
    guarantee_target = target_g | target_a
    guarantees = {
        "init": gr1._init_terms_refine(
            guarantee_source.init_terms(),
            guarantee_source.inv_terms(),
            guarantee_target.init_terms(),
        ),
        "inv": gr1._inv_terms_refine(guarantee_source.inv_terms(), guarantee_target.inv_terms()),
    }
    assumption_liv = gr1._liv_terms_refine(target_a.inv_terms(), target_a.liv_terms(), source_a.liv_terms())
    guarantee_liv = gr1._liv_terms_refine(
        guarantee_source.inv_terms(),
        guarantee_source.liv_terms(),
        guarantee_target.liv_terms(),
    )
    return assumptions, guarantees, assumption_liv, guarantee_liv


@pytest.fixture(scope="module")
def aeb_contracts():
    supervisor = example.make_supervisor()
    vehicle = example.make_vehicle()
    target = supervisor.compose(vehicle, simplify=True)
    quotient = target.quotient(vehicle, simplify=True)
    recomposed = vehicle.compose(quotient, simplify=True)
    return supervisor, vehicle, target, quotient, recomposed


def test_aeb_contract_inputs_are_unchanged(aeb_contracts):
    supervisor, vehicle, _, _, _ = aeb_contracts
    assert [len(getattr(supervisor.g, f"{tag}_terms")()) for tag in ("init", "inv", "liv")] == [4, 11, 1]
    assert [len(getattr(vehicle.g, f"{tag}_terms")()) for tag in ("init", "inv", "liv")] == [1, 3, 0]
    d_0, u_0, v_0, v_1 = z3.Reals("d_0 u_0 v_0 v_1")
    assert _implies(_conjunction(supervisor.g.init_terms()), u_0 == d_0 / 10)
    assert _implies(_conjunction(supervisor.g.inv_terms()), u_0 <= 6)
    assert _implies(_conjunction(vehicle.g.init_terms()), v_0 == u_0)
    assert _implies(_conjunction(vehicle.g.inv_terms()), u_0 - z3.RealVal("1/2") <= v_1)
    assert _implies(_conjunction(vehicle.g.inv_terms()), v_1 <= u_0 + z3.RealVal("1/2"))


def test_aeb_interfaces_show_quotient_projection_is_separate(aeb_contracts):
    supervisor, vehicle, target, quotient, recomposed = aeb_contracts
    assert ({v.name for v in supervisor.inputvars}, {v.name for v in supervisor.outputvars}) == (
        {"d", "URG", "WRN"},
        {"MOV", "DCL", "STP", "u"},
    )
    assert ({v.name for v in vehicle.inputvars}, {v.name for v in vehicle.outputvars}) == (
        {"u", "MOV", "DCL", "STP"},
        {"v"},
    )
    assert {v.name for v in target.inputvars} == {"d", "URG", "WRN"}
    assert {v.name for v in target.outputvars} == {"v"}
    assert {v.name for v in quotient.inputvars} == {"d", "URG", "WRN"}
    assert {v.name for v in quotient.outputvars} == {"MOV", "DCL", "STP", "u"}
    assert target.shares_io_with(recomposed)
    assert quotient.shares_io_with(supervisor)


def test_aeb_canonical_refinement_is_proved_bucket_by_bucket(aeb_contracts):
    _, _, target, _, recomposed = aeb_contracts
    assumptions, guarantees, assumption_liv, guarantee_liv = _representation_refinement(
        recomposed, target, canonical=True
    )
    assert assumptions == {"init": True, "inv": True}
    assert guarantees == {"init": True, "inv": True}
    assert assumption_liv
    assert guarantee_liv


def test_aeb_raw_safety_is_proved_by_normal_refinement(aeb_contracts):

    _, _, target, _, recomposed = aeb_contracts
    source_inv = recomposed._operation_guarantees.inv_terms() + target._operation_assumptions.inv_terms()
    target_inv = _conjunction(target._operation_guarantees.inv_terms())

    closure_zero = gr1._shift_closed_inv_expr(source_inv, 0)
    closure_one = gr1._shift_closed_inv_expr(source_inv, 1)
    assert not _implies(closure_zero, target_inv)
    assert _implies(closure_one, target_inv)
    assert not gr1._inv_terms_refine(source_inv, target._operation_guarantees.inv_terms(), max_horizon=0)
    assert gr1._inv_terms_refine(source_inv, target._operation_guarantees.inv_terms(), max_horizon=1)
    assert gr1._inv_terms_refine(source_inv, target._operation_guarantees.inv_terms(), max_horizon=2)
    assert gr1.GR1TermList(source_inv).refines(gr1.GR1TermList(target._operation_guarantees.inv_terms()))


def test_aeb_raw_guarantee_liveness_is_proved_from_invariants(aeb_contracts):
    _, _, target, _, recomposed = aeb_contracts
    source = recomposed._operation_guarantees | target._operation_assumptions
    target_guarantee_liv = target._operation_guarantees.liv_terms()

    assert gr1._inv_terms_refine(source.inv_terms(), target_guarantee_liv, max_horizon=0)
    assert gr1._inv_terms_refine(source.inv_terms(), target_guarantee_liv, max_horizon=2)
    assert gr1._liv_terms_refine(source.inv_terms(), source.liv_terms(), target_guarantee_liv)

    closure = gr1._shift_closed_inv_expr(source.inv_terms(), 2)
    for support in source.liv_terms():
        for target_liv in target_guarantee_liv:
            assert gr1._implies(z3.And(closure, support.core.expr), target_liv.core.expr)


def test_aeb_stored_refinement_is_proved(aeb_contracts):
    _, _, target, quotient, recomposed = aeb_contracts
    assumptions, guarantees, assumption_liv, guarantee_liv = _representation_refinement(
        recomposed, target, canonical=False
    )
    assert assumptions == {"init": True, "inv": True}
    assert guarantees == {"init": True, "inv": True}
    assert assumption_liv
    assert guarantee_liv
    assert recomposed.refines(target)

    assert _implies(_conjunction(target.a.init_terms()), _conjunction(recomposed.a.init_terms()))
    assert gr1._init_terms_refine(target.a.init_terms(), target.a.inv_terms(), recomposed.a.init_terms(), max_horizon=0)
    guarantee_source = recomposed.g | target.a
    guarantee_target = target.g | target.a
    assert not _implies(
        _conjunction(guarantee_source.init_terms()),
        _conjunction(guarantee_target.init_terms()),
    )
    assert gr1._init_terms_refine(
        guarantee_source.init_terms(),
        guarantee_source.inv_terms(),
        guarantee_target.init_terms(),
        max_horizon=0,
    )
    # The final hidden-interface architecture yields a quotient with the same
    # interface as the supervisor and preserves its initial environment bound.
    assert _implies(
        _conjunction(quotient._operation_assumptions.init_terms()),
        _conjunction(quotient.a.init_terms()),
    )
    assert gr1._init_terms_refine(
        quotient.a.init_terms(),
        quotient.a.inv_terms(),
        quotient._operation_assumptions.init_terms(),
    )


def _contract(inputs, outputs, sorts, assumptions=None, guarantees=None):
    return gr1.GR1IoContract.from_dict(
        {
            "input_vars": inputs,
            "output_vars": outputs,
            "variable_sorts": sorts,
            "assumptions": assumptions or {},
            "guarantees": guarantees or {},
        },
        simplify=False,
    )


def _round_trip_law(first, second):
    target = first.compose(second, simplify=True)
    quotient = target.quotient(second, simplify=True)
    recomposed = second.compose(quotient, simplify=True)
    canonical = _representation_refinement(recomposed, target, canonical=True)
    canonical_safety = all(canonical[0].values()) and all(canonical[1].values())
    stored = recomposed.refines(target)
    return canonical_safety, stored


@pytest.mark.parametrize(
    "case, first, second, expected",
    [
        (
            "A boolean INIT/INV",
            _contract(["e"], ["u"], {"e": "bool", "u": "bool"}, guarantees={"init": ["u=e"], "inv": ["u=e"]}),
            _contract(["u"], ["y"], {"u": "bool", "y": "bool"}, guarantees={"init": ["y=u"], "inv": ["y=u"]}),
            (True, True),
        ),
        (
            "B boolean with X",
            _contract(
                ["e"], ["u"], {"e": "bool", "u": "bool"}, guarantees={"init": ["u=e"], "inv": ["u=e", "e -> X(u)"]}
            ),
            _contract(["u"], ["y"], {"u": "bool", "y": "bool"}, guarantees={"init": ["y=u"], "inv": ["u=X(y)"]}),
            (True, True),
        ),
        (
            "C boolean with LIV",
            _contract(
                ["e"],
                ["u"],
                {"e": "bool", "u": "bool"},
                assumptions={"liv": ["e"]},
                guarantees={"init": ["u=e"], "inv": ["u=e"], "liv": ["u"]},
            ),
            _contract(
                ["u"],
                ["y"],
                {"u": "bool", "y": "bool"},
                assumptions={"liv": ["u"]},
                guarantees={"init": ["y=u"], "inv": ["y=u"], "liv": ["y"]},
            ),
            (True, True),
        ),
        (
            "D boolean with X and LIV",
            _contract(
                ["e"],
                ["u"],
                {"e": "bool", "u": "bool"},
                assumptions={"liv": ["e"]},
                guarantees={"init": ["u=e"], "inv": ["u=e", "e -> X(u)"], "liv": ["u"]},
            ),
            _contract(
                ["u"],
                ["y"],
                {"u": "bool", "y": "bool"},
                assumptions={"liv": ["u"]},
                guarantees={"init": ["y=u"], "inv": ["u=X(y)"], "liv": ["y"]},
            ),
            (True, True),
        ),
        (
            "E arithmetic with projected shared input",
            _contract(
                ["d"], ["u"], {"d": "real", "u": "real", "v": "real"}, guarantees={"init": ["u=d"], "inv": ["u=d"]}
            ),
            _contract(
                ["d", "u"], ["v"], {"d": "real", "u": "real", "v": "real"}, guarantees={"init": ["v=u"], "inv": ["v=u"]}
            ),
            (True, False),
        ),
        (
            "F arithmetic X and LIV with projected shared input",
            _contract(
                ["d"],
                ["u"],
                {"d": "real", "u": "real", "v": "real"},
                assumptions={"liv": ["d>=0"]},
                guarantees={"init": ["u=d"], "inv": ["u=d"], "liv": ["u>=0"]},
            ),
            _contract(
                ["d", "u"],
                ["v"],
                {"d": "real", "u": "real", "v": "real"},
                assumptions={"liv": ["u>=0"]},
                guarantees={"init": ["v=u"], "inv": ["u-1<=X(v)", "X(v)<=u+1"], "liv": ["v>=0"]},
            ),
            (True, False),
        ),
    ],
    ids=lambda item: item if isinstance(item, str) else None,
)
def test_minimal_feature_matrix(case, first, second, expected):
    del case
    assert _round_trip_law(first, second) == expected


def test_shared_input_projection_is_the_first_minimal_trigger():
    sorts = {"d": "real", "u": "real", "v": "real"}
    first = _contract(["d"], ["u"], sorts, guarantees={"init": ["u=d"], "inv": ["u=d"]})
    downstream_without_d = _contract(["u"], ["v"], sorts, guarantees={"init": ["v=u"], "inv": ["v=u"]})
    downstream_with_d = _contract(["d", "u"], ["v"], sorts, guarantees={"init": ["v=u"], "inv": ["v=u"]})
    assert _round_trip_law(first, downstream_without_d) == (True, True)
    assert _round_trip_law(first, downstream_with_d) == (True, False)


def test_minimal_raw_safety_failure_needs_mode_transition_and_projected_real_input():
    """Characterize the smaller form of the AEB raw quotient failure."""

    sorts = {"d": "real", "u": "real", "v": "real", "w": "bool", "b": "bool"}
    producer = _contract(
        ["d", "w"],
        ["b", "u"],
        sorts,
        assumptions={"inv": ["0<=d", "d<=30", "w -> (10<d & d<=15)"]},
        guarantees={"inv": ["w->X(b)", "b->u<=d/10", "0<=u", "u<=7"]},
    )
    downstream = _contract(
        ["d", "u"],
        ["v"],
        sorts,
        assumptions={"inv": ["0<=u", "u<=d/4"]},
        guarantees={"inv": ["u-1/2<=X(v)", "X(v)<=u+1/2"]},
    )
    target = producer.compose(downstream, simplify=True)
    quotient = target.quotient(downstream, simplify=True)
    recomposed = downstream.compose(quotient, simplify=True)

    source_inv = recomposed._operation_guarantees.inv_terms() + target._operation_assumptions.inv_terms()
    first_target = target._operation_guarantees.inv_terms()[0]
    shifted_source = gr1._shifted_inv_guard_for_cores(source_inv, [first_target.core])
    solver = z3.Solver()
    solver.add(shifted_source, z3.Not(first_target.core.expr))

    assert {var.name for var in quotient.inputvars} == {"w"}
    assert solver.check() == z3.sat
    target_inv = target._operation_guarantees.inv_terms()
    assert not gr1._inv_terms_refine(source_inv, target_inv, max_horizon=0)
    assert not gr1._inv_terms_refine(source_inv, target_inv, max_horizon=1)
    assert gr1._inv_terms_refine(source_inv, target_inv, max_horizon=2)
    assert gr1.GR1TermList(source_inv).refines(gr1.GR1TermList(target_inv))
