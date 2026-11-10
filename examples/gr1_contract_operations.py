"""Executable end-to-end demonstration of GR(1) contract operations.

Run from the repository root with::

    PYTHONPATH=src .venv/bin/python examples/gr1_contract_operations.py

The assertions make this both a readable example and a lightweight integration
test.  A failed operation stops the script at the corresponding assertion.
"""

from __future__ import annotations

import json

import z3

from pacti.iocontract import Var
from pacti.iocontract.gr1_iocontract import (
    GR1Behavior,
    GR1CoreFormula,
    GR1IoContract,
    GR1TermList,
)


def heading(title: str) -> None:
    """Print a visible section heading."""
    print(f"\n{'=' * 8} {title} {'=' * 8}")


def equivalent(left: z3.BoolRef, right: z3.BoolRef) -> bool:
    """Return whether two Boolean Z3 formulas are logically equivalent."""
    solver = z3.Solver()
    solver.add(left != right)
    return solver.check() == z3.unsat


def core(expr: z3.BoolRef) -> GR1CoreFormula:
    """Wrap a manually flattened Z3 formula for the QE examples."""
    return GR1CoreFormula.of_expr(
        text=str(expr),
        vars=[Var(variable.decl().name()) for variable in z3.z3util.get_vars(expr)],
        expr=expr,
    )


def parsing_behavior_renaming_and_round_trip() -> None:
    """Exercise typed parsing, nested next, behavior checks, and persistence."""
    heading("typed parsing")
    source = {
        "input_vars": ["request", "temperature", "counter"],
        "output_vars": ["grant"],
        "variable_sorts": {
            "request": "bool",
            "temperature": "real",
            "counter": "int",
            "grant": "bool",
        },
        "assumptions": {
            "init": ["temperature >= 0 & counter = 0"],
            "inv": ["temperature <= 100", "X(counter) = counter + 1"],
            "liv": ["request"],
        },
        "guarantees": {
            "init": ["!grant"],
            "inv": ["request -> X(grant)"],
            "liv": ["grant"],
        },
    }
    contract = GR1IoContract.from_dict(source, simplify=False)
    parsed = contract.g.inv_terms()[0].core
    print(contract.to_pretty_string())

    # ------------------------------------------------------------------
    # Optional detailed debugging output retained intentionally.
    # Uncomment when inspecting parsed, flattened, and internal forms.
    # ------------------------------------------------------------------
    # print("user formula:   ", parsed.text)
    # print("flattened Z3:   ", parsed.expr)
    # print("internal vars:  ", [variable.name for variable in parsed.vars])
    assert {variable.name for variable in parsed.vars} == {"request_0", "grant_1"}

    heading("lasso behavior")
    guarantee_behavior = GR1Behavior(
        states=[
            {"request": True, "temperature": 20, "counter": 0, "grant": False},
            {"request": True, "temperature": 20, "counter": 1, "grant": True},
        ],
        loop_start=1,
    )
    assert contract.g.contains_behavior(guarantee_behavior)
    print("the ultimately-periodic behavior satisfies all guarantees")

    heading("structural renaming")
    renamed = contract.rename_variables([("grant", "ack")])
    renamed_core = renamed.g.inv_terms()[0].core
    print(renamed.to_pretty_string())

    # Optional raw renamed forms retained intentionally for debugging.
    # print("renamed formula:", renamed_core.text)
    # print("renamed Z3:    ", renamed_core.expr)
    assert renamed.outputvars == [Var("ack")]
    assert {variable.name for variable in renamed_core.vars} == {"request_0", "ack_1"}

    heading("serialization round trip")
    serialized = renamed.to_dict()
    restored = GR1IoContract.from_dict(serialized, simplify=False)
    restored_expr = restored.g.inv_terms()[0].core.expr
    assert restored_expr is not None and renamed_core.expr is not None
    assert equivalent(restored_expr, renamed_core.expr)
    print("serialization preserves the renamed contract semantics: PASS")

    # Optional machine serialization retained intentionally for debugging.
    # print(json.dumps(serialized, indent=2, sort_keys=True))


