from pacti.terms.polyhedra import PolyhedralContract

contract1 = PolyhedralContract.from_string(
    input_vars=["i"],
    output_vars=["o"],
    assumptions=["|i| <= 2"],
    guarantees=["o - i <= 0", "i - 2o <= 2"])

contract2 = PolyhedralContract.from_string(
    input_vars=["o"],
    output_vars=["o_p"],
    assumptions=["o <= 0.2", "-o <= 1"],
    guarantees=["o_p - o <= 0"])

system_contract = contract1.compose(contract2)
print(system_contract)
system_contract = contract1.compose(contract2, vars_to_keep=["o"])
print(system_contract)
