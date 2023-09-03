

import matplotlib.pyplot as plt  # noqa: WPS301 Found dotted raw import

from pacti.contracts import PolyhedralIoContract
from pacti.iocontract import Var
from pacti.utils.plots import plot_assumptions, plot_guarantees
from typing import Union

numeric = Union[int, float]

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
c1 = PolyhedralIoContract.from_dict(contract1)
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
c2 = PolyhedralIoContract.from_dict(contract2)
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
c3 = PolyhedralIoContract.from_dict(contract3)

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
