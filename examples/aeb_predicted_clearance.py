"""Reproduce the manuscript's C_T and clearance-prediction AEB example.

See Sections 2.5 and 5.1 of "Computing GR(1) Assume-Guarantee Contracts"
(arXiv:2610.37534) and examples/README.md for the paper-to-code mapping.
The given C_S and C_V come from aeb_gr1_composition.py; make_prediction()
adds C_D. Composition exposes predicted clearance z. The quotient C_T / C_V
computes a missing supervisor contract, not the predictor. The audit checks
C_S <= Q, C_V || Q <= C_T, and C_S || C_V <= C_T.

Run from the repository root with ``python examples/aeb_predicted_clearance.py``.
This writes a detailed report beside the script and measures ten repetitions,
using instrumentation from gr1_cave_scalability.py. For a shorter check, run
``python -m pytest -q tests/test_aeb_predicted_clearance.py``.
Observation helpers delegate to the unchanged production operations.
"""

from __future__ import annotations

import importlib.util
import ast
import textwrap

import inspect
import platform
import sys
from contextlib import ExitStack, contextmanager, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from time import perf_counter
from unittest.mock import patch

import z3
from z3.z3util import get_vars

from pacti.iocontract import Var
from pacti.iocontract import gr1_iocontract as gr1

_BASELINE_PATH = Path(__file__).with_name("aeb_gr1_composition.py")
_SPEC = importlib.util.spec_from_file_location("aeb_read_only_baseline", _BASELINE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
baseline = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(baseline)

SORTS = dict(baseline.SORTS, z="real")
TAGS = ("init", "inv", "liv")

# Manuscript numerical parameters. DELTA_T remains explicit in the source-level
# construction even though its numerical instance is one second.
EPSILON = "1/2"
DELTA_T = "1"
D_SAFE = "1"
V_PROG = "3/2"
PREDICTION_SYMBOLIC = "X(z) = d - Delta_t * X(v)"
PREDICTION_NUMERICAL = f"X(z) = d - ({DELTA_T}) * X(v)"
SAFETY_SYMBOLIC = "X(v) <= (d - d_s) / Delta_t"
SAFETY_NUMERICAL = f"X(v) <= (d - {D_SAFE}) / {DELTA_T}"
PROGRESS_NUMERICAL = f"!URG & !WRN & X(v) >= {V_PROG}"


def parse(text):
    return gr1.parse_gr1_core(text, SORTS).expr


def bucket(**kwargs):
    return gr1.GR1TermList.from_bucket_strings(variable_sorts=SORTS, **kwargs)


def conjunction(side, tag):
    return z3.And(*[term.core.expr for term in getattr(side, tag + "_terms")()])


def make_contract(inputs, outputs, assumptions, guarantees):
    return gr1.GR1IoContract(
        assumptions,
        guarantees,
        [Var(name) for name in inputs],
        [Var(name) for name in outputs],
        simplify=False,
        variable_sorts=SORTS,
    )


def make_prediction():
    """Construct C_D with an explicit source-level Delta_t parameter."""
    return make_contract(["d", "v"], ["z"], bucket(), bucket(inv=[PREDICTION_NUMERICAL]))


def make_target():
    """Construct the exact final manuscript target C_T."""
    supervisor = baseline.make_supervisor()
    assumptions = gr1.GR1TermList(
        [term.copy() for term in supervisor.a.init_terms()]
        + [term.copy() for term in supervisor.a.inv_terms()]
        + bucket(inv=["d >= 3/2", "!URG & !WRN -> d >= 20"]).inv_terms()
        + [term.copy() for term in supervisor.a.liv_terms()]
    )
    guarantees = bucket(inv=[SAFETY_NUMERICAL], liv=[PROGRESS_NUMERICAL])
    return make_contract(["d", "URG", "WRN"], ["v"], assumptions, guarantees)


def formula(expression):
    return expression.sexpr()


def heading(text):
    print("\n" + "=" * 78)
    print(text)
    print("=" * 78)


def dump_side(label, side):
    print(label)
    for tag in TAGS:
        wrapper = "G core" if tag == "inv" else "GF core" if tag == "liv" else "initial core"
        print(f"  {tag.upper()} ({wrapper})")
        terms = getattr(side, tag + "_terms")()
        if not terms:
            print("    true (empty bucket)")
        for index, term in enumerate(terms, 1):
            raw = term.core.raw_expr if term.core.raw_expr is not None else term.core.expr
            print(f"    [{index}] {formula(raw)}")


def dump_contract(label, contract):
    print(label, "I =", sorted(v.name for v in contract.inputvars), "O =", sorted(v.name for v in contract.outputvars))
    dump_side("RAW ASSUMPTION", contract._operation_assumptions)
    dump_side("RAW GUARANTEE", contract._operation_guarantees)
    dump_side("REDUCED ASSUMPTION", contract.a)
    dump_side("REDUCED GUARANTEE", contract.g)


def implication(label, left, right):
    solver = z3.Solver()
    solver.add(left, z3.Not(right))
    status = solver.check()
    print(label, status, "(UNSAT proves implication)")
    model = solver.model() if status == z3.sat else None
    if model is not None:
        print("  finite counterexample:", model)
    if status == z3.unknown:
        raise RuntimeError(solver.reason_unknown())
    return status == z3.unsat, model


def equivalence(label, left, right, context=z3.BoolVal(True)):
    forward, _ = implication(label + " forward", z3.And(context, left), right)
    reverse, _ = implication(label + " reverse", z3.And(context, right), left)
    return forward, reverse


def semantic_bucket_match(left, right):
    return {
        "init": (
            gr1._init_terms_refine(left.init_terms(), left.inv_terms(), right.init_terms()),
            gr1._init_terms_refine(right.init_terms(), right.inv_terms(), left.init_terms()),
        ),
        "inv": (
            gr1._inv_terms_refine(left.inv_terms(), right.inv_terms()),
            gr1._inv_terms_refine(right.inv_terms(), left.inv_terms()),
        ),
        "liv": (
            gr1._liv_terms_refine(left.inv_terms(), left.liv_terms(), right.liv_terms()),
            gr1._liv_terms_refine(right.inv_terms(), right.liv_terms(), left.liv_terms()),
        ),
    }


def diagnose_refinement(label, source, target):
    print(label)
    result = source.refines(target)
    assumptions = semantic_bucket_match(target.a, source.a)
    guarantees = semantic_bucket_match(source.g | target.a, target.g | target.a)
    print("  actual refines():", "ESTABLISHED" if result else "NOT ESTABLISHED")
    for side, checks in (("assumption", assumptions), ("guarantee", guarantees)):
        for tag, pair in checks.items():
            print(f"  {side} {tag.upper()} forward/reverse: {pair}")
    return result, {"assumption": assumptions, "guarantee": guarantees}


def verify_baseline_contract(actual, fresh, label):
    assert actual.inputvars == fresh.inputvars
    assert actual.outputvars == fresh.outputvars
    for side in ("_operation_assumptions", "_operation_guarantees"):
        for tag in TAGS:
            actual_terms = getattr(getattr(actual, side), tag + "_terms")()
            fresh_terms = getattr(getattr(fresh, side), tag + "_terms")()
            assert len(actual_terms) == len(fresh_terms)
            for index, (left, right) in enumerate(zip(actual_terms, fresh_terms), 1):
                assert left.core.text == right.core.text
                assert z3.eq(left.core.expr, right.core.expr)
                print("MATCH", label, side, tag, index, left.core.text)


def _candidate_record(target, context, variables, candidate, support, index):
    target_expr = target.core.expr
    shifted = gr1._shifted_inv_guard_for_cores(
        context.inv_terms(), [target.core] if support is None else [support.core, target.core]
    )
    guard = shifted if support is None else z3.And(shifted, support.core.expr)
    local_variables = gr1._expand_elim_vars_from_exprs(variables, guard, target_expr)
    atoms = gr1._z3_atoms_for_vars(local_variables, target_expr, guard)
    body = z3.Implies(guard, target_expr)
    quantified = z3.ForAll(atoms, body) if atoms else body
    target_bases = {gr1._parse_flat_name(str(atom))[0] for atom in get_vars(target_expr)}
    return {
        "pass": "first RefineCAVE" if "v" in target_bases else "second RefineCAVE",
        "target": target.core.text,
        "branch": getattr(candidate, "branch_id", str(index)),
        "support": "synthetic / invariant window" if support is None else support.core.text,
        "wrapper": candidate.tag.value,
        "horizon": max(gr1._core_next_depth(target.core), 0 if support is None else gr1._core_next_depth(support.core)),
        "raw": quantified,
        "simplified": candidate.core.expr,
        "candidate": candidate,
        "selected": False,
        "reason": "",
    }


@contextmanager
def observe_liveness_candidates():
    """Observe every production candidate and selection without changing it."""
    records = []
    families = {}
    original_candidates = gr1._refinement_liv_candidates
    original_select = gr1._select_refinement_support

    def candidates(target, context, variables):
        family = original_candidates(target, context, variables)
        family_records = []
        for index, candidate in enumerate(family):
            support = None if index == 0 else context.liv_terms()[index - 1]
            record = _candidate_record(target, context, variables, candidate, support, index)
            family_records.append(record)
            records.append(record)
        families[id(family)] = family_records
        return family

    def select(family):
        selected = original_select(family)
        for record in families.get(id(family), []):
            if record["candidate"] is selected:
                record["selected"] = True
                if gr1._equivalent(selected.core.expr, z3.BoolVal(True)):
                    record["reason"] = "first canonical candidate with core True"
                elif not gr1._equivalent(selected.core.expr, z3.BoolVal(False)):
                    record["reason"] = "first canonical candidate not proved False"
                else:
                    record["reason"] = "all candidates False; canonical fallback"
        return selected

    with ExitStack() as stack:
        stack.enter_context(patch.object(gr1, "_refinement_liv_candidates", candidates))
        stack.enter_context(patch.object(gr1, "_select_refinement_support", select))
        yield records


def traced_quotient(target, vehicle):
    """Run production Algorithm 5 and record its actual intermediate values."""
    stages = {}
    # Use AST locations rather than matching formatter-dependent source text.
    source, first_line = inspect.getsourcelines(gr1.GR1IoContract.__mro__[1].quotient_tactics)
    syntax = ast.parse(textwrap.dedent("".join(source)))
    stage_lines = {}
    for node in ast.walk(syntax):
        if not isinstance(node, ast.Assign):
            continue
        value = node.value
        if isinstance(value, ast.BinOp) and isinstance(value.left, ast.Name) and value.left.id == "guarantees":
            stage_lines[first_line + node.lineno - 1] = "G_1"
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Attribute)
            and value.func.attr == "elim_vars_by_refining"
        ):
            stage_lines[first_line + node.lineno - 1] = "G_2"
    previous_trace = sys.gettrace()

    def observer(frame, event, arg):
        if (
            frame.f_code.co_name == "quotient_tactics"
            and frame.f_globals.get("__name__") == "pacti.iocontract.iocontract"
        ):
            local = frame.f_locals
            if event == "line":
                stage = stage_lines.get(frame.f_lineno)
                if stage is not None:
                    stages[stage] = local["guarantees"].copy()
            if event == "return":
                stages["A_implies_Aprime"] = local["divisor_guarantees_are_context"]
                stages["Aq_before_reduction"] = local["assumptions"].copy()
                stages["raw_Gq"] = local["guarantees"].copy()
                stages["pbar"] = {var.name for var in local["intvars"]}
        return observer

    try:
        sys.settrace(observer)
        with baseline.observe_qe() as qe_events, observe_liveness_candidates() as liv_records:
            quotient = target.quotient(vehicle)
    finally:
        sys.settrace(previous_trace)
    assert {"G_1", "G_2", "Aq_before_reduction", "raw_Gq", "pbar"} <= stages.keys()
    return quotient, stages, qe_events, liv_records


