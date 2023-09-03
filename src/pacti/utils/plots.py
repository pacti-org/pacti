"""Plotting functionality for polyhedral contracts."""


from copy import copy
from math import atan2
from typing import Callable, Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt  # noqa: WPS301 Found dotted raw import
import numpy as np
from matplotlib.figure import Figure as MplFigure
from matplotlib.patches import Polygon as MplPatchPolygon
from scipy.optimize import linprog
from scipy.spatial import HalfspaceIntersection, QhullError

from pacti.contracts import PolyhedralIoContract
from pacti.iocontract import Var
from pacti.terms.polyhedra.polyhedra import PolyhedralTerm, PolyhedralTermList
from pacti.utils.lists import list_diff, list_union

numeric = Union[int, float]


def _to_var(input_arg: Union[Var, str]) -> Var:
    if isinstance(input_arg, str):
        return Var(input_arg)
    return copy(input_arg)


def _to_vals_dict(input_arg: Dict[Union[Var, str], numeric]) -> Dict[Var, numeric]:
    if len(input_arg) > 0:
        keys = list(input_arg.keys())
        newdict = {}
        for k in keys:
            if isinstance(k, str):
                newdict[Var(k)] = input_arg[k]
            else:
                newdict[k] = input_arg[k]
        return newdict
    return {}


def _to_bool(input_arg: Optional[bool]) -> bool:
    if isinstance(input_arg, bool):
        return input_arg
    return False


