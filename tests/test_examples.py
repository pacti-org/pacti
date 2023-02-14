import pacti.iocontract as iocontract
from pacti.terms.polyhedra import *

def test_examples():
    contract1 = {
        "InputVars":[
            "u_1"
        ],
        "OutputVars":[
            "x_1"
        ],
        "assumptions":
        [
            {"coefficients":{"u_1":-1},
            "constant":-1}
        ],
        "guarantees":
        [
            {"coefficients":{"x_1":-1},
            "constant":-1.5}
        ]
    }
    contract2 = {
            "InputVars":[
                "u_2"
            ],
            "OutputVars":[
                "x_2"
            ],
            "assumptions":
            [
                {"coefficients":{"u_2":-1},
                "constant":-1}
            ],
            "guarantees":
            [
                {"coefficients":{"x_2":-1},
                "constant":-0.3}
            ]
        }
    c1 = PolyhedralContract.from_dict(contract1)
    print("c1:")
    print(str(c1))
    c2 = PolyhedralContract.from_dict(contract2)
    contract_str = "Contract1:InVars: [u_1]"
    contract_str += "\nOutVars:[x_1]\nA: [\n  -u_1 <= -1.0\n"
    contract_str += "]\nG: [\n  -x_1 <= -1.5\n]"
    assert "Contract1:" + str(c1) ==  contract_str
    contract_comp = c1.compose(c2)
    assert isinstance(contract_comp, iocontract.IoContract)
