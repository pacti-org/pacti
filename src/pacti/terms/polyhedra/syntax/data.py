"""Basis data structures for polyhedral parsing."""

import dataclasses
from enum import Enum
from itertools import product
from typing import Dict, List, Optional, Union

from pacti.terms.polyhedra.polyhedra import PolyhedralTerm, Var, numeric


def _factor_repr(f: float, v: str) -> str:
    n = f"{f}"
    if n == "1.0":
        return v
    elif n == "-1.0":
        return f"-{v}"
    return f"{n}{v}"


@dataclasses.dataclass
class PolyhedralSyntaxTermList:
    """Represents a reduced list of syntactic terms (variables with a multiplicative coefficient) with an additive constant."""

    constant: float
    factors: Dict[str, float] = dataclasses.field(default_factory=dict)

    def is_positive(self: "PolyhedralSyntaxTermList") -> bool:
        """
        Checks whether the TermList is positive.

        Returns:
            True if either the constant is positive or, if the first ordered factor is positive.
        """
        if self.constant > 0:
            return True
        elif self.constant < 0:
            return False
        var = sorted(self.factors)[0]
        return self.factors[var] > 0

    def negate(self: "PolyhedralSyntaxTermList") -> "PolyhedralSyntaxTermList":
        """
        Negated PolyhedralSyntaxTermList

        Returns:
            A PolyhedralSyntaxTermList with the negated constant and all factors negated.
        """
        c = -self.constant
        fs = {}
        for f, v in self.factors.items():
            fs[f] = -v
        return PolyhedralSyntaxTermList(constant=c, factors=fs)

    def add(self: "PolyhedralSyntaxTermList", other: "PolyhedralSyntaxTermList") -> "PolyhedralSyntaxTermList":
        """
        Addition for PolyhedralSyntaxTermList.

        Args:
            other: a PolyhedralSyntaxTermList to add to self.

        Returns:
            A new PolyhedralSyntaxTermList with the sum of the constants and with the factors added by their variables.
        """
        fs = self.factors.copy()
        for f, v in other.factors.items():
            if f in fs:
                fs[f] += v
                fv = f"{fs[f]}"
                if fv == "0.0":
                    fs.pop(f)
                elif fv == "-0.0":
                    fs.pop(f)
            else:
                fs[f] = v
        return PolyhedralSyntaxTermList(constant=self.constant + other.constant, factors=fs)

    def to_polyhedral_term(self: "PolyhedralSyntaxTermList") -> PolyhedralTerm:
        """
        Converts a PolyhedralSyntaxTermList to a PolyhedralTerm.

        Returns:
            A PolyhedralTerm with the right-hand-side constant as the negated constant of the PolyhedralSyntaxTermList
            and left-hand-side variables mapped from the PolyhedralSyntaxTermList variables with their multiplicative coefficients.
        """
        fs: Dict[Var, numeric] = {Var(k): v for k, v in self.factors.items()}
        return PolyhedralTerm(variables=fs, constant=-self.constant)

    def __repr__(self) -> str:
        if self.constant == 0:
            s = ""
        else:
            s = f"{self.constant}"
        for var in sorted(self.factors):
            f: float = self.factors[var]
            if len(s) == 0:
                s = _factor_repr(f, var)
            else:
                if f > 0:
                    s += f" + {_factor_repr(f, var)}"
                else:
                    s += f" - {_factor_repr(abs(f), var)}"
        return s


