import os
from pathlib import Path

from case_studies.topologies.grammar import Grammar
from case_studies.topologies.grammar.contracts import ContractsAlternatives
from case_studies.topologies.grammar.grid import GridBuilder
from case_studies.topologies.tools.analysis import get_best_direction_assignment
from case_studies.topologies.tools.refinement_checking import find_refinements
from gear.terms.polyhedra import string_to_polyhedra_contract

grammar_rules_processed_path = Path(os.path.dirname(__file__)) / "grammar" / "grammar_rules.json"

if __name__ == "__main__":

    grammar = Grammar.from_json(rules_json_path=grammar_rules_processed_path)

    directions_assignment = get_best_direction_assignment(grammar)
    print(directions_assignment)

    rule_contracts: dict[str, ContractsAlternatives()] = {}

    for rule in grammar.rules:
        str_contracts = rule.to_str_contract(directions_assignment)
        contract_alternatives = ContractsAlternatives()
        for contract in str_contracts:
            io_contract = string_to_polyhedra_contract(contract)
            contract_alternatives.contracts.add(io_contract)
        rule_contracts[rule.name] = contract_alternatives

    grid = GridBuilder.generate(half_size=3)
    grid.plot.show()
    current_node_state = grid.local_state(grid.current_point)
    current_node_state.plot.show()

    while not grid.symbol(grid.current_point).is_terminal:
        current_state = grid.local_state()
        str_contracts = current_state.to_str_contract(directions_assignment)
        state_contracts = ContractsAlternatives()
        for contract in str_contracts:
            io_contract = string_to_polyhedra_contract(contract)
            state_contracts.contracts.add(io_contract)
        rules = find_refinements(state_contracts, rule_contracts)
        for refinement in rules:
            print(refinement)
