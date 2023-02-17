import pytest
from test_iocontract import validate_iocontract

import pacti.iocontract as iocontract
from pacti.terms.polyhedra import *
from pacti.terms.polyhedra.serializer import write_contract


def create_contracts(num=1) -> list[dict]:
    """
    Creates `num` number of contracts and returns a list of dicts
    """
    contracts = []
    for i in range(num):
        c_i = {
            "InputVars": ["u" + str(i)],
            "OutputVars": ["x" + str(i)],
            "assumptions": [{"coefficients": {"u" + str(i): float(1)}, "constant": float(i)}],
            "guarantees": [{"coefficients": {"x" + str(i): float(1)}, "constant": float(i)}],
        }
        contracts.append(c_i)
    
    return contracts


def test_read_contract():
    """
    Test read_contract
    """
    # Create 1 contract and read it
    c_i = create_contracts(1)
    for c in c_i:
        assert validate_iocontract(PolyhedralContract.from_dict(c))

    # Create 5 contracts and read
    c_i = create_contracts(5)
    io_contracts = [PolyhedralContract.from_dict(c) for c in c_i]
    assert len(io_contracts) == 5
    for io_c in io_contracts:
        assert isinstance(io_c, iocontract.IoContract)
        assert validate_iocontract(io_c)
    # Ensure that all contracts are dictionaries
    c_i = [("InputVars", "u"), ("OutputVars", "x")]
    with pytest.raises(ValueError, match="A dict type contract is expected."):
        PolyhedralContract.from_dict(c_i)


def test_write_contract():
    """
    Test write_contract
    """
    c_i = create_contracts(1)
    io_c = [PolyhedralContract.from_dict(c) for c in c_i]
    assert c_i == write_contract(io_c)
    all_contracts = create_contracts(5)
    io_contracts = [PolyhedralContract.from_dict(c) for c in all_contracts]
    assert all_contracts == write_contract(io_contracts)
