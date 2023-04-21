"""Plotting functionality for polyhedral contracts."""


from math import atan2
from typing import Dict, Tuple, Union

import matplotlib.pyplot as plt  # noqa: WPS301 Found dotted raw import
import numpy as np
from matplotlib.figure import Figure as MplFigure
from matplotlib.patches import Polygon as MplPatchPolygon
from scipy.optimize import linprog
from scipy.spatial import HalfspaceIntersection, QhullError

from pacti.iocontract import Var
from pacti.terms.polyhedra import PolyhedralContract
from pacti.terms.polyhedra.polyhedra import PolyhedralTerm, PolyhedralTermList
from pacti.utils.lists import list_diff, list_union

numeric = Union[int, float]


def plot_assumptions(
    contract: PolyhedralContract,
    x_var: Union[Var, str],
    y_var: Union[Var, str],
    var_values: Dict[Var, numeric],
    x_lims: Tuple[numeric, numeric],
    y_lims: Tuple[numeric, numeric],
) -> MplFigure:
    """
    Plots the assumptions of an IoContract with polyhedral terms.

    Args:
        contract: the contract whose assumptions will be plotted.
        x_var: variable mapped to the x-axis.
        y_var: variable mapped to the y-axis.
        var_values: values of other variables appearing in the assumptions.
        x_lims: range of values in the x-axis.
        y_lims: range of values in the y-axis.

    Returns:
        Figure element with a single "axes" object showing the feasible region for the assumptions.

    Raises:
        ValueError: arguments provided failed sanity checks.
    """
    if x_var not in contract.vars:
        raise ValueError("Variable %s is not in an input or output variable of contract." % (x_var))
    if y_var not in contract.vars:
        raise ValueError("Variable %s is not in an input or output variable of contract." % (y_var))
    for var in var_values.keys():  # noqa: VNE002
        if var not in contract.vars:
            raise ValueError("Var %s from var_values is not in the interface of the contract." % (var))
    fig = _plot_constraints(contract.a, x_var, y_var, var_values, x_lims, y_lims)
    ax = fig.axes[0]
    ax.set_title("Assumptions")
    return fig


def plot_guarantees(
    contract: PolyhedralContract,
    x_var: Union[Var, str],
    y_var: Union[Var, str],
    var_values: Dict[Var, numeric],
    x_lims: Tuple[numeric, numeric],
    y_lims: Tuple[numeric, numeric],
) -> MplFigure:
    """
    Plots the guarantees and assumptions of an IoContract with polyhedral terms.

    Args:
        contract: the contract whose assumptions & guarantees will be plotted.
        x_var: variable mapped to the x-axis.
        y_var: variable mapped to the y-axis.
        var_values: values of other variables appearing in the assumptions & guarantees.
        x_lims: range of values in the x-axis.
        y_lims: range of values in the y-axis.

    Returns:
        Figure element with a single "axes" object showing the feasible region for the assumptions & guarantees.

    Raises:
        ValueError: arguments provided failed sanity checks.
    """
    str_list_of_vars =[str(var) for var in contract.vars]
    if x_var not in contract.vars and x_var not in str_list_of_vars:
        raise ValueError("Variable %s is not in an input or output variable of contract." % (x_var))
    if y_var not in contract.vars and y_var not in str_list_of_vars:
        raise ValueError("Variable %s is not in an input or output variable of contract." % (y_var))
    if x_var in str_list_of_vars:
        x_var = contract.vars[str_list_of_vars.index(x_var)]
    if y_var in str_list_of_vars:
        y_var = contract.vars[str_list_of_vars.index(y_var)]
    for var in var_values.keys():  # noqa: VNE002
        if var not in contract.vars:
            raise ValueError("Var %s from var_values is not in the interface of the contract." % (var))
    fig = _plot_constraints(contract.a | contract.g, x_var, y_var, var_values, x_lims, y_lims)
    ax = fig.axes[0]
    ax.set_title("Guarantees")
    return fig


def _substitute_in_termlist(  # noqa: WPS231
    constraints: PolyhedralTermList, var_values: Dict[Var, numeric]
) -> PolyhedralTermList:
    plot_list = []
    for term in constraints.terms:
        term_bk = term.copy()
        for var, val in var_values.items():  # noqa: VNE002
            term = term.substitute_variable(var=var, subst_with_term=PolyhedralTerm(variables={}, constant=-val))
        # we may have eliminated all variables after substitution
        if not term.vars:
            if term.constant < 0:
                raise ValueError("Constraint %s is violated by assignment" % (term_bk))
            else:
                continue  # noqa: WPS503 Found useless returning `else` statement
        plot_list.append(term)
    return PolyhedralTermList(plot_list)


