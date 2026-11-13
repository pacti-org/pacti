"""Executable audit of the full-bucket GR(1) emergency-braking derivation.

This example deliberately keeps three views separate: literal raw CAVE output,
the stored post-CAVE contract, and the assumption-relative Unicode display.
All predictions are checked semantically with Z3; a mismatch is reported and
never patched into the GR(1) implementation.

Retained as a fixture provider for tests/test_gr1_aeb_full_buckets.py.
This historical supervisor/actuator model is separate from the manuscript's
C_T/clearance-prediction example in aeb_predicted_clearance.py.

Some hand-written quotient predictions below are obsolete: they omit a second
recurrence assumption and successor-state context, or compare reduced buckets
without the invariants used in reduction. Quotient need not recover the
original actuator. The script reports these mismatches as OVERALL: FAIL but
does not set a failing exit status. Use the maintained regression tests for
current canonical-bucket and finite-window expectations.

Run with ``python examples/gr1_aeb_full_buckets.py`` from the repository root;
verify with ``python -m pytest -q tests/test_gr1_aeb_full_buckets.py``.
"""

from __future__ import annotations

from typing import Dict, Iterable, Optional, Tuple

import z3

from pacti.iocontract import Var
from pacti.iocontract.gr1_iocontract import (
    GR1IoContract,
    GR1Term,
    GR1TermList,
    _assumption_relative_guarantee_view,
    _project_liv_terms,
    _shifted_inv_guard_for_cores,
)


def conjunction(terms: Iterable[GR1Term]) -> z3.BoolRef:
    """Conjoin flattened cores; an empty bucket denotes true."""
    return z3.And(*[term.core.expr for term in terms])


def equivalent(left: z3.BoolRef, right: z3.BoolRef, context: z3.BoolRef = z3.BoolVal(True)) -> bool:
    solver = z3.Solver()
    solver.add(context, left != right)
    return solver.check() == z3.unsat


def implies(left: z3.BoolRef, right: z3.BoolRef) -> bool:
    solver = z3.Solver()
    solver.add(left, z3.Not(right))
    return solver.check() == z3.unsat


def counterexample(left: z3.BoolRef, right: z3.BoolRef, context: z3.BoolRef) -> Optional[z3.ModelRef]:
    solver = z3.Solver()
    solver.add(context, left != right)
    return solver.model() if solver.check() == z3.sat else None


def make_supervisor() -> GR1IoContract:
    """Create the exact supervisor from the paper-side derivation."""
    return GR1IoContract.from_dict(
        {
            "input_vars": ["d", "e"],
            "output_vars": ["u"],
            "variable_sorts": {"d": "real", "e": "bool", "u": "real"},
            "assumptions": {
                "init": ["d >= 15", "!e"],
                "inv": ["d >= 0", "d <= 20", "d <= 8 -> e", "d >= 15 -> !e"],
                "liv": ["d >= 15"],
            },
            "guarantees": {
                "init": ["u = 0"],
                "inv": ["u >= -5", "u <= 2 - d/10", "e -> u <= -3", "!e -> u >= -1/2"],
                "liv": ["u >= -1/2"],
            },
        },
        simplify=False,
    )


def make_actuator() -> GR1IoContract:
    """Create the exact bounded-response actuator from the derivation."""
    return GR1IoContract.from_dict(
        {
            "input_vars": ["u"],
            "output_vars": ["a"],
            "variable_sorts": {"u": "real", "a": "real"},
            "assumptions": {
                "init": ["u = 0"],
                "inv": ["u >= -5", "u <= 1"],
                "liv": ["u >= -1/2"],
            },
            "guarantees": {
                "init": ["a = 0"],
                "inv": ["X(a) >= u - 1/2", "X(a) <= u + 1/2"],
                "liv": ["a >= -1"],
            },
        },
        simplify=False,
    )


def shifted_assumption_context(contract: GR1IoContract, terms: Iterable[GR1Term]) -> z3.BoolRef:
    """Return the invariant assumption closure required by ``terms``."""
    cores = [term.core for term in terms]
    return _shifted_inv_guard_for_cores(contract.a.inv_terms(), cores)


def _liv_contains_equivalent(term_list: GR1TermList, expected: z3.BoolRef) -> bool:
    return any(equivalent(term.core.expr, expected) for term in term_list.liv_terms())


def verified_quotient_init_candidate(contract: GR1IoContract) -> GR1TermList:
    """Return the compact INIT guarantee after proving it against canonical data."""
    candidate = GR1TermList.from_bucket_strings(
        init=["a = 0", "-1/2 <= X(a)", "X(a) <= 1/2"],
        variable_sorts={"u": "real", "a": "real"},
    )
    exact_terms = contract._operation_guarantees.init_terms()
    context = z3.And(
        conjunction(contract._operation_assumptions.init_terms()),
        shifted_assumption_context(contract, exact_terms + candidate.init_terms()),
    )
    if not equivalent(conjunction(exact_terms), conjunction(candidate.init_terms()), context):
        raise AssertionError("quotient INIT presentation candidate is not contextually equivalent")
    return candidate