@dataclasses.dataclass
class PolyhedralSyntaxAbsoluteTerm:
    """Represents an absolute list of terms with an optional coefficient."""

    term_list: PolyhedralSyntaxTermList
    coefficient: Optional[float] = dataclasses.field(default=None)

    def __repr__(self) -> str:
        s = f"|{self.term_list}|"
        if self.coefficient is None:
            return s
        return f"{self.coefficient}{s}"

    def is_positive(self: "PolyhedralSyntaxAbsoluteTerm") -> bool:
        """
        Checks whether this PolyhedralSyntaxAbsoluteTerm is positive.

        Returns:
            True if either there is no coefficient or the coefficient is positive.
        """
        if self.coefficient is None:
            return True
        return self.coefficient > 0

    def negate(self: "PolyhedralSyntaxAbsoluteTerm") -> "PolyhedralSyntaxAbsoluteTerm":
        """
        Negated PolyhedralSyntaxAbsoluteTerm.

        Returns:
            A negated copy of this PolyhedralSyntaxAbsoluteTerm.
        """
        if self.coefficient is None:
            return PolyhedralSyntaxAbsoluteTerm(term_list=self.term_list, coefficient=-1.0)
        return PolyhedralSyntaxAbsoluteTerm(term_list=self.term_list, coefficient=self.coefficient * -1.0)

    def same_term_list(self, other: "PolyhedralSyntaxAbsoluteTerm") -> bool:
        """
        Check whether this PolyhedralSyntaxAbsoluteTerm has the same term_list as other.

        Args:
            other: Another PolyhedralSyntaxAbsoluteTerm

        Returns:
            True if the representation of self's term_list is equal to that of other's.
        """
        s = f"{self.term_list}"
        o = f"{other.term_list}"
        return s == o

    def to_term_list(self: "PolyhedralSyntaxAbsoluteTerm") -> PolyhedralSyntaxTermList:
        """
        Converts an PolyhedralSyntaxAbsoluteTerm into a PolyhedralSyntaxTermList.

        Returns:
            A PolyhedralSyntaxTermList with the PolyhedralSyntaxAbsoluteTerm coefficient
            applied as a multiplier for the constant and factors of the term_list.
        """
        if self.coefficient is None:
            m = 1.0
        else:
            m = self.coefficient
        c = m * self.term_list.constant
        fs: Dict[str, float] = {}
        for f, v in self.term_list.factors.items():
            fs[f] = m * v
        return PolyhedralSyntaxTermList(constant=c, factors=fs)


PolyhedralSyntaxAbsoluteTermOrTerm = Union[PolyhedralSyntaxAbsoluteTerm, PolyhedralSyntaxTermList]


def _combine_optional_floats(f1: Optional[float], f2: Optional[float]) -> Optional[float]:
    if f1 is None:
        if f2 is None:
            return None
        return f2 + 1
    if f2 is None:
        return f1 + 1
    return f1 + f2


def _combine_or_append(
    atl: List[PolyhedralSyntaxAbsoluteTerm], term: PolyhedralSyntaxAbsoluteTerm
) -> List[PolyhedralSyntaxAbsoluteTerm]:
    r: List[PolyhedralSyntaxAbsoluteTerm] = []
    appended = False
    for at in atl:
        if at.same_term_list(term):
            r.append(
                PolyhedralSyntaxAbsoluteTerm(
                    term_list=at.term_list, coefficient=_combine_optional_floats(at.coefficient, term.coefficient)
                )
            )
            appended = True
        else:
            r.append(at)
    if not appended:
        r.append(term)
    return r


def _generate_absolute_term_combinations(
    absolute_term_list: List[PolyhedralSyntaxAbsoluteTerm],
) -> List[PolyhedralSyntaxTermList]:
    cs = []
    for signs in product([True, False], repeat=len(absolute_term_list)):
        c = PolyhedralSyntaxTermList(constant=0, factors={})
        for i, is_positive in enumerate(signs):
            if is_positive:
                c = c.add(absolute_term_list[i].to_term_list())
            else:
                c = c.add(absolute_term_list[i].negate().to_term_list())
        cs.append(c)
    return cs


