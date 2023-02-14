import pacti.iocontract as iocontract
from pacti.terms.polyhedra import *


def validate_iocontract(contract):
    return isinstance(contract, iocontract.IoContract)


def create_contracts(num=1) -> list[dict]:
    """
    Creates `num` number of contracts and returns a list of dicts
    """
    contracts = []
    for i in range(num):
        c_i = {
            "InputVars": ["i" + str(i)],
            "OutputVars": ["o" + str(i)],
            "assumptions": [{"coefficients": {"i" + str(i): 1}, "constant": i}],
            "guarantees": [{"coefficients": {"o" + str(i): 1}, "constant": 1}],
        }
        contracts.append(c_i)
    return contracts

def test_validate_iocontract():
    [c_1, c_2] = [PolyhedralContract.from_dict(c) for c in create_contracts(num=2)]
    assert validate_iocontract(c_1)
    assert validate_iocontract(c_2)


def test_contract_equality():
    pass
