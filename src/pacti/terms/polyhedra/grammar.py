"""Grammar for polyhedral terms."""

import pyparsing as pp
from enum import Enum
from typing import Dict, List, Optional, Union
from functools import reduce
from itertools import product
from pacti.terms.polyhedra.polyhedra import numeric, PolyhedralTerm, Var
import dataclasses
from typing import cast


def _factor_repr(f: float, v: str) -> str:
    n = f"{f}"
    if n == "1.0":
        return v
    elif n == "-1.0":
        return f"-{v}"
    return f"{n}{v}"


@dataclasses.dataclass
class TermList:
    """Represents a reduced list of terms (variables with a coefficient) with a constant."""

    constant: float
    factors: Dict[str, float] = dataclasses.field(default_factory=dict)

    def is_positive(self: "TermList") -> bool:
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

    def negate(self: "TermList") -> "TermList":
        """
        Negated TermList

        Returns:
            A TermList with the negated constant and all factors negated.
        """
        if self.constant is None:
            c = None
        else:
            c = -self.constant
        fs = {}
        for f, v in self.factors.items():
            fs[f] = -v
        return TermList(constant=c, factors=fs)

    def add(self: "TermList", other: "TermList") -> "TermList":
        """
        Addition of TermList.

        Args:
            other: a TermList to add to self.

        Returns:
            A new TermList with the sum of the constants and with the factors added by their variables.
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
        return TermList(constant=self.constant + other.constant, factors=fs)

    def to_polyhedral_term(self: "TermList") -> PolyhedralTerm:
        """
        Converts a TermList to a PolyhedralTerm.

        Returns:
            A PolyhedralTerm with th constant from the TermList and variables mapped from the TermList factors.
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


def _parse_only_variable(tokens: pp.ParseResults) -> TermList:
    assert len(tokens) == 1
    v = tokens[0]
    assert isinstance(v, str)
    return TermList(constant=0, factors={v: 1.0})


def _parse_number_and_variable(tokens: pp.ParseResults) -> TermList:
    number = tokens[0]
    assert isinstance(number, float)
    variable_term = tokens[len(tokens) - 1]
    assert isinstance(variable_term, TermList)
    assert variable_term.constant == 0
    for k in variable_term.factors:
        variable_term.factors[k] *= number
    return variable_term


def _parse_term(tokens: pp.ParseResults) -> TermList:
    assert len(tokens) == 1
    t0 = tokens[0]
    assert isinstance(t0, pp.ParseResults)
    tl = t0[0]
    if isinstance(tl, TermList):
        return tl
    if isinstance(tl, float):
        return TermList(constant=tl, factors={})
    raise ValueError(f"_parse_term should involve either a TermList or a float, got: {type(tl)}")


def _parse_first_term(tokens: pp.ParseResults) -> TermList:
    assert len(tokens) == 1
    group = tokens[0]
    if len(group) == 2:
        sign = group[0]
        assert isinstance(sign, str)
        tl = group[1]
        assert isinstance(tl, TermList)
        if sign == "-":
            tl.constant *= -1
            for k in tl.factors:
                tl.factors[k] *= -1
        return tl
    tl = group[0]
    assert isinstance(tl, TermList)
    return tl


def _parse_signed_term(tokens: pp.ParseResults) -> TermList:
    assert len(tokens) == 1
    group = tokens[0]
    sign = group[0]
    assert isinstance(sign, str)
    tl = group[1]
    assert isinstance(tl, TermList)
    if sign == "-":
        tl.constant *= -1
        for k in tl.factors:
            tl.factors[k] *= -1
    return tl


def _parse_term_list(tokens: pp.ParseResults) -> TermList:
    assert len(tokens) == 1
    group = tokens[0]
    return reduce(TermList.add, group, TermList(constant=0, factors={}))


def _parse_paren_terms(tokens: pp.ParseResults) -> TermList:
    assert len(tokens) == 1
    group = tokens[0]
    tl = group[1]
    assert isinstance(tl, TermList)
    return tl


