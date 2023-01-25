import pacti.iocontract as iocontract
from pacti.terms.polyhedra.loaders import read_contract


def validate_iocontract(contract):
    return isinstance(contract, iocontract.IoContract)


def create_contracts(num=1):
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
    if num == 1:
        return contracts[0]
    else:
        return contracts

def test_validate_iocontract():
    c_1, c_2 = read_contract(create_contracts(num=2))
    assert validate_iocontract(c_1)
    assert validate_iocontract(c_2)


def test_contract_equality():
    pass
