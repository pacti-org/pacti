import pytest
from test_iocontract import validate_iocontract

import pacti.iocontract as iocontract
from pacti.terms.polyhedra.loaders import readContract, writeContract


def create_contracts(num=1):
    """
    Creates `num` number of contracts and returns a list of dicts
    """
    contracts = []
    for i in range(num):
        c = {
            "InputVars": ["u" + str(i)],
            "OutputVars": ["x" + str(i)],
            "assumptions": [{"coefficients": {"u" + str(i): 1}, "constant": i}],
            "guarantees": [{"coefficients": {"x" + str(i): 1}, "constant": 1}],
        }
        contracts.append(c)
    if num == 1:
        return contracts[0]
    else:
        return contracts


def test_read_contract():
    # Create 1 contract and read it
    c = create_contracts(1)
    validate_iocontract(readContract(c))
    # Create 5 contracts and read
    c = create_contracts(5)
    io_contracts = readContract(c)
    assert len(io_contracts) == 5
    for io_c in io_contracts:
        assert isinstance(io_c, iocontract.IoContract)
        assert validate_iocontract(io_c)
    # Ensure that all contracts are dictionaries
    c = [("InputVars", "u"), ("OutputVars", "x")]
    with pytest.raises(ValueError, match="A dict type contract is expected."):
        readContract(c)


def test_write_contract():
    c = create_contracts(1)
    io_c = readContract(c)
    assert c == writeContract(io_c)
    all_contracts = create_contracts(5)
    io_contracts = readContract(all_contracts)
    assert all_contracts == writeContract(io_contracts)
