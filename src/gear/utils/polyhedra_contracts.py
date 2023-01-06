from gear.iocontract import IoContract, Var
from gear.terms.polyhedra import PolyhedralTerm, PolyhedralTermList
from gear.utils.string_contract import StrContract


def create_polyhedrea_contarct(string_contract: StrContract):
    assumptions: list[PolyhedralTerm] = list(map(lambda x: PolyhedralTerm.from_string(x), string_contract.assumptions))
    guarantees: list[PolyhedralTerm] = list(map(lambda x: PolyhedralTerm.from_string(x), string_contract.guarantees))
    inputs: list[Var] = [Var(x) for x in string_contract.inputs]
    outputs: list[Var] = [Var(x) for x in string_contract.outputs]

    io_contract = IoContract(
        assumptions=PolyhedralTermList(assumptions),
        guarantees=PolyhedralTermList(guarantees),
        inputVars=inputs,
        outputVars=outputs,
    )

    print(io_contract)
