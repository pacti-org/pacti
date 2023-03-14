from pacti.terms.polyhedra import PolyhedralContract

contract1 = PolyhedralContract.from_string(
    input_vars=["i"],
    output_vars=["o"],
    assumptions=["|i| <= 2"],
    guarantees=["o - i <= 0", "i - 2o <= 2"])

print(contract1.get_variable_bounds("i"))
print(contract1.get_variable_bounds("o"))
print(contract1.optimize("3 o - 2 i", maximize=True))
print(contract1.optimize("3 o - 2 i", maximize=False))