def print_view(
    title: str,
    contract: GR1IoContract,
    *,
    raw: bool = False,
    preserve_term_boundaries: bool = False,
) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)
    if raw:
        print(contract.debug_dump())
        return
    candidate_a = contract.a if preserve_term_boundaries else None
    candidate_g = contract.g if preserve_term_boundaries else None
    print(
        contract.to_pretty_string(
            assumption_relative=True,
            candidate_assumptions=candidate_a,
            candidate_guarantees=candidate_g,
        )
    )


def print_canonical_view(title: str, contract: GR1IoContract) -> None:
    """Print the preserved operation-grade buckets."""
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)
    print(contract.canonical_debug_dump())


def run_audit() -> Tuple[Dict[str, bool], Dict[str, GR1IoContract]]:
    """Run the complete composition/quotient audit and return its observations."""
    supervisor, actuator = make_supervisor(), make_actuator()
    print_view("SUPERVISOR", supervisor, preserve_term_boundaries=True)
    print_view("ACTUATOR", actuator, preserve_term_boundaries=True)

    raw_target = supervisor.compose(actuator, simplify=False)
    target = supervisor.compose(actuator, simplify=True)
    target_before = target.to_machine_dict()
    target_counts = (len(target.a.terms), len(target.g.terms))
    # ------------------------------------------------------------------
    # Optional detailed debugging output retained intentionally.
    # Uncomment when inspecting raw, canonical, and stored composition.
    # ------------------------------------------------------------------
    # print_view("RAW CAVE COMPOSITION", raw_target, raw=True)
    # print_canonical_view("CANONICAL OPERATION COMPOSITION", target)
    # print_view("STORED COMPOSITION", target, raw=True)
    print_view("COMPOSED CONTRACT", target)
    target_unchanged = target.to_machine_dict() == target_before and target_counts == (
        len(target.a.terms),
        len(target.g.terms),
    )

    d0, d1, u0, a0, a1 = z3.Reals("d_0 d_1 u_0 a_0 a_1")
    e0, e1 = z3.Bools("e_0 e_1")
    half = z3.RealVal("1/2")
    expected_a_init = z3.And(d0 >= 15, z3.Not(e0))
    original_a_inv = z3.And(d0 >= 0, d0 <= 20, z3.Implies(d0 <= 8, e0), z3.Implies(d0 >= 15, z3.Not(e0)))
    compatibility = z3.Or(e0, d0 >= 10)
    expected_a_inv = z3.And(original_a_inv, compatibility)
    expected_g_init = z3.And(a0 == 0, a1 >= -half, a1 <= half)
    expected_g_inv = z3.And(
        a1 >= z3.RealVal("-11/2"),
        a1 <= z3.RealVal("5/2") - d0 / 10,
        z3.Implies(e0, a1 <= z3.RealVal("-5/2")),
        z3.Implies(z3.Not(e0), a1 >= -1),
    )

    # Claims 1--3 are checked independently of composition.
    supervisor_inv = conjunction(supervisor.g.inv_terms())
    actuator_required_inv = conjunction(actuator.a.inv_terms())
    claim1_qe = z3.Tactic("qe")(z3.ForAll([u0], z3.Implies(supervisor_inv, actuator_required_inv))).as_expr()
    projected_liv = _project_liv_terms(supervisor.g.liv_terms(), supervisor.g, [Var("u")])[0].core.expr
    expected_projected_liv = z3.And(z3.Not(e0), d0 <= 25)
    tracking = conjunction(actuator.g.inv_terms())
    claim2_qe = z3.Tactic("qe")(z3.Exists([u0], z3.And(supervisor_inv, tracking))).as_expr()

    display_g = _assumption_relative_guarantee_view(target)
    raw_g_inv = conjunction(raw_target.g.inv_terms())
    display_g_inv = conjunction(display_g.inv_terms())
    raw_inv_context = shifted_assumption_context(target, raw_target.g.inv_terms())
    display_inv_context = shifted_assumption_context(target, display_g.inv_terms())
    init_context = z3.And(conjunction(target.a.init_terms()), shifted_assumption_context(target, target.g.init_terms()))

    checks: Dict[str, bool] = {
        # The raw bucket matches literally.  Stored post-CAVE reduction removes
        # !e because stored INIT d>=15 plus stored INV already entails it.
        "Composition A INIT": equivalent(conjunction(raw_target.a.init_terms()), expected_a_init),
        "Composition new A INV: !e -> d >= 10": equivalent(claim1_qe, compatibility),
        "Composition A INV": equivalent(conjunction(target.a.inv_terms()), expected_a_inv),
        "Composition A LIV": _liv_contains_equivalent(target.a, d0 >= 15) and len(target.a.liv_terms()) == 1,
        "Projected supervisor LIV": equivalent(projected_liv, expected_projected_liv),
        "Independent projection INV": equivalent(claim2_qe, expected_g_inv, expected_a_inv),
        "Composition G INIT": equivalent(conjunction(target.g.init_terms()), expected_g_init, init_context),
        "Composition G INV": equivalent(raw_g_inv, expected_g_inv, raw_inv_context),
        "Composition display G INV": equivalent(display_g_inv, expected_g_inv, display_inv_context),
        "Composition G LIV": _liv_contains_equivalent(display_g, a0 >= -1)
        and not _liv_contains_equivalent(display_g, expected_projected_liv),
        "Close obstacle consequence": implies(
            z3.And(expected_a_inv, expected_g_inv), z3.Implies(d0 <= 8, a1 <= z3.RealVal("-5/2"))
        ),
        "Clear road consequence": implies(z3.And(expected_a_inv, expected_g_inv), z3.Implies(d0 >= 15, a1 >= -1)),
        "Non-emergency <= 3/2 consequence": implies(
            z3.And(expected_a_inv, expected_g_inv), z3.Implies(z3.Not(e0), a1 <= z3.RealVal("3/2"))
        ),
        "Target pretty view non-mutating": target_unchanged,
        "Canonical target context gate": target._operation_assumptions.refines(supervisor._operation_assumptions),
    }

    print("\nINDEPENDENT THEORY CHECKS")
    print("  Compatibility projection:", "PASS" if checks["Composition new A INV: !e -> d >= 10"] else "FAIL")
    print("  Invariant projection:", "PASS" if checks["Independent projection INV"] else "FAIL")
    print("  Supervisor liveness projection:", "PASS" if checks["Projected supervisor LIV"] else "FAIL")

    # Optional raw theory output retained intentionally. Uncomment when
    # comparing exact QE and projected liveness formulas.
    # print("  Claim 1 QE:", z3.simplify(claim1_qe))
    # print("  projected supervisor LIV obtained:", z3.simplify(projected_liv))
    # print("  projected supervisor LIV expected: !e & d <= 25")

    if not checks["Composition G INV"]:
        print("\nComposition invariant theory check: FAIL")
        # Optional mismatch details retained intentionally for debugging.
        # print("  expected:", expected_g_inv)
        # print("  raw implies expected:", implies(z3.And(raw_inv_context, raw_g_inv), expected_g_inv))
        # print("  expected implies raw:", implies(z3.And(raw_inv_context, expected_g_inv), raw_g_inv))
        # print("  counterexample:", counterexample(raw_g_inv, expected_g_inv, raw_inv_context))

    raw_quotient = target.quotient(supervisor, simplify=False)
    quotient = target.quotient(supervisor, simplify=True)
    quotient_before = quotient.to_machine_dict()
    quotient_counts = (len(quotient.a.terms), len(quotient.g.terms))
    # ------------------------------------------------------------------
    # Optional detailed debugging output retained intentionally.
    # Uncomment when inspecting raw, canonical, and stored quotient.
    # ------------------------------------------------------------------
    # print_view("RAW CAVE QUOTIENT", raw_quotient, raw=True)
    # print_canonical_view("CANONICAL OPERATION QUOTIENT", quotient)
    # print_view("STORED QUOTIENT", quotient, raw=True)
    print("\n" + "=" * 78)
    print("QUOTIENT CONTRACT")
    print("=" * 78)
    display_a, display_g = quotient.presentation_view(assumption_relative=True)
    compact_init = verified_quotient_init_candidate(quotient)
    concise_liv = GR1TermList(display_g.liv_terms())
    print(f"Inputs:  {', '.join(variable.name for variable in quotient.inputvars) or 'none'}")
    print(f"Outputs: {', '.join(variable.name for variable in quotient.outputvars) or 'none'}")
    print("\nAssumptions")
    print("\n".join(f"  {line}" for line in display_a.to_pretty_string().splitlines()))
    print("\nGuarantees")
    print("\n".join(f"  {line}" for line in compact_init.to_pretty_string().splitlines()))
    print("  INV:")
    print("    [exact generated invariant unavailable in compact form]")
    print("\n".join(f"  {line}" for line in concise_liv.to_pretty_string().splitlines()))
    # Previous concise-output notice retained intentionally for debugging.
    # print("Compact quotient display unavailable; semantic results are reported below.")
    # The existing presentation layer deliberately retains the exact large
    # quotient when no compact candidate passes SMT validation. Keep the full
    # Unicode view available for an explicit solver audit, but not in normal
    # terminal output.
    # print_view("QUOTIENT CONTRACT", quotient)
    quotient_unchanged = quotient.to_machine_dict() == quotient_before and quotient_counts == (
        len(quotient.a.terms),
        len(quotient.g.terms),
    )

    expected_q_a_init = u0 == 0
    expected_q_a_inv = z3.And(u0 >= -5, u0 <= 1, z3.Or(u0 <= -3, u0 >= -half))
    expected_q_a_liv = z3.And(u0 >= -half, u0 <= 1)
    expected_q_g_init = expected_g_init
    expected_q_g_inv = z3.And(
        z3.Implies(u0 <= -3, z3.And(a1 >= z3.RealVal("-11/2"), a1 <= z3.RealVal("-5/2"))),
        z3.Implies(z3.And(u0 >= -half, u0 <= 0), z3.And(a1 >= -1, a1 <= half)),
        z3.Implies(z3.And(u0 >= 0, u0 <= 1), z3.And(a1 >= -1, a1 <= u0 + half)),
    )
    q_display_g = _assumption_relative_guarantee_view(quotient)
    q_raw_inv = conjunction(raw_quotient.g.inv_terms())
    q_display_inv = conjunction(q_display_g.inv_terms())
    q_raw_context = shifted_assumption_context(quotient, raw_quotient.g.inv_terms())
    q_display_context = shifted_assumption_context(quotient, q_display_g.inv_terms())
    q_init_context = z3.And(
        conjunction(quotient.a.init_terms()), shifted_assumption_context(quotient, quotient.g.init_terms())
    )
    checks.update(
        {
            "Quotient A INIT": equivalent(conjunction(quotient.a.init_terms()), expected_q_a_init),
            "Quotient A INV": equivalent(conjunction(quotient.a.inv_terms()), expected_q_a_inv),
            "Quotient A LIV": _liv_contains_equivalent(quotient.a, expected_q_a_liv)
            and len(quotient.a.liv_terms()) == 1,
            "Quotient G INIT": equivalent(conjunction(quotient.g.init_terms()), expected_q_g_init, q_init_context),
            "Quotient G INV": equivalent(q_raw_inv, expected_q_g_inv, q_raw_context),
            "Quotient display G INV": equivalent(q_display_inv, expected_q_g_inv, q_display_context),
            "Quotient G LIV": _liv_contains_equivalent(q_display_g, a0 >= -1),
            "Quotient pretty view non-mutating": quotient_unchanged,
        }
    )
    if not checks["Quotient G INV"]:
        print("\nQuotient invariant theory check: FAIL")
        # Optional mismatch details retained intentionally for debugging.
        # print("  expected:", expected_q_g_inv)
        # print("  raw implies expected:", implies(z3.And(q_raw_context, q_raw_inv), expected_q_g_inv))
        # print("  expected implies raw:", implies(z3.And(q_raw_context, expected_q_g_inv), q_raw_inv))
        # print("  counterexample:", counterexample(q_raw_inv, expected_q_g_inv, q_raw_context))

    q_refines_a = quotient.refines(actuator)
    a_refines_q = actuator.refines(quotient)
    recomposed = supervisor.compose(quotient, simplify=True)
    recomposed_refines = recomposed.refines(target)
    target_refines = target.refines(recomposed)
    checks.update(
        {
            "Quotient <= actuator": q_refines_a,
            "Actuator <= quotient": a_refines_q,
            "Recomposition S || Q <= target": recomposed_refines,
            "Recomposition target <= S || Q": target_refines,
        }
    )
    print("\nREFINEMENT RESULTS")
    print("  quotient <= actuator:", q_refines_a)
    print("  actuator <= quotient:", a_refines_q)
    print("  mutually refine:", q_refines_a and a_refines_q)
    print("  supervisor || quotient <= target:", recomposed_refines)
    print("  target <= supervisor || quotient:", target_refines)
    print("  mutually refine:", recomposed_refines and target_refines)

    print("\n" + "=" * 78)
    print("THEORETICAL PREDICTIONS")
    print("=" * 78)
    for label, passed in checks.items():
        print(f"{label:<52} {'PASS' if passed else 'FAIL'}")
    print("\nOVERALL:", "PASS" if all(checks.values()) else "FAIL")
    return checks, {
        "supervisor": supervisor,
        "actuator": actuator,
        "raw_target": raw_target,
        "target": target,
        "raw_quotient": raw_quotient,
        "quotient": quotient,
        "recomposed": recomposed,
    }


if __name__ == "__main__":
    run_audit()
