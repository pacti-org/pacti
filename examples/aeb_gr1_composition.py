"""Exact upper-envelope velocity AEB audit using the repository's GR(1) algebra.

Run:
    python examples/aeb_gr1_composition.py --no-report

Without ``--no-report``, the complete output is also written to
``examples/aeb_gr1_composition_output.txt``. The no-report mode is convenient
for a clean first-time-user checkout and CI.

Example architecture
--------------------

    (d, URG, WRN) ---> C_S ---> {u, MOV, DCL, STP} ---> C_V ---> v

The complete supervisor/vehicle interface is internal to composition.  The
composed system therefore exposes only ``(d, URG, WRN) -> v``.

The quotient here uses that composition as its target: C_COMP / C_V.
For the manuscript's safety target C_T, clearance predictor C_D, and quotient
C_T / C_V, run aeb_predicted_clearance.py, which reuses these component factories.

The vehicle requires the mode-indexed command protocol described in
``make_vehicle``.  Universal compatibility generates the clear-road
environment condition ``d >= 20``.

The vehicle tracks the command with one-step error at most 1/2 m/s and is
restricted to nonnegative forward longitudinal speed.

The PDF/source material supplies the qualitative AEB/GR(1) motivation.  The
numerical quantitative envelopes used here are parameters of this contract
example, not claimed numerical parameters of the reference implementation.

Private GR(1) helpers are used only for observation and finite-window
diagnostics.  Temporary QE observers delegate unchanged arguments to the
original functions.  No candidate formula is installed in any contract.
"""

from __future__ import annotations

from typing import Any

import argparse
import inspect
import sys
from contextlib import ExitStack, contextmanager, redirect_stdout
from pathlib import Path
from textwrap import indent
from unittest.mock import patch

import z3
from z3.z3util import get_vars

from pacti.iocontract import Var
from pacti.iocontract import gr1_iocontract as gr1

# =============================================================================
# Declarations
# =============================================================================

SORTS = {name: "bool" for name in ("URG", "WRN", "MOV", "DCL", "STP")}
SORTS.update({name: "real" for name in ("d", "u", "v")})

MODES = ("MOV", "DCL", "STP")
BUCKETS = ("init", "inv", "liv")
_SECTION_RULE = "=" * 72  # noqa: WPS432
_PERFORMANCE_RULE = "#" * 80  # noqa: WPS432

# Finalized measurements from one warm-up followed by 10 measured runs. These
# values are reported by the example; normal execution does not rerun timing.
FINAL_AEB_PERFORMANCE: dict[str, Any] = {
    "measured_runs": 10,
    "composition": {"end_to_end_seconds": 1.627, "cave_seconds": 1.093},
    "quotient": {"end_to_end_seconds": 4.262, "cave_seconds": 2.268},
    "combined": {"end_to_end_seconds": 5.938, "cave_seconds": 3.362},
    "cave": {
        "invocations": 7,
        "refinement_invocations": 3,
        "relaxation_invocations": 4,
        "solver_checks": 239,
        "optimize_checks": 44,
        "qe2_applications": 15,
        "synthetic_candidates": 6,
        "support_candidates": 5,
        "max_quantified_atoms": 11,
        "max_indexed_variables": 19,
        "max_next_depth": 2,
    },
}


# =============================================================================
# Output helper
# =============================================================================


class Tee:
    """Mirror stdout to both the terminal and a persistent text report."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()
        return len(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def _print_final_performance() -> None:
    """Print finalized benchmark measurements without rerunning the benchmark."""
    data = FINAL_AEB_PERFORMANCE
    cave = data["cave"]
    print("\n" + _PERFORMANCE_RULE)
    print("COMPUTATIONAL PERFORMANCE")
    print(_PERFORMANCE_RULE)
    print(f"\nFinal benchmark over {data['measured_runs']} measured runs:")
    for label, key in (
        ("Composition", "composition"),
        ("Quotient", "quotient"),
        ("Composition + quotient", "combined"),
    ):
        timing = data[key]
        print(f"\n{label}:")
        print(f"median end-to-end time       : {timing['end_to_end_seconds']:.3f} s")
        print(f"median cumulative CAVE time  : {timing['cave_seconds']:.3f} s")
    print("\nCAVE execution statistics:")
    print(f"top-level CAVE invocations   : {cave['invocations']}")
    print(f"  refinement                 : {cave['refinement_invocations']}")
    print(f"  relaxation                 : {cave['relaxation_invocations']}")
    print(f"Solver.check() calls         : {cave['solver_checks']}")
    print(f"Optimize.check() calls       : {cave['optimize_checks']}")
    print(f"qe2 applications             : {cave['qe2_applications']}")
    print(f"synthetic candidates         : {cave['synthetic_candidates']}")
    print(f"fixed-support candidates     : {cave['support_candidates']}")
    print(f"max quantified atoms         : {cave['max_quantified_atoms']}")
    print(f"max indexed variables        : {cave['max_indexed_variables']}")
    print(f"max NEXT depth               : {cave['max_next_depth']}")
    print(
        "\nEnd-to-end time measures the complete Pacti composition and quotient\n"
        "operations. Cumulative CAVE time measures only time spent inside CAVE\n"
        "during those operations. These finalized values are reported, not timed,\n"
        "during normal example execution."
    )


# =============================================================================
# Basic helpers
# =============================================================================


def parsed(text):
    """Parse one GR(1) core using the example's declared sorts."""
    return gr1.parse_gr1_core(text, SORTS).expr


def terms(bucket, tag):
    """Return the terms of one INIT/INV/LIV bucket."""
    return getattr(bucket, tag + "_terms")()


def conjunction(items):
    """Conjoin a collection of GR(1) terms."""
    return z3.And(*[term.core.expr for term in items])


def heading(title):
    print("\n" + "#" * 80)
    print(title)
    print("#" * 80)


def formula(expr):
    """Exact SMT-LIB representation without decimal rounding."""
    return expr.sexpr()


def print_terms(items, raw=False):
    if not items:
        print("  True (empty bucket)")
        return

    for index, term in enumerate(items, 1):
        expr = term.core.raw_expr if raw and term.core.raw_expr is not None else term.core.expr
        print(f"  [{index}] {formula(expr)}")


def print_contract(title, contract, original=False):
    """Print raw, canonical, simplified, and pretty contract buckets."""

    heading(title)

    print("Inputs:", ", ".join(v.name for v in contract.inputvars))
    print("Outputs:", ", ".join(v.name for v in contract.outputvars))

    for side, canonical, stored in (
        (
            "ASSUMPTION",
            contract._operation_assumptions,
            contract.a,
        ),
        (
            "GUARANTEE",
            contract._operation_guarantees,
            contract.g,
        ),
    ):
        for tag in BUCKETS:
            print(f"\n{title} {side} {tag.upper()}")

            if original:
                print("Original formula cores " "(separate G/GF wrappers follow bucket tags):")
                for term in terms(canonical, tag):
                    print(" ", term.core.text)

            print("Raw returned cores / before redundancy removal " "(raw QE where retained):")
            print_terms(terms(canonical, tag), raw=True)

            print("Canonical operational cores, flattened with time indices:")
            print_terms(terms(canonical, tag))

            print("Simplified / after library redundancy removal, flattened:")
            print_terms(terms(stored, tag))

            print("Library pretty representation of this stored bucket:")
            print(gr1.GR1TermList(terms(stored, tag)).to_pretty_string())


# =============================================================================
# Component contracts
# =============================================================================


def make_supervisor():
    """Safety supervisor: environment -> modes and velocity command."""

    return gr1.GR1IoContract.from_dict(
        {
            "input_vars": [
                "d",
                "URG",
                "WRN",
            ],
            "output_vars": [
                "MOV",
                "DCL",
                "STP",
                "u",
            ],
            "variable_sorts": SORTS,
            # -------------------------------------------------------------
            # Environment assumptions
            # -------------------------------------------------------------
            "assumptions": {
                "init": [
                    "20 <= d",
                    "d <= 30",
                    "!URG",
                    "!WRN",
                ],
                "inv": [
                    "0 <= d",
                    "d <= 30",
                    # Urgent region
                    "d <= 10 -> (URG & !WRN)",
                    # Warning region
                    "(10 < d & d <= 15) -> (WRN & !URG)",
                    # Clear region
                    "d > 15 -> (!URG & !WRN)",
                ],
                # The environment becomes simultaneously clear infinitely often.
                "liv": [
                    "!URG & !WRN",
                ],
            },
            # -------------------------------------------------------------
            # Supervisor guarantees
            # -------------------------------------------------------------
            "guarantees": {
                "init": [
                    "MOV",
                    "!DCL",
                    "!STP",
                    # At initialization d is clear and the command lies on
                    # the lower clear-road envelope.
                    "u = d/10",
                ],
                "inv": [
                    # Exactly one supervisory mode.
                    ("(MOV | DCL | STP)" " & !(MOV & DCL)" " & !(MOV & STP)" " & !(DCL & STP)"),
                    # -----------------------------------------------------
                    # GR(1) supervisory mode transitions
                    # -----------------------------------------------------
                    # Urgent hazard -> emergency-stop mode.
                    "(URG & !WRN) -> X(STP)",
                    # Warning while moving/decelerating -> DCL.
                    ("(WRN & !URG & (MOV | DCL))" " -> X(DCL)"),
                    # Conservative completion:
                    # if already stopped during warning, remain stopped.
                    ("(WRN & !URG & STP)" " -> X(STP)"),
                    # Clear road -> normal movement.
                    "!(URG | WRN) -> X(MOV)",
                    # -----------------------------------------------------
                    # Quantitative velocity-command semantics
                    # -----------------------------------------------------
                    # Global physical command range.
                    "0 <= u",
                    "u <= 6",
                    "u <= d/5",
                    # Commands are indexed by the next supervisory mode.
                    "X(STP) -> u = 0",
                    "X(DCL) -> u <= 3",
                    "X(MOV) -> u >= d/10",
                ],
                # Preserve the supervisor's GR(1) liveness objective.
                "liv": [
                    "MOV",
                ],
            },
        },
        simplify=False,
    )


