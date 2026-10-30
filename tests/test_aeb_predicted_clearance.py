"""Focused regressions for the final manuscript predicted-clearance AEB design."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def module():
    path = Path(__file__).parents[1] / "examples" / "aeb_predicted_clearance.py"
    spec = spec_from_file_location("aeb_predicted_clearance", path)
    assert spec is not None and spec.loader is not None
    loaded = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(loaded)
    return loaded


@pytest.fixture(scope="module")
def audit(module):
    return module.run_audit()


def test_baseline_supervisor_and_vehicle_are_exact_factory_matches(module, audit):
    for key, factory in (("supervisor", module.baseline.make_supervisor), ("vehicle", module.baseline.make_vehicle)):
        actual, fresh = audit[key], factory()
        assert actual.inputvars == fresh.inputvars
        assert actual.outputvars == fresh.outputvars
        for side in ("_operation_assumptions", "_operation_guarantees"):
            for tag in module.TAGS:
                left = getattr(getattr(actual, side), tag + "_terms")()
                right = getattr(getattr(fresh, side), tag + "_terms")()
                assert [term.core.text for term in left] == [term.core.text for term in right]
                assert all(module.z3.eq(a.core.expr, b.core.expr) for a, b in zip(left, right))


def test_prediction_uses_explicit_delta_t_and_three_way_interface(module, audit):
    assert "Delta_t" in module.PREDICTION_SYMBOLIC
    assert module.DELTA_T == "1"
    assert f"({module.DELTA_T}) * X(v)" in module.PREDICTION_NUMERICAL
    prediction = audit["prediction"]
    expected = module.bucket(inv=["X(z) = d - 1 * X(v)"])
    assert module.semantic_bucket_match(prediction.g, expected)["inv"] == (True, True)
    assert {var.name for var in audit["svd"].inputvars} == {"d", "URG", "WRN"}
    assert {var.name for var in audit["svd"].outputvars} == {"z"}
    assert all(pair == (True, True) for pair in audit["svd_assumption_equivalence"].values())


def test_three_clearance_envelopes_are_strict_one_way_consequences(audit):
    assert audit["envelopes"] == {"URG": (True, False), "WRN": (True, False), "clear": (True, False)}


def test_final_target_matches_all_six_manuscript_buckets(module, audit):
    target = audit["target"]
    assert all(all(pair) for side in audit["target_matches"].values() for pair in side.values())
    assert len(target.a.init_terms()) == 4
    assert len(target.a.inv_terms()) == 7
    assert len(target.a.liv_terms()) == 1
    assert not target.g.init_terms()
    assert len(target.g.inv_terms()) == 1
    assert len(target.g.liv_terms()) == 1
    assert module.gr1._equivalent(target.a.liv_terms()[0].core.expr, module.parse("!URG & !WRN"))
    assert module.gr1._equivalent(target.g.liv_terms()[0].core.expr, module.parse("!URG & !WRN & X(v) >= 3/2"))


def test_final_quotient_interface_and_complete_trace(audit):
    quotient = audit["quotient"]
    assert audit["stages"]["pbar"] == {"v"}
    assert {var.name for var in quotient.inputvars} == {"d", "URG", "WRN"}
    assert {var.name for var in quotient.outputvars} == {"u", "MOV", "DCL", "STP"}
    assert audit["stages"]["A_implies_Aprime"] is False
    assert {"G_1", "G_2", "raw_Gq", "Aq_before_reduction"} <= audit["stages"].keys()


def test_raw_and_contextual_safety_projections_are_exact(audit):
    assert audit["raw_safety"] == (True, True)
    assert audit["contextual_safety"] == (True, True)


def test_raw_and_contextual_target_liveness_are_traced(audit):
    assert audit["raw_liveness"] == (True, True)
    assert audit["contextual_liveness"] == (True, True)
    assert audit["liv_records"]
    assert any(record["selected"] for record in audit["liv_records"])
    assert any(record["support"] == "synthetic / invariant window" for record in audit["liv_records"])
    assert any(record["support"] == "(!(URG) and !(WRN))" for record in audit["liv_records"])


def test_final_quotient_retains_vehicle_admissibility(module, audit):
    quotient, vehicle = audit["quotient"], audit["vehicle"]
    assert [len(getattr(quotient.a, tag + "_terms")()) for tag in module.TAGS] == [1, 1, 1]
    assert [len(getattr(quotient.g, tag + "_terms")()) for tag in module.TAGS] == [1, 1, 2]
    source = quotient.g | quotient.a
    for tag in module.TAGS:
        for term in getattr(vehicle.a, tag + "_terms")():
            requirement = module.gr1.GR1TermList([term]) | quotient.a
            if tag == "init":
                assert module.gr1._init_terms_refine(source.init_terms(), source.inv_terms(), requirement.init_terms())
            elif tag == "inv":
                assert module.gr1._inv_terms_refine(source.inv_terms(), requirement.inv_terms())
            else:
                assert module.gr1._liv_terms_refine(source.inv_terms(), source.liv_terms(), requirement.liv_terms())


def test_final_refinement_and_recomposition_properties(audit):
    assert audit["supervisor_refines"] is True
    assert audit["recomposition_refines"] is True
    assert audit["reverse_recomposition"] is False
    assert audit["sv_refines_target"] is True


def test_w8_three_way_diagnostic(audit):
    assert audit["support_only"] is False
    assert audit["support_counterexample"] is not None
    assert audit["invariant_only"] is False
    assert audit["w8_combined"] is True
    assert audit["w8_horizon"] is not None
    assert audit["verified"] is True


def test_runtime_report_measures_final_operations_without_changing_results(module, audit, capsys):
    original_refine = module.gr1.GR1TermList.elim_vars_by_refining
    original_check = module.z3.Solver.check
    performance = module.report_performance(repetitions=1)
    assert module.gr1.GR1TermList.elim_vars_by_refining is original_refine
    assert module.z3.Solver.check is original_check
    for key, reference in (("composition", audit["svd"]), ("quotient", audit["quotient"])):
        measured = performance[key]
        assert measured.refines(reference)
        assert reference.refines(measured)
    run = performance["runs"][0]
    stages = [run[name] for name in ("C_S || C_V", "C_SV || C_D", "Quotient C_T / C_V")]
    combined_time, combined = run["Composition + quotient"]
    assert combined_time == pytest.approx(sum(elapsed for elapsed, _ in stages))
    for elapsed, metrics in stages:
        assert 0 < metrics.cumulative_cave_seconds <= elapsed
        assert metrics.cave_invocations == metrics.refinement_invocations + metrics.relaxation_invocations
        assert metrics.qe_tactic_applications > 0
    assert combined.cave_invocations == sum(metrics.cave_invocations for _, metrics in stages)
    assert combined.maximum_quantified_depth == max(metrics.maximum_quantified_depth for _, metrics in stages)
    output = capsys.readouterr().out
    for label in (
        "COMPUTATIONAL PERFORMANCE",
        "median end-to-end time",
        "median cumulative CAVE time",
        "Solver.check() calls",
        "Optimize.check() calls",
        "qe2 applications",
        "synthetic candidates",
        "fixed-support candidates",
        "max quantified atoms",
        "max indexed variables",
        "max NEXT depth",
        "Raw measured times",
    ):
        assert label in output
