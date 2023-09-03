from typing import List

import pacti.iocontract as iocontract
from pacti.contracts import PolyhedralIoContract


def validate_iocontract(contract: object) -> bool:
    return isinstance(contract, iocontract.IoContract)


def create_contracts(num: int = 1) -> List[dict]:
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
    [c_1, c_2] = [PolyhedralIoContract.from_dict(c) for c in create_contracts(num=2)]
    assert validate_iocontract(c_1)
    assert validate_iocontract(c_2)


def test_contract_equality() -> None:
    pass
