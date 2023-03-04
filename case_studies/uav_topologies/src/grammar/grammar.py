from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from ..contracts_utils.union import ContractsUnions
from ..shared import SymbolType
from .rule import Rule


@dataclass
class Grammar:
    rules: dict[str, Rule]

    """TODO"""

    @classmethod
    def from_json(cls, rules_json_path: Path) -> Grammar:
        return Grammar.from_dict(json.load(open(rules_json_path)))

    @classmethod
    def from_dict(cls, rules_dict: dict) -> Grammar:
        rules: dict[str, Rule] = {}
        """"e.g.."""
        for rule_id, elements in rules_dict.items():
            rules[rule_id] = Rule.from_dict(elements, name=rule_id)

        return cls(rules=rules)

    def to_contracts(self) -> dict[SymbolType, list[ContractsUnions]]:
        """It computes a list of ContractsUnions, where each element represents a rule.
        Then it groups the list according to which production symbol is generated by the rule and it
        returns a dictionary."""

        contracts_alternatives = {}

        for rule_id, rule in self.rules.items():
            if rule.production.symbol_type not in contracts_alternatives.keys():
                contracts_alternatives[rule.production.symbol_type] = []
            contracts_alternatives[rule.production.symbol_type].append(rule.contract)

        return contracts_alternatives

    def get_directions_assignment(self) -> dict[str, int]:
        direction_set_stats = Counter()
        direction_single_stats = Counter()
        for rule_id, rule in self.rules.items():
            for symbol in rule.conditions.get_all_symbol_types():
                all_directions = rule.conditions.get_all_directions_where_is_symbol(symbol)
                direction_key = "-".join(sorted([d.name for d in all_directions]))
                if direction_key not in direction_set_stats.keys():
                    direction_set_stats[direction_key] = 0
                direction_set_stats[direction_key] += 1
                for direction in all_directions:
                    if direction not in direction_single_stats.keys():
                        direction_single_stats[direction] = 0
                    direction_single_stats[direction] += 1

        direction_single_stats_ordered = direction_single_stats.most_common()

        best_assignment = {}

        for i, (key, occurrences) in enumerate(direction_single_stats_ordered):
            best_assignment[key] = i

        best_assignment["ego"] = len(direction_single_stats_ordered)

        return best_assignment
