from typing import List

import pytest
from test_iocontract import validate_iocontract

import pacti.iocontract as iocontract
from pacti.contracts import PolyhedralIoContract


def create_contracts(num: int = 1) -> List[dict]:
    """
    Creates `num` number of contracts and returns a list of dicts
    """
    contracts = []
    for i in range(num):
        c_i = {
            "input_vars": ["u" + str(i)],
            "output_vars": ["x" + str(i)],
            "assumptions": [{"coefficients": {"u" + str(i): float(1)}, "constant": float(i)}],
            "guarantees": [{"coefficients": {"x" + str(i): float(1)}, "constant": float(i)}],
        }
        contracts.append(c_i)

    return contracts


def test_read_contract() -> None:
    """
    Test read_contract
    """
    # Create 1 contract and read it
    c_i = create_contracts(1)
    for c in c_i:
        assert validate_iocontract(PolyhedralIoContract.from_dict(c))

    # Create 5 contracts and read
    c_i = create_contracts(5)
    io_contracts = [PolyhedralIoContract.from_dict(c) for c in c_i]
    assert len(io_contracts) == 5
    for io_c in io_contracts:
        assert isinstance(io_c, iocontract.IoContract)
        assert validate_iocontract(io_c)
    # Ensure that all contracts are dictionaries
    c_n = {"input_vars": "u", "output_vars": "x"}
    with pytest.raises(ValueError, match="Passed dictionary does not have key assumptions."):
        PolyhedralIoContract.from_dict(c_n)
