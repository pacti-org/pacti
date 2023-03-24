from src.contracts_utils.union import ContractsUnions


def rule_matching(state_contracts: ContractsUnions, rules_contracts: list[ContractsUnions]) -> set[ContractsUnions]:
    """Returns a set 'rules_contract' are refined by 'state_contracts'
    after the constraints have been adjusted"""

    rules_compatible = set()

    for rules_contract in rules_contracts:
        rule_relaxed = rules_contract.get_relaxed(state_contracts)
        check_1 = rule_relaxed.can_be_composed_with(state_contracts)
        if check_1:
            if len(rule_relaxed.vars) == 1:
                continue
            rules_compatible.add(rule_relaxed)

    return rules_compatible
