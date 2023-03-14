import logging

import pytest

from pacti.iocontract import Var
from pacti.terms.polyhedra import PolyhedralTermList
from pacti.terms.polyhedra.serializer import polyhedral_termlist_from_string

FORMAT = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
logging.basicConfig(filename="../pacti.log", filemode="w", level=logging.DEBUG, format=FORMAT)


def to_pts(str_rep_list: list[str]) -> PolyhedralTermList:
    return PolyhedralTermList([item for el in str_rep_list for item in polyhedral_termlist_from_string(el)])


def test_polyhedral_var_elim_by_refinement_1() -> None:
    x = Var("x")
    # the context cannot simplify or transform the reference
    reference = to_pts(["2*x <= 4"])
    context = to_pts(["2*x <= 5"])
    expected = reference.copy()
    vars_elim = [x]
    reference = reference.elim_vars_by_refining(context, vars_elim)
    assert reference.terms == expected.terms


def test_polyhedral_var_elim_by_refinement_2() -> None:
    x = Var("x")
    # the context can simplify but not transform the reference
    reference = to_pts(["2*x <= 4"])
    context = to_pts(["2*x <= 3"])
    expected = to_pts([])
    vars_elim = [x]
    reference = reference.elim_vars_by_refining(context, vars_elim)
    assert reference.terms == expected.terms


def test_polyhedral_var_elim_by_refinement_3() -> None:
    # the context can transform the reference
    x = Var("x")
    y = Var("y")
    reference = to_pts(["x + y <= 4"])
    context = to_pts(["y <= 10"])
    expected = to_pts(["x <= -6"])
    vars_elim = [y]
    reference = reference.elim_vars_by_refining(context, vars_elim)
    assert reference.terms == expected.terms


def test_polyhedral_var_elim_by_refinement_4() -> None:
    # a term that cannot be simplified
    x = Var("x")
    reference = to_pts(["x <= -1"])
    context = to_pts(["-x + y <= 0"])
    expected = to_pts(["x <= -1"])
    vars_elim = [x]
    with pytest.raises(ValueError) as e_info:
        reference = reference.elim_vars_by_refining(context, vars_elim)


def test_polyhedral_var_elim_by_refinement_5() -> None:
    # a term that can be simplified with one element of the context
    x = Var("x")
    reference = to_pts(["x <= -1"])
    context = to_pts(["x - y <= 0"])
    expected = to_pts(["y <= -1"])
    vars_elim = [x]
    reference = reference.elim_vars_by_refining(context, vars_elim)
    assert reference.terms == expected.terms


def test_polyhedral_var_elim_by_refinement_6() -> None:
    # a term that can be simplified with one element of the context
    x = Var("x")
    z = Var("z")
    reference = to_pts(["x <= -1"])
    context = to_pts(["x - y <= 0", "-z + x <= 0"])
    expected = to_pts(["y <= -1"])
    vars_elim = [x, z]
    reference = reference.elim_vars_by_refining(context, vars_elim)
    assert reference.terms == expected.terms

def test_polyhedral_var_elim_by_refinement_7() -> None:
    # a term that can be simplified with one element of the context
    x = Var("soc2_exit")
    reference = to_pts(["1.8326033352452644 duration_sbo3 - soc2_exit <= 0.0"])
    context = to_pts([
        "-duration_charging2 <= 0.0",
        "3.807706401697026 duration_charging2 - 3.05877199128224 duration_dsn1 + soc1_entry <= 100.0",
        "-duration_dsn1 <= 0.0",
        "soc1_entry <= 100.0",
        "4.325975663494785 duration_dsn1 - soc1_entry <= 0.0",
        "-4.325975663494785 duration_dsn1 - output_soc1 + soc1_entry <= 0.0",
        "3.058771991282236 duration_dsn1 + output_soc1 - soc1_entry <= 0.0",
        "-3.807706401697026 duration_charging2 - output_soc1 + soc2_exit <= 0.0",
        "3.0049617464042018 duration_charging2 + output_soc1 - soc2_exit <= 0.0"
    ])
    print(reference)
    #expected = to_pts([""])
    vars_elim = [x, Var('output_soc1')]
    reference = reference.elim_vars_by_refining(context, vars_elim)
    print(reference)
    assert reference.terms == expected.terms







def test_polyhedral_var_elim_by_relaxation_7() -> None:
    # a term that can be simplified with one element of the context
    x = Var("x")
    y = Var("y")
    z = Var("z")
    reference = to_pts(["x - y <= -1"])
    context = to_pts(["y - z <= -1"])
    expected = to_pts(["x - z <= -2"])
    vars_elim = [y]
    reference = reference.elim_vars_by_relaxing(context, vars_elim)
    assert reference.terms == expected.terms


def test_simplify_1() -> None:
    reference = to_pts(["-0.5i <= -1.5", "3*i <= 1", "-1*i <= 2", "1*i <= 2"])
    expected = to_pts(["-0.5*i <= -1.5", "3*i <= 1"])
    with pytest.raises(ValueError):
        _ = reference.simplify()


def test_issue171() -> None:
    constraints = to_pts(
        ["-1*dt0 - 1*t0 <= 0.0", "-1*t0 <= 0.0", "-1*dt0 - 1*t0 + 1*t1 <= 0.0", "1*dt0 + 1*t0 - 1*t1 <= 0.0"]
    )
    transformed = constraints.elim_vars_by_relaxing(PolyhedralTermList([]), [Var("t0"), Var("dt0")])
    expected = to_pts(["-1*t1 <= 0"])
    assert expected == transformed


if __name__ == "__main__":
    test_polyhedral_var_elim_by_refinement_7()