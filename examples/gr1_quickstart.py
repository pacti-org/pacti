"""First-time-user tutorial for typed GR(1) contracts.

Run from an installed source checkout with::

    python examples/gr1_quickstart.py

The assertions are semantic documentation checks: a failure stops at the
operation whose documented behavior no longer holds.
"""

from pacti.iocontract import GR1IoContract, Var


def request_grant_sorts() -> dict[str, str]:
    """Return a fresh declaration map for the request/grant interface."""
    return {"request": "bool", "grant": "bool"}


def request_grant_contract() -> GR1IoContract:
    """Build a contract containing INIT, invariant, liveness, and next."""
    return GR1IoContract.from_dict(
        {
            "input_vars": ["request"],
            "output_vars": ["grant"],
            "variable_sorts": request_grant_sorts(),
            "assumptions": {
                "init": ["!request"],
                "liv": ["request"],
            },
            "guarantees": {
                "init": ["!grant"],
                "inv": ["request -> X(grant)"],
                "liv": ["grant"],
            },
        }
    )


def wire_contract(input_name: str, output_name: str) -> GR1IoContract:
    """Return a small connector used to explain composition and quotient."""
    return GR1IoContract.from_dict(
        {
            "input_vars": [input_name],
            "output_vars": [output_name],
            "variable_sorts": {input_name: "bool", output_name: "bool"},
            "assumptions": {},
            "guarantees": {"inv": [f"{output_name} = {input_name}"]},
        }
    )


def main() -> None:
    """Execute the introductory contract workflow."""
    temporal = request_grant_contract()
    assert temporal.inputvars == [Var("request")]
    assert temporal.outputvars == [Var("grant")]
    assert len(temporal.a.init_terms()) == 1
    assert len(temporal.a.liv_terms()) == 1
    assert len(temporal.g.inv_terms()) == 1
    print("Typed temporal contract:\n", temporal.to_pretty_string())

    specification = GR1IoContract.from_dict(
        {
            "input_vars": ["request"],
            "output_vars": ["grant"],
            "variable_sorts": request_grant_sorts(),
            "assumptions": {},
            "guarantees": {"inv": ["request -> grant"]},
        }
    )
    implementation = GR1IoContract.from_dict(
        {
            "input_vars": ["request"],
            "output_vars": ["grant"],
            "variable_sorts": request_grant_sorts(),
            "assumptions": {},
            "guarantees": {"inv": ["grant = request"]},
        }
    )
    assert implementation.refines(specification)
    print("Refinement certificate: implementation refines specification")

    monitoring = GR1IoContract.from_dict(
        {
            "input_vars": ["request"],
            "output_vars": ["healthy"],
            "variable_sorts": {"request": "bool", "healthy": "bool"},
            "assumptions": {},
            "guarantees": {"inv": ["healthy"]},
        }
    )
    merged = implementation.merge(monitoring)
    assert set(merged.outputvars) == {Var("grant"), Var("healthy")}
    print("Merge outputs:", [variable.name for variable in merged.outputvars])

    producer = wire_contract("request", "wire")
    consumer = wire_contract("wire", "response")
    system = producer.compose(consumer)
    assert system.inputvars == [Var("request")]
    assert system.outputvars == [Var("response")]
    assert Var("wire") not in system.a.vars + system.g.vars
    print("Composition hides the internal variable 'wire'.")

    residual = system.quotient(producer)
    assert residual.inputvars == [Var("wire")]
    assert residual.outputvars == [Var("response")]
    assert producer.compose(residual).refines(system)
    print("Quotient recovers a residual from wire to response.")

    restored = GR1IoContract.from_dict(system.to_dict())
    assert restored.refines(system)
    assert system.refines(restored)
    print("Serialization round trip preserves the contract.")


if __name__ == "__main__":
    main()
