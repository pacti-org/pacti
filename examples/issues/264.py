from pacti.terms.polyhedra import PolyhedralContract

contract1 = PolyhedralContract.from_string(
    input_vars=["i"],
    output_vars=[],
    assumptions=["|i| <= 1.234567e-5"],
    guarantees=[])

print(contract1)