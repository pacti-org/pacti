from case_studies.topologies.grammar.contracts import ContractsAlternatives


def find_refinements(state_contracts: ContractsAlternatives,
                     rules_contract: dict[str, [ContractsAlternatives]],
                     allow_rotors: bool = True, allow_wings: bool = True) -> set[str]:
    """Returns a set of rules that refine contract_a"""

    ret = set()
    for rule, rule_alternatives in rules_contract.items():
        if rule == "r10":
            print("wait")
        # print("\n\n\n\n")
        # print(rule)
        # print("STATE_CONTRACT:")
        # for sr in state_contracts.contracts:
        #     print(sr)
        # print("---REFINES?----")
        # print("RULE_ALTERNATIVES:")
        # for cr in rule_alternatives.contracts:
        #     print(cr)
        print("\n\t" + rule)
        # refine = state_contracts <= rule_alternatives

        refine = state_contracts <= rule_alternatives
        # print(refine)

        # print("\n\n\n\n")
        # print(rule)
        # print("RULE_ALTERNATIVES:")
        # for sr in rule_alternatives.contracts:
        #     print(sr)
        # print("---REFINES?----")
        # print("STATE_CONTRACT:")
        # for cr in state_contracts.contracts:
        #     print(cr)

        if refine:
            ret.add(rule)


    return ret