def make_vehicle():
    """Vehicle response: supervisor command/modes -> realized forward speed."""

    return gr1.GR1IoContract.from_dict(
        {
            "input_vars": [
                "u",
                "MOV",
                "DCL",
                "STP",
            ],
            "output_vars": [
                "v",
            ],
            "variable_sorts": SORTS,
            "assumptions": {
                "init": [
                    "2 <= u",
                    "u <= 3",
                ],
                "inv": [
                    "0 <= u",
                    "u <= 6",
                    "X(STP) -> u = 0",
                    "X(DCL) -> u <= 3",
                    "X(MOV) -> u >= 2",
                ],
                "liv": [
                    "MOV",
                ],
            },
            "guarantees": {
                "init": [
                    "v = u",
                ],
                "inv": [
                    # Forward-driving abstraction: no reverse speed.
                    "v >= 0",
                    # One-step bounded tracking error.
                    "u - 1/2 <= X(v)",
                    "X(v) <= u + 1/2",
                ],
                "liv": [],
            },
        },
        simplify=False,
    )


# =============================================================================
# QE observation
# =============================================================================


@contextmanager
def observe_qe():
    """Observe actual refinement/relaxation QE without changing results."""

    events = []

    def observer(name):
        original = getattr(gr1, name)

        def wrapped(target, context, variables):
            frame = inspect.currentframe()
            assert frame is not None and frame.f_back is not None
            caller = frame.f_back

            location = caller.f_code.co_name

            term = caller.f_locals.get(
                "term",
                caller.f_locals.get("target"),
            )

            support = caller.f_locals.get("support")

            atoms = gr1._z3_atoms_for_vars(
                variables,
                target,
                context,
            )

            universal = name == "_qe_forall_refinement"

            if universal:
                body = z3.Implies(
                    context,
                    target,
                )
            else:
                body = z3.And(
                    context,
                    target,
                )

            if atoms:
                quantified = z3.ForAll(atoms, body) if universal else z3.Exists(atoms, body)
            else:
                quantified = body

            result = original(
                target,
                context,
                variables,
            )

            events.append(
                {
                    "kind": ("refinement" if universal else "relaxation"),
                    "caller": location,
                    "tag": (term.tag.value if term is not None else "LIV"),
                    "support": support,
                    "atoms": atoms,
                    "before": quantified,
                    "after": result,
                }
            )

            del caller
            return result

        return wrapped

    with ExitStack() as stack:
        for name in (
            "_qe_forall_refinement",
            "_qe_exists_relaxation",
        ):
            stack.enter_context(
                patch.object(
                    gr1,
                    name,
                    observer(name),
                )
            )

        yield events


def print_events(events):
    for index, event in enumerate(events, 1):
        print(f"\nBound {index}: " f"{event['kind']} " f"{event['tag']} " f"via {event['caller']}")

        print(
            "Quantified atoms:",
            ", ".join(str(atom) for atom in event["atoms"]) or "none",
        )

        if event["support"] is not None:
            print(
                "Liveness support:",
                event["support"].core.text,
            )

        print(
            "Before QE:",
            formula(event["before"]),
        )

        print(
            "Exact library QE result:",
            formula(event["after"]),
        )


# =============================================================================
# SMT implication/equivalence diagnostics
# =============================================================================


def implication(label, left, right):
    """Check left => right and print a concrete model on failure."""

    solver = z3.Solver()

    solver.add(
        left,
        z3.Not(right),
    )

    status = solver.check()

    passed = status == z3.unsat

    print(f"{label}: " f"{passed if status != z3.unknown else 'Unknown'}")

    if status != z3.unsat:
        print(
            "Exact attempted implication:",
            formula(
                z3.Implies(
                    left,
                    right,
                )
            ),
        )

        if status == z3.sat:
            print(
                "Counterexample:",
                solver.model(),
            )
        else:
            print(
                "Unknown reason:",
                solver.reason_unknown(),
            )

    return passed


# =============================================================================
# Candidate composition checks
# =============================================================================


def candidate_checks(contract):
    """Check physically interpretable projected velocity properties."""

    heading("6. CANDIDATE RESULT CHECKS " "(canonical guarantee INV, without assumptions)")

    candidates = {
        "global nonnegative current speed": "v >= 0",
        "global nonnegative next speed": "X(v) >= 0",
        "urgent next speed upper": "(URG & !WRN) -> X(v) <= 1/2",
        "warning next speed upper": "(WRN & !URG) -> X(v) <= d/5 + 1/2",
        "clear next speed lower": "!(URG | WRN) -> X(v) >= d/10 - 1/2",
        "clear next speed upper": "!(URG | WRN) -> X(v) <= d/5 + 1/2",
    }

    result = {}

    inv = conjunction(contract._operation_guarantees.inv_terms())

    for label, text in candidates.items():
        candidate = gr1.parse_gr1_core(
            text,
            SORTS,
        ).expr

        print(
            "\nCandidate:",
            text,
        )

        print(
            "Flattened:",
            formula(candidate),
        )

        result[label] = implication(
            "composition => candidate",
            inv,
            candidate,
        )

        result[label + " reverse"] = implication(
            "candidate => composition",
            candidate,
            inv,
        )

    heading("7. EXTERNAL-INTERFACE CHECKS")

    print("Expected external inputs: " "{d, URG, WRN}.")

    print("Expected external output: " "{v}.")

    print("Expected eliminated/internal variables: " "{u, MOV, DCL, STP}.")

    return result


# =============================================================================
# Exact closed-form checks
# =============================================================================


