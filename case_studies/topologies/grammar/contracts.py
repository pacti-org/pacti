from __future__ import annotations

from dataclasses import dataclass

from ..tools.analysis import get_clusters_consecutive_integers
from . import Rule, symbols_short


@dataclass
class RuleContract:
    assumptions: list[str]
    guarantees: list[str]
    name: str = ""

    @classmethod
    def from_rule(cls, rule: Rule, assignment: dict[str, int]) -> RuleContract:
        for symbol in rule.conditions.get_all_symbol_types():
            all_directions = rule.conditions.get_all_directions_where_is_symbol(symbol)
            all_directions_ints = list(map(lambda x: assignment[x], all_directions))
            clusters = get_clusters_consecutive_integers(all_directions_ints)
            constraints = []
            for cluster in clusters:
                if cluster[0] != 0:
                    constraints.append(f"-{symbols_short[symbol]} <= {cluster[0]}")
                constraints.append(f"{symbols_short[symbol]} <= {cluster[1]}")
            if rule.production.connection is None:
                dir_connection = "-1"
            else:
                dir_connection = assignment[rule.production.connection.name]
            guarantees = [
                f"{symbols_short[rule.production.ego.symbol_type]} <= {dir_connection}",
                f"- {symbols_short[rule.production.ego.symbol_type]} <= - {dir_connection}",
            ]

            return cls(assumptions=constraints, guarantees=guarantees, name=rule.name)