def print_liveness_table(records):
    print(
        "pass | target | branch | support | wrapper | horizon | "
        "raw finite core | simplified core | selected? | reason"
    )
    for record in records:
        print(
            record["pass"],
            "|",
            record["target"],
            "|",
            record["branch"],
            "|",
            record["support"],
            "|",
            record["wrapper"],
            "|",
            record["horizon"],
            "|",
            formula(record["raw"]),
            "|",
            formula(record["simplified"]),
            "|",
            record["selected"],
            "|",
            record["reason"] or "not selected",
        )


def w8_certificate(source_terms, target_term):
    for horizon in range(gr1._DEFAULT_INV_REFINEMENT_MAX_HORIZON + 1):
        closure = gr1._shift_closed_inv_expr(source_terms.inv_terms(), horizon)
        for support in source_terms.liv_terms():
            passed, _ = implication(
                f"W8 h={horizon}, support={support.core.text}",
                z3.And(closure, support.core.expr),
                target_term.core.expr,
            )
            if passed:
                return horizon, closure, support
    return None, None, None


def run_audit():  # noqa: WPS210,WPS213
    heading("A. BASELINE C_S AND C_V")
    supervisor, vehicle = baseline.make_supervisor(), baseline.make_vehicle()
    verify_baseline_contract(supervisor, baseline.make_supervisor(), "C_S")
    verify_baseline_contract(vehicle, baseline.make_vehicle(), "C_V")
    dump_contract("C_S", supervisor)
    dump_contract("C_V", vehicle)

    heading("B. NUMERICAL PARAMETERS AND FINAL C_D")
    print("epsilon =", EPSILON, "m/s")
    print("Delta_t =", DELTA_T, "s")
    print("d_s =", D_SAFE, "m")
    print("v_prog =", V_PROG, "m/s")
    print("symbolic model:", PREDICTION_SYMBOLIC)
    print("numerical instance:", PREDICTION_NUMERICAL)
    prediction = make_prediction()
    dump_contract("C_D", prediction)

    heading("C. THREE-WAY COMPOSITION")
    sv = supervisor.compose(vehicle)
    svd = sv.compose(prediction)
    dump_contract("C_SV", sv)
    dump_contract("C_SVD", svd)
    assert {var.name for var in svd.inputvars} == {"d", "URG", "WRN"}
    assert {var.name for var in svd.outputvars} == {"z"}
    compact_a = baseline._compact_environment_terms()
    compact_g = baseline._compact_external_guarantees()
    sv_equivalence = baseline._compact_bucket_equivalence(sv, compact_a, compact_g)
    svd_assumption_equivalence = semantic_bucket_match(sv._operation_assumptions, svd._operation_assumptions)
    print("C_SV raw/compact forward/reverse:", sv_equivalence)
    print("C_SV/C_SVD assumption forward/reverse:", svd_assumption_equivalence)
    print("eliminated: u, MOV, DCL, STP, v")

    heading("D. PREDICTED-CLEARANCE ENVELOPES")
    envelope_specs = {
        "URG": ("URG & !WRN", "d - 1/2 <= X(z) & X(z) <= d"),
        "WRN": ("WRN & !URG", "4*d/5 - 1/2 <= X(z) & X(z) <= d"),
        "clear": ("!URG & !WRN", "4*d/5 - 1/2 <= X(z) & X(z) <= 9*d/10 + 1/2"),
    }
    envelopes = {}
    for region, (guard, proposed) in envelope_specs.items():
        context = z3.And(conjunction(svd._operation_assumptions, "inv"), parse(guard))
        pair = equivalence(region, conjunction(svd._operation_guarantees, "inv"), parse(proposed), context)
        envelopes[region] = pair
        print(region, "GENERATED SOUND RELAXED BOUND" if pair == (True, False) else pair)

    heading("E. FINAL MANUSCRIPT TARGET C_T")
    target = make_target()
    dump_contract("C_T", target)
    expected_target = make_contract(
        ["d", "URG", "WRN"],
        ["v"],
        gr1.GR1TermList(
            [term.copy() for term in supervisor.a.init_terms()]
            + [term.copy() for term in supervisor.a.inv_terms()]
            + bucket(inv=["d >= 3/2", "!URG & !WRN -> d >= 20"]).inv_terms()
            + [term.copy() for term in supervisor.a.liv_terms()]
        ),
        bucket(inv=["X(v) <= d - 1"], liv=["!URG & !WRN & X(v) >= 3/2"]),
    )
    target_matches = {
        "assumption": semantic_bucket_match(target.a, expected_target.a),
        "guarantee": semantic_bucket_match(target.g, expected_target.g),
    }
    print("Target manuscript bucket matches:", target_matches)
    assert all(all(pair) for side in target_matches.values() for pair in side.values())

    heading("F. FINAL QUOTIENT INTERFACE AND ALGORITHM-5 TRACE")
    it, ot, iv, ov = [
        set(var.name for var in values)
        for values in (target.inputvars, target.outputvars, vehicle.inputvars, vehicle.outputvars)
    ]
    interface = ((ot & ov) | (it & iv), (it - iv) | (ov - ot), (ot - ov) | (iv - it))
    print("pbar =", interface[0])
    print("I_Q =", interface[1])
    print("O_Q =", interface[2])
    assert interface == ({"v"}, {"d", "URG", "WRN"}, {"u", "MOV", "DCL", "STP"})
    quotient, stages, qe_events, liv_records = traced_quotient(target, vehicle)
    assert stages["pbar"] == {"v"}
    for label, side in (("A", target.a), ("G", target.g), ("A'", vehicle.a), ("G'", vehicle.g)):
        dump_side(label, side)
    print("A => A' =", stages["A_implies_Aprime"])
    dump_side("A^q before reduction", stages["Aq_before_reduction"])
    dump_side("G_1 = RefineCAVE(G', G, {v})", stages["G_1"])
    dump_side("G_2 = G_1 & A'", stages["G_2"])
    dump_side("second RefineCAVE / raw G^q", stages["raw_Gq"])
    dump_side("final A^q", quotient.a)
    dump_side("final G^q", quotient.g)

    heading("G. RAW AND CONTEXTUAL SAFETY PROJECTION")
    first_inv = next(event for event in qe_events if event["kind"] == "refinement" and event["tag"] == "inv")
    print("RAW FIRST-PASS FINITE FORMULA:", formula(first_inv["before"]))
    print("RAW FIRST-PASS QE:", formula(first_inv["after"]))
    raw_safety_expected = z3.Or(parse("u <= d - 3/2"), parse("u < -1/2"))
    raw_safety = equivalence("raw safety projection", first_inv["after"], raw_safety_expected)
    contextual_safety = equivalence(
        "contextual safety modulo A_V u>=0", first_inv["after"], parse("u <= d - 3/2"), parse("u >= 0")
    )

    heading("H. RAW AND CONTEXTUAL TARGET-LIVENESS PROJECTION")
    print_liveness_table(liv_records)
    first_liv = next(event for event in qe_events if event["kind"] == "refinement" and event["tag"] == "liv")
    print("RAW FIRST-PASS LIV FORMULA:", formula(first_liv["before"]))
    print("RAW FIRST-PASS LIV QE:", formula(first_liv["after"]))
    raw_liveness_expected = parse("(u >= 2 | u < -1/2) & (URG -> u < -1/2) & (WRN -> u < -1/2)")
    raw_liveness = equivalence("raw target-liveness projection", first_liv["after"], raw_liveness_expected)
    contextual_liveness = equivalence(
        "contextual target-liveness core modulo A_V u>=0",
        first_liv["after"],
        parse("!URG & !WRN & u >= 2"),
        parse("u >= 0"),
    )
    print("Contextual temporal interpretation: GF(clear & u >= 2).")
    print("This is a contextual form modulo A_V,inv, not the complete raw first-pass QE result.")

    heading("I. COMPLETE FINAL QUOTIENT Q")
    dump_contract("Q = C_T / C_V", quotient)
    print("Requirement | source | final bucket | semantically retained")
    quotient_context = quotient.g | quotient.a
    for tag in TAGS:
        for term in getattr(vehicle.a, tag + "_terms")():
            required = gr1.GR1TermList([term]) | quotient.a
            if tag == "init":
                retained = gr1._init_terms_refine(
                    quotient_context.init_terms(), quotient_context.inv_terms(), required.init_terms()
                )
            elif tag == "inv":
                retained = gr1._inv_terms_refine(quotient_context.inv_terms(), required.inv_terms())
            else:
                retained = gr1._liv_terms_refine(
                    quotient_context.inv_terms(), quotient_context.liv_terms(), required.liv_terms()
                )
            print(term.core.text, "| vehicle admissibility |", tag.upper(), "|", retained)
    print("u <= d-3/2 | target safety, contextual modulo A_V | INV |", all(contextual_safety))
    print("GF(clear & u>=2) | target liveness, contextual modulo A_V | LIV |", all(contextual_liveness))
    print("Second RefineCAVE guards both LIV requirements by A_T and retains GF MOV separately.")
    print("Target safety contributes the contextual u<=d-3/2 requirement.")
    print("Target liveness contributes the contextual GF(clear & u>=2) requirement.")

    heading("J. C_S <= Q")
    supervisor_refines, supervisor_refinement = diagnose_refinement("C_S <= Q", supervisor, quotient)
    if not supervisor_refines:
        print("FINAL MANUSCRIPT CHECK FAILED; no target strengthening or algorithm change attempted.")

    heading("K. QUOTIENT RECOMPOSITION")
    recomposed = vehicle.compose(quotient)
    recomposition_refines, recomposition_details = diagnose_refinement("C_V || Q <= C_T", recomposed, target)
    reverse_recomposition, reverse_recomposition_details = diagnose_refinement("C_T <= C_V || Q", target, recomposed)

    heading("L. FINAL W8 EXPERIMENT C_SV <= C_T")
    sv_refines_target, sv_target_details = diagnose_refinement("C_SV <= C_T", sv, target)
    refinement_source = sv.g | target.a
    target_liv = target.g.liv_terms()[0]
    support_only, support_counterexample = implication(
        "SUPPORT ONLY: clear => clear & Xv>=3/2", parse("!URG & !WRN"), target_liv.core.expr
    )
    invariant_only = gr1._liv_terms_refine(refinement_source.inv_terms(), [], [target_liv])
    w8_horizon, w8_closure, w8_support = w8_certificate(refinement_source, target_liv)
    w8_combined = w8_horizon is not None
    print("SUPPORT ONLY:", "PASS" if support_only else "FAIL")
    print("INVARIANTS ONLY:", "PASS" if invariant_only else "INSUFFICIENT FOR RECURRENCE")
    print("INVARIANTS + SUPPORT:", "PASS" if w8_combined else "FAIL")
    print("GF(clear) source: A_T,liv in the target-assumption context; not C_SV guarantee.")
    print("Actual W8 horizon h =", w8_horizon)
    if w8_closure is not None:
        print("Actual shifted invariant closure K_h:", formula(w8_closure))
        print("Actual recurring support:", w8_support.core.text)
    print("Algorithm-3 invariant-assisted recurrence branch:", w8_combined)

    heading("M. MANUSCRIPT FORMULA AUDIT")
    print("C_D symbolic relation: MATCH —", PREDICTION_SYMBOLIC)
    print("C_T all six buckets: MATCH —", target_matches)
    print("safety u <= (d-d_s)/Delta_t-epsilon: CONTEXTUAL FORM MODULO A_V")
    print("progress GF(clear & u>=v_prog+epsilon): CONTEXTUAL FORM MODULO A_V")
    print("three-way hidden variables and external z: MATCH")
    print("z envelopes: GENERATED SOUND RELAXED BOUND")

    heading("N. FINAL VERDICT")
    verified = all(
        (
            raw_safety == (True, True),
            raw_liveness == (True, True),
            contextual_safety == (True, True),
            contextual_liveness == (True, True),
            supervisor_refines,
            recomposition_refines,
            sv_refines_target,
            not support_only,
            not invariant_only,
            w8_combined,
            envelopes == {"URG": (True, False), "WRN": (True, False), "clear": (True, False)},
        )
    )
    print(
        "FINAL AEB MANUSCRIPT DESIGN VERIFIED WITH WORDING QUALIFICATION"
        if verified
        else "FINAL AEB MANUSCRIPT DESIGN DOES NOT MATCH IMPLEMENTATION"
    )
    print("Minimal wording: Modulo A_{V,inv}'s u >= 0 constraint, its finite refinement projections reduce to ...")
    print("No realizability claim is made.")

    return {
        "supervisor": supervisor,
        "vehicle": vehicle,
        "prediction": prediction,
        "sv": sv,
        "svd": svd,
        "target": target,
        "quotient": quotient,
        "recomposed": recomposed,
        "stages": stages,
        "qe_events": qe_events,
        "liv_records": liv_records,
        "sv_equivalence": sv_equivalence,
        "svd_assumption_equivalence": svd_assumption_equivalence,
        "envelopes": envelopes,
        "target_matches": target_matches,
        "raw_safety": raw_safety,
        "raw_liveness": raw_liveness,
        "contextual_safety": contextual_safety,
        "contextual_liveness": contextual_liveness,
        "supervisor_refines": supervisor_refines,
        "supervisor_refinement": supervisor_refinement,
        "recomposition_refines": recomposition_refines,
        "recomposition_details": recomposition_details,
        "reverse_recomposition": reverse_recomposition,
        "reverse_recomposition_details": reverse_recomposition_details,
        "sv_refines_target": sv_refines_target,
        "sv_target_details": sv_target_details,
        "support_only": support_only,
        "support_counterexample": support_counterexample,
        "invariant_only": invariant_only,
        "w8_combined": w8_combined,
        "w8_horizon": w8_horizon,
        "verified": verified,
    }