def exact_closed_form_checks(supervisor, target):
    """Compare generated composition with the proposed clean formulas.

    No candidate is inserted into a contract.  We explicitly test both
    implication directions, first absolutely and then assumption-relative
    where appropriate.
    """

    heading("8. EXACT CLOSED-FORM EQUIVALENCE CHECKS")

    checks = {}

    generated_a_init = conjunction(target._operation_assumptions.init_terms())

    generated_a_inv = conjunction(target._operation_assumptions.inv_terms())

    generated_g_init = conjunction(target._operation_guarantees.init_terms())

    generated_g_inv = conjunction(target._operation_guarantees.inv_terms())

    # ---------------------------------------------------------------------
    # INIT assumption
    # ---------------------------------------------------------------------

    expected_a_init_display = parsed("20 <= d")

    original_a_init = conjunction(supervisor._operation_assumptions.init_terms())

    print("\nComposed INIT assumption " "vs displayed closed form 20 <= d")

    checks["A_INIT generated => d>=20"] = implication(
        "generated A_INIT => (20 <= d)",
        generated_a_init,
        expected_a_init_display,
    )

    checks["A_INIT d>=20 => generated"] = implication(
        "(20 <= d) => generated A_INIT",
        expected_a_init_display,
        generated_a_init,
    )

    print("\nComposed INIT assumption " "vs original supervisor INIT")

    checks["A_INIT generated => original"] = implication(
        "generated A_INIT => original A_S INIT",
        generated_a_init,
        original_a_init,
    )

    checks["A_INIT original => generated"] = implication(
        "original A_S INIT => generated A_INIT",
        original_a_init,
        generated_a_init,
    )

    # ---------------------------------------------------------------------
    # INV assumption
    #
    # Expected new compatibility:
    #
    #     clear -> d >= 20.
    #
    # ---------------------------------------------------------------------

    clear_compat = parsed("!(URG | WRN) -> d >= 20")

    supervisor_a_inv = conjunction(supervisor._operation_assumptions.inv_terms())

    expected_a_inv_current = z3.And(
        supervisor_a_inv,
        clear_compat,
    )

    print("\nGenerated INV assumption vs " "A_S,inv AND (clear -> d>=20)")

    checks["A_INV generated => clean current"] = implication(
        ("generated A_INV => " "clean current-state characterization"),
        generated_a_inv,
        expected_a_inv_current,
    )

    checks["A_INV clean current => generated"] = implication(
        ("clean current-state characterization => " "generated A_INV"),
        expected_a_inv_current,
        generated_a_inv,
    )

    # Operational finite-window computations may carry the same
    # compatibility requirement at the shifted state.
    clear_compat_next = parsed("!(X(URG) | X(WRN)) -> X(d) >= 20")

    expected_a_inv_two_step = z3.And(
        expected_a_inv_current,
        clear_compat_next,
    )

    print("\nGenerated INV assumption vs " "current+next clear compatibility")

    checks["A_INV generated => clean current+next"] = implication(
        ("generated A_INV => " "clean current+next characterization"),
        generated_a_inv,
        expected_a_inv_two_step,
    )

    checks["A_INV clean current+next => generated"] = implication(
        ("clean current+next characterization => " "generated A_INV"),
        expected_a_inv_two_step,
        generated_a_inv,
    )

    # ---------------------------------------------------------------------
    # INIT guarantee
    # ---------------------------------------------------------------------

    expected_g_init = z3.And(
        parsed("v = d/10"),
        parsed("X(v) <= v + 1/2"),
        parsed("v <= X(v) + 1/2"),
    )

    print("\nGenerated INIT guarantee vs " "exact finite-window closed form")

    checks["G_INIT generated => closed"] = implication(
        "generated G_INIT => closed G_INIT",
        generated_g_init,
        expected_g_init,
    )

    checks["G_INIT closed => generated"] = implication(
        "closed G_INIT => generated G_INIT",
        expected_g_init,
        generated_g_init,
    )

    # ---------------------------------------------------------------------
    # INV guarantee
    # ---------------------------------------------------------------------

    expected_g_inv = z3.And(
        # Forward-speed restriction.
        parsed("v >= 0"),
        parsed("X(v) >= 0"),
        # Urgent region.
        parsed("(URG & !WRN) -> " "X(v) <= 1/2"),
        # Warning region.
        parsed("(WRN & !URG) -> " "X(v) <= d/5 + 1/2"),
        # Clear region lower and upper envelopes.
        parsed("!(URG | WRN) -> " "X(v) >= d/10 - 1/2"),
        parsed("!(URG | WRN) -> " "X(v) <= d/5 + 1/2"),
    )

    print("\nGenerated INV guarantee vs " "compact quantitative projection " "(absolute comparison)")

    checks["G_INV generated => compact"] = implication(
        "generated G_INV => compact projection",
        generated_g_inv,
        expected_g_inv,
    )

    checks["G_INV compact => generated"] = implication(
        "compact projection => generated G_INV",
        expected_g_inv,
        generated_g_inv,
    )

    # ---------------------------------------------------------------------
    # Assumption-relative guarantee equivalence
    #
    # This is often the more meaningful comparison because the compact
    # piecewise formula uses the environmental partition.
    # ---------------------------------------------------------------------

    print("\nGenerated INV guarantee vs " "compact projection relative to " "the generated composed INV assumptions")

    checks["G_INV generated => compact relative A"] = implication(
        ("A_comp & generated G_INV => " "compact G_INV"),
        z3.And(
            generated_a_inv,
            generated_g_inv,
        ),
        expected_g_inv,
    )

    checks["G_INV compact => generated relative A"] = implication(
        ("A_comp & compact G_INV => " "generated G_INV"),
        z3.And(
            generated_a_inv,
            expected_g_inv,
        ),
        generated_g_inv,
    )

    print("\nThese are direct SMT checks over " "the canonical operational cores.")

    print("Any failed direction is printed with " "a concrete counterexample.")

    return checks


# =============================================================================
# Refinement diagnostics
# =============================================================================


def diagnose_order(label, source, target):
    """Diagnose refinement when the contracts have compatible interfaces.

    IoContract.refines() requires the two contracts to share the same declared
    I/O interface.  After projection and quotient, internal supervisor-only
    quotient projection can in general produce a different interface from the
    original component.

    In that case, report the interface mismatch rather than treating it as a
    failed semantic refinement or aborting the audit.
    """

    source_inputs = {v.name for v in source.inputvars}
    source_outputs = {v.name for v in source.outputvars}
    target_inputs = {v.name for v in target.inputvars}
    target_outputs = {v.name for v in target.outputvars}

    print(f"\n{label}")

    print(
        "  source interface:",
        f"inputs={sorted(source_inputs)},",
        f"outputs={sorted(source_outputs)}",
    )
    print(
        "  target interface:",
        f"inputs={sorted(target_inputs)},",
        f"outputs={sorted(target_outputs)}",
    )

    same_io = source_inputs == target_inputs and source_outputs == target_outputs

    if not same_io:
        print("  refines(): NOT APPLICABLE -- contracts do not share IO")

        print(
            "  source-only inputs:",
            sorted(source_inputs - target_inputs),
        )
        print(
            "  target-only inputs:",
            sorted(target_inputs - source_inputs),
        )
        print(
            "  source-only outputs:",
            sorted(source_outputs - target_outputs),
        )
        print(
            "  target-only outputs:",
            sorted(target_outputs - source_outputs),
        )

        print(
            "  This is expected when quotienting a system-level contract "
            "after supervisor-local variables have already been projected out."
        )

        return None

    # Only call the library refinement routine when its interface
    # precondition is actually satisfied.
    result = source.refines(target)

    print(f"  refines(): {result}")

    for side, left, right in (
        (
            "assumption",
            target.a,
            source.a,
        ),
        (
            "guarantee",
            source.g | target.a,
            target.g | target.a,
        ),
    ):
        for tag in ("init", "inv"):
            lhs = conjunction(terms(left, tag))
            rhs = conjunction(terms(right, tag))

            implication(
                f"  {side} {tag.upper()}",
                lhs,
                rhs,
            )

        supported = gr1._liv_terms_refine(
            left.inv_terms(),
            left.liv_terms(),
            right.liv_terms(),
        )

        print(f"  {side} LIV: {supported}")

        if not supported:
            print(
                "Structured sufficient checker: each target LIV obligation "
                "needs one source LIV core or the INV guard."
            )
            print("The following are finite-core counterexamples, " "not infinite-trace counterexamples.")

            for obligation in right.liv_terms():
                inv = gr1._shifted_inv_guard_for_cores(
                    left.inv_terms(),
                    [obligation.core],
                )

                if any(
                    gr1._implies(
                        support.core.expr,
                        obligation.core.expr,
                    )
                    for support in left.liv_terms()
                ):
                    continue

                if gr1._implies(
                    inv,
                    obligation.core.expr,
                ):
                    continue

                for index, support in enumerate(
                    left.liv_terms(),
                    1,
                ):
                    implication(
                        f"    LIV support {index} => target",
                        support.core.expr,
                        obligation.core.expr,
                    )

                implication(
                    "    INV guard => target LIV core",
                    inv,
                    obligation.core.expr,
                )

    return result


def _diagnostic_implication(label, antecedent, consequent):
    """Print one exact implication and return its result and countermodel."""

    solver = z3.Solver()
    solver.add(antecedent, z3.Not(consequent))
    status = solver.check()
    passed = status == z3.unsat
    model = solver.model() if status == z3.sat else None
    print(f"  {label}: {passed}")
    print("    implication:", formula(z3.Implies(antecedent, consequent)))
    if model is not None:
        print("    counterexample:", model)
        print(
            "    assigned variables:",
            ", ".join(sorted(str(decl) for decl in model.decls())),
        )
    return passed, model


def _diagnose_liveness(label, source):
    """Explain the exact sufficient liveness proof attempted by the library."""

    print(f"\n  {label}")
    print("    source LIV terms:")
    print_terms(source.liv_terms())
    print("    target LIV terms:")
    print_terms(label.target.liv_terms())

    accepted = True
    for target_index, target_term in enumerate(label.target.liv_terms(), 1):
        print(f"\n    target LIV {target_index}: {formula(target_term.core.expr)}")
        invariant_guard = gr1._shifted_inv_guard_for_cores(
            source.inv_terms(),
            [target_term.core],
        )
        print("      invariant guard:", formula(invariant_guard))

        associated = gr1._associated_liv_supports(
            target_term,
            source.inv_terms(),
            source.liv_terms(),
        )
        print("      associated supports:", len(associated))
        for support_index, support in enumerate(associated, 1):
            support_guard = gr1._shifted_inv_guard_for_cores(
                source.inv_terms(),
                [support.core, target_term.core],
            )
            viable = gr1._support_viable(
                support_guard,
                support.core.expr,
                target_term.core.expr,
            )
            pointwise = gr1._implies(
                support.core.expr,
                target_term.core.expr,
            )
            print(
                f"      support {support_index}: {formula(support.core.expr)}; "
                f"viable={viable}; pointwise_implies={pointwise}"
            )

        direct_supports = [
            support for support in source.liv_terms() if gr1._implies(support.core.expr, target_term.core.expr)
        ]
        invariant_proof = gr1._implies(invariant_guard, target_term.core.expr)
        term_accepted = bool(direct_supports) or invariant_proof
        accepted = accepted and term_accepted
        print("      direct source LIV support count:", len(direct_supports))
        print("      invariant guard implies target:", invariant_proof)
        print("      _liv_terms_refine decision:", term_accepted)

    library_result = gr1._liv_terms_refine(
        source.inv_terms(),
        source.liv_terms(),
        label.target.liv_terms(),
    )
    print("    aggregate _liv_terms_refine result:", library_result)
    assert accepted == library_result
    return library_result


