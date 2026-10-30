"""Full-bucket GR(1) audit for an increasing-in-distance AEB supervisor.

Run with::

    PYTHONPATH=src .venv/bin/python examples/gr1_aeb_increasing_distance.py

The example intentionally prints the canonical, stored, and Unicode views.
All hand formulas below are used only as SMT oracles; they are never installed
in a contract and do not alter CAVE or quotient behavior.
"""

from __future__ import annotations

from typing import Dict, Iterable, Optional

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
    return z3.And(*[term.core.expr for term in terms])


def equivalent(left: z3.BoolRef, right: z3.BoolRef, context: z3.BoolRef = z3.BoolVal(True)) -> bool:
    solver = z3.Solver()
    solver.add(context, left != right)
    return solver.check() == z3.unsat


def implies(left: z3.BoolRef, right: z3.BoolRef) -> bool:
    solver = z3.Solver()
    solver.add(left, z3.Not(right))
    return solver.check() == z3.unsat


def model_for(left: z3.BoolRef, right: z3.BoolRef, context: z3.BoolRef = z3.BoolVal(True)) -> Optional[z3.ModelRef]:
    solver = z3.Solver()
    solver.add(context, left != right)
    return solver.model() if solver.check() == z3.sat else None


def make_supervisor() -> GR1IoContract:
    return GR1IoContract.from_dict(
        {
            "input_vars": ["d", "e"],
            "output_vars": ["u"],
            "variable_sorts": {"d": "real", "e": "bool", "u": "real"},
            "assumptions": {
                "init": ["d >= 20", "!e"],
                "inv": ["d >= 0", "d <= 30", "d <= 8 -> e", "d >= 20 -> !e"],
                "liv": ["d >= 20"],
            },
            "guarantees": {
                "init": ["u = 0"],
                "inv": ["u >= -5", "u <= d/10 - 1", "e -> u <= -3", "!e -> u >= -1/2"],
                "liv": ["u >= -1/2"],
            },
        },
        simplify=False,
    )


def make_actuator() -> GR1IoContract:
    return GR1IoContract.from_dict(
        {
            "input_vars": ["u"],
            "output_vars": ["a"],
            "variable_sorts": {"u": "real", "a": "real"},
            "assumptions": {
                "init": ["u = 0"],
                "inv": ["-5 <= u", "u <= 3/2"],
                "liv": ["u >= -1/2"],
            },
            "guarantees": {
                "init": ["a = 0"],
                "inv": ["u - 1/2 <= X(a)", "X(a) <= u + 1/2"],
                "liv": ["a >= -1"],
            },
        },
        simplify=False,
    )


def shifted_context(contract: GR1IoContract, terms: Iterable[GR1Term]) -> z3.BoolRef:
    return _shifted_inv_guard_for_cores(contract.a.inv_terms(), [term.core for term in terms])


def contains_liv(bucket: GR1TermList, expected: z3.BoolRef) -> bool:
    return any(equivalent(term.core.expr, expected) for term in bucket.liv_terms())


def termlists_equivalent(left: GR1TermList, right: GR1TermList) -> bool:
    """Compare safety conjunctions and match separate liveness cores one-to-one."""
    if not equivalent(conjunction(left.init_terms()), conjunction(right.init_terms())):
        return False
    if not equivalent(conjunction(left.inv_terms()), conjunction(right.inv_terms())):
        return False
    left_liv, right_liv = left.liv_terms(), right.liv_terms()
    if len(left_liv) != len(right_liv):
        return False

    def match(position: int, used: set[int]) -> bool:
        if position == len(left_liv):
            return True
        return any(
            index not in used
            and equivalent(left_liv[position].core.expr, candidate.core.expr)
            and match(position + 1, used | {index})
            for index, candidate in enumerate(right_liv)
        )

    return match(0, set())


