import os
from pathlib import Path
from case_studies.topologies.grammar import Grammar
from case_studies.topologies.grammar.contracts import StrContract
from case_studies.topologies.tools.analysis import get_best_direction_assignment

grammar_rules_processed_path = Path(os.path.dirname(__file__)) / "grammar" / "grammar_rules.json"

if __name__ == "__main__":

    grammar = Grammar.from_json(rules_json_path=grammar_rules_processed_path)
    directions_assignment = get_best_direction_assignment(grammar)

    contracts = []
    for rule in grammar.rules:
        contract = StrContract.from_rule(rule, directions_assignment)
        contracts.append(contract)
        print(contract)