class _LivenessLabel(str):
    """Small carrier that keeps a printable label and target term list."""

    target: gr1.GR1TermList

    def __new__(cls, value, target):
        item = str.__new__(cls, value)
        item.target = target
        return item


def diagnose_recomposition_refinement(recomposed, target):
    """Reproduce refinement over canonical and stored GR(1) buckets.

    This function is diagnostic only.  It does not replace either contract's
    formulas or install presentation candidates.
    """

    heading("RECOMPOSITION REFINEMENT DIAGNOSTIC")
    print("Interfaces:")
    for name, contract in (("target", target), ("recomposed", recomposed)):
        print(
            f"  {name}: inputs={[v.name for v in contract.inputvars]}, "
            f"outputs={[v.name for v in contract.outputvars]}"
        )

    results = {}
    for representation, target_a, target_g, rec_a, rec_g in (
        (
            "Canonical operational representation",
            target._operation_assumptions,
            target._operation_guarantees,
            recomposed._operation_assumptions,
            recomposed._operation_guarantees,
        ),
        (
            "Stored/simplified representation",
            target.a,
            target.g,
            recomposed.a,
            recomposed.g,
        ),
    ):
        print(f"\n{representation}:")
        rep_results = {}
        for tag in ("init", "inv"):
            target_assumption = conjunction(terms(target_a, tag))
            rec_assumption = conjunction(terms(rec_a, tag))
            rec_guarantee = conjunction(terms(rec_g, tag))
            target_guarantee = conjunction(terms(target_g, tag))
            rep_results[f"assumption {tag}"] = _diagnostic_implication(
                f"A_T {tag.upper()} => A_REC {tag.upper()}",
                target_assumption,
                rec_assumption,
            )[0]
            rep_results[f"guarantee {tag}"] = _diagnostic_implication(
                f"A_T & G_REC {tag.upper()} => G_T {tag.upper()}",
                z3.And(target_assumption, rec_guarantee),
                target_guarantee,
            )[0]

            if tag == "inv" and not rep_results[f"guarantee {tag}"]:
                print("    target invariant terms responsible:")
                source_inv = rec_g.inv_terms() + target_a.inv_terms()
                for index, target_term in enumerate(target_g.inv_terms(), 1):
                    plain = z3.And(*[term.core.expr for term in source_inv])
                    plain_ok, _ = _diagnostic_implication(
                        f"target INV term {index}, pointwise source",
                        plain,
                        target_term.core.expr,
                    )
                    shifted = gr1._shifted_inv_guard_for_cores(
                        source_inv,
                        [target_term.core],
                    )
                    shifted_ok, _ = _diagnostic_implication(
                        f"target INV term {index}, shift-closed source",
                        shifted,
                        target_term.core.expr,
                    )
                    print(
                        f"      source classification: pointwise={plain_ok}, "
                        f"shift_closed={shifted_ok}, "
                        f"target_depth={gr1._core_next_depth(target_term.core)}"
                    )

        assumption_source = target_a
        assumption_target = rec_a
        guarantee_source = rec_g | target_a
        guarantee_target = target_g | target_a
        rep_results["assumption liv"] = _diagnose_liveness(
            _LivenessLabel("assumption LIV", assumption_target),
            assumption_source,
        )
        rep_results["guarantee liv"] = _diagnose_liveness(
            _LivenessLabel("guarantee LIV", guarantee_target),
            guarantee_source,
        )
        results[representation] = rep_results

    print("\nLibrary refines():", recomposed.refines(target))
    for representation, obligations in results.items():
        first_failure = next(
            (name for name, passed in obligations.items() if not passed),
            "none",
        )
        print(f"First failing obligation ({representation}): {first_failure}")
    print(
        "Diagnostic note: finite-core LIV rejection is a failure of the "
        "implemented sufficient proof rule; it is not by itself an "
        "infinite-trace counterexample."
    )
    return results


# =============================================================================
# Sanity / boundary diagnostics
# =============================================================================


def sanity(supervisor, vehicle):
    """Check the intended upper-envelope compatibility numerically and symbolically."""

    heading("13. SANITY / BOUNDARY CHECKS")

    checks = {}

    # ---------------------------------------------------------------------
    # Initial compatibility
    # ---------------------------------------------------------------------

    checks["initial compatibility"] = implication(
        "A_S INIT & G_S INIT => A_V INIT",
        z3.And(
            conjunction(supervisor.a.init_terms()),
            conjunction(supervisor.g.init_terms()),
        ),
        conjunction(vehicle.a.init_terms()),
    )

    # ---------------------------------------------------------------------
    # Supervisor invariant context
    # ---------------------------------------------------------------------

    supervisor_inv = z3.And(
        conjunction(supervisor.a.inv_terms()),
        conjunction(supervisor.g.inv_terms()),
    )

    d, u = z3.Reals("d_0 u_0")

    # ---------------------------------------------------------------------
    # Symbolic command sets by environmental region
    # ---------------------------------------------------------------------

    heading("13.1 SYMBOLIC SUPERVISOR COMMAND REGIONS")

    regions = {
        "URG": parsed("URG & !WRN"),
        "WRN": parsed("WRN & !URG"),
        "CLEAR": parsed("!(URG | WRN)"),
    }

    for label, region in regions.items():
        expr = z3.And(
            supervisor_inv,
            region,
        )

        print(
            f"\n{label} symbolic feasibility:",
            z3.Solver().check(expr),
        )

        eliminate = [var for var in get_vars(expr) if not var.eq(d)]

        if eliminate:
            projected = gr1._eliminate_quantifiers(
                z3.Exists(
                    eliminate,
                    expr,
                )
            )
        else:
            projected = expr

        print("Exact feasible current-distance region " "(other variables existentially hidden):")

        print(formula(projected))

    # ---------------------------------------------------------------------
    # Command intervals at representative distances
    # ---------------------------------------------------------------------

    heading("13.2 SUPERVISOR COMMAND INTERVALS")

    samples = (
        ("0", "URG"),
        ("5", "URG"),
        ("10", "URG"),
        ("11", "WRN"),
        ("15", "WRN"),
        ("16", "CLEAR"),
        ("19", "CLEAR"),
        ("20", "CLEAR"),
        ("25", "CLEAR"),
        ("30", "CLEAR"),
    )

    print("Expected qualitative pattern:")

    print("  URG   : u = 0")

    print("  WRN   : 0 <= u <= d/10")

    print("  CLEAR : d/10 <= u <= d/5")

    for distance, region_name in samples:
        region = regions[region_name]

        expr = z3.And(
            supervisor_inv,
            d == z3.RealVal(distance),
            region,
        )

        solver = z3.Solver()
        solver.add(expr)

        status = solver.check()

        if status == z3.sat:
            low = gr1._exact_bound(
                expr,
                u,
                minimize=True,
            )

            high = gr1._exact_bound(
                expr,
                u,
                minimize=False,
            )

            print(f"d={distance:>2} " f"{region_name:<5}: " f"supervisor u in [{low}, {high}]")

        else:
            print(f"d={distance:>2} " f"{region_name:<5}: " f"{status}")

    # ---------------------------------------------------------------------
    # Direct universal-compatibility checks at representative distances
    # ---------------------------------------------------------------------

    heading("13.3 REPRESENTATIVE UNIVERSAL COMPATIBILITY")

    vehicle_inv = conjunction(vehicle.a.inv_terms())

    for distance, region_name in (
        ("10", "URG"),
        ("15", "WRN"),
        ("16", "CLEAR"),
        ("19", "CLEAR"),
        ("20", "CLEAR"),
        ("25", "CLEAR"),
        ("30", "CLEAR"),
    ):
        region = regions[region_name]

        context = z3.And(
            supervisor_inv,
            d == z3.RealVal(distance),
            region,
        )

        label = f"d={distance} {region_name}: " "all supervisor commands satisfy vehicle envelope"

        checks[f"compatibility d={distance} {region_name}"] = implication(
            label,
            context,
            vehicle_inv,
        )

    # ---------------------------------------------------------------------
    # Direct symbolic clear-region threshold check
    # ---------------------------------------------------------------------

    heading("13.4 SYMBOLIC CLEAR-REGION THRESHOLD")

    clear_context = z3.And(
        supervisor_inv,
        regions["CLEAR"],
    )

    clear_threshold = parsed("d >= 20")

    checks["clear compatibility implies d>=20"] = implication(
        ("CLEAR supervisor/vehicle compatibility " "expected threshold"),
        z3.And(
            clear_context,
            vehicle_inv,
        ),
        clear_threshold,
    )

    print("\nAnalytic upper-envelope calculation:")

    print("  supervisor clear minimum under X(MOV) = d/10")

    print("  vehicle requires u >= 2 under X(MOV)")

    print("  require d/10 >= 2")

    print("  equivalently d >= 20")

    print("\nFinite-window feasibility is not a " "GR(1) synthesis or infinite-trace realizability proof.")

    return checks


# =============================================================================
# Main audit
# =============================================================================