# Find interior point of the set -> we compute the Chebyshev center of the polyhedron
def _get_feasible_point(a_mat: np.ndarray, b: np.ndarray, interior: bool = True) -> np.ndarray:
    a_mat_1 = np.concatenate((a_mat, np.linalg.norm(a_mat, axis=1, keepdims=True)), axis=1)
    a_mat_new = np.concatenate((a_mat_1, np.array([[0, 0, -1]])), axis=0)
    b_new = np.concatenate((np.reshape(b, (-1, 1)), np.array([[0]])), axis=0)
    obj = np.array([0, 0, 1])
    if interior:
        obj = np.array([0, 0, -1])
    res = linprog(c=obj, A_ub=a_mat_new, b_ub=b_new, bounds=(None, None))
    if res["status"] == 2:
        raise ValueError("Constraints are unfeasible")
    return np.array(res["x"])[0:-1]  # noqa: WPS349 Found redundant subscript slice


# given a bounded polygon, return its vertices
def _get_bounding_vertices(a_mat: np.ndarray, b: np.ndarray) -> Tuple[tuple, tuple]:
    try:
        interior_point = _get_feasible_point(a_mat, b)
    except ValueError as e:
        raise ValueError("Region is empty") from e
    halfspaces = np.concatenate((a_mat, -np.reshape(b, (-1, 1))), axis=1)
    try:  # noqa: WPS229 Found too long ``try`` body length: 2 > 1
        hs = HalfspaceIntersection(halfspaces, interior_point)
        x, y = zip(*hs.intersections)
    except QhullError:
        # polygon has no interior. optimize four directions
        res = linprog(c=[0, 1], A_ub=a_mat, b_ub=b, bounds=(None, None))
        p1 = np.array(res["x"])
        res = linprog(c=[0, -1], A_ub=a_mat, b_ub=b, bounds=(None, None))
        p2 = np.array(res["x"])
        res = linprog(c=[1, 0], A_ub=a_mat, b_ub=b, bounds=(None, None))
        p3 = np.array(res["x"])
        res = linprog(c=[-1, 0], A_ub=a_mat, b_ub=b, bounds=(None, None))
        p4 = np.array(res["x"])
        x = (p1[0], p2[0], p3[0], p4[0])
        y = (p1[1], p2[1], p3[1], p4[1])
    # sort the points by angle from the center of the polygon
    center = (sum(x) / len(x), sum(y) / len(y))
    points = sorted(zip(x, y), key=lambda p: atan2(p[1] - center[1], p[0] - center[0]))
    x, y = zip(*points)
    return x, y  # noqa: WPS331 Found variables that are only used for `return`: x, y


def _gen_boundary_constraints(
    x_var: Var, y_var: Var, x_lims: Tuple[numeric, numeric], y_lims: Tuple[numeric, numeric]
) -> PolyhedralTermList:
    constraints = [PolyhedralTerm({x_var: 1}, x_lims[1])]
    constraints.append(PolyhedralTerm({x_var: -1}, -x_lims[0]))
    constraints.append(PolyhedralTerm({y_var: 1}, y_lims[1]))
    constraints.append(PolyhedralTerm({y_var: -1}, -y_lims[0]))
    return PolyhedralTermList(constraints)


def _plot_constraints(
    constraints: PolyhedralTermList,
    x_var: Var,
    y_var: Var,
    var_values: Dict[Var, numeric],
    x_lims: Tuple[numeric, numeric],
    y_lims: Tuple[numeric, numeric],
) -> MplFigure:
    if not isinstance(constraints, PolyhedralTermList):
        raise ValueError("Expecting polyhedral constraints. Constraint type: %s" % (type(constraints)))
    if x_var in var_values.keys():
        raise ValueError("x-axis variable %s can't be assigned a value" % (x_var))
    if y_var in var_values.keys():
        raise ValueError("y-axis variable %s can't be assigned a value" % (y_var))
    diff = list_diff(constraints.vars, list_union([x_var, y_var], list(var_values.keys())))
    if diff:
        raise ValueError("Need to set variables %s" % (diff))
    # for every term in the assumptions, replace all variables with the values provided
    term_list = constraints | _gen_boundary_constraints(x_var, y_var, x_lims, y_lims)
    plot_tl = _substitute_in_termlist(term_list, var_values)
    assert not list_diff(plot_tl.vars, [x_var, y_var]), "termlist vars: %s" % (plot_tl.vars)
    # Now we plot the polygon
    res_tuple = PolyhedralTermList.termlist_to_polytope(plot_tl, PolyhedralTermList([]))
    variables = res_tuple[0]
    a_mat = res_tuple[1]
    b = res_tuple[2]
    if variables[0] == y_var:
        # place the x variable in first row
        a_mat[:, [0, 1]] = a_mat[:, [1, 0]]  # noqa: WPS359 Found an iterable unpacking to list

    x, y = _get_bounding_vertices(a_mat, b)

    # generate figure
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1, aspect="equal")
    ax.set_xlim(x_lims)
    ax.set_ylim(y_lims)
    ax.set_xlabel(x_var.name)
    ax.set_ylabel(y_var.name)
    ax.set_aspect((x_lims[1] - x_lims[0]) / (y_lims[1] - y_lims[0]))

    poly = MplPatchPolygon(
        np.column_stack([x, y]), animated=False, closed=True, facecolor="deepskyblue", edgecolor="deepskyblue"
    )
    ax.add_patch(poly)

    return fig


