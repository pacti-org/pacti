from case_studies.topologies.grammar.contracts import ContractsAlternatives
from gear.iocontract import IoContract


def find_refinements(contract_a: IoContract,
                     rules_contract: dict[str, [ContractsAlternatives]]) -> set[str]:
    """Returns a set of rules that refine contract_a"""

    ret = set()
    for rule, contract_alternatives in rules_contract.items():
        if contract_alternatives <= contract_a:
            ret.add(rule)

    return ret
