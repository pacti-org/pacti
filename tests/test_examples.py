import pacti.iocontract as iocontract
from pacti.contracts import PolyhedralIoContract
from pacti.terms.polyhedra.polyhedra import PolyhedralTermList


def test_examples1() -> None:
    contract1 = {
        "input_vars": ["u_1"],
        "output_vars": ["x_1"],
        "assumptions": [{"coefficients": {"u_1": -1}, "constant": -1}],
        "guarantees": [{"coefficients": {"x_1": -1}, "constant": -1.5}],
    }
    contract2 = {
        "input_vars": ["u_2"],
        "output_vars": ["x_2"],
        "assumptions": [{"coefficients": {"u_2": -1}, "constant": -1}],
        "guarantees": [{"coefficients": {"x_2": -1}, "constant": -0.3}],
    }
    c1 = PolyhedralIoContract.from_dict(contract1)
    print("c1:")
    print(str(c1))
    c2 = PolyhedralIoContract.from_dict(contract2)
    contract_str = "Contract1:InVars: [u_1]"
    contract_str += "\nOutVars:[x_1]\nA: [\n  -u_1 <= -1\n"
    contract_str += "]\nG: [\n  -x_1 <= -1.5\n]"
    assert "Contract1:" + str(c1) == contract_str
    contract_comp = c1.compose(c2)
    assert isinstance(contract_comp, iocontract.IoContract)
    unecessary_simplification = contract_comp.copy()
    unecessary_simplification.simplify()
    assert unecessary_simplification == contract_comp


def test_examples2() -> None:
    contract1 = {
        "input_vars": ["u_1"],
        "output_vars": ["x_1"],
        "assumptions": [{"coefficients": {"u_1": -1}, "constant": -1}],
        "guarantees": [{"coefficients": {"x_1": -1}, "constant": -1.5}],
    }
    contract2 = {
        "input_vars": ["u_2"],
        "output_vars": ["x_2"],
        "assumptions": [{"coefficients": {"u_2": -1}, "constant": -1}],
        "guarantees": [{"coefficients": {"x_2": -1}, "constant": -0.3}],
    }
    c1 = PolyhedralIoContract.from_dict(contract1)
    print("c1:")
    print(str(c1))
    c2 = PolyhedralIoContract.from_dict(contract2)
    contract_str = "Contract1:InVars: [u_1]"
    contract_str += "\nOutVars:[x_1]\nA: [\n  -u_1 <= -1\n"
    contract_str += "]\nG: [\n  -x_1 <= -1.5\n]"
    assert "Contract1:" + str(c1) == contract_str
    contract_comp, _ = c1.compose_tactics(c2)
    assert isinstance(contract_comp, iocontract.IoContract)
    unecessary_simplification = contract_comp.copy()
    unecessary_simplification.simplify()
    assert unecessary_simplification == contract_comp


def test_IoContract_compose_and_quotient_tactics() -> None:
    contract1 = iocontract.IoContract(
        assumptions=PolyhedralTermList(), guarantees=PolyhedralTermList(), input_vars=[], output_vars=[]
    )
    contract2 = iocontract.IoContract(
        assumptions=PolyhedralTermList(), guarantees=PolyhedralTermList(), input_vars=[], output_vars=[]
    )
    result1, _ = contract1.compose_tactics(contract2, tactics_order=None)
    assert isinstance(result1, iocontract.IoContract)

    result2, _ = contract1.quotient_tactics(contract2, tactics_order=None)
    assert isinstance(result2, iocontract.IoContract)


if __name__ == "__main__":
    test_examples1()
    test_examples2()
