import os
from pathlib import Path

from case_studies.topologies.grammar import Grammar
from case_studies.topologies.grammar.contracts import RuleContract
from case_studies.topologies.tools.analysis import get_best_direction_assignment
from gear.utils.polyhedra_contracts import create_polyhedrea_contarct

grammar_rules_processed_path = Path(os.path.dirname(__file__)) / "grammar" / "grammar_rules.json"

if __name__ == "__main__":
    grammar = Grammar.from_json(rules_json_path=grammar_rules_processed_path)
    directions_assignment = get_best_direction_assignment(grammar)

    contracts = []
    for rule in grammar.rules:
        str_contract = rule.to_str_contract(directions_assignment)
        print(str_contract)
        io_contract = create_polyhedrea_contarct(str_contract)
        # print(io_contract)
        # contract = RuleContract.from_rule(rule, directions_assignment)
        # contracts.append(contract)
        # print(contract)
