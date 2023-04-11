"""Grammar for polyhedral terms."""

import pyparsing as pp
from typing import Dict, List, Optional, Union
import dataclasses


def _factor_repr(f: float, v: str) -> str:
    n = f"{f}"
    if n == "1.0":
        return v
    elif n == "-1.0":
        return f"-{v}"
    return f"{n}{v}"


@dataclasses.dataclass
class Term:
    """A Term represents either a constant (variable=None) or a variable with a constant coefficient."""

    coefficient: float
    variable: Union[str, None]

    def __repr__(self) -> str:
        if self.variable:
            return _factor_repr(self.coefficient, self.variable)
        return f"{self.coefficient}"

    def combine(self, other: "Term") -> "Term":
        """
        Combines a number term with a variable term.

        Args:
            other: a variable Term

        Returns:
            A new Term with the product of the coefficients for the other variable.
        """
        return Term(coefficient=self.coefficient * other.coefficient, variable=other.variable)

    def negate(self: "Term") -> "Term":
        """
        Negates this term.

        Returns:
            The negative of this term.
        """
        return Term(coefficient=-1.0, variable=None).combine(self)


def _parse_only_variable(tokens: pp.ParseResults) -> Term:
    assert len(tokens) == 1
    v = str(tokens[0])
    return Term(coefficient=1.0, variable=v)


def _parse_only_number(tokens: pp.ParseResults) -> Term:
    assert len(tokens) == 1
    return Term(coefficient=float(tokens[0]), variable=None)


def _parse_number_and_variable(tokens: pp.ParseResults) -> Term:
    assert len(tokens) == 2
    number_term = tokens[0]
    assert isinstance(number_term, Term)
    variable_term = tokens[1]
    assert isinstance(variable_term, Term)
    return number_term.combine(variable_term)


def _parse_term(tokens: pp.ParseResults) -> Term:
    assert len(tokens) == 1
    t0 = tokens[0]
    assert isinstance(t0, pp.ParseResults)
    term = t0[0]
    assert isinstance(term, Term)
    return term


def _parse_signed_term(tokens: pp.ParseResults) -> Term:
    assert len(tokens) == 1
    group = tokens[0]
    sign = group[0]
    assert isinstance(sign, str)
    term = group[1]
    assert isinstance(term, Term)
    if sign == "-":
        term.coefficient *= -1
    return term


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
        if self.constant is not None:
            return self.constant > 0
        var = sorted(self.factors)[0]
        return self.factors[var] > 0

    def combine(self: "TermList", term: Term) -> "TermList":
        """
        Additively combine an extra Term into this TermList.

        Args:
            term: A Term.

        Returns:
            The TermList with the extra term additively combined as a factor or a constant according
            to whether the term has a variable or not.
        """
        if term.variable is None:
            self.constant += term.coefficient
        else:
            if term.variable in self.factors:
                self.factors[term.variable] += term.coefficient
            else:
                self.factors[term.variable] = term.coefficient
        return self

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


def _parse_term_list(tokens: pp.ParseResults) -> TermList:
    assert len(tokens) == 1
    group = tokens[0]
    constant = 0
    factors: Dict[str, float] = {}

    # Process the terms along with their corresponding symbols
    for symbol, term in zip(["+"] + group[1::2], [group[0]] + group[2::2]):
        if symbol == "-":
            term.coefficient *= -1

        if term.variable is None:
            constant += term.coefficient
        else:
            if term.variable in factors:
                factors[term.variable] += term.coefficient
            else:
                factors[term.variable] = term.coefficient

    return TermList(constant=constant, factors=factors)


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


def _parse_absolute_term(tokens: pp.ParseResults) -> AbsoluteTerm:
    assert len(tokens) == 1
    group = tokens[0]
    if len(group) == 4:
        coefficient = group[0]
        assert isinstance(coefficient, Term)
        assert coefficient.variable is None
        term_list = group[2]
        assert isinstance(term_list, TermList)
        return AbsoluteTerm(term_list=term_list, coefficient=coefficient.coefficient)
    term_list = group[1]
    assert isinstance(term_list, TermList)
    return AbsoluteTerm(term_list=term_list, coefficient=None)


AbsoluteTermOrTerm = Union[AbsoluteTerm, Term]


def _to_absolute_term_or_term(tokens: pp.ParseResults) -> AbsoluteTermOrTerm:
    if isinstance(tokens, AbsoluteTerm):
        return tokens
    elif isinstance(tokens, Term):
        return tokens
    raise ValueError(f"Expecting either an AbsoluteTerm or a Term; got: {type(tokens)}")


def _parse_absolute_term_or_term(tokens: pp.ParseResults) -> AbsoluteTermOrTerm:
    assert len(tokens) == 1
    group = tokens[0]
    assert len(group) == 1
    tokens = group[0]
    return _to_absolute_term_or_term(tokens)


def _parse_sign_of_absolute_term_or_term(tokens: pp.ParseResults) -> AbsoluteTermOrTerm:
    assert len(tokens) == 1
    group = tokens[0]
    if len(group) == 1:
        tokens = group[0]
        return _to_absolute_term_or_term(tokens)
    sign = group[0]
    tokens = group[1]
    if sign == "+":
        return _to_absolute_term_or_term(tokens)
    if isinstance(tokens, AbsoluteTerm):
        if tokens.coefficient is None:
            tokens.coefficient = -1.0
        else:
            tokens.coefficient *= -1.0
        return tokens
    elif isinstance(tokens, Term):
        tokens.coefficient *= -1.0
        return tokens
    raise ValueError(f"Expecting either an AbsoluteTerm or a Term; got: {type(tokens)}")


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