def _parse_factor_paren_terms(tokens: pp.ParseResults) -> TermList:
    assert len(tokens) == 1
    group = tokens[0]
    f = group[0]
    assert isinstance(f, float)
    pt = group[len(group) - 1]
    assert isinstance(pt, TermList)
    pt.constant *= f
    for k in pt.factors:
        pt.factors[k] *= f
    return pt


@dataclasses.dataclass
class AbsoluteTerm:
    """Represents an absolute list of terms with an optional coefficient."""

    term_list: TermList
    coefficient: Optional[float] = dataclasses.field(default=None)

    def __repr__(self) -> str:
        s = f"|{self.term_list}|"
        if self.coefficient is None:
            return s
        return f"{self.coefficient}{s}"

    def is_positive(self: "AbsoluteTerm") -> bool:
        """
        Checks whether this AbsoluteTerm is positive.

        Returns:
            True if either there is no coefficient or the coefficient is positive.
        """
        if self.coefficient is None:
            return True
        return self.coefficient > 0

    def negate(self: "AbsoluteTerm") -> "AbsoluteTerm":
        """
        Constructs the negative of this AbsoluteTerm.

        Returns:
            A negated copy of this AbsoluteTerm.
        """
        if self.coefficient is None:
            return AbsoluteTerm(term_list=self.term_list, coefficient=-1.0)
        return AbsoluteTerm(term_list=self.term_list, coefficient=self.coefficient * -1.0)

    def same_term_list(self, other: "AbsoluteTerm") -> bool:
        """
        Check whether this AbsoluteTerm has the same term_list as other.

        Args:
            other: Another AbsoluteTerm

        Returns:
            True if the representation of self's term_list is equal to that of other's.
        """
        s = f"{self.term_list}"
        o = f"{other.term_list}"
        return s == o

    def to_term_list(self: "AbsoluteTerm") -> TermList:
        """
        Converts an AbsoluteTerm into a TermList.

        Returns:
            A TermList with the AbsoluteTerm coefficient applied as a multiplier for the constant and factors of the term_list.
        """
        if self.coefficient is None:
            m = 1.0
        else:
            m = self.coefficient
        c = m * self.term_list.constant
        fs: Dict[str, float] = {}
        for f, v in self.term_list.factors.items():
            fs[f] = m * v
        return TermList(constant=c, factors=fs)


def _parse_absolute_term(tokens: pp.ParseResults) -> AbsoluteTerm:
    assert len(tokens) == 1
    group = tokens[0]
    if len(group) == 4:
        coefficient = group[0]
        # group[1] = "|"
        # group[3] = "|"
        assert isinstance(coefficient, float)
        term_list = group[2]
        assert isinstance(term_list, TermList)
        return AbsoluteTerm(term_list=term_list, coefficient=coefficient)
    # group[0] = "|"
    # group[2] = "|"
    term_list = group[1]
    assert isinstance(term_list, TermList)
    return AbsoluteTerm(term_list=term_list, coefficient=None)


def _parse_positive_abs_term(tokens: pp.ParseResults) -> AbsoluteTerm:
    assert len(tokens) == 1
    group = tokens[0]
    term = group[1]
    assert isinstance(term, AbsoluteTerm)
    return term


def _parse_first_abs_term(tokens: pp.ParseResults) -> AbsoluteTerm:
    assert len(tokens) == 1
    group = tokens[0]
    if len(group) == 2:
        term = group[1]
    else:
        term = group[0]
    assert isinstance(term, AbsoluteTerm)
    return term


AbsoluteTermOrTerm = Union[AbsoluteTerm, TermList]


def _to_absolute_term_or_term(tokens: pp.ParseResults) -> AbsoluteTermOrTerm:
    if isinstance(tokens, AbsoluteTerm):
        return tokens
    elif isinstance(tokens, TermList):
        return tokens
    raise ValueError(f"Expecting either an AbsoluteTerm or a Term; got: {type(tokens)}")


def _parse_abs_or_term(tokens: pp.ParseResults) -> AbsoluteTermOrTerm:
    assert len(tokens) == 1
    group = tokens[0]
    assert len(group) == 1
    tokens = group[0]
    return _to_absolute_term_or_term(tokens)


