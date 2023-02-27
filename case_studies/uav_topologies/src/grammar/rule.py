from __future__ import annotations

import itertools
import random
from dataclasses import dataclass

from matplotlib.figure import Figure

from pacti.terms.polyhedra import PolyhedralContract
from .figures import DirectionsGrid
from ..contracts_utils.union import ContractsUnions
from ..shared import Direction, SymbolType, symbols_colors
from ..tools.constraints import from_symbol_directions_to_constraints


@dataclass
class Rule:
    conditions: ConditionSet
    production: Production
    name: str = "rule"

    @classmethod
    def from_dict(cls, rule_dict: dict, name: str = "rule") -> Rule:
        cs = ConditionSet.from_dict(rule_dict["conditions"])
        connection = None
        if "connection" in rule_dict["production"].keys():
            connection = Direction[rule_dict["production"]["connection"]]
        symbol_name = rule_dict["production"]["ego"]

        pr = Production(symbol_type=getattr(SymbolType, symbol_name),
                        connection=connection)

        return Rule(conditions=cs, production=pr, name=name)

    @property
    def contract(self) -> ContractsUnions:

        symbols_dirs = self.conditions.get_all_symbol_types_and_directions()
        constraints, symbols = from_symbol_directions_to_constraints(symbols_dirs)

        """Creating Contracts"""
        contract_union = ContractsUnions(name=self.name)
        for constraint in constraints:
            io_contract = PolyhedralContract.from_string(
                InputVars=list(symbols),
                OutputVars=[],
                assumptions=constraint,
                guarantees=[])

            contract_union.contracts.add(io_contract)

        return contract_union


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
                # set_symbols |= set(filter(lambda x: x != SymbolType.UNOCCUPIED, symbol_types))
                set_symbols |= symbol_types
        return set_symbols

    def get_all_directions_where_is_symbol(self, symbol: SymbolType) -> set[Direction]:
        directions: set[Direction] = set()
        for direction, symbol_types in self.__dict__.items():
            if isinstance(symbol_types, set):
                if symbol in symbol_types:
                    directions.add(getattr(Direction, direction))
        return directions

    def get_all_symbol_types_and_directions(self) -> dict[SymbolType, set[Direction]]:
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
            """Add all types if empty"""
            if len(symbol_types) == 0:
                # symbol_types = ["UNOCCUPIED", "FUSELAGE", "EMPTY", "ROTOR", "WING", "CONNECTOR"]
                symbol_types = ["UNOCCUPIED", "EMPTY"]
            if "EMPTY" in symbol_types and "UNOCCUPIED" not in symbol_types:
                symbol_types.append("UNOCCUPIED")
            for symbol_type in symbol_types:
                all_dirs[direction].add(SymbolType[symbol_type])
        return cls(
            front=all_dirs["front"],
            bottom=all_dirs["bottom"],
            left=all_dirs["left"],
            right=all_dirs["right"],
            top=all_dirs["top"],
            rear=all_dirs["rear"],
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
        # for elem in res:
        #     print(elem)
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
class Production:
    symbol_type: SymbolType
    connection: Direction | None
