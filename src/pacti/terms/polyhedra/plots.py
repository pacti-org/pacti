
from pacti.iocontract import IoContract, Var
from pacti.terms.polyhedra.polyhedra import PolyhedralTerm, PolyhedralTermList
from pacti.utils.lists import list_diff, list_union
from pacti.terms.polyhedra import PolyhedralContract

from typing import Union

from math import atan2

from scipy.spatial import HalfspaceIntersection
import numpy as np

from scipy.optimize import linprog
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.figure import Figure

numeric = Union[int, float]

def plot_assumptions(contract:IoContract, x_var:Var, y_var:Var, var_values:dict[Var,numeric], x_lims:tuple[numeric], y_lims: tuple[numeric]) -> Figure:
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
    """
    if not(x_var in contract.vars):
        raise ValueError("Variable %s is not in an input or output variable of contract." % (x_var))
    if not(y_var in contract.vars):
        raise ValueError("Variable %s is not in an input or output variable of contract." % (y_var))
    for var in var_values.keys():
        if not var in contract.vars:
            raise ValueError("Var %s from var_values is not in the interface of the contract." %(var))
    fig = _plot_constraints(contract.a,x_var, y_var, var_values, x_lims, y_lims)
    ax = fig.axes[0]
    ax.set_title("Assumptions")
    return fig

def plot_guarantees(contract:IoContract, x_var:Var, y_var:Var, var_values:dict[Var,numeric], x_lims:tuple[numeric], y_lims: tuple[numeric]) -> Figure:
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
    """
    if not(x_var in contract.vars):
        raise ValueError("Variable %s is not in an input or output variable of contract." % (x_var))
    if not(y_var in contract.vars):
        raise ValueError("Variable %s is not in an input or output variable of contract." % (y_var))
    for var in var_values.keys():
        if not var in contract.vars:
            raise ValueError("Var %s from var_values is not in the interface of the contract." %(var))
    fig = _plot_constraints(contract.a | contract.g, x_var, y_var, var_values, x_lims, y_lims)
    ax = fig.axes[0]
    ax.set_title("Guarantees")
    return fig


def _plot_constraints(constraints:PolyhedralTermList, x_var:Var, y_var:Var, var_values:dict[Var,numeric], x_lims:tuple[numeric], y_lims: tuple[numeric]) -> Figure:
    if not isinstance(constraints, PolyhedralTermList):
        raise ValueError("Expecting polyhedral constraints. Constraint type: %s" %(type(constraints)))
    diff = list_diff(constraints.vars, list_union([x_var,y_var], list(var_values.keys())))
    if diff:
        raise ValueError("Need to set variables %s" % (diff))
    # for every term in the assumptions, replace all variables with the values provided
    term_list = constraints.copy()
    term_list = term_list | PolyhedralTermList([PolyhedralTerm({x_var:1},x_lims[1]), PolyhedralTerm({x_var:-1},-x_lims[0]), PolyhedralTerm({y_var:1},y_lims[1]), PolyhedralTerm({y_var:-1},-y_lims[0])]) 
    plot_list = []
    for term in term_list.terms:
        for var, val in var_values.items():
            term = term.substitute_variable(var=var, subst_with_term=PolyhedralTerm(variables={},constant=-val))
        # we may have eliminated all variables after substitution
        if not term.vars:
            if term.constant < 0:
                print("Assumptions are unfeasible")
                return
            else:
                continue
        plot_list.append(term)
    #print(plot_list)
    plot_tl = PolyhedralTermList(plot_list)
    assert not list_diff(plot_tl.vars, [x_var,y_var]), "termlist vars: %s" %(plot_tl.vars)
    # Now we plot the polyhedra.
    variables, A, b, C, d = PolyhedralTermList.termlist_to_polytope(plot_tl, PolyhedralTermList([]))
    # Find interior point of the set -> we compue the Chebyshev center of the polyhedron
    A_1 = np.concatenate((A, np.linalg.norm(A,axis=1,keepdims=True)),axis=1)
    A_new = np.concatenate((A_1 ,np.array([[0,0,-1]])),axis=0)
    b_new = np.concatenate((np.reshape(b, (-1,1)),np.array([[0]])),axis=0)
    res = linprog(c=np.array([0,0,-1]), A_ub=A_new, b_ub=b_new, bounds=(None, None))
    if res["status"] == 2:
        print("Assumptions are unfeasible")
        return
    interior_point = np.array(res["x"])[0:-1]
    print(interior_point)

    halfspaces = np.concatenate((A, -np.reshape(b, (-1,1))), axis=1)
    if variables[0] == y_var:
        # place the x variable in first row
        halfspaces[[0,1]] = halfspaces[[1,0]]
        interior_point[[0,1]] = interior_point[[1,0]]
    
    hs = HalfspaceIntersection(halfspaces,interior_point)
    # Now that we have all vertices, we can plot the polygon
    x, y = zip(*hs.intersections)
    # sort the points in polar coordinates
    center=(sum(x)/len(x),sum(y)/len(y))
    points = sorted(zip(x,y), key= lambda p: atan2(p[1]-center[1],p[0]-center[0]))
    x,y = zip(*points)

    # generate figure
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1, aspect='equal')
    ax.set_xlim(x_lims)
    ax.set_ylim(y_lims)
    ax.set_xlabel(x_var.name)
    ax.set_ylabel(y_var.name)

    poly = Polygon(np.column_stack([x, y]), animated=False,closed=True)
    ax.add_patch(poly)

    return fig



if __name__ == "__main__":
    contract1 = {
        "InputVars":[
            "u_1",
            "u_2"
        ],
        "OutputVars":[
            "x_1"
        ],
        "assumptions":
        [
            {"coefficients":{"u_1":-1,"u_2":0}, "constant":0},
            {"coefficients":{"u_1":1,"u_2":0}, "constant":1},
            {"coefficients":{"u_1":0,"u_2":-1}, "constant":0},
            {"coefficients":{"u_1":0,"u_2":1}, "constant":1}
        ],
        "guarantees":
        [
            {"coefficients":{"x_1":-1},
            "constant":-1.5}
        ]
    }
    c1 = PolyhedralContract.from_dict(contract1)
    fig = plot_assumptions(contract=c1,x_var=Var("u_1"),y_var=Var("u_2"),var_values={Var("x_1"):0},x_lims=(-2,2),y_lims=(-2,2))
    fig = plot_guarantees(contract=c1,x_var=Var("u_1"),y_var=Var("x_1"),var_values={Var("u_2"):1},x_lims=(-2,2),y_lims=(-2,2))
    plt.show()
