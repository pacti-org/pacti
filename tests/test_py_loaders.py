import gear.iocontract as iocontract
from gear.terms.polyhedra.loaders import read_contract, write_contract
from test_iocontract import validate_iocontract
import pytest

def create_contracts(num=1):
    """
    Creates `num` number of contracts and returns a list of dicts
    """
    contracts = []
    for i in range(num):
        c_i = {
            "InputVars": ["u" + str(i)],
            "OutputVars": ["x" + str(i)],
            "assumptions": [{"coefficients": {"u" + str(i): 1}, "constant": i}],
            "guarantees": [{"coefficients": {"x" + str(i): 1}, "constant": 1}],
        }
        contracts.append(c_i)
    if num == 1:
        return contracts[0]
    else:
        return contracts


def test_read_contract():
    """
    Test read_contract
    """
    # Create 1 contract and read it
    c_i = create_contracts(1)
    validate_iocontract(read_contract(c_i))
    # Create 5 contracts and read
    c_i = create_contracts(5)
    io_contracts = read_contract(c_i)
    assert len(io_contracts) == 5
    for io_c in io_contracts:
        assert isinstance(io_c, iocontract.IoContract)
        assert validate_iocontract(io_c)
    # Ensure that all contracts are dictionaries
    c_i = [("InputVars", "u"), ("OutputVars", "x")]
    with pytest.raises(ValueError, match="A dict type contract is expected."):
        read_contract(c_i)

def test_write_contract():
    """
    Test write_contract
    """
    c_i = create_contracts(1)
    io_c = read_contract(c_i)
    assert c_i == write_contract(io_c)
    all_contracts = create_contracts(5)
    io_contracts = read_contract(all_contracts)
    assert all_contracts == write_contract(io_contracts)
