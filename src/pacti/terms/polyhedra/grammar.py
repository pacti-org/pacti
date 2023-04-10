"""Grammar for polyhedral terms."""

import pyparsing as pp
from typing import Dict, Optional, Union
import dataclasses


@dataclasses.dataclass
class Term:
    """A Term represents either a constant (variable=None) or a variable with a constant coefficient."""

    coefficient: float
    variable: Union[str, None]

    def __repr__(self) -> str:
        if self.variable:
            return f"{self.coefficient}{self.variable}"
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


def _parse_only_variable(t: pp.ParseResults) -> Term:
    assert len(t) == 1
    v = str(t[0])
    return Term(coefficient=1.0, variable=v)


def _parse_only_number(t: pp.ParseResults) -> Term:
    assert len(t) == 1
    return Term(coefficient=float(t[0]), variable=None)


def _parse_number_and_variable(t: pp.ParseResults) -> Term:
    assert len(t) == 2
    number_term = t[0]
    assert isinstance(number_term, Term)
    variable_term = t[1]
    assert isinstance(variable_term, Term)
    return number_term.combine(variable_term)


def _parse_term(t: pp.ParseResults) -> Term:
    assert len(t) == 1
    t0 = t[0]
    assert isinstance(t0, pp.ParseResults)
    term = t0[0]
    assert isinstance(term, Term)
    return term


def _parse_signed_term(t: pp.ParseResults) -> Term:
    assert len(t) == 1
    group = t[0]
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

    def __repr__(self) -> str:
        if self.constant == 0:
            s = ""
        else:
            s = f"{self.constant}"
        for var in sorted(self.factors):
            f: float = self.factors[var]
            if len(s) == 0:
                s = f"{f}{var}"
            else:
                if f > 0:
                    s += f" + {f}{var}"
                else:
                    s += f" - {abs(f)}{var}"
        return s


def _parse_term_list(t: pp.ParseResults) -> TermList:
    assert len(t) == 1
    group = t[0]
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


def _parse_absolute_term(t: pp.ParseResults) -> AbsoluteTerm:
    assert len(t) == 1
    group = t[0]
    if len(group) == 4:
        coefficient = group[0]
        assert isinstance(coefficient, Term)
        assert coefficient.variable is None
        term_list = group[2]
        assert isinstance(term_list, TermList)
        return AbsoluteTerm(term_list=term_list)
    term_list = group[1]
    assert isinstance(term_list, TermList)
    return AbsoluteTerm(term_list=term_list, coefficient=1.0)


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

abs_term = (
    pp.Group(pp.Optional(floating_point_number) + "|" + terms + "|")
    .set_parse_action(_parse_absolute_term)  # noqa: WPS348
    .set_name("abs_term")  # noqa: WPS348
)

abs_or_term = pp.Group(abs_term | term).set_name("abs_or_term")

signed_abs_or_term = pp.Group(pp.Optional(symbol, default="+") + abs_or_term).set_name("signed_abs_or_term")

abs_or_terms = pp.Group(signed_abs_or_term + pp.ZeroOrMore(symbol + abs_or_term)).set_name("abs_or_terms")

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
