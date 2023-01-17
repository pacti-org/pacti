import os
import random
from pathlib import Path

from case_studies.topologies.grammar import Grammar, SymbolType
from case_studies.topologies.grammar.contracts import ContractsAlternatives
from case_studies.topologies.grammar.grid import GridBuilder, Point
from case_studies.topologies.tools.analysis import get_best_direction_assignment
from case_studies.topologies.tools.refinement_checking import find_refinements
from pacti.terms.polyhedra import string_to_polyhedra_contract

grammar_rules_processed_path = Path(os.path.dirname(__file__)) / "grammar" / "grammar_rules.json"

if __name__ == "__main__":

    grammar = Grammar.from_json(rules_json_path=grammar_rules_processed_path)

    directions_assignment = get_best_direction_assignment(grammar)
    print(directions_assignment)

    rules_wings_contracts: dict[str, ContractsAlternatives()] = {}
    rules_rotors_contracts: dict[str, ContractsAlternatives()] = {}
    rules_other_contracts: dict[str, ContractsAlternatives()] = {}

    for rule_id, rule in grammar.rules.items():
        str_contracts = rule.to_str_contract(directions_assignment)
        contract_alternatives = ContractsAlternatives()
        for contract in str_contracts:
            io_contract = string_to_polyhedra_contract(contract)
            contract_alternatives.contracts.add(io_contract)

        if rule.production.ego.symbol_type == SymbolType.WING:
            rules_wings_contracts[rule.name] = contract_alternatives
        elif rule.production.ego.symbol_type == SymbolType.ROTOR:
            rules_rotors_contracts[rule.name] = contract_alternatives
        else:
            rules_other_contracts[rule.name] = contract_alternatives

    grid = GridBuilder.generate(half_size=2)
    # grid.plot.show()
    current_node_state = grid.local_state(grid.current_point)

    grammar_string = ""

    max_num_wings = 2
    max_num_rotors = 4

    step = 0
    grammar_string += str(grid.current_point)
    """Fist Step Always Add Fuselage"""
    grid.apply_rule(grammar.rules["r0"].production)

    grammar_string += "[r0]"
    """Keep track of the points to explore"""
    # grid.update_current_point()
    grid.current_point = grid.current_point.front
    # grid.plot.show()
    step += 1
    while len(grid.points_to_visit) > 0:
        # print(f"\n\n\nSTEP {step}")
        current_state = grid.local_state()
        grammar_string += str(grid.current_point)
        # current_state.plot.show()
        """Adding guarantees on the current number of Wings and Rotors"""
        str_contracts = current_state.to_str_contract(directions_assignment)
        state_contracts = ContractsAlternatives()
        for contract in str_contracts:
            io_contract = string_to_polyhedra_contract(contract)
            state_contracts.contracts.add(io_contract)

        rules_allowed = rules_other_contracts
        if grid.n_wings < max_num_wings:
            rules_allowed = rules_allowed | rules_wings_contracts
        if grid.n_rotors < max_num_rotors:
            rules_allowed = rules_allowed | rules_rotors_contracts
        # print(len(rules_allowed))
        rule_ids = find_refinements(state_contracts, rules_allowed)
        # print(rule_ids)
        """Choose a rule to apply randomly"""
        if len(rule_ids) == 0:
            break
        rule_id = random.choice(list(rule_ids))
        print(rule_id)
        grid.apply_rule(grammar.rules[rule_id].production)
        grammar_string += str(f"[{rule_id}]")
        # print(grid.current_point)
        grid.update_current_point()
        # print(grid.current_point)
        grid.plot_with_edges.show()
        # print(grid.current_point)
        step += 1
    print(grammar_string)
    grid.plot_with_edges.show()
