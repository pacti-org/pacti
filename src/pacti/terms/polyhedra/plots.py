
from pacti.iocontract import IoContract, Var
from pacti.terms.polyhedra.polyhedra import PolyhedralTerm, PolyhedralTermList
from pacti.utils.lists import list_diff, list_union, lists_equal
from pacti.terms.polyhedra.loaders import read_contract, write_contract

from typing import Union

from scipy.spatial import HalfspaceIntersection
import numpy as np

from scipy.optimize import linprog


numeric = Union[int, float]

def plot_assumptions(contract:IoContract, x_var:Var, y_var:Var, var_values:dict[Var,numeric]) -> None:
    if not(x_var in contract.vars):
        raise ValueError("Variable %s is not in an input or output variable of contract." % (x_var))
    if not(y_var in contract.vars):
        raise ValueError("Variable %s is not in an input or output variable of contract." % (y_var))
    if not isinstance(contract.a, PolyhedralTermList):
        raise ValueError("Expecting contract with polyhedral assumptions. Assumptions type: %s" %(type(contract.a)))
    for var in var_values.keys():
        if not var in contract.vars:
            raise ValueError("Var %s from var_values is not in the interface of the contract." %(var))
    diff = list_diff(contract.vars, list_union([x_var,y_var], list(var_values.keys())))
    if diff:
        raise ValueError("Need to set variables %s" % (diff))
    # for every term in the assumptions, replace all variables with the provided values
    term_list = contract.a.copy()
    plot_list = []
    for term in term_list.terms:
        for var, val in enumerate(var_values):
            term = term.substitute_variable(var=var, subst_with_term=PolyhedralTerm(variables={},constant=-val))
        # we may have eliminated all variables after substitution
        if not term.vars:
            if term.contant < 0:
                print("Assumptions are unfeasible")
                return
            else:
                continue
        plot_list.append(term)
    plot_tl = PolyhedralTermList(plot_list)
    assert lists_equal([x_var,y_var], plot_tl.vars)
    # Now we plot the polyhedra.
    variables, A, b, C, d = PolyhedralTermList.termlist_to_polytope(plot_tl)
    # Find a feasible point.
    res = linprog(c=np.array([1,1]), A_ub=A, b_ub=b, bounds=(None, None))
    if res["status"] == 2:
        print("Assumptions are unfeasible")
        return
    feasible_point = np.reshape(np.array(res["x"]), (-1,1))

    halfspaces = np.concatenate(A, np.reshape(b, (-1,1)))
    if variables[0] == y_var:
        # place the x variable in first row
        halfspaces[[0,1]] = halfspaces[[1,0]]
        feasible_point[[0,1]] = feasible_point[[1,0]]
    hs = HalfspaceIntersection(halfspaces,feasible_point)
    # Now that we have all vertices, we can plot the polygon
    x, y = zip(*hs.intersections)
    ax.plot(x, y, 'o', markersize=8)



if __name__ == "__main__":
    contract1 = {
        "InputVars":[
            "u_1"
        ],
        "OutputVars":[
            "x_1"
        ],
        "assumptions":
        [
            {"coefficients":{"u_1":-1}, "constant":-1}
        ],
        "guarantees":
        [
            {"coefficients":{"x_1":-1},
            "constant":-1.5}
        ]
    }
    c1 = read_contract(contract1)
    plot_assumptions(c1)