def _update_term_list(term_list: TermList, symbol: str, term: Term) -> TermList:
    if symbol == "-":
        term_list = term_list.combine(term.negate())
    else:
        term_list = term_list.combine(term)
    return term_list


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


def _update_absolute_term_list(
    absolute_term_list: List[AbsoluteTerm], symbol: str, term: AbsoluteTerm
) -> List[AbsoluteTerm]:
    if symbol == "-":
        return _combine_or_append(absolute_term_list, term.negate())
    return _combine_or_append(absolute_term_list, term)


def _parse_abs_or_terms(tokens: pp.ParseResults) -> AbsoluteTermList:
    assert len(tokens) == 1
    group = tokens[0]

    term_list: TermList = TermList(constant=0)
    absolute_term_list: List[AbsoluteTerm] = []

    for symbol, term in zip(["+"] + group[1::2], [group[0]] + group[2::2]):
        if isinstance(term, Term):
            term_list = _update_term_list(term_list, symbol, term)
        elif isinstance(term, AbsoluteTerm):
            absolute_term_list = _update_absolute_term_list(absolute_term_list, symbol, term)

    return AbsoluteTermList(term_list=term_list, absolute_term_list=absolute_term_list)


# Grammar rules

floating_point_number = (
    pp.Combine(
        pp.Word(pp.nums)
        + pp.Optional("." + pp.Optional(pp.Word(pp.nums)))
        + pp.Optional(pp.CaselessLiteral("E") + pp.Optional(pp.oneOf("+ -")) + pp.Word(pp.nums))
    )
    .set_parse_action(lambda t: float(t[0]))  # noqa: WPS348
    .set_name("floating_point_number")  # noqa: WPS348
)

variable = pp.Word(pp.alphas).set_name("variable")
symbol = pp.oneOf("+ -").set_name("symbol")

# Define term options with corresponding parse actions

only_variable = variable.set_parse_action(_parse_only_variable)
number_and_variable = (floating_point_number + variable).set_parse_action(_parse_number_and_variable)
only_number = floating_point_number.set_parse_action(_parse_only_number)

# Produces a Term
term = pp.Group(only_variable | number_and_variable | only_number).set_parse_action(_parse_term).set_name("term")

# Produces a Term
signed_term = (
    pp.Group(pp.Optional(symbol, default="+") + term).set_parse_action(_parse_signed_term).set_name("signed_term")
)

# Produces a TermList
terms = pp.Group(signed_term + pp.ZeroOrMore(symbol + term)).set_parse_action(_parse_term_list).set_name("terms")

# Produces an AbsoluteTerm
abs_term = (
    pp.Group(pp.Optional(floating_point_number) + "|" + terms + "|")
    .set_parse_action(_parse_absolute_term)  # noqa: WPS348
    .set_name("abs_term")  # noqa: WPS348
)

# Produces an AbsoluteTermOrTerm
abs_or_term = pp.Group(abs_term | term).set_parse_action(_parse_absolute_term_or_term).set_name("abs_or_term")

# Produces an AbsoluteTermOrTerm
signed_abs_or_term = (
    pp.Group(pp.Optional(symbol, default="+") + abs_or_term)
    .set_parse_action(_parse_sign_of_absolute_term_or_term)  # noqa: WPS348
    .set_name("signed_abs_or_term")  # noqa: WPS348
)

# Produces an AbsoluteTermList
abs_or_terms = (
    pp.Group(signed_abs_or_term + pp.ZeroOrMore(symbol + abs_or_term))
    .set_parse_action(_parse_abs_or_terms)  # noqa: WPS348
    .set_name("abs_or_terms")  # noqa: WPS348
)

equality_expression = pp.Group(abs_or_terms + "==" + abs_or_terms).set_name("equality_expression")

leq_expression = pp.Group(abs_or_terms + pp.OneOrMore("<=" + abs_or_terms)).set_name("leq_expression")

geq_expression = pp.Group(abs_or_terms + pp.OneOrMore(">=" + abs_or_terms)).set_name("geq_expression")

expression = pp.Group(equality_expression | leq_expression | geq_expression).set_name("expression")

# The generated html is missing the styles to show shapes with a different color than the background.
# https://github.com/pyparsing/pyparsing/blob/efb796099fd77d003dcd49df6a75d1dcc19cefb1/docs/_static/sql_railroad.html#L21-L52

# If this is done outside of this file, we get an import exception.
# <style>/* <![CDATA[ */
#     svg.railroad-diagram {
#         background-color:hsl(30,20%,95%);
#     }
#     svg.railroad-diagram path {
#         stroke-width:3;
#         stroke:black;
#         fill:rgba(0,0,0,0);
#     }
#     svg.railroad-diagram text {
#         font:bold 14px monospace;
#         text-anchor:middle;
#     }
#     svg.railroad-diagram text.label{
#         text-anchor:start;
#     }
#     svg.railroad-diagram text.comment{
#         font:italic 12px monospace;
#     }
#     svg.railroad-diagram rect{
#         stroke-width:3;
#         stroke:black;
#         fill:hsl(120,100%,90%);
#     }
#     svg.railroad-diagram rect.group-box {
#         stroke: gray;
#         stroke-dasharray: 10 5;
#         fill: none;
#     }

# /* ]]> */
# </style>

# expression.create_diagram(output_html="docs/expression.html", show_groups=True)
