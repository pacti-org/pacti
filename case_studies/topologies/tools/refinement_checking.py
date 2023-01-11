from case_studies.topologies.grammar.contracts import ContractsAlternatives
from pacti.iocontract import IoContract


def find_refinements(state_contracts: ContractsAlternatives,
                     rules_contract: dict[str, [ContractsAlternatives]]) -> set[str]:
    """Returns a set of rules that refine contract_a"""

    ret = set()
    for rule, contract_alternatives in rules_contract.items():
        if contract_alternatives <= state_contracts:
            ret.add(rule)

    return ret
