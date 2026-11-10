"""Focused regressions for the final hidden-interface AEB case study."""

import contextlib
import importlib.util
import io
from pathlib import Path

import pytest
import z3
from z3.z3util import get_vars

from pacti.iocontract import Var
from pacti.iocontract import gr1_iocontract as gr1

_SPEC = importlib.util.spec_from_file_location(
    "aeb_gr1_composition", Path(__file__).parents[1] / "examples" / "aeb_gr1_composition.py"
)
assert _SPEC is not None and _SPEC.loader is not None
example = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(example)


@pytest.fixture(scope="module")
def audit():
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        checks, contracts, events = example.run_audit()
    return checks, contracts, events, output.getvalue()


def test_exact_target_contracts():
    supervisor = example.make_supervisor()
    vehicle = example.make_vehicle()
    assert {var.name for var in supervisor.inputvars} == {"d", "URG", "WRN"}
    assert {var.name for var in supervisor.outputvars} == {"u", "MOV", "DCL", "STP"}
    assert {var.name for var in vehicle.inputvars} == {"u", "MOV", "DCL", "STP"}
    assert {var.name for var in vehicle.outputvars} == {"v"}
    assert [len(getattr(supervisor.g, f"{tag}_terms")()) for tag in example.BUCKETS] == [4, 11, 1]
    assert [len(getattr(vehicle.a, f"{tag}_terms")()) for tag in example.BUCKETS] == [2, 5, 1]
    assert [len(getattr(vehicle.g, f"{tag}_terms")()) for tag in example.BUCKETS] == [1, 3, 0]


def test_composition_hides_complete_supervisor_vehicle_interface(audit):
    _, contracts, _, _ = audit
    composed = contracts["composition"]
    assert {var.name for var in composed.inputvars} == {"d", "URG", "WRN"}
    assert {var.name for var in composed.outputvars} == {"v"}
    for bucket in (composed.a, composed.g, composed._operation_assumptions, composed._operation_guarantees):
        for hidden in ("u", "MOV", "DCL", "STP"):
            assert Var(hidden) not in bucket.vars
        for term in bucket.terms:
            assert all(
                gr1._parse_flat_name(str(variable))[0] not in {"u", "MOV", "DCL", "STP"}
                for variable in get_vars(term.core.expr)
            )


def test_generated_compatibility_matches_documented_condition(audit):
    checks, contracts, _, _ = audit
    assert checks["generated compatibility => documented compatibility"]
    assert checks["documented compatibility => generated compatibility"]
    assumption_liv = contracts["composition"]._operation_assumptions.liv_terms()
    assert [term.core.text for term in assumption_liv] == ["(!(URG) and !(WRN))"]


def test_supervisor_liveness_rejects_alternating_hazard_modes():
    supervisor = example.make_supervisor()
    alternating_hazards = gr1.GR1Behavior(
        states=[
            {"d": 20, "URG": False, "WRN": False},
            {"d": 10, "URG": True, "WRN": False},
            {"d": 12, "URG": False, "WRN": True},
        ],
        loop_start=1,
    )

    assert not supervisor.a.contains_behavior(alternating_hazards)


def test_documented_quantitative_projections_hold(audit):
    checks, _, _, _ = audit
    for label in (
        "urgent projection",
        "warning projection",
        "warning uniform upper bound",
        "clear projection",
        "global nonnegative next speed",
        "global next-speed upper envelope",
        "clear uniform range",
    ):
        assert checks[label]


def test_initial_projection_contains_v_equals_d_over_ten(audit):
    _, contracts, _, _ = audit
    composed = contracts["composition"]
    source = composed._operation_assumptions | composed._operation_guarantees
    expected = gr1.GR1TermList.from_bucket_formulas(init=[gr1.parse_gr1_core("v=d/10", example.SORTS)])
    assert gr1._init_terms_refine(source.init_terms(), source.inv_terms(), expected.init_terms())


def test_public_quotient_law_and_interfaces(audit):
    checks, contracts, _, _ = audit
    quotient = contracts["quotient"]
    recomposed = contracts["recomposed"]
    composed = contracts["composition"]
    assert {var.name for var in quotient.inputvars} == {"d", "URG", "WRN"}
    assert {var.name for var in quotient.outputvars} == {"u", "MOV", "DCL", "STP"}
    assert recomposed.shares_io_with(composed)
    assert checks["C_V || (C_COMP / C_V) <= C_COMP"]
    assert recomposed.refines(composed)


