from pacti.utils.contracts_union import ContractsUnions


def rule_matching(state_contracts: ContractsUnions, rules_contracts: list[ContractsUnions]) -> set[ContractsUnions]:
    """Returns a set 'rules_contract' are refined by 'state_contracts'
    after the constraints have been adjusted"""

    rules_compatible = set()

    for rules_contract in rules_contracts:
        print(f"\n\nChecking Rule {rules_contract.name}")
        rule_relaxed = rules_contract.get_relaxed(state_contracts)
        check_1 = rule_relaxed.can_be_composed_with(state_contracts)
        if check_1:
            if len(rule_relaxed.vars) == 1:
                continue
            print(rule_relaxed.vars)
            print(f"RULE\n{rule_relaxed}")
            print(f"STATE\n{state_contracts}\n")
            rules_compatible.add(rule_relaxed)

    return rules_compatible