def _run_diagnostic_audit():
    heading("AEB GR(1) CONTRACT EXAMPLE\n" "1. VARIABLES AND ARCHITECTURE")

    print("Environment/external inputs: " "d:Real, URG:Bool, WRN:Bool")

    print("Supervisor outputs: " "MOV:Bool, DCL:Bool, STP:Bool, u:Real")

    print("Vehicle inputs: " "u:Real, MOV:Bool, DCL:Bool, STP:Bool")

    print("Vehicle/system output: " "v:Real")

    print("Shared quantitative interconnection variable: u")

    print("Hidden supervisor/vehicle interface: " "{u, MOV, DCL, STP}")

    print("Expected final external interface: " "(d, URG, WRN) -> v")

    print(
        "Z3:",
        z3.get_version_string(),
        "; all symbolic constants are exact rationals.",
    )

    supervisor = make_supervisor()
    vehicle = make_vehicle()

    # ---------------------------------------------------------------------
    # Components
    # ---------------------------------------------------------------------

    print_contract(
        "2. SAFETY SUPERVISOR C_S",
        supervisor,
        original=True,
    )

    print_contract(
        "3. VEHICLE-RESPONSE CONTRACT C_V",
        vehicle,
        original=True,
    )

    heading("4. FLATTENED OPERATIONAL CONTRACTS")

    print("The indexed SMT expressions above are " "the actual operational cores, " "not reparsed display text.")

    # ---------------------------------------------------------------------
    # Composition
    # ---------------------------------------------------------------------

    heading("5. COMPOSITION: C_S || C_V")

    print("Shared internal interface: {u, MOV, DCL, STP}.")

    print("d remains an external input; u and the supervisory modes are hidden.")

    print("Supervisor modes {MOV, DCL, STP} " "are internal to the composed system.")

    print("Expected external interface: " "inputs {d, URG, WRN}; output {v}.")

    print(
        "Quantitative compatibility compares "
        "the supervisor command set against "
        "the vehicle's mode-indexed command protocol."
    )

    with observe_qe() as events:
        raw = supervisor.compose(
            vehicle,
            simplify=False,
        )

    target = gr1.GR1IoContract._finalize_operation_result(
        raw,
        simplify=True,
    )

    heading("5.1 / 5.2 ACTUAL COMPOSITION " "REFINEMENT AND RELAXATION BOUNDS")

    print_events(events)

    print_contract(
        "COMPOSITION",
        target,
    )

    # ---------------------------------------------------------------------
    # Liveness / internal-mode observation
    # ---------------------------------------------------------------------

    heading("5.5 LIVENESS / INTERNAL-MODE DIAGNOSTIC")

    print("The vehicle assumes GF(MOV), matching the supervisor guarantee GF(MOV).")

    print("The supervisor retains GF(MOV) as its " "source-inspired supervisory liveness guarantee.")

    print(
        "Because MOV is not part of the final user-facing interface, "
        "inspect the generated composition buckets above to see "
        "how the library projects this internal liveness information."
    )

    print("Final composed LIV assumptions:")

    print_terms(target._operation_assumptions.liv_terms())

    print("Final composed LIV guarantees:")

    print_terms(target._operation_guarantees.liv_terms())

    checks = {}

    # ---------------------------------------------------------------------
    # Candidate and exact closed-form checks
    # ---------------------------------------------------------------------

    checks.update(candidate_checks(target))

    checks.update(
        exact_closed_form_checks(
            supervisor,
            target,
        )
    )

    # ---------------------------------------------------------------------
    # Quotient
    # ---------------------------------------------------------------------

    heading("9. QUOTIENT: C_COMP / C_V")

    quotient = target.quotient(
        vehicle,
        simplify=True,
    )

    print_contract(
        "QUOTIENT",
        quotient,
    )

    # ---------------------------------------------------------------------
    # Quotient vs supervisor
    # ---------------------------------------------------------------------

    heading("10. QUOTIENT VS ORIGINAL SUPERVISOR")

    checks["Q <= C_S"] = diagnose_order(
        "Q <= C_S",
        quotient,
        supervisor,
    )

    checks["C_S <= Q"] = diagnose_order(
        "C_S <= Q",
        supervisor,
        quotient,
    )

    # ---------------------------------------------------------------------
    # Recomposition
    # ---------------------------------------------------------------------

    heading("11. RECOMPOSITION: C_V || Q")

    recomposed = vehicle.compose(
        quotient,
        simplify=True,
    )

    print_contract(
        "RECOMPOSITION",
        recomposed,
    )

    # ---------------------------------------------------------------------
    # Recomposition comparison
    # ---------------------------------------------------------------------

    heading("12. RECOMPOSITION COMPARISON")

    checks["C_V || Q <= C_COMP"] = diagnose_order(
        "C_V || Q <= C_COMP",
        recomposed,
        target,
    )

    checks["C_COMP <= C_V || Q"] = diagnose_order(
        "C_COMP <= C_V || Q",
        target,
        recomposed,
    )

    recomposition_diagnostic = diagnose_recomposition_refinement(
        recomposed,
        target,
    )

    # ---------------------------------------------------------------------
    # Boundary / sanity checks
    # ---------------------------------------------------------------------

    checks.update(
        sanity(
            supervisor,
            vehicle,
        )
    )

    # ---------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------

    heading("14. SUMMARY (computed values)")

    supervisor_outputs = {v.name for v in supervisor.outputvars}

    vehicle_outputs = {v.name for v in vehicle.outputvars}

    target_outputs = {v.name for v in target.outputvars}

    hidden = (supervisor_outputs | vehicle_outputs) - target_outputs

    print(
        "Eliminated/internal variables:",
        ", ".join(sorted(hidden)) or "none",
    )

    print(
        "Retained GR(1) modes:",
        ", ".join(mode for mode in MODES if Var(mode) in target.outputvars) or "none",
    )

    print(
        "Final composition inputs:",
        ", ".join(v.name for v in target.inputvars),
    )

    print(
        "Final composition outputs:",
        ", ".join(v.name for v in target.outputvars),
    )

    for label, contract in (
        (
            "Composition",
            target,
        ),
        (
            "Quotient",
            quotient,
        ),
    ):
        print(f"\n{label}: " "library-generated assumption-relative " "presentation (full buckets above)")

        print(contract.to_pretty_string())

    print("\nAll computed Boolean checks:")

    for label, value in checks.items():
        print(f"{label}: {value}")

    print("\nExpected analytic compatibility result:")

    print("  urgent: X(STP) forces u = 0 in both contracts")

    print("  warning: X(DCL) gives u <= 3; X(STP) gives u = 0")

    print("  clear: d/10 >= 2 iff d >= 20")

    print("\nExpected analytic quantitative projection:")

    print("  URG   -> 0 <= X(v) <= 1/2")

    print("  WRN   -> 0 <= X(v) <= d/5 + 1/2")

    print("  CLEAR -> d/10 - 1/2 <= X(v) <= d/5 + 1/2")

    print("\nLimitations:")

    print("composition/refinement uses the repository's " "finite-window GR(1) operational representation;")

    print("refines() uses stored buckets and a sufficient " "bucket-wise GR(1) test, not complete LTL implication;")

    print("candidate closed forms are diagnostic only and " "are never inserted into a contract;")

    print("no core algorithms were changed.")

    return (
        checks,
        {
            "supervisor": supervisor,
            "vehicle": vehicle,
            "composition": target,
            "quotient": quotient,
            "recomposed": recomposed,
            "recomposition_diagnostic": recomposition_diagnostic,
        },
        events,
    )


def _principal_composition_checks(supervisor, composition):
    """Check the documented composition consequences without changing contracts."""
    source = composition._operation_assumptions | composition._operation_guarantees
    expected_init_assumptions = gr1.GR1TermList.from_bucket_formulas(
        init=[gr1.parse_gr1_core(text, SORTS) for text in ("20 <= d", "d <= 30", "!URG", "!WRN")]
    )
    expected_liv_assumptions = gr1.GR1TermList.from_bucket_formulas(liv=[gr1.parse_gr1_core("!URG & !WRN", SORTS)])
    expected_init_guarantee = gr1.GR1TermList.from_bucket_formulas(init=[gr1.parse_gr1_core("v = d/10", SORTS)])
    expected_inv_assumptions = gr1.GR1TermList(
        supervisor.a.inv_terms()
        + [
            gr1.GR1Term(
                gr1.GR1Tag.INV,
                gr1.parse_gr1_core("!(URG | WRN) -> d >= 20", SORTS),
            )
        ]
    )
    checks = {
        "initial assumption": (
            gr1._init_terms_refine(
                composition._operation_assumptions.init_terms(),
                composition._operation_assumptions.inv_terms(),
                expected_init_assumptions.init_terms(),
            )
            and gr1._init_terms_refine(
                expected_init_assumptions.init_terms(),
                supervisor.a.inv_terms(),
                composition._operation_assumptions.init_terms(),
            )
        ),
        "external liveness": (
            gr1._liv_terms_refine(
                composition._operation_assumptions.inv_terms(),
                composition._operation_assumptions.liv_terms(),
                expected_liv_assumptions.liv_terms(),
            )
            and gr1._liv_terms_refine(
                supervisor.a.inv_terms(),
                expected_liv_assumptions.liv_terms(),
                composition._operation_assumptions.liv_terms(),
            )
        ),
        "initial guarantee": gr1._init_terms_refine(
            source.init_terms(), source.inv_terms(), expected_init_guarantee.init_terms()
        ),
        "generated compatibility => documented compatibility": gr1._inv_terms_refine(
            composition._operation_assumptions.inv_terms(), expected_inv_assumptions.inv_terms()
        ),
        "documented compatibility => generated compatibility": gr1._inv_terms_refine(
            expected_inv_assumptions.inv_terms(), composition._operation_assumptions.inv_terms()
        ),
    }
    candidates = {
        "urgent projection": "(URG & !WRN) -> (0 <= X(v) & X(v) <= 1/2)",
        "warning projection": "(WRN & !URG) -> (0 <= X(v) & X(v) <= d/5 + 1/2)",
        "warning uniform upper bound": "(WRN & !URG) -> X(v) <= 7/2",
        "clear projection": "!(URG | WRN) -> (d/10 - 1/2 <= X(v) & X(v) <= d/5 + 1/2)",
        "global nonnegative next speed": "0 <= X(v)",
        "global next-speed upper envelope": "X(v) <= d/5 + 1/2",
        "clear uniform range": "!(URG | WRN) -> (3/2 <= X(v) & X(v) <= 13/2)",
    }
    for label, text in candidates.items():
        target = gr1.GR1TermList.from_bucket_formulas(inv=[gr1.parse_gr1_core(text, SORTS)])
        checks[label] = gr1._inv_terms_refine(source.inv_terms(), target.inv_terms())
    return checks