def test_normal_output_is_compact_and_omits_raw_sections(audit):
    _, contracts, events, output = audit
    assert events == []
    for heading in (  # noqa: WPS352
        "SAFETY SUPERVISOR C_S",
        "VEHICLE-RESPONSE CONTRACT C_V",
        "EXACT COMPOSITION RESULT C_COMP = C_S || C_V",
        "COMPACT FORM OF C_COMP = C_S || C_V",
        "EXACT QUOTIENT RESULT Q = C_COMP / C_V",
        "COMPACT FORM OF Q = C_COMP / C_V",
        "COMPACT FORM OF C_REC = C_V || Q",
    ):
        assert heading in output
    assert "VERIFIED COMPACT FORM" in output
    assert "VERIFIED EQUIVALENT COMPACT FORM" in output
    assert "presentation_view()" in output
    assert "GR1TermList.to_pretty_string()" in output
    assert "□(" in output
    assert "□◇(" in output
    assert "→" in output
    assert "¬(" in output
    assert "This is a semantically verified principal summary" in output
    assert contracts["quotient"].to_pretty_string() not in output
    assert contracts["recomposed"].to_pretty_string() not in output
    assert contracts["composition"].to_pretty_string() not in output
    assert "Q <= C_S: not proved by the finite refinement checker" in output
    assert "C_S <= Q: proved" in output
    assert "C_REC <= C_COMP: proved" in output
    assert "C_COMP <= C_REC: proved" in output
    assert "Raw returned cores" not in output
    assert "Canonical operational cores" not in output
    assert "before redundancy removal" not in output
    assert example._unicode_term_list(contracts["composition"]._operation_assumptions) in output
    assert example._unicode_term_list(contracts["composition"]._operation_guarantees) in output
    assert example._unicode_term_list(contracts["quotient"]._operation_assumptions) in output
    assert example._unicode_term_list(contracts["quotient"]._operation_guarantees) in output


def test_normal_output_reports_finalized_performance_without_timing(audit):
    """Ensure normal output reports the centralized finalized benchmark."""
    _, _, _, output = audit
    performance = example.FINAL_AEB_PERFORMANCE
    assert "COMPUTATIONAL PERFORMANCE" in output
    assert "Final benchmark over 10 measured runs:" in output
    assert "median end-to-end time       : 1.627 s" in output
    assert "median cumulative CAVE time  : 1.093 s" in output
    assert "median end-to-end time       : 4.262 s" in output
    assert "median cumulative CAVE time  : 2.268 s" in output
    assert "median end-to-end time       : 5.938 s" in output
    assert "median cumulative CAVE time  : 3.362 s" in output
    assert f"top-level CAVE invocations   : {performance['cave']['invocations']}" in output
    assert "Solver.check() calls         : 239" in output
    assert "Optimize.check() calls       : 44" in output
    assert "qe2 applications             : 15" in output
    assert "synthetic candidates         : 6" in output
    assert "fixed-support candidates     : 5" in output
    assert "These finalized values are reported, not timed" in output


def test_displayed_generated_contract_summaries_are_checked(audit):  # noqa: WPS118,WPS442
    """Ensure generated-contract summaries are backed by actual checks.

    Args:
        audit: Captured executable audit fixture.
    """
    _, contracts, _, _ = audit
    assert all(contracts["quotient_checks"].values())
    assert all(contracts["recomposition_checks"].values())
    assert contracts["relations"] == {
        "C_COMP^disp <= C_COMP": True,
        "C_COMP <= C_COMP^disp": True,
        "Q^disp <= Q": True,
        "Q <= Q^disp": True,
        "Q <= C_S": False,
        "C_S <= Q": True,
        "C_REC <= C_COMP": True,
        "C_COMP <= C_REC": True,
    }