def composition_presentation_candidates() -> tuple[GR1TermList, GR1TermList]:
    """Return paper-derived display candidates; the library SMT-verifies them."""
    assumptions = GR1TermList.from_bucket_strings(
        inv=["d >= 0", "d <= 30", "d <= 8 -> e", "d >= 20 -> !e", "!e -> d <= 25"],
        variable_sorts={"d": "real", "e": "bool", "a": "real"},
    )
    guarantees = GR1TermList.from_bucket_strings(
        init=["a = 0", "-1/2 <= X(a)", "X(a) <= 1/2"],
        inv=[
            "-11/2 <= X(a)",
            "X(a) <= d/10 - 1/2",
            "e -> X(a) <= -5/2",
            "!e -> X(a) >= -1",
        ],
        variable_sorts={"d": "real", "e": "bool", "a": "real"},
    )
    return assumptions, guarantees


def quotient_presentation_candidates() -> tuple[GR1TermList, GR1TermList]:
    """Return compact quotient candidates, accepted only after contextual proof."""
    assumptions = GR1TermList.from_bucket_strings(
        inv=["-5 <= u", "u <= 3/2", "u <= -3 | u >= -1/2"],
        variable_sorts={"u": "real", "a": "real"},
    )
    guarantees = GR1TermList.from_bucket_strings(
        init=["a = 0", "-1/2 <= X(a)", "X(a) <= 1/2"],
        inv=[
            "u <= -3 -> (-11/2 <= X(a) & X(a) <= u + 1/2)",
            "u >= -1/2 -> (a >= -1 & -1 <= X(a) & X(a) <= u + 1/2)",
        ],
        variable_sorts={"u": "real", "a": "real"},
    )
    return assumptions, guarantees


def verified_quotient_init_candidate(
    contract: GR1IoContract,
    candidate: GR1TermList,
) -> GR1TermList:
    """Certify a compact INIT view against the canonical quotient bucket."""
    exact_terms = contract._operation_guarantees.init_terms()
    candidate_terms = candidate.init_terms()
    context = z3.And(
        conjunction(contract._operation_assumptions.init_terms()),
        shifted_context(contract, exact_terms + candidate_terms),
    )
    if not equivalent(conjunction(exact_terms), conjunction(candidate_terms), context):
        raise AssertionError("quotient INIT presentation candidate is not contextually equivalent")
    return GR1TermList(candidate_terms)


def print_three_views(
    name: str,
    contract: GR1IoContract,
    candidates: Optional[tuple[GR1TermList, GR1TermList]] = None,
    omit_verbose_guarantee_init: bool = False,
) -> bool:
    before = contract.to_dict()
    # ------------------------------------------------------------------
    # Optional detailed debugging output retained intentionally.
    # Uncomment when inspecting canonical and stored representations.
    # ------------------------------------------------------------------
    # print(f"\n{'=' * 78}\n{name}: CANONICAL\n{'=' * 78}\n{contract.canonical_debug_dump()}")
    # print(f"\n{name}: STORED/REDUCED\n{'-' * 78}\n{contract.debug_dump()}")
    candidate_a, candidate_g = candidates or (None, None)
    if omit_verbose_guarantee_init:
        display_a, display_g = contract.presentation_view(
            candidate_assumptions=candidate_a,
            candidate_guarantees=candidate_g,
            assumption_relative=True,
        )
        verified_init = verified_quotient_init_candidate(contract, candidate_g or GR1TermList())
        concise_display_g = GR1TermList(verified_init.init_terms() + display_g.inv_terms() + display_g.liv_terms())
        print(f"\n{'=' * 78}\n{name}\n{'=' * 78}")
        print(f"Inputs:  {', '.join(variable.name for variable in contract.inputvars) or 'none'}")
        print(f"Outputs: {', '.join(variable.name for variable in contract.outputvars) or 'none'}")
        print("\nAssumptions")
        print("\n".join(f"  {line}" for line in display_a.to_pretty_string().splitlines()))
        print("\nGuarantees")
        print("\n".join(f"  {line}" for line in concise_display_g.to_pretty_string().splitlines()))
        # Previous omission marker retained intentionally for debugging the
        # exact generated boundary before a certified candidate is available.
        # print("  INIT:")
        # print("    [exact generated condition omitted from concise output]")
        # The exact presentation remains available for a detailed boundary
        # audit; it is intentionally retained rather than deleted.
        # print(contract.to_pretty_string(
        #     assumption_relative=True,
        #     candidate_assumptions=candidate_a,
        #     candidate_guarantees=candidate_g,
        # ))
    else:
        print(
            f"\n{'=' * 78}\n{name}\n{'=' * 78}\n"
            f"{contract.to_pretty_string(assumption_relative=True, candidate_assumptions=candidate_a, candidate_guarantees=candidate_g)}"
        )
    return contract.to_dict() == before