def plot_assumptions(
    contract: PolyhedralIoContract,
    x_var: Union[Var, str],
    y_var: Union[Var, str],
    var_values: Dict[Union[Var, str], numeric],
    x_lims: Tuple[numeric, numeric],
    y_lims: Tuple[numeric, numeric],
    show: Optional[bool] = True,
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
        show: If `True` (default), the figure is displayed.
              If `False` the display is suppressed.

    Returns:
        Figure element with a single "axes" object showing the feasible region for the assumptions.

    Raises:
        ValueError: arguments provided failed sanity checks.
    """
    x_var_var = _to_var(x_var)
    y_var_var = _to_var(y_var)
    var_values_var = _to_vals_dict(var_values)

    if x_var_var not in contract.vars:
        raise ValueError("Variable %s is not in an input or output variable of contract." % (x_var_var))
    if y_var_var not in contract.vars:
        raise ValueError("Variable %s is not in an input or output variable of contract." % (y_var_var))
    for var in var_values_var.keys():  # noqa: VNE002
        if var not in contract.vars:
            raise ValueError("Var %s from var_values is not in the interface of the contract." % (var))
    fig = _plot_constraints(contract.a, x_var_var, y_var_var, var_values_var, x_lims, y_lims, _to_bool(show))
    ax = fig.axes[0]
    ax.set_title("Assumptions")
    return fig


def plot_guarantees(
    contract: PolyhedralIoContract,
    x_var: Union[Var, str],
    y_var: Union[Var, str],
    var_values: Dict[Union[Var, str], numeric],
    x_lims: Tuple[numeric, numeric],
    y_lims: Tuple[numeric, numeric],
    new_x_var: Optional[str] = None,
    new_y_var: Optional[str] = None,
    x_transform: Optional[Callable[[numeric, numeric], numeric]] = None,
    y_transform: Optional[Callable[[numeric, numeric], numeric]] = None,
    number_of_points: Optional[int] = 30,
    show: Optional[bool] = True,
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
        new_x_var: name of horizontal transformed variable.
        new_y_var: name of vertical transformed variable.
        x_transform: function to map (x,y) values to new horizontal variable.
        y_transform: function to map (x,y) values to new vertical variable.
        number_of_points: number of points to transform on each side of (x,y) polyhedron.
        show: If `True` (default), the figure is displayed.
              If `False` the display is suppressed.

    Returns:
        Figure element with a single "axes" object showing the feasible region for the assumptions & guarantees.

    Raises:
        ValueError: arguments provided failed sanity checks.
    """
    x_var_var = _to_var(x_var)
    y_var_var = _to_var(y_var)
    var_values_var = _to_vals_dict(var_values)

    if x_var_var not in contract.vars:
        raise ValueError("Variable %s is not in an input or output variable of contract." % (x_var_var))
    if y_var_var not in contract.vars:
        raise ValueError("Variable %s is not in an input or output variable of contract." % (y_var_var))
    for var in var_values_var.keys():  # noqa: VNE002
        if var not in contract.vars:
            raise ValueError("Var %s from var_values is not in the interface of the contract." % (var))

    if x_transform is not None and y_transform is not None:
        assert new_x_var
        assert new_y_var
        assert number_of_points
        fig = _plot_transformed_constraints(
            contract.a | contract.g,
            x_var_var,
            y_var_var,
            var_values_var,
            x_lims,
            y_lims,
            new_x_var,
            new_y_var,
            x_transform,
            y_transform,
            number_of_points,
            _to_bool(show),
        )
    else:
        fig = _plot_constraints(
            contract.a | contract.g, x_var_var, y_var_var, var_values_var, x_lims, y_lims, _to_bool(show)
        )

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


def constraints_to_vertices(
    constraints: PolyhedralTermList,
    x_var: Var,
    y_var: Var,
    var_values: Dict[Var, numeric],
    x_lims: Tuple[numeric, numeric],
    y_lims: Tuple[numeric, numeric],
) -> Tuple[Tuple, Tuple]:
    """
    Return the bounding vertices of a set of constraints.

    Args:
        constraints: the set of constraints.
        x_var: The variable among those in the constraints that will be used as the horizontal variable.
        y_var: The variable among those in the constraints that will be used as the vertical variable.
        var_values: Values to which the rest of the variables in the constraints are set.
        x_lims: Horizontal limits of polyhedron.
        y_lims: Vertical limits of polyhedron.

    Returns:
        A tuple of x and y tuples correponding to the vertices.

    Raises:
        ValueError: Arguments do not meet expectations, i.e., other variables are not set to constant values, etc.
    """
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

    return _get_bounding_vertices(a_mat, b)


def _plot_constraints(
    constraints: PolyhedralTermList,
    x_var: Var,
    y_var: Var,
    var_values: Dict[Var, numeric],
    x_lims: Tuple[numeric, numeric],
    y_lims: Tuple[numeric, numeric],
    show: bool,
) -> MplFigure:
    x, y = constraints_to_vertices(constraints, x_var, y_var, var_values, x_lims, y_lims)

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
    if not show:
        plt.close(fig)
    return fig


def get_path(
    x0: numeric,
    x1: numeric,
    y0: numeric,
    y1: numeric,
    x_transform: Callable,
    y_transform: Callable,
    number_of_points: int,
) -> Tuple[List, List]:
    """
    Transform a path in original coordinates.

    Args:
        x0: x-value of the starting point of the path to transform.
        x1: x-value of the final point of the path to transform.
        y0: y-value of the starting point of the path to transform.
        y1: y-value of the final point of the path to transform.
        x_transform: function to map (x,y) values to new horizontal variable.
        y_transform: function to map (x,y) values to new vertical variable.
        number_of_points: number of points to transform on each side of (x,y) polyhedron.

    Returns:
        A tuple of x tuples and y tuples corresponding to the transformed path.
    """
    xx = np.linspace(x0, x1, number_of_points)
    yy = np.linspace(y0, y1, number_of_points)
    x_tranform_vec = np.vectorize(x_transform)
    y_tranform_vec = np.vectorize(y_transform)
    return x_tranform_vec(xx, yy).tolist(), y_tranform_vec(xx, yy).tolist()


def _plot_transformed_constraints(
    constraints: PolyhedralTermList,
    x_var: Var,
    y_var: Var,
    var_values: Dict[Var, numeric],
    x_lims: Tuple[numeric, numeric],
    y_lims: Tuple[numeric, numeric],
    new_x_var: str,
    new_y_var: str,
    x_transform: Callable,
    y_transform: Callable,
    number_of_points: int,
    show: bool,
) -> MplFigure:
    x, y = constraints_to_vertices(constraints, x_var, y_var, var_values, x_lims, y_lims)

    # generate figure
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1, aspect="auto")
    # for i in range(len(x)):
    #    xx, yy = get_path(x[i-1],x[i],y[i-1],y[i],x_transform,y_transform,number_of_points)
    #    ax.plot(xx,yy)
    xx: List = []
    yy: List = []
    for i in range(len(x)):  # noqa: WPS518 Found implicit `enumerate()` call
        newx, newy = get_path(x[i - 1], x[i], y[i - 1], y[i], x_transform, y_transform, number_of_points)
        xx += newx
        yy += newy
    plt.fill(xx, yy, facecolor="deepskyblue")
    # ax.set_xlim(x_lims)
    # ax.set_ylim(y_lims)
    ax.set_xlabel(new_x_var)
    ax.set_ylabel(new_y_var)
    # ax.set_aspect((x_lims[1] - x_lims[0]) / (y_lims[1] - y_lims[0]))
    if not show:
        plt.close(fig)

    return fig