def test_compact_bucket_status_requires_both_directions(audit):  # noqa: WPS118,WPS218,WPS442
    """Require both implications before any bucket is called equivalent.

    Args:
        audit: Captured executable audit fixture.
    """
    _, contracts, _, output = audit
    composition = contracts["composition_equivalence"]
    quotient = contracts["quotient_equivalence"]
    assert composition == {
        "assumption INIT": (True, True),
        "assumption INV": (True, True),
        "assumption LIV": (True, True),
        "guarantee INIT": (True, True),
        "guarantee INV": (True, True),
        "guarantee LIV": (True, True),
    }
    assert quotient == {
        "assumption INIT": (True, True),
        "assumption INV": (True, True),
        "assumption LIV": (True, True),
        "guarantee INIT": (True, True),
        "guarantee INV": (True, True),
        "guarantee LIV": (True, True),
    }
    assert "canonical => compact: True" in output
    assert "compact => canonical: False" not in output
    assert "equivalent: False" not in output
    assert not contracts["composition_countermodels"]
    assert not contracts["quotient_countermodels"]


def test_primary_compact_inv_excludes_uniform_corollaries(audit):  # noqa: WPS118,WPS442
    """Keep derived uniform bounds outside the primary equivalence object.

    Args:
        audit: Captured executable audit fixture.
    """
    _, contracts, _, output = audit
    texts = [term.core.text for term in contracts["compact_external_guarantees"].inv_terms()]
    assert len(texts) == 5
    assert all("7/2" not in text and "13/2" not in text for text in texts)
    assert "Derived uniform corollaries (not primary equivalence terms)" in output


def test_table_two_compact_buckets_are_all_equivalent(audit):  # noqa: WPS118,WPS442
    """Require both SMT directions for every displayed composition and quotient bucket.

    Args:
        audit: Captured executable audit fixture.
    """
    _, contracts, _, _ = audit
    for result_name in ("composition_equivalence", "quotient_equivalence"):
        assert all(forward and reverse for forward, reverse in contracts[result_name].values())

    composition_init = [term.core.text for term in contracts["compact_external_guarantees"].init_terms()]
    assert composition_init == ["(v = (d / 10))", "((v - (1 / 2)) <= X(v))", "(X(v) <= (v + (1 / 2)))"]

    quotient_inv = [term.core.text for term in contracts["compact_quotient_guarantees"].inv_terms()]
    assert "((URG and !(WRN)) -> (u = 0))" in quotient_inv
    assert "(!((URG or WRN)) -> (u >= (d / 10)))" in quotient_inv


def test_displayed_contracts_mutually_refine_generated_contracts(audit):  # noqa: WPS118,WPS442
    """Check contract-level equivalence of both Table-2 display contracts.

    Args:
        audit: Captured executable audit fixture.
    """
    _, contracts, _, _ = audit
    composition = contracts["composition"]
    quotient = contracts["quotient"]
    composition_display = contracts["composition_display"]
    quotient_display = contracts["quotient_display"]
    assert composition_display.refines(composition)
    assert composition.refines(composition_display)
    assert quotient_display.refines(quotient)
    assert quotient.refines(quotient_display)


def test_compact_objects_are_independent_and_do_not_mutate_generated_contracts(  # noqa: WPS118,WPS442
    audit,  # noqa: WPS442
):
    """Ensure verification/display objects remain separate from generated contracts.

    Args:
        audit: Captured executable audit fixture.
    """
    _, contracts, _, _ = audit
    generated = [contracts[name] for name in ("composition", "quotient", "recomposed")]
    before = [contract.to_dict() for contract in generated]
    assert contracts["compact_assumptions"] is not contracts["composition"].a
    assert contracts["compact_external_guarantees"] is not contracts["composition"].g
    assert contracts["compact_quotient_guarantees"] is not contracts["quotient"].g
    assert before == [contract.to_dict() for contract in generated]


def test_compact_views_use_contract_presentation_api(audit):  # noqa: WPS118,WPS442
    """Require generated contracts to certify candidates through their presentation API.

    Args:
        audit: Captured executable audit fixture.
    """
    _, contracts, _, _ = audit
    for key in ("composition_presentation", "quotient_presentation", "recomposition_presentation"):
        assumptions, guarantees = contracts[key]
        assert isinstance(assumptions, gr1.GR1TermList)
        assert isinstance(guarantees, gr1.GR1TermList)
        assert "□" in assumptions.to_pretty_string()


def test_vehicle_liveness_assumption_is_discharged_externally(audit):
    _, contracts, _, _ = audit
    vehicle = contracts["vehicle"]
    composed = contracts["composition"]
    assert [term.core.text for term in vehicle.a.liv_terms()] == ["MOV"]
    assert all(
        "MOV" not in {gr1._parse_flat_name(str(variable))[0] for variable in get_vars(term.core.expr)}
        for term in composed._operation_assumptions.liv_terms()
    )