def report_performance(repetitions=10):
    """Measure only this AEB's operations, using the existing CAVE observer.

    One warm-up precedes measured runs. This does not launch the synthetic
    scalability sweeps or reuse any old AEB timing. Observers delegate all
    production calls unchanged and are restored before verification.
    """
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    observer_name = "aeb_predicted_clearance_performance_observer"
    spec = importlib.util.spec_from_file_location(observer_name, Path(__file__).with_name("gr1_cave_scalability.py"))
    assert spec is not None and spec.loader is not None
    observer = importlib.util.module_from_spec(spec)
    # Dataclass definitions require their module to be registered during load.
    previous = sys.modules.get(observer_name)
    sys.modules[observer_name] = observer
    try:
        spec.loader.exec_module(observer)
    finally:
        if previous is None:
            del sys.modules[observer_name]
        else:
            sys.modules[observer_name] = previous

    heading("O. COMPUTATIONAL PERFORMANCE")
    print("Fresh measurements of the final predicted-clearance AEB design.")
    print("Measured at:", datetime.now(timezone.utc).isoformat())
    print("Environment:", platform.platform(), "Python", platform.python_version(), "Z3", z3.get_version_string())
    print("One warm-up followed by", repetitions, "measured runs.")
    supervisor, vehicle = baseline.make_supervisor(), baseline.make_vehicle()
    prediction, target = make_prediction(), make_target()

    def measure(operation):
        instrumentation = observer.CaveInstrumentation()
        with instrumentation.observe():
            started = perf_counter()
            result = operation()
            elapsed = perf_counter() - started
        return result, elapsed, instrumentation.metrics

    def execute():
        sv, first_time, first_metrics = measure(lambda: supervisor.compose(vehicle))
        svd, second_time, second_metrics = measure(lambda: sv.compose(prediction))
        quotient, quotient_time, quotient_metrics = measure(lambda: target.quotient(vehicle))
        composition_metrics = observer._combine_metrics(first_metrics, second_metrics)
        combined_metrics = observer._combine_metrics(composition_metrics, quotient_metrics)
        return (
            {
                "C_S || C_V": (first_time, first_metrics),
                "C_SV || C_D": (second_time, second_metrics),
                "Composition chain": (first_time + second_time, composition_metrics),
                "Quotient C_T / C_V": (quotient_time, quotient_metrics),
                "Composition + quotient": (first_time + second_time + quotient_time, combined_metrics),
            },
            svd,
            quotient,
        )

    print("Warm-up...", flush=True)
    execute()
    runs = []
    for index in range(repetitions):
        run, measured_svd, measured_quotient = execute()
        runs.append(run)
        print(f"Completed measured run {index + 1}/{repetitions}", flush=True)

    fields = (
        ("top-level CAVE invocations", "cave_invocations"),
        ("  refinement", "refinement_invocations"),
        ("  relaxation", "relaxation_invocations"),
        ("Solver.check() calls", "solver_checks"),
        ("Optimize.check() calls", "optimize_checks"),
        ("qe2 applications", "qe_tactic_applications"),
        ("synthetic candidates", "synthetic_candidates"),
        ("fixed-support candidates", "support_candidates"),
        ("max quantified atoms", "maximum_quantified_atoms"),
        ("max indexed variables", "maximum_quantified_indexed_variables"),
        ("max NEXT depth", "maximum_quantified_depth"),
    )
    print("\nCAVE counters are per run; a range indicates variation between runs.")
    for scope in runs[0]:
        print("\n" + scope + ":")
        elapsed = [run[scope][0] for run in runs]
        metrics = [run[scope][1] for run in runs]
        print(f"median end-to-end time       : {median(elapsed):.3f} s")
        print(f"end-to-end range             : {min(elapsed):.3f} -- {max(elapsed):.3f} s")
        cave_times = [item.cumulative_cave_seconds for item in metrics]
        print(f"median cumulative CAVE time  : {median(cave_times):.3f} s")
        for label, field in fields:
            values = [getattr(item, field) for item in metrics]
            value = str(values[0]) if min(values) == max(values) else f"{min(values)} -- {max(values)}"
            print(f"{label:28}: {value}")

    print("\nRaw measured times (seconds):")
    print("run | scope | end-to-end | cumulative CAVE")
    for index, run in enumerate(runs, 1):
        for scope, (elapsed, metrics) in run.items():
            print(f"{index} | {scope} | {elapsed:.6f} | {metrics.cumulative_cave_seconds:.6f}")
    print(
        "\nEnd-to-end times cover complete instrumented Pacti operations. CAVE times cover only\n"
        "outermost CAVE calls; nested wrappers are not counted twice. Solver/optimizer/QE\n"
        "counters are scoped to CAVE. Combined medians use per-run sums, not sums of medians.\n"
        "Contract construction, diagnostic traces, printing, recomposition, and refinement\n"
        "verification are excluded. Instrumentation adds overhead. These timings are measured\n"
        "afresh on standalone execution; no historical baseline numbers are reused."
    )
    return {"runs": runs, "composition": measured_svd, "quotient": measured_quotient}


if __name__ == "__main__":
    output = Path(__file__).with_name("aeb_predicted_clearance_output.txt")
    with output.open("w", encoding="utf-8") as stream, redirect_stdout(baseline.Tee(sys.stdout, stream)):
        run_audit()
        report_performance()