def _generate_absolute_term_combinations(absolute_term_list: List[AbsoluteTerm]) -> List[TermList]:
    cs = []
    for signs in product([True, False], repeat=len(absolute_term_list)):
        c = TermList(constant=0, factors={})
        for i, is_positive in enumerate(signs):
            if is_positive:
                c = c.add(absolute_term_list[i].to_term_list())
            else:
                c = c.add(absolute_term_list[i].negate().to_term_list())
        cs.append(c)
    return cs


@dataclasses.dataclass
class AbsoluteTermList:
    """Represents lists of absolute terms and of terms."""

    term_list: TermList
    absolute_term_list: List[AbsoluteTerm] = dataclasses.field(default_factory=list)

    def __repr__(self) -> str:
        s = f"{self.term_list}"
        for a in self.absolute_term_list:
            if a.is_positive():
                s += f" + {a}"
            else:
                s += f" {a}"
        return s

    def expand(self) -> List[TermList]:
        """
        Expand all positive/negative combinations of AbsoluteTermList into TermLists.

        Expands the AbsoluteTermList into a list of TermLists. Each TermList corresponds to
        combining the term_list of a given AbsoluteTerm with one of all possible
        combinations of the positive and negative variants of the absolute_term_list elements.
        If n is the length of the absolute_term_list, then the result has 2^n TermLists, one
        for each of the positive/negative combinations of each absolute_term_list element combined
        with the term_list.

        Returns:
            A list of TermList instances.
        """
        if len(self.absolute_term_list) == 0:
            return [self.term_list]

        expanded: List[TermList] = []

        if len(self.absolute_term_list) > 0:
            for tl in _generate_absolute_term_combinations(self.absolute_term_list):
                tlc = TermList(constant=self.term_list.constant, factors=self.term_list.factors.copy()).add(tl)
                expanded.append(tlc)
        else:
            expanded.append(TermList(constant=self.term_list.constant, factors=self.term_list.factors.copy()))

        return expanded

    def negate(self) -> "AbsoluteTermList":
        """
        Negated AbsoluteTermList

        Returns:
            An AbsoluteTermList with negated term_list and all absolute_term_list negated.
        """
        return AbsoluteTermList(
            term_list=self.term_list.negate(), absolute_term_list=[at.negate() for at in self.absolute_term_list]
        )

    def add(self, other: "AbsoluteTermList") -> "AbsoluteTermList":
        """
        Addition of AbsoluteTermList

        Args:
            other: An AbsoluteTermList to add to self.

        Returns:
            An AbsoluteTermList with the term_list added
        """
        atl = self.absolute_term_list.copy()
        for at in other.absolute_term_list:
            atl = _combine_or_append(atl, at)
        return AbsoluteTermList(term_list=self.term_list.add(other.term_list), absolute_term_list=atl)

    def is_constant(self) -> bool:
        """
        Is this AbsoluteTermList equivalent to a constant.

        Returns:
            True if there are no AbsoluteTerms and no factors in the term_list.
        """
        if len(self.absolute_term_list) > 0:
            return False
        if len(self.term_list.factors) > 0:
            return False
        return True


def _combine_optional_floats(f1: Optional[float], f2: Optional[float]) -> Optional[float]:
    if f1 is None:
        if f2 is None:
            return None
        return f2 + 1
    if f2 is None:
        return f1 + 1
    return f1 + f2


def _combine_or_append(atl: List[AbsoluteTerm], term: AbsoluteTerm) -> List[AbsoluteTerm]:
    r: List[AbsoluteTerm] = []
    appended = False
    for at in atl:
        if at.same_term_list(term):
            r.append(
                AbsoluteTerm(
                    term_list=at.term_list, coefficient=_combine_optional_floats(at.coefficient, term.coefficient)
                )
            )
            appended = True
        else:
            r.append(at)
    if not appended:
        r.append(term)
    return r


