from pacti.terms.polyhedra.polyhedral_contract import PolyhedralContract
from pacti.utils.multiple_composition import compose_multiple_contracts


def test_multiple_composition() -> None:
    c1 = PolyhedralContract.from_string(
        assumptions=["x <= 1"], guarantees=["y <= 0"], input_vars=["x"], output_vars=["y"]
    )
    c2 = PolyhedralContract.from_string(
        assumptions=["y <= 0"], guarantees=["z <= 0"], input_vars=["y"], output_vars=["z"]
    )
    c3 = PolyhedralContract.from_string(
        assumptions=["y <= 0"], guarantees=["q <= 0"], input_vars=["y"], output_vars=["q"]
    )
    c4 = PolyhedralContract.from_string(
        assumptions=["q <= 0"], guarantees=["v <= 0"], input_vars=["q"], output_vars=["v"]
    )

    contract = compose_multiple_contracts([c1, c2, c3, c4])

    if contract.inputvars[0].name == "y" and contract.outputvars[0].name == "z":
        assert str(contract.a.to_str_list()[0]) == "y <= 0"
        assert str(contract.g.to_str_list()[0]) == "z <= 0"
    elif contract.inputvars[0].name == "q" and contract.outputvars[0].name == "z":
        assert str(contract.a.to_str_list()[0]) == "q <= 0"
        assert str(contract.g.to_str_list()[0]) == "z <= 0"
    elif contract.inputvars[0].name == "q" and contract.outputvars[0].name == "y":
        assert str(contract.a.to_str_list()[0]) == "q <= 0"
        assert str(contract.g.to_str_list()[0]) == "z <= 0"
    elif contract.inputvars[0].name == "q" and contract.outputvars[0].name == "v":
        assert str(contract.a.to_str_list()[0]) == "q <= 0"
        assert str(contract.g.to_str_list()[0]) == "v <= 0"
    else:
        raise ValueError(f"Don't know how to handle this case\n{contract}")
