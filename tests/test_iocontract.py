import pacti.iocontract as iocontract
from pacti.terms.polyhedra import *


def validate_iocontract(contract: object) -> bool:
    return isinstance(contract, iocontract.IoContract)


def create_contracts(num: int = 1) -> list[dict]:
    """
    Creates `num` number of contracts and returns a list of dicts
    """
    contracts = []
    for i in range(num):
        c_i = {
            "input_vars": ["i" + str(i)],
            "output_vars": ["o" + str(i)],
            "assumptions": [{"coefficients": {"i" + str(i): 1}, "constant": i}],
            "guarantees": [{"coefficients": {"o" + str(i): 1}, "constant": 1}],
        }
        contracts.append(c_i)
    return contracts


def test_validate_iocontract() -> None:
    [c_1, c_2] = [PolyhedralContract.from_dict(c) for c in create_contracts(num=2)]
    assert validate_iocontract(c_1)
    assert validate_iocontract(c_2)

def test_contract_copy() -> None:
    [c1a, c2a] = [PolyhedralContract.from_dict(c) for c in create_contracts(num=2)]
    c1b = c1a.copy()
    c2b = c2a.copy()
    assert c1a.pacti_id != c1b.pacti_id
    assert c1a.a.terms[0].pacti_id != c1b.a.terms[0].pacti_id
    assert c1a.g.terms[0].pacti_id != c1b.g.terms[0].pacti_id
    assert c2a.pacti_id != c2b.pacti_id
    assert c2a.a.terms[0].pacti_id != c2b.a.terms[0].pacti_id
    assert c2a.g.terms[0].pacti_id != c2b.g.terms[0].pacti_id

def test_contract_equality() -> None:
    pass
