from pacti.contracts import PolyhedralIoContract

contract1 = {
        "input_vars":[
            "u_1",
            "u_2"
        ],
        "output_vars":[
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
c1 = PolyhedralIoContract.from_dict(contract1)
print(c1)