def refinement_and_relaxation() -> None:
    """Exercise universal refinement and existential relaxation elimination."""
    p_0, q_0 = z3.Bools("p_0 q_0")
    target = GR1TermList.from_bucket_formulas(inv=[core(p_0), core(p_0 == q_0)])

    heading("relaxation")
    relaxed, _ = target.elim_vars_by_relaxing(
        context=GR1TermList(),
        vars_to_elim=[Var("p")],
        simplify=False,
        tactics_order=[],
    )
    relaxed_expr = relaxed.inv_terms()[0].core.expr
    assert relaxed_expr is not None and equivalent(relaxed_expr, q_0)
    print("existential relaxation matches q: PASS")

    # Optional raw QE result retained intentionally for debugging.
    # print("exists p. (p & (p = q))  ==> ", relaxed_expr)

    heading("liveness-index refinement")
    liveness_target = GR1TermList.from_bucket_formulas(liv=[core(p_0)])
    liveness_context = GR1TermList.from_bucket_formulas(liv=[core(z3.Or(p_0, q_0))])
    refined, _ = liveness_target.elim_vars_by_refining(
        context=liveness_context,
        vars_to_elim=[Var("p")],
        simplify=False,
        tactics_order=[],
    )
    refined_expr = refined.inv_terms()[0].core.expr
    assert refined_expr is not None and equivalent(refined_expr, z3.Not(q_0))
    print("selected liveness support produces the expected invariant: PASS")

    # Optional raw refinement result retained intentionally for debugging.
    # print("selected liveness support produces INV:", refined_expr)


def composition_and_quotient() -> None:
    """Exercise contract-level composition, hiding, quotient, and round-trip."""
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

    heading("composition")
    composed = producer.compose(consumer, simplify=True)
    assert composed.inputvars == [Var("q")]
    assert composed.outputvars == [Var("r")]
    assert Var("p") not in composed.a.vars + composed.g.vars
    expected = z3.Bool("q_0") == z3.Bool("r_1")
    composed_expr = composed.g.inv_terms()[0].core.expr
    assert composed_expr is not None and equivalent(composed_expr, expected)
    print(composed.to_pretty_string())
    print("composition hides the shared variable p: PASS")

    # ------------------------------------------------------------------
    # Optional detailed debugging output retained intentionally.
    # Uncomment when inspecting the hidden-variable result and raw liveness.
    # ------------------------------------------------------------------
    # print("external interface:", composed.inputvars, "->", composed.outputvars)
    # print("hidden p gives:   ", composed_expr)
    # print("liveness terms:   ", composed.g.to_bucket_dict()["liv"])

    heading("quotient")
    quotient = composed.quotient(producer, simplify=True)
    restored = GR1IoContract.from_dict(quotient.to_dict(), simplify=False)
    assert quotient.inputvars == [Var("p")]
    assert quotient.outputvars == [Var("r")]
    assert len(quotient.a.liv_terms()) == 1
    assert equivalent(quotient.a.liv_terms()[0].core.expr, z3.Bool("p_0"))
    assert len(quotient.g.inv_terms()) == 1
    assert equivalent(
        quotient.g.inv_terms()[0].core.expr,
        z3.Bool("p_0") == z3.Bool("r_1"),
    )
    assert len(quotient.g.liv_terms()) == 1
    assert equivalent(quotient.g.liv_terms()[0].core.expr, z3.Bool("r_0"))
    assert restored.a.refines(quotient.a) and quotient.a.refines(restored.a)
    assert restored.g.refines(quotient.g) and quotient.g.refines(restored.g)
    assert producer.compose(quotient, simplify=True).refines(composed)
    print(quotient.to_pretty_string())
    print("quotient round trip preserves both assumption and guarantee semantics")

    # Optional raw quotient buckets retained intentionally for debugging.
    # print("recovered interface:", quotient.inputvars, "->", quotient.outputvars)
    # print("recovered guarantees:", quotient.g.to_bucket_dict())


def main() -> None:
    """Run every integration scenario and report success."""
    parsing_behavior_renaming_and_round_trip()
    refinement_and_relaxation()
    composition_and_quotient()
    heading("success")
    print("All GR(1) operation checks passed.")


if __name__ == "__main__":
    main()
