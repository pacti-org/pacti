from __future__ import annotations

import itertools
import json
import random
from dataclasses import dataclass
from pathlib import Path

from aenum import Enum
from matplotlib.figure import Figure

from pacti.utils.string_contract import StrContract

from .figures import DirectionsGrid
from .symbols import Connector, Empty, Fuselage, Rotor, Symbol, SymbolType, Unoccupied, Wing, symbols_short, \
    symbols_colors, symbols_short_in, symbols_short_out


class Direction(Enum):
    ego = 0
    front = 1
    bottom = 2
    left = 3
    right = 4
    top = 5
    rear = 6


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

    def learn_from_isomorphisms(self):
        """ "TODO by Pier"""


@dataclass
class Rule:
    conditions: ConditionSet
    production: Production
    name: str = "rule"

    """TODO"""

    def matches(self, state: LocalState) -> LocalState | None:
        if self.conditions.matches(state):
            return self.production.apply(state)
        return None

    @classmethod
    def from_dict(cls, rule_dict: dict, name: str = "rule") -> Rule:
        cs = ConditionSet.from_dict(rule_dict["conditions"])
        connection = None
        if "connection" in rule_dict["production"].keys():
            connection = Direction[rule_dict["production"]["connection"]]
        symbol_name = rule_dict["production"]["ego"]

        if symbol_name == "UNOCCUPIED":
            symbol = Unoccupied()
        elif symbol_name == "FUSELAGE":
            symbol = Fuselage()
        elif symbol_name == "EMPTY":
            symbol = Empty()
        elif symbol_name == "ROTOR":
            symbol = Rotor()
        elif symbol_name == "CONNECTOR":
            symbol = Connector()
        elif symbol_name == "WING":
            symbol = Wing()
        else:
            print(f"{symbol_name} not present")
            raise AttributeError

        pr = Production(ego=symbol, connection=connection)

        return Rule(conditions=cs, production=pr, name=name)

    def to_str_contract(self, assignment: dict) -> list[StrContract]:
        guarantees = []

        from case_studies.topologies.tools.alternative_assumptions import get_alternative_assumptions
        new_assumptions_or, input_symbols = get_alternative_assumptions(assignment,
                                                                        self.conditions.get_all_symbol_types_and_directions())

        dir_connection = assignment["ego"]
        if self.production.connection is not None:
            dir_connection = assignment[self.production.connection.name]
        output_symbol = f"{symbols_short_out(self.production.ego.symbol_type)}"
        guarantees.extend(constraint_str_between_integers(output_symbol, (dir_connection, dir_connection)))

        """Creating Contracts"""
        str_contracts_or = []
        for or_assumption in new_assumptions_or:
            new_c = StrContract(
                assumptions=or_assumption, guarantees=guarantees, inputs=list(input_symbols), outputs=[output_symbol]
            )
            str_contracts_or.append(new_c)

        return str_contracts_or


@dataclass
class ConditionSet:
    front: set[SymbolType]
    bottom: set[SymbolType]
    left: set[SymbolType]
    right: set[SymbolType]
    top: set[SymbolType]
    rear: set[SymbolType]
    ego: SymbolType = SymbolType.UNOCCUPIED

    def get_all_symbol_types(self) -> set[SymbolType]:
        set_symbols = set()
        for direction, symbol_types in self.__dict__.items():
            if isinstance(symbol_types, set):
                set_symbols |= set(filter(lambda x: x != SymbolType.UNOCCUPIED, symbol_types))
        return set_symbols

    def get_all_directions_where_is_symbol(self, symbol: SymbolType) -> set[str]:
        directions: set[str] = set()
        for direction, symbol_types in self.__dict__.items():
            if isinstance(symbol_types, set):
                if symbol in symbol_types:
                    directions.add(direction)
        return directions

    def get_all_symbol_types_and_directions(self) -> dict[SymbolType, set[str]]:
        ret = {}
        all_sym = self.get_all_symbol_types()
        for sym in all_sym:
            ret[sym] = self.get_all_directions_where_is_symbol(sym)
        return ret

    @classmethod
    def from_dict(cls, conditions):
        all_dirs = {}
        for direction, symbol_types in conditions.items():
            all_dirs[direction] = set()
            for symbol_type in symbol_types:
                all_dirs[direction].add(SymbolType[symbol_type])
            if len(all_dirs[direction]) == 0:
                all_dirs[direction] = {SymbolType.ANY}
        return cls(
            front=all_dirs["front"],
            bottom=all_dirs["bottom"],
            left=all_dirs["left"],
            right=all_dirs["right"],
            top=all_dirs["top"],
            rear=all_dirs["rear"],
        )

    def matches(self, state: LocalState):
        return (
                state.ego.symbol_type in self.ego
                and state.front.symbol_type in self.front
                and state.bottom.symbol_type in self.bottom
                and state.left.symbol_type in self.left
                and state.right.symbol_type in self.right
                and state.top.symbol_type in self.top
                and state.rear.symbol_type in self.rear
        )

    def draw_condition(self):
        return Condition(
            front=random.choice(list(self.front)),
            bottom=random.choice(list(self.bottom)),
            left=random.choice(list(self.left)),
            right=random.choice(list(self.right)),
            top=random.choice(list(self.top)),
            rear=random.choice(list(self.rear)),
        )

    def get_all_conditions(self) -> list[Condition]:
        conditions: list[Condition] = []
        res = itertools.product(
            list(self.front), list(self.bottom), list(self.left), list(self.right), list(self.top), list(self.rear)
        )
        for elem in res:
            print(elem)
        for f, b, l, ri, t, re in itertools.product(
                *[list(self.front), list(self.bottom), list(self.left), list(self.right), list(self.top),
                  list(self.rear)]
        ):
            conditions.append(Condition(f, b, l, ri, t, re))
        return conditions


