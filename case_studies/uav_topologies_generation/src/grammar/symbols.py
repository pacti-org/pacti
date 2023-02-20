from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass

from ..shared import SymbolType


@dataclass(frozen=True)
class Symbol:
    """General Symbol class"""
    symbol_type = SymbolType.UNOCCUPIED

    @property
    @abstractmethod
    def is_terminal(self):
        pass

    @property
    def is_start(self):
        return False


@dataclass(frozen=True)
class TSymbol(Symbol):
    """Terminal Symbol"""

    @property
    def is_terminal(self):
        return True


@dataclass(frozen=True)
class NTSymbol(Symbol):
    """Non-Terminal Symbol"""

    @property
    def is_terminal(self):
        return False


@dataclass(frozen=True)
class Unoccupied(NTSymbol):
    symbol_type = SymbolType.UNOCCUPIED


@dataclass(frozen=True)
class Fuselage(TSymbol):
    symbol_type = SymbolType.FUSELAGE


@dataclass(frozen=True)
class Rotor(TSymbol):
    symbol_type = SymbolType.ROTOR


@dataclass(frozen=True)
class Wing(TSymbol):
    symbol_type = SymbolType.WING


@dataclass(frozen=True)
class Connector(TSymbol):
    symbol_type = SymbolType.CONNECTOR


@dataclass(frozen=True)
class Empty(TSymbol):
    symbol_type = SymbolType.EMPTY