@dataclasses.dataclass
class PolyhedralSyntaxAbsoluteTermList:
    """Represents lists of absolute terms and of terms."""

    term_list: PolyhedralSyntaxTermList
    absolute_term_list: List[PolyhedralSyntaxAbsoluteTerm] = dataclasses.field(default_factory=list)

    def __repr__(self) -> str:
        s = f"{self.term_list}"
        for a in self.absolute_term_list:
            if a.is_positive():
                s += f" + {a}"
            else:
                s += f" {a}"
        return s

    def expand(self) -> List[PolyhedralSyntaxTermList]:
        """
        Expand all positive/negative combinations of the absolute_term_list into PolyhedralSyntaxTermList.

        Each expanded PolyhedralSyntaxTermList corresponds to combining the
        term_list of a given PolyhedralSyntaxAbsoluteTerm with one of all
        possible combinations of the positive and negative variants of the
        absolute_term_list elements. If n is the length of the
        absolute_term_list, then the result has 2^n PolyhedralSyntaxTermList,
        one for each of the positive/negative combinations of each
        absolute_term_list element combined with the term_list.

        Returns:
            A list of PolyhedralSyntaxTermList instances.
        """
        if len(self.absolute_term_list) == 0:
            return [self.term_list]

        expanded: List[PolyhedralSyntaxTermList] = []

        if len(self.absolute_term_list) > 0:
            for tl in _generate_absolute_term_combinations(self.absolute_term_list):
                tlc = PolyhedralSyntaxTermList(
                    constant=self.term_list.constant, factors=self.term_list.factors.copy()
                ).add(tl)
                expanded.append(tlc)
        else:
            expanded.append(
                PolyhedralSyntaxTermList(constant=self.term_list.constant, factors=self.term_list.factors.copy())
            )

        return expanded

    def negate(self) -> "PolyhedralSyntaxAbsoluteTermList":
        """
        Negated PolyhedralSyntaxAbsoluteTermList

        Returns:
            An PolyhedralSyntaxAbsoluteTermList with negated term_list and all absolute_term_list negated.
        """
        return PolyhedralSyntaxAbsoluteTermList(
            term_list=self.term_list.negate(), absolute_term_list=[at.negate() for at in self.absolute_term_list]
        )

    def add(self, other: "PolyhedralSyntaxAbsoluteTermList") -> "PolyhedralSyntaxAbsoluteTermList":
        """
        Addition for PolyhedralSyntaxAbsoluteTermList

        Args:
            other: An PolyhedralSyntaxAbsoluteTermList to add to self.

        Returns:
            An PolyhedralSyntaxAbsoluteTermList with the term_list added
        """
        atl = self.absolute_term_list.copy()
        for at in other.absolute_term_list:
            atl = _combine_or_append(atl, at)
        return PolyhedralSyntaxAbsoluteTermList(term_list=self.term_list.add(other.term_list), absolute_term_list=atl)

    def is_constant(self) -> bool:
        """
        Is this PolyhedralSyntaxAbsoluteTermList equivalent to a constant.

        Returns:
            True if there are no PolyhedralSyntaxAbsoluteTermList and no factors in the term_list.
        """
        return len(self.absolute_term_list) == 0 and len(self.term_list.factors) == 0


class PolyhedralSyntaxOperator(Enum):
    """Represents the different kinds of expression operators."""

    eql = 1
    leq = 2
    geq = 3


@dataclasses.dataclass
class PolyhedralSyntaxExpression:
    """Base class a linear expression with an operator in between sides."""


@dataclasses.dataclass
class PolyhedralSyntaxEqlExpression(PolyhedralSyntaxExpression):
    """Represents a linear equality expression with a left and right side PolyhedralSyntaxTermList."""

    lhs: PolyhedralSyntaxTermList
    rhs: PolyhedralSyntaxTermList
    operator: PolyhedralSyntaxOperator = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        # For the validity of the following supression, see
        # https://github.com/wemake-services/wemake-python-styleguide/issues/1926
        self.operator = PolyhedralSyntaxOperator.eql  # noqa: WPS601 Found shadowed class attribute.


@dataclasses.dataclass
class PolyhedralSyntaxIneqExpression(PolyhedralSyntaxExpression):
    """Represents a linear inequality expression with 2 or more sides of type PolyhedralSyntaxAbsoluteTermList."""

    operator: PolyhedralSyntaxOperator
    sides: List[PolyhedralSyntaxAbsoluteTermList] = dataclasses.field(default_factory=list)