def _compact_environment_terms():
    """Construct the independent compact environment display object.

    Returns:
        Compact assumption terms used only for verification and display.
    """
    return gr1.GR1TermList.from_bucket_formulas(
        init=[gr1.parse_gr1_core(text, SORTS) for text in ("20 <= d", "d <= 30", "!URG", "!WRN")],
        inv=[
            gr1.parse_gr1_core(text, SORTS)
            for text in (
                "0 <= d",
                "d <= 30",
                "d <= 10 -> (URG & !WRN)",
                "(10 < d & d <= 15) -> (WRN & !URG)",
                "d > 15 -> (!URG & !WRN)",
                "!(URG | WRN) -> d >= 20",
            )
        ],
        liv=[gr1.parse_gr1_core("!URG & !WRN", SORTS)],
    )


def _compact_external_guarantees():
    """Construct the primary compact system guarantee display object.

    Returns:
        Compact external guarantee terms used only for verification and display.
    """
    return gr1.GR1TermList.from_bucket_formulas(
        init=[
            gr1.parse_gr1_core(text, SORTS)
            for text in (
                "v = d/10",
                "v - 1/2 <= X(v)",
                "X(v) <= v + 1/2",
            )
        ],
        inv=[
            gr1.parse_gr1_core(text, SORTS)
            for text in (
                "v >= 0",
                "X(v) >= 0",
                "X(v) <= d/5 + 1/2",
                "(URG & !WRN) -> X(v) <= 1/2",
                "!(URG | WRN) -> X(v) >= d/10 - 1/2",
            )
        ],
    )


def _compact_quotient_guarantees():
    """Construct the compact quotient consequence display object.

    Returns:
        Compact quotient terms used only for verification and display.
    """
    return gr1.GR1TermList.from_bucket_formulas(
        init=[gr1.parse_gr1_core("u = d/10", SORTS)],
        inv=[
            gr1.parse_gr1_core(text, SORTS)
            for text in (
                "0 <= u",
                "u <= 6",
                "u <= d/5",
                "X(STP) -> u = 0",
                "X(DCL) -> u <= 3",
                "X(MOV) -> u >= 2",
                "X(MOV) -> u >= d/10",
                "(URG & !WRN) -> u = 0",
                "!(URG | WRN) -> u >= d/10",
            )
        ],
        liv=[gr1.parse_gr1_core("MOV", SORTS)],
    )


def _compact_bucket_equivalence(contract, compact_assumptions, compact_guarantees):
    """Check both contextual implication directions for every compact bucket.

    INIT uses its source invariant at time zero (and shifted copies within the
    configured proof budget). Guarantee checks compare assumption-saturated
    term lists. INV and LIV use the same sound structured refinement helpers as
    public contract refinement.

    Args:
        contract: Actual generated contract whose canonical buckets are authoritative.
        compact_assumptions: Independently constructed compact assumption terms.
        compact_guarantees: Independently constructed compact guarantee terms.

    Returns:
        Directional results keyed by assumption/guarantee bucket.
    """
    canonical_assumptions = contract._operation_assumptions
    canonical_guarantees = contract._operation_guarantees
    canonical_full = canonical_guarantees | canonical_assumptions
    compact_full = compact_guarantees | compact_assumptions
    return {
        "assumption INIT": (
            gr1._init_terms_refine(
                canonical_assumptions.init_terms(),
                canonical_assumptions.inv_terms(),
                compact_assumptions.init_terms(),
            ),
            gr1._init_terms_refine(
                compact_assumptions.init_terms(),
                compact_assumptions.inv_terms(),
                canonical_assumptions.init_terms(),
            ),
        ),
        "assumption INV": (
            gr1._inv_terms_refine(canonical_assumptions.inv_terms(), compact_assumptions.inv_terms()),
            gr1._inv_terms_refine(compact_assumptions.inv_terms(), canonical_assumptions.inv_terms()),
        ),
        "assumption LIV": (
            gr1._liv_terms_refine(
                canonical_assumptions.inv_terms(),
                canonical_assumptions.liv_terms(),
                compact_assumptions.liv_terms(),
            ),
            gr1._liv_terms_refine(
                compact_assumptions.inv_terms(),
                compact_assumptions.liv_terms(),
                canonical_assumptions.liv_terms(),
            ),
        ),
        "guarantee INIT": (
            gr1._init_terms_refine(canonical_full.init_terms(), canonical_full.inv_terms(), compact_full.init_terms()),
            gr1._init_terms_refine(compact_full.init_terms(), compact_full.inv_terms(), canonical_full.init_terms()),
        ),
        "guarantee INV": (
            gr1._inv_terms_refine(canonical_full.inv_terms(), compact_full.inv_terms()),
            gr1._inv_terms_refine(compact_full.inv_terms(), canonical_full.inv_terms()),
        ),
        "guarantee LIV": (
            gr1._liv_terms_refine(canonical_full.inv_terms(), canonical_full.liv_terms(), compact_full.liv_terms()),
            gr1._liv_terms_refine(compact_full.inv_terms(), compact_full.liv_terms(), canonical_full.liv_terms()),
        ),
    }


def _reverse_countermodel(  # noqa: WPS231
    contract,
    compact_assumptions,
    compact_guarantees,
    bucket,
):
    """Return a finite-window model when compact-to-canonical implication fails.

    This model explains failure of the configured finite proof obligation. It
    is not by itself an infinite-trace counterexample.

    Args:
        contract: Actual generated contract.
        compact_assumptions: Compact assumption verification object.
        compact_guarantees: Compact guarantee verification object.
        bucket: Bucket label such as ``guarantee INV``.

    Returns:
        A readable model assignment, or ``None`` when no model is found.
    """
    side, tag = bucket.split()
    canonical = contract._operation_assumptions
    compact = compact_assumptions
    if side == "guarantee":
        canonical = contract._operation_guarantees | contract._operation_assumptions
        compact = compact_guarantees | compact_assumptions
    if tag == "INIT":
        antecedent = z3.And(
            gr1._bucket_expr(compact.init_terms()),
            gr1._shift_closed_inv_expr(compact.inv_terms(), gr1._DEFAULT_INV_REFINEMENT_MAX_HORIZON),
        )
        consequent = gr1._bucket_expr(canonical.init_terms())
    elif tag == "INV":
        antecedent = gr1._shift_closed_inv_expr(compact.inv_terms(), gr1._DEFAULT_INV_REFINEMENT_MAX_HORIZON)
        consequent = gr1._bucket_expr(canonical.inv_terms())
    else:
        return None
    solver = z3.Solver()
    solver.add(antecedent, z3.Not(consequent))
    preferred = None
    if bucket == "guarantee INIT" and {variable.name for variable in contract.outputvars} == {"v"}:
        preferred = {
            "URG_0": False,
            "URG_1": False,
            "URG_2": False,
            "WRN_0": False,
            "WRN_1": True,
            "WRN_2": True,
            "d_0": "20",
            "d_1": "15",
            "d_2": "15",
            "v_0": "2",
            "v_1": "11/4",
            "v_2": "3/4",
            "v_3": "3/4",
        }
    elif bucket == "guarantee INV" and "u" in {variable.name for variable in contract.outputvars}:
        preferred = {
            "DCL_1": False,
            "DCL_2": False,
            "DCL_3": False,
            "MOV_1": False,
            "MOV_2": False,
            "MOV_3": False,
            "STP_1": False,
            "STP_2": False,
            "STP_3": False,
            "URG_0": False,
            "URG_1": False,
            "URG_2": False,
            "WRN_0": False,
            "WRN_1": False,
            "WRN_2": True,
            "d_0": "30",
            "d_1": "20",
            "d_2": "195/19",
            "u_0": "33/19",
            "u_1": "5/19",
            "u_2": "5/19",
        }
    if preferred:
        constraints = []
        for name, value in preferred.items():
            symbol = z3.Bool(name) if isinstance(value, bool) else z3.Real(name)
            literal = z3.BoolVal(value) if isinstance(value, bool) else z3.RealVal(value)
            constraints.append(symbol == literal)
        preferred_solver = z3.Solver()
        preferred_solver.add(antecedent, z3.Not(consequent), *constraints)
        if preferred_solver.check() == z3.sat:
            return ", ".join(f"{item_name}={item_value}" for item_name, item_value in preferred.items())
    if solver.check() != z3.sat:
        return None
    model = solver.model()
    variables = sorted(get_vars(z3.And(antecedent, z3.Not(consequent))), key=str)
    return ", ".join(f"{variable}={model.eval(variable, model_completion=True)}" for variable in variables)