@dataclass
class Condition:
    front: SymbolType
    bottom: SymbolType
    left: SymbolType
    right: SymbolType
    top: SymbolType
    rear: SymbolType
    ego: SymbolType = SymbolType.UNOCCUPIED

    @property
    def plot(self) -> Figure:
        local_grid = DirectionsGrid(
            front=symbols_colors[self.front],
            bottom=symbols_colors[self.bottom],
            left=symbols_colors[self.left],
            right=symbols_colors[self.right],
            top=symbols_colors[self.top],
            rear=symbols_colors[self.rear],
        )
        return local_grid.plot


@dataclass
class SymbolConnection:
    symbol_a: Symbol
    symbol_b: Symbol



def constraint_str_between_integers(symbol: str, cluster: tuple[int, int]) -> list[str]:
    if cluster[1] < cluster[0]:
        raise AttributeError("Not valid interval")
    constraints = []
    if cluster[0] > 0:
        constraints.append(constraint_str_greater_eq_than(symbol, cluster[0]))
    constraints.append(constraint_str_less_eq_than(symbol, cluster[1]))

    return constraints


def constraint_str_greater_eq_than(symbol: str, n: int) -> str:
    return f"-1 * {symbol} <= -1 * {n}"


def constraint_str_less_eq_than(symbol: str, n: int) -> str:
    return f"{symbol} <= {n}"


@dataclass
class LocalState:
    ego: Symbol
    front: Symbol
    bottom: Symbol
    left: Symbol
    right: Symbol
    top: Symbol
    rear: Symbol

    def get_all_symbol_types_and_directions(self) -> dict[SymbolType, set[str]]:
        ret = {}
        for direction, symbol in self.__dict__.items():
            if symbol.symbol_type == SymbolType.UNOCCUPIED:
                continue
            if direction == "ego":
                continue
            if symbol.symbol_type not in ret.keys():
                ret[symbol.symbol_type] = {direction}
            else:
                ret[symbol.symbol_type].add(direction)
        return ret

    @property
    def plot(self) -> Figure:
        local_grid = DirectionsGrid(
            ego=symbols_colors[self.ego.symbol_type],
            front=symbols_colors[self.front.symbol_type],
            bottom=symbols_colors[self.bottom.symbol_type],
            left=symbols_colors[self.left.symbol_type],
            right=symbols_colors[self.right.symbol_type],
            top=symbols_colors[self.top.symbol_type],
            rear=symbols_colors[self.rear.symbol_type],
        )
        return local_grid.plot

    def to_str_contract(self, assignment: dict) -> list[StrContract]:
        from case_studies.topologies.tools.alternative_assumptions import get_alternative_assumptions

        new_assumptions_or, input_symbols = get_alternative_assumptions(assignment,
                                                                        self.get_all_symbol_types_and_directions())

        """Creating Contracts"""
        str_contracts_or = []
        for or_assumption in new_assumptions_or:
            new_c = StrContract(
                assumptions=or_assumption, inputs=list(input_symbols)
            )
            str_contracts_or.append(new_c)

        return str_contracts_or


@dataclass
class Production:
    ego: Symbol
    connection: Direction | None

    def apply(self, state: LocalState) -> SymbolConnection | None:
        state.ego = self.ego
        if self.connection is not None:
            connection = SymbolConnection(self.ego, getattr(state, self.connection.name))
            return connection
        return None