def _parse_abs_or_terms(tokens: pp.ParseResults) -> AbsoluteTermList:
    assert len(tokens) == 1
    group = tokens[0]

    term_list: TermList = TermList(constant=0)
    absolute_term_list: List[AbsoluteTerm] = []

    for term in group:
        if isinstance(term, TermList):
            term_list = term_list.add(term)
        elif isinstance(term, AbsoluteTerm):
            absolute_term_list = _combine_or_append(absolute_term_list, term)

    return AbsoluteTermList(term_list=term_list, absolute_term_list=absolute_term_list)


def _parse_paren_abs_or_terms(tokens: pp.ParseResults) -> AbsoluteTermList:
    assert len(tokens) == 1
    group = tokens[0]
    if len(group) == 3:
        atl = group[1]
        assert isinstance(atl, AbsoluteTermList)
        return atl
    f = group[0]
    assert isinstance(f, float)
    atl = group[2]
    assert isinstance(atl, AbsoluteTermList)
    for k in atl.term_list.factors:
        atl.term_list.factors[k] *= f
    for at in atl.absolute_term_list:
        if at.coefficient is None:
            at.coefficient = f
        else:
            at.coefficient *= f
    return atl


class Operator(Enum):
    """Represents the different kinds of expression operators."""

    eql = 1
    leq = 2
    geq = 3


@dataclasses.dataclass
class Expression:
    """Represents a linear inequality expression with an operator in between sides."""

    operator: Operator
    sides: List[AbsoluteTermList] = dataclasses.field(default_factory=list)


def _parse_equality_expression(tokens: pp.ParseResults) -> Expression:
    assert len(tokens) == 1
    group = tokens[0]
    lhs = group[0]
    assert group[1] == "==" or group[1] == "="
    rhs = group[2]
    if isinstance(lhs, AbsoluteTermList) & isinstance(rhs, AbsoluteTermList):
        return Expression(operator=Operator.eql, sides=[lhs, rhs])
    raise ValueError(f"lhs and rhs should be AbsoluteTermList, got: {type(lhs)}, {type(rhs)}")


def _parse_expression_sides(op: Operator, tokens: pp.ParseResults) -> Expression:
    sides: List[AbsoluteTermList] = []
    for s in tokens.asList():
        if isinstance(s, AbsoluteTermList):
            sides.append(s)
    return Expression(operator=op, sides=sides)


def _parse_leq_expression(tokens: pp.ParseResults) -> Expression:
    assert len(tokens) == 1
    group = tokens[0]
    assert group[1] == "<="
    return _parse_expression_sides(Operator.leq, group)


def _parse_geq_expression(tokens: pp.ParseResults) -> Expression:
    assert len(tokens) == 1
    group = tokens[0]
    assert group[1] == ">="
    return _parse_expression_sides(Operator.geq, group)


def _parse_expression(tokens: pp.ParseResults) -> Expression:
    assert len(tokens) == 1
    group = tokens[0]
    e = group[0]
    if isinstance(e, Expression):
        return e
    raise ValueError(f"Expected an Expression, got: {type(e)}")


# Grammar rules

# Produces a float
floating_point_number = (
    pp.Combine(
        pp.Word(pp.nums)
        + pp.Optional("." + pp.Optional(pp.Word(pp.nums)))
        + pp.Optional(pp.CaselessLiteral("E") + pp.Optional(pp.oneOf("+ -")) + pp.Word(pp.nums))
    )
    .set_parse_action(lambda t: float(t[0]))  # noqa: WPS348
    .set_name("floating_point_number")  # noqa: WPS348
)

variable = pp.Word(pp.alphas, pp.alphanums + "_").set_name("variable")
symbol = pp.oneOf("+ -").set_name("symbol")

# Define a forward declaration for parenthesized terms
paren_terms = cast(pp.Forward, pp.Forward().set_name("paren_terms"))

# Define term options with corresponding parse actions

# Produces a TermList
only_variable = variable.set_parse_action(_parse_only_variable)

# Produces a TermList
number_and_variable = (floating_point_number + pp.Optional("*") + variable).set_parse_action(_parse_number_and_variable)

# Produces a float
only_number = floating_point_number

