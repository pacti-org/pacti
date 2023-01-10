from gear.iocontract import IoContract


def find_refinements(contract_a: IoContract, contracts: set[IoContract]) -> set[IoContract]:
    """Returns a subset of IOContract in contracts that refine contract_a"""

    ret = set()
    for contract in contracts:
        inputs_a = contract_a.inputvars
        inputs_b = contract.inputvars
        outputs_a = contract_a.outputvars
        outputs_b = contract.outputvars
        if contract <= contract_a:
            print(f"Checking:{contract}\nREFINES\n{contract_a}")
            ret.add(contract)

    return ret