if __name__ == "__main__":
    contract1 = {
        "input_vars": ["u_1", "u_2"],
        "output_vars": ["x_1"],
        "assumptions": [
            {"coefficients": {"u_1": -1, "u_2": 0}, "constant": 0},
            {"coefficients": {"u_1": 1, "u_2": 0}, "constant": 1},
            {"coefficients": {"u_1": 0, "u_2": -1}, "constant": 0},
            {"coefficients": {"u_1": 0, "u_2": 1}, "constant": 1},
        ],
        "guarantees": [{"coefficients": {"x_1": -1}, "constant": -1.5}],
    }
    c1 = PolyhedralContract.from_dict(contract1)
    fig = plot_assumptions(
        contract=c1, x_var=Var("u_1"), y_var=Var("u_2"), var_values={Var("x_1"): 0}, x_lims=(-2, 2), y_lims=(-2, 2)
    )
    fig = plot_guarantees(
        contract=c1, x_var=Var("u_1"), y_var=Var("x_1"), var_values={Var("u_2"): 1}, x_lims=(-2, 2), y_lims=(-2, 2)
    )

    contract2 = {
        "input_vars": ["t0", "v0"],
        "output_vars": ["t1", "v1"],
        "assumptions": [{"coefficients": {"v0": 1}, "constant": 20000}],
        "guarantees": [
            {"coefficients": {"t1": -1}, "constant": -90},
            {"coefficients": {"v1": -1}, "constant": -1600},
        ],
    }
    c2 = PolyhedralContract.from_dict(contract2)
    fig = plot_guarantees(
        contract=c2,
        x_var=Var("t0"),
        y_var=Var("v1"),
        var_values={Var("t1"): 91, Var("v0"): 20000},
        x_lims=(-10, 100),
        y_lims=(1000, 21000),
    )

    contract3 = {
        "input_vars": ["t10", "soc10", "d10", "e10", "r10"],
        "output_vars": ["t11", "soc11", "d11", "e11", "r11"],
        "assumptions": [
            {"constant": -6.0, "coefficients": {"soc10": -1.0}},
            {"constant": -1.0, "coefficients": {"d10": -1.0}},
        ],
        "guarantees": [
            {"constant": 2.0, "coefficients": {"t11": 1.0, "t10": -1.0}},
            {"constant": -2.0, "coefficients": {"t11": -1.0, "t10": 1.0}},
            {"constant": 6.0, "coefficients": {"soc10": 1.0, "soc11": -1.0}},
            {"constant": float(0), "coefficients": {"d11": 1.0}},
            {"constant": float(0), "coefficients": {"d11": -1.0}},
            {"constant": float(0), "coefficients": {"e11": 1.0, "e10": -1.0}},
            {"constant": float(0), "coefficients": {"e11": -1.0, "e10": 1.0}},
            {"constant": float(0), "coefficients": {"r11": 1.0, "r10": -1.0}},
            {"constant": float(0), "coefficients": {"r11": -1.0, "r10": 1.0}},
        ],
    }
    c3 = PolyhedralContract.from_dict(contract3)

    fig = plot_guarantees(
        contract=c3,
        x_var=Var("t10"),
        y_var=Var("soc11"),
        var_values={
            # Var("t10"):0,
            Var("t11"): 2,
            Var("d10"): 1,
            Var("d11"): 0,
            Var("e10"): 0,
            Var("e11"): 0,
            Var("r10"): 0,
            Var("r11"): 0,
            Var("soc10"): 6,
        },
        x_lims=(-2, 2),
        y_lims=(-2, 2),
    )

    plt.show()
