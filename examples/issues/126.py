
from pacti.terms.polyhedra import PolyhedralContract
from pacti import write_contracts_to_file

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

system_contract, _ = contract1.compose(contract2)
print(system_contract)

contract1_n = PolyhedralContract.from_string(
    input_vars=["i"],
    output_vars=["o"],
    assumptions=["|i| <= 2"],
    guarantees=["|o| <= 3"])


write_contracts_to_file([contract1, contract2], ["c1", "c2"], "hola.json")
write_contracts_to_file([contract1, contract2], ["c1", "c2"], "hola_n.json", True)