# Add support for parenthesized terms
# Produces a TermList
only_variable |= paren_terms

# Produces a TermList
number_and_variable |= pp.Group(floating_point_number + pp.Optional("*") + paren_terms).set_parse_action(
    _parse_factor_paren_terms
)

# Produces a TermList
only_number |= paren_terms

# Produces a TermList
term = pp.Group(only_variable | number_and_variable | only_number).set_parse_action(_parse_term).set_name("term")

# Produces a TermList
first_term = (
    pp.Group(pp.Optional(symbol, default="+") + term).set_parse_action(_parse_first_term).set_name("first_term")
)

signed_term = pp.Group(symbol + term).set_parse_action(_parse_signed_term).set_name("signed_term")

# Produces a TermList
terms = pp.Group(first_term + pp.ZeroOrMore(signed_term)).set_parse_action(_parse_term_list).set_name("terms")

# Define the rule for parenthesized terms
# Produces a TermList
paren_terms <<= pp.Group("(" + terms + ")").set_parse_action(_parse_paren_terms).set_name("paren_terms_contents")

# Produces an AbsoluteTerm
abs_term = (
    pp.Group(pp.Optional(floating_point_number) + "|" + terms + "|")
    .set_parse_action(_parse_absolute_term)  # noqa: WPS348
    .set_name("abs_term")  # noqa: WPS348
)

# Produces an AbsoluteTerm
positive_abs_term = (
    pp.Group("+" + abs_term)
    .set_parse_action(_parse_positive_abs_term)  # noqa: WPS348
    .set_name("positive_abs_term")  # noqa: WPS348
)

# Produces an AbsoluteTerm
first_abs_term = (
    pp.Group(pp.Optional("+") + abs_term)
    .set_parse_action(_parse_first_abs_term)  # noqa: WPS348
    .set_name("first_abs_term")  # noqa: WPS348
)

# Produces an AbsoluteTermOrTerm
first_abs_or_term = (
    pp.Group(first_abs_term | first_term)
    .set_parse_action(_parse_abs_or_term)  # noqa: WPS348
    .set_name("first_abs_or_term")  # noqa: WPS348
)

# Produces an AbsoluteTermOrTerm
addl_abs_or_term = (
    pp.Group(positive_abs_term | signed_term)
    .set_parse_action(_parse_abs_or_term)  # noqa: WPS348
    .set_name("addl_abs_or_term")  # noqa: WPS348
)

# Produces an AbsoluteTermList
abs_or_terms = (
    pp.Group(first_abs_or_term + pp.ZeroOrMore(addl_abs_or_term))
    .set_parse_action(_parse_abs_or_terms)
    .set_name("abs_or_terms")
)

# Produces an AbsoluteTermList
# paren_abs_or_terms = (
#     pp.Group(pp.Optional(floating_point_number) + abs_or_terms)
#     .set_parse_action(_parse_paren_abs_or_terms)
#     .set_name("paren_abs_or_terms")
# )

equality_operator = pp.Or([pp.Literal("=="), pp.Literal("=")])

# Produces an Expression
equality_expression = (
    pp.Group(abs_or_terms + equality_operator + abs_or_terms)
    .set_parse_action(_parse_equality_expression)  # noqa: WPS348
    .set_name("equality_expression")  # noqa: WPS348
)

# Produces an Expression
leq_expression = (
    pp.Group(abs_or_terms + pp.OneOrMore("<=" + abs_or_terms))
    .set_parse_action(_parse_leq_expression)  # noqa: WPS348
    .set_name("leq_expression")  # noqa: WPS348
)

# Produces an Expression
geq_expression = (
    pp.Group(abs_or_terms + pp.OneOrMore(">=" + abs_or_terms))
    .set_parse_action(_parse_geq_expression)  # noqa: WPS348
    .set_name("geq_expression")  # noqa: WPS348
)

# Produces an Expression
expression = (
    pp.Group(equality_expression | leq_expression | geq_expression)
    .set_parse_action(_parse_expression)  # noqa: WPS348
    .set_name("expression")  # noqa: WPS348
)
