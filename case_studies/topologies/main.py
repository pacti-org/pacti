import os
from pathlib import Path

from case_studies.topologies.grammar import Grammar
from case_studies.topologies.grammar.grid import GridBuilder
from case_studies.topologies.tools.analysis import get_best_direction_assignment
from gear.terms.polyhedra import string_to_polyhedra_contract

grammar_rules_processed_path = Path(os.path.dirname(__file__)) / "grammar" / "grammar_rules.json"

if __name__ == "__main__":

    grammar = Grammar.from_json(rules_json_path=grammar_rules_processed_path)

    directions_assignment = get_best_direction_assignment(grammar)
    print(directions_assignment)

    contracts = []

    for rule in grammar.rules:
        str_contract = rule.to_str_contract(directions_assignment)
        print(str_contract)
        io_contract = string_to_polyhedra_contract(str_contract)
        contracts.append(io_contract)

    for contract in contracts:
        print(contract)

    grid = GridBuilder.generate(half_size=3)
    grid.plot.show()
    current_node_state = grid.local_state(grid.current_point)
    current_node_state.plot.show()

    while not grid.symbol(grid.current_point).is_terminal:
        current_state = grid.local_state()
        str_contract = current_state.to_str_contract(directions_assignment)
        print(str_contract)
        io_contract = string_to_polyhedra_contract(str_contract)
        print(io_contract)