def audit() -> tuple[Dict[str, bool], Dict[str, GR1IoContract]]:
    supervisor, actuator = make_supervisor(), make_actuator()
    raw_target = supervisor.compose(actuator, simplify=False)
    target = supervisor.compose(actuator, simplify=True)
    raw_q = target.quotient(supervisor, simplify=False)
    quotient = target.quotient(supervisor, simplify=True)

    unchanged = {
        "SUPERVISOR": print_three_views("SUPERVISOR", supervisor, (supervisor.a, supervisor.g)),
        "ACTUATOR": print_three_views("ACTUATOR", actuator, (actuator.a, actuator.g)),
        "COMPOSITION": print_three_views("COMPOSITION", target, composition_presentation_candidates()),
        "QUOTIENT": print_three_views(
            "QUOTIENT",
            quotient,
            quotient_presentation_candidates(),
            omit_verbose_guarantee_init=True,
        ),
    }

    d0, u0, a0, a1 = z3.Reals("d_0 u_0 a_0 a_1")
    e0 = z3.Bool("e_0")
    half = z3.RealVal("1/2")
    h = z3.And(z3.Implies(e0, d0 >= -40), z3.Implies(z3.Not(e0), d0 >= 5))
    a_init = z3.And(d0 >= 20, z3.Not(e0))
    a_inv = z3.And(
        d0 >= 0, d0 <= 30, z3.Implies(d0 <= 8, e0), z3.Implies(d0 >= 20, z3.Not(e0)), z3.Implies(z3.Not(e0), d0 <= 25)
    )
    g_init = z3.And(a0 == 0, a1 >= -half, a1 <= half)
    g_inv = z3.And(
        a1 >= z3.RealVal("-11/2"),
        a1 <= d0 / 10 - half,
        z3.Implies(e0, a1 <= z3.RealVal("-5/2")),
        z3.Implies(z3.Not(e0), a1 >= -1),
    )
    compact_raw_inv = z3.And(h, g_inv)

    compatibility = z3.Tactic("qe")(
        z3.ForAll([u0], z3.Implies(conjunction(supervisor.g.inv_terms()), conjunction(actuator.a.inv_terms())))
    ).as_expr()
    projected_s_liv = _project_liv_terms(supervisor.g.liv_terms(), supervisor.g, [Var("u")])[0].core.expr
    projected_a_liv = z3.Tactic("qe")(
        z3.Exists([u0], z3.And(conjunction(supervisor.g.inv_terms()), a0 >= -1))
    ).as_expr()
    direct_inv_projection = z3.Tactic("qe")(
        z3.Exists([u0], z3.And(conjunction(supervisor.g.inv_terms()), conjunction(actuator.g.inv_terms())))
    ).as_expr()
    display_g = _assumption_relative_guarantee_view(target)
    raw_inv = conjunction(raw_target.g.inv_terms())
    raw_inv_guard = shifted_context(target, raw_target.g.inv_terms())
    display_inv_guard = shifted_context(target, display_g.inv_terms())

    serialized = target.to_dict()
    restored = GR1IoContract.from_dict(serialized)
    restored_q = restored.quotient(supervisor, simplify=True)
    checks: Dict[str, bool] = {
        "Raw A INIT": equivalent(conjunction(raw_target.a.init_terms()), a_init),
        "New compatibility !e -> d <= 25": equivalent(compatibility, z3.Or(e0, d0 <= 25)),
        "A INV": equivalent(conjunction(target._operation_assumptions.inv_terms()), a_inv),
        "A LIV": len(target._operation_assumptions.liv_terms()) == 1
        and contains_liv(target._operation_assumptions, d0 >= 20),
        "Raw projected GF supervisor liveness": equivalent(projected_s_liv, z3.And(z3.Not(e0), d0 >= 5)),
        "Raw projected actuator liveness": equivalent(projected_a_liv, z3.And(a0 >= -1, h)),
        "Raw G INIT": all(
            implies(conjunction(raw_target.g.init_terms()), fact)
            for fact in (a0 == 0, a1 >= -half, a1 <= half, d0 >= 10, z3.Not(e0))
        ),
        "Display G INIT": equivalent(
            conjunction(display_g.init_terms()), g_init, z3.And(a_init, shifted_context(target, display_g.init_terms()))
        ),
        "Raw G INV exact compact equivalence": equivalent(direct_inv_projection, compact_raw_inv),
        "Canonical G INV under assumptions": equivalent(raw_inv, g_inv, raw_inv_guard),
        "Display G INV under assumptions": equivalent(conjunction(display_g.inv_terms()), g_inv, display_inv_guard),
        "Display GF(a >= -1)": len(display_g.liv_terms()) == 1
        and equivalent(display_g.liv_terms()[0].core.expr, a0 >= -1, a_inv),
        "Close-obstacle consequence": implies(z3.And(a_inv, g_inv), z3.Implies(d0 <= 8, a1 <= z3.RealVal("-5/2"))),
        "Clear-road consequence": implies(z3.And(a_inv, g_inv), z3.Implies(d0 >= 20, a1 >= -1)),
        "Non-emergency X(a) <= 2": implies(z3.And(a_inv, g_inv), z3.Implies(z3.Not(e0), a1 <= 2)),
        "Pretty-print non-mutation": all(unchanged.values()),
        "Serialization stored preservation": termlists_equivalent(target.a, restored.a)
        and termlists_equivalent(target.g, restored.g),
        "Serialization canonical preservation": termlists_equivalent(
            target._operation_assumptions, restored._operation_assumptions
        )
        and termlists_equivalent(target._operation_guarantees, restored._operation_guarantees),
        "Round-trip quotient A": termlists_equivalent(
            quotient._operation_assumptions, restored_q._operation_assumptions
        ),
        "Round-trip quotient G": termlists_equivalent(quotient._operation_guarantees, restored_q._operation_guarantees),
    }

    recomposed = supervisor.compose(quotient, simplify=True)
    checks["Recomposition S || Q <= target"] = recomposed.refines(target)
    checks["Recomposition target <= S || Q"] = target.refines(recomposed)

    print("\nPREDICTION TABLE")
    print("-" * 78)
    for label, passed in checks.items():
        print(f"{label:<58} {'PASS' if passed else 'FAIL'}")
    # ------------------------------------------------------------------
    # Optional detailed debugging output retained intentionally.
    # Uncomment when inspecting every canonical quotient bucket and core.
    # ------------------------------------------------------------------
    # print("\nQUOTIENT BUCKET SUMMARY")
    # for side, bucket in (("A", quotient._operation_assumptions), ("G", quotient._operation_guarantees)):
    #     for tag, terms in (
    #         ("INIT", bucket.init_terms()),
    #         ("INV", bucket.inv_terms()),
    #         ("LIV", bucket.liv_terms()),
    #     ):
    #         print(f"  {side}_Q {tag}: {len(terms)} term(s)")
    #         for term in terms:
    #             print("   ", z3.simplify(term.core.expr))

    if not checks["Canonical G INV under assumptions"]:
        print("\nCanonical composition INV mismatch model:", model_for(raw_inv, g_inv, raw_inv_guard))
    if not checks["Recomposition S || Q <= target"] or not checks["Recomposition target <= S || Q"]:
        left = conjunction((target.g | recomposed.a).inv_terms())
        right = conjunction((recomposed.g | recomposed.a).inv_terms())
        print("\nRecomposition is not mutually refining; no library semantics were changed.")
        print("  failing canonical bucket: target <= R, guarantee INV")
        print("  counterexample:", model_for(left, right))
        print("  classification: current-state quotient boundary effect")
    return checks, {
        "supervisor": supervisor,
        "actuator": actuator,
        "raw_target": raw_target,
        "target": target,
        "raw_quotient": raw_q,
        "quotient": quotient,
        "recomposed": recomposed,
    }


if __name__ == "__main__":
    audit()