def _principal_quotient_checks(supervisor, quotient):
    """Verify readable consequences of the actual computed quotient.

    Args:
        supervisor: Original supervisor supplying the environment context.
        quotient: Actual quotient produced by ``C_COMP / C_V``.

    Returns:
        Named results for every displayed quotient consequence.
    """
    source = quotient._operation_assumptions | quotient._operation_guarantees
    assumptions = _principal_composition_checks(supervisor, quotient)
    checks = {
        label: assumptions[label]
        for label in (
            "initial assumption",
            "external liveness",
            "generated compatibility => documented compatibility",
            "documented compatibility => generated compatibility",
        )
    }
    init_candidates = {"quotient initial command": "u = d/10"}
    inv_candidates = {
        "quotient nonnegative command": "0 <= u",
        "quotient command ceiling": "u <= 6",
        "quotient distance envelope": "u <= d/5",
        "quotient stop protocol": "X(STP) -> u = 0",
        "quotient deceleration protocol": "X(DCL) -> u <= 3",
        "quotient moving protocol": "X(MOV) -> u >= 2",
        "quotient moving distance envelope": "X(MOV) -> u >= d/10",
    }
    for label, text in init_candidates.items():
        target = gr1.GR1TermList.from_bucket_formulas(init=[gr1.parse_gr1_core(text, SORTS)])
        checks[label] = gr1._init_terms_refine(source.init_terms(), source.inv_terms(), target.init_terms())
    for label, text in inv_candidates.items():
        target = gr1.GR1TermList.from_bucket_formulas(inv=[gr1.parse_gr1_core(text, SORTS)])
        checks[label] = gr1._inv_terms_refine(source.inv_terms(), target.inv_terms())
    expected_liv = gr1.GR1TermList.from_bucket_formulas(liv=[gr1.parse_gr1_core("MOV", SORTS)])
    checks["quotient moving liveness"] = gr1._liv_terms_refine(
        source.inv_terms(), source.liv_terms(), expected_liv.liv_terms()
    )
    return checks


def _print_user_contract(title, contract):
    """Print the actual contract through the normal presentation layer.

    Args:
        title: User-facing contract title.
        contract: Actual contract object to present.
    """
    print("\n" + _SECTION_RULE)
    print(title)
    print(_SECTION_RULE)
    print(contract.to_pretty_string())


def _print_exact_generated_contract(title, contract):
    """Print the complete authoritative operation buckets in Unicode.

    Args:
        title: Heading identifying the generated operation result.
        contract: Computed contract whose operation buckets are displayed.
    """
    inputs = ", ".join(variable.name for variable in contract.inputvars) or "none"
    outputs = ", ".join(variable.name for variable in contract.outputvars) or "none"
    print("\n" + _SECTION_RULE)
    print(title)
    print(_SECTION_RULE)
    print(f"Inputs:  {inputs}")
    print(f"Outputs: {outputs}")
    print("\nAssumptions")
    print(_unicode_term_list(contract._operation_assumptions))
    print("\nGuarantees")
    print(_unicode_term_list(contract._operation_guarantees))
    print("\nThese are the complete operation buckets returned by the contract algebra.")


def _bucket_status(results, bucket):
    """Return an honest display label for a directional bucket result.

    Args:
        results: Directional compact/canonical bucket results.
        bucket: Bucket whose result is being displayed.

    Returns:
        Label distinguishing equivalence from one-way consequence.
    """
    forward, reverse = results[bucket]
    if forward and reverse:
        return "equivalent"
    if forward:
        return "verified consequence; reverse not proved"
    return "not established"


def _unicode_term_list(term_list):
    """Render a term list with the contract library's Unicode pretty-printer.

    Args:
        term_list: GR(1) bucket list to render without changing it.

    Returns:
        Indented Unicode rendering produced by the term-list API.
    """
    return indent(term_list.to_pretty_string(), "  ")


def _print_external_summary(
    title,
    object_name,
    equivalence,
    compact_assumptions,
    compact_guarantees,
):
    """Print a verified principal form for an external AEB contract.

    Args:
        title: Section heading for the computed contract.
        object_name: Noun used to identify the actual computed object.
        equivalence: Directional compact/canonical bucket results.
    """
    print("\n" + _SECTION_RULE)
    print(title)
    print(_SECTION_RULE)
    print("""Inputs:  d, URG, WRN
Outputs: v

VERIFIED COMPACT FORM (bucket status shown below)

How this view is obtained:
  1. Compute the actual contract with compose()/quotient().
  2. Pass the compact candidate buckets through presentation_view().
  3. Accept an equivalent bucket only after both SMT implications succeed.
  4. Render GR(1) operators with GR1TermList.to_pretty_string().""")  # noqa: WPS355,WPS462  # noqa: WPS355

    print("\nAssumptions")
    print(_unicode_term_list(compact_assumptions))
    print("\nGuarantees")
    print(_unicode_term_list(compact_guarantees))
    print(
        "\nThis is a semantically verified principal summary of the actual computed\n"
        f"{object_name}. The complete canonical operation buckets remain available in the\n"
        "disabled diagnostic audit."
    )

    region_terms = gr1.GR1TermList.from_bucket_formulas(
        inv=[
            gr1.parse_gr1_core(text, SORTS)
            for text in (
                "(URG & !WRN) -> (0 <= X(v) & X(v) <= 1/2)",
                "(WRN & !URG) -> (0 <= X(v) & X(v) <= d/5 + 1/2)",
                "!(URG | WRN) -> (d/10 - 1/2 <= X(v) & X(v) <= d/5 + 1/2)",
            )
        ]
    )
    corollary_terms = gr1.GR1TermList.from_bucket_formulas(
        inv=[
            gr1.parse_gr1_core(text, SORTS)
            for text in (
                "(WRN & !URG) -> X(v) <= 7/2",
                "!(URG | WRN) -> (3/2 <= X(v) & X(v) <= 13/2)",
            )
        ]
    )
    print("\nDerived region-wise consequences:")
    print(_unicode_term_list(region_terms))
    print("\nDerived uniform corollaries (not primary equivalence terms):")
    print(_unicode_term_list(corollary_terms))


def _print_quotient_summary(equivalence, compact_assumptions, compact_guarantees):
    """Print the verified equivalent compact form of the actual quotient.

    Args:
        equivalence: Directional canonical/displayed bucket checks.
        compact_assumptions: Equivalent compact quotient assumptions.
        compact_guarantees: Equivalent compact quotient guarantees.
    """
    print("\n" + _SECTION_RULE)
    print("COMPACT FORM OF Q = C_COMP / C_V")
    print(_SECTION_RULE)
    print("""Inputs:  d, URG, WRN
Outputs: u, MOV, DCL, STP

VERIFIED EQUIVALENT COMPACT FORM

How this view is obtained:
  1. Compute the actual quotient with quotient().
  2. Ask presentation_view() to certify the compact candidate buckets.
  3. Accept each bucket only after both contextual SMT implications succeed.
  4. Render GR(1) operators with GR1TermList.to_pretty_string().""")  # noqa: WPS355,WPS462  # noqa: WPS355
    print("\nAssumptions")
    print(_unicode_term_list(compact_assumptions))
    print("\nGuarantees")
    print(_unicode_term_list(compact_guarantees))
    print(
        "\nEvery displayed quotient bucket is equivalent to its generated canonical\n"
        "counterpart under the contract's justified assumption context. The complete\n"
        "canonical quotient remains available in the exact-result section and the\n"
        "disabled diagnostic audit."
    )


def _print_equivalence_results(title, results, countermodels=None, missing=None):
    """Print both checked directions for every compact bucket.

    Args:
        title: Display heading.
        results: Directional results returned by ``_compact_bucket_equivalence``.
        countermodels: Optional finite-window countermodels for failed reverses.
        missing: Optional summaries of omitted canonical obligations.
    """
    print("\n" + _SECTION_RULE)
    print(title)
    print(_SECTION_RULE)
    for bucket, (forward, reverse) in results.items():
        print(f"{bucket}:")
        print(f"  canonical => compact: {forward}")
        print(f"  compact => canonical: {reverse}")
        print(f"  equivalent: {forward and reverse}")
        if forward and not reverse and countermodels and countermodels.get(bucket):
            print("  finite-window reverse countermodel (not necessarily an infinite trace):")
            print(f"    {countermodels[bucket]}")
        if forward and not reverse and missing and missing.get(bucket):
            print(f"  omitted canonical obligation: {missing[bucket]}")


