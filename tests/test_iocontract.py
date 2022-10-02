import io
import pytest
import gear.iocontract as iocontract

def validate_iocontract(contract):
    assert isinstance(contract, iocontract.IoContract)

def test_validate_iocontract():
    c1 = 
    c2 = 
    assert validate_iocontract(c1)
    assert validate_iocontract(c2)

def test_contract_equality():
