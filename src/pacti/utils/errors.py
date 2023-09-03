"""Global error classes."""
import dataclasses
from typing import List

import pyparsing as pp


class IncompatibleArgsError(ValueError):
    """Argument validation errors."""


class FileDataFormatError(Exception):
    """Incorrect format"""


class ContractFormatError(FileDataFormatError):
    """Incorrect format"""


@dataclasses.dataclass
class PolyhedralSyntaxException(pp.ParseBaseException):
    """Polyhedral Term syntax error"""

    parse_exception: pp.ParseBaseException
    string_input: str

    def __str__(self) -> str:
        msg = []
        msg.append("pacti.terms.polyhedra.PolyhedralTerm syntax error.")
        msg.append(self.parse_exception.line)
        msg.append(" " * (self.parse_exception.column - 1) + "^")
        msg.append(format(self.parse_exception))
        return "\n".join(msg)

    def __repr__(self) -> str:
        return str(self)


@dataclasses.dataclass
class PolyhedralSyntaxConvexException(pp.ParseBaseException):
    """Polyhedral Term convexity error"""

    string_input: str
    negative_absolute_terms: List[str]

    def __str__(self) -> str:
        msg = []
        msg.append("pacti.terms.polyhedra.PolyhedralTerm non-convexity error.")
        msg.append(f"Convexity requires that the parsing of '{self.string_input}'")
        msg.append(
            f"yields only positive absolute value terms; but we got {len(self.negative_absolute_terms)} negative."
        )
        for nat in self.negative_absolute_terms:
            msg.append(nat)

        return "\n".join(msg)

    def __repr__(self) -> str:
        return str(self)
