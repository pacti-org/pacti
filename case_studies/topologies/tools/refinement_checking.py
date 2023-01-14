from case_studies.topologies.grammar.contracts import ContractsAlternatives


def find_refinements(state_contracts: ContractsAlternatives,
                     rules_contract: dict[str, [ContractsAlternatives]]) -> set[str]:
    """Returns a set of rules that refine contract_a"""

    ret = set()
    for rule, rules_contrats in rules_contract.items():
        if state_contracts <= rules_contrats:
            ret.add(rule)

    return ret