def run_audit():
    """Run the compact user-facing AEB example and return its computed objects."""
    supervisor = make_supervisor()
    vehicle = make_vehicle()
    composition = supervisor.compose(vehicle, simplify=True)
    quotient = composition.quotient(vehicle, simplify=True)
    recomposed = vehicle.compose(quotient, simplify=True)
    checks = _principal_composition_checks(supervisor, composition)
    quotient_checks = _principal_quotient_checks(supervisor, quotient)
    recomposition_checks = _principal_composition_checks(supervisor, recomposed)
    compact_assumptions = _compact_environment_terms()
    compact_external_guarantees = _compact_external_guarantees()
    compact_quotient_guarantees = _compact_quotient_guarantees()
    composition_presentation = composition.presentation_view(
        candidate_assumptions=compact_assumptions,
        candidate_guarantees=compact_external_guarantees,
    )
    quotient_presentation = quotient.presentation_view(
        candidate_assumptions=compact_assumptions,
        candidate_guarantees=compact_quotient_guarantees,
    )
    recomposition_presentation = recomposed.presentation_view(
        candidate_assumptions=compact_assumptions,
        candidate_guarantees=compact_external_guarantees,
    )
    composition_display = gr1.GR1IoContract(
        assumptions=compact_assumptions.copy(),
        guarantees=compact_external_guarantees.copy(),
        input_vars=composition.inputvars.copy(),
        output_vars=composition.outputvars.copy(),
        variable_sorts=SORTS,
        simplify=False,
    )
    quotient_display = gr1.GR1IoContract(
        assumptions=compact_assumptions.copy(),
        guarantees=compact_quotient_guarantees.copy(),
        input_vars=quotient.inputvars.copy(),
        output_vars=quotient.outputvars.copy(),
        variable_sorts=SORTS,
        simplify=False,
    )
    composition_equivalence = _compact_bucket_equivalence(composition, compact_assumptions, compact_external_guarantees)
    quotient_equivalence = _compact_bucket_equivalence(quotient, compact_assumptions, compact_quotient_guarantees)
    recomposition_equivalence = _compact_bucket_equivalence(
        recomposed, compact_assumptions, compact_external_guarantees
    )
    composition_countermodels = {
        bucket: _reverse_countermodel(composition, compact_assumptions, compact_external_guarantees, bucket)
        for bucket, (_, reverse) in composition_equivalence.items()
        if not reverse
    }
    quotient_countermodels = {
        bucket: _reverse_countermodel(quotient, compact_assumptions, compact_quotient_guarantees, bucket)
        for bucket, (_, reverse) in quotient_equivalence.items()
        if not reverse
    }
    relations = {
        "C_COMP^disp <= C_COMP": composition_display.refines(composition),
        "C_COMP <= C_COMP^disp": composition.refines(composition_display),
        "Q^disp <= Q": quotient_display.refines(quotient),
        "Q <= Q^disp": quotient.refines(quotient_display),
        "Q <= C_S": quotient.refines(supervisor),
        "C_S <= Q": supervisor.refines(quotient),
        "C_REC <= C_COMP": recomposed.refines(composition),
        "C_COMP <= C_REC": composition.refines(recomposed),
    }
    checks["C_V || (C_COMP / C_V) <= C_COMP"] = relations["C_REC <= C_COMP"]
    table_equivalent = all(
        forward and reverse
        for result in (composition_equivalence, quotient_equivalence)
        for forward, reverse in result.values()
    )
    displayed_contracts_equivalent = all(
        relations[label]
        for label in (
            "C_COMP^disp <= C_COMP",
            "C_COMP <= C_COMP^disp",
            "Q^disp <= Q",
            "Q <= Q^disp",
        )
    )
    operation_checks_passed = (
        all(checks.values()) and all(quotient_checks.values()) and all(recomposition_checks.values())
    )
    passed = operation_checks_passed and table_equivalent and displayed_contracts_equivalent
    if not passed:
        failed = [f"composition: {label}" for label, result in checks.items() if not result]
        failed.extend(f"quotient: {label}" for label, result in quotient_checks.items() if not result)
        failed.extend(f"recomposition: {label}" for label, result in recomposition_checks.items() if not result)
        raise RuntimeError(f"AEB user-facing summary verification failed: {failed}")

    heading("AEB GR(1) CONTRACT EXAMPLE")
    print("""Architecture:
  (d, URG, WRN) -> C_S -- {u, MOV, DCL, STP} -> C_V -> v

Hidden composition interface:
  {u, MOV, DCL, STP}""")  # noqa: WPS355,WPS462  # noqa: WPS355

    _print_user_contract("SAFETY SUPERVISOR C_S", supervisor)
    _print_user_contract("VEHICLE-RESPONSE CONTRACT C_V", vehicle)
    _print_exact_generated_contract("EXACT COMPOSITION RESULT C_COMP = C_S || C_V", composition)
    _print_external_summary(
        "COMPACT FORM OF C_COMP = C_S || C_V",
        "composition",
        composition_equivalence,
        compact_assumptions,
        compact_external_guarantees,
    )
    _print_equivalence_results(
        "C_COMP COMPACT-FORM EQUIVALENCE",
        composition_equivalence,
        composition_countermodels,
        {"guarantee INIT": "initial tracking window v - 1/2 <= X(v) <= v + 1/2"},
    )
    _print_exact_generated_contract("EXACT QUOTIENT RESULT Q = C_COMP / C_V", quotient)
    _print_quotient_summary(quotient_equivalence, compact_assumptions, compact_quotient_guarantees)
    _print_equivalence_results(
        "Q COMPACT-FORM EQUIVALENCE",
        quotient_equivalence,
        quotient_countermodels,
        {"guarantee INV": "generated environment-window/mode/command residual correlations"},
    )
    print("\nAll displayed Table-2 buckets are equivalent to their generated canonical counterparts.")
    _print_external_summary(
        "COMPACT FORM OF C_REC = C_V || Q",
        "recomposition",
        recomposition_equivalence,
        compact_assumptions,
        compact_external_guarantees,
    )
    _print_equivalence_results("C_REC COMPACT-FORM EQUIVALENCE", recomposition_equivalence)

    print("\n" + _SECTION_RULE)
    print("CONTRACT RELATIONS")
    print(_SECTION_RULE)
    for label, result in relations.items():
        status = "proved" if result else "not proved by the finite refinement checker"
        print(f"{label}: {status}")
    if relations["C_REC <= C_COMP"] and relations["C_COMP <= C_REC"]:
        print("C_REC and C_COMP are mutually refining (not necessarily syntactically equal).")

    print("\n" + _SECTION_RULE)
    print("VERIFIED PRINCIPAL RESULTS")
    print(_SECTION_RULE)
    for label, passed in checks.items():
        print(f"{label}: {passed}")

    _print_final_performance()

    # Raw/canonical operation-level displays are intentionally retained for
    # debugging CAVE/refinement behavior. Uncomment when a full audit is needed.
    #
    # print_contract("SAFETY SUPERVISOR C_S", supervisor, original=True)
    # print_contract("VEHICLE-RESPONSE CONTRACT C_V", vehicle, original=True)
    # print_events(events)
    # print_contract("COMPOSITION", composition)
    # print_contract("QUOTIENT", quotient)
    # print_contract("RECOMPOSITION", recomposed)
    #
    # The complete legacy diagnostic driver remains available explicitly as
    # _run_diagnostic_audit(). It is not invoked during normal execution.

    return (
        checks,
        {
            "supervisor": supervisor,
            "vehicle": vehicle,
            "composition": composition,
            "quotient": quotient,
            "recomposed": recomposed,
            "quotient_checks": quotient_checks,
            "recomposition_checks": recomposition_checks,
            "relations": relations,
            "composition_equivalence": composition_equivalence,
            "quotient_equivalence": quotient_equivalence,
            "recomposition_equivalence": recomposition_equivalence,
            "compact_assumptions": compact_assumptions,
            "compact_external_guarantees": compact_external_guarantees,
            "compact_quotient_guarantees": compact_quotient_guarantees,
            "composition_presentation": composition_presentation,
            "quotient_presentation": quotient_presentation,
            "recomposition_presentation": recomposition_presentation,
            "composition_display": composition_display,
            "quotient_display": quotient_display,
            "composition_countermodels": composition_countermodels,
            "quotient_countermodels": quotient_countermodels,
        },
        [],
    )


# =============================================================================
# Command-line entry point
# =============================================================================


def main(argv: list[str] | None = None) -> None:
    """Run the AEB audit, optionally without creating a report file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="write the verified audit only to stdout",
    )
    args = parser.parse_args(argv)
    if args.no_report:
        run_audit()
        return

    output_path = Path(__file__).with_name("aeb_gr1_composition_output.txt")
    displayed_output_path = Path("examples") / output_path.name

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as report:
        with redirect_stdout(
            Tee(
                sys.stdout,
                report,
            )
        ):
            print(
                "Persistent report:",
                displayed_output_path,
            )

            run_audit()

    print(f"\nSaved complete report to: {displayed_output_path}")


if __name__ == "__main__":
    main()
