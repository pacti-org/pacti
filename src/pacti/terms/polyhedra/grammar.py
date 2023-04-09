import pyparsing as pp
from typing import Dict, List, Union
import dataclasses

@dataclasses.dataclass
class Term:
    coefficient: float
    variable: Union[str, None]

    def __repr__(self) -> str:
        if self.variable:
            return f"{self.coefficient}{self.variable}"
        else:
            return f"{self.coefficient}"

    def combine(self, other: "Term") -> "Term":
        return Term(coefficient=self.coefficient * other.coefficient, variable=other.variable)


def parse_only_variable(t: List[pp.ParseResults]) -> Term:
    return Term(coefficient=1.0, variable=t[0])


def parse_only_number(t: List[pp.ParseResults]) -> Term:
    return Term(coefficient=float(t[0]), variable=None)


def parse_number_and_variable(t: List[pp.ParseResults]) -> Term:
    number_term = t[0]
    variable_term = t[1]
    return number_term.combine(variable_term)


def parse_term(t: List[pp.ParseResults]) -> Term:
    term: Term = t[0]
    return term


def parse_signed_term(t: List[pp.ParseResults]) -> Term:
    group = t[0]
    sign: str = group[0]
    term: Term = group[1]
    if sign == "-":
        term.coefficient *= -1
    return term


@dataclasses.dataclass
class TermList:
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


def parse_term_list(t: List[pp.ParseResults]) -> TermList:
    group = t[0]
    constant = 0
    factors: Dict[str, float] = {}

    # Process the terms
    for term in [group[0], *group[2::2]]:
        if term.variable is None:
            constant += term.coefficient
        else:
            if term.variable in factors:
                factors[term.variable] += term.coefficient
            else:
                factors[term.variable] = term.coefficient

    return TermList(constant=constant, factors=factors)



# Grammar rules

floating_point_number = pp.Combine(
    pp.Word(pp.nums)
    + pp.Optional("." + pp.Optional(pp.Word(pp.nums)))
    + pp.Optional(pp.CaselessLiteral("E") + pp.Optional(pp.oneOf("+ -")) + pp.Word(pp.nums))
).set_parse_action(lambda t: float(t[0]))

variable = pp.Word(pp.alphas)
symbol = pp.oneOf("+ -")

# Define term options with corresponding parse actions

only_variable = variable.set_parse_action(parse_only_variable)
number_and_variable = (floating_point_number + variable).set_parse_action(parse_number_and_variable)
only_number = floating_point_number.set_parse_action(parse_only_number)

# Produces a Term
term = pp.Group(only_variable | number_and_variable | only_number).set_parse_action(parse_term)

# Produces a Term
signed_term = pp.Group(pp.Optional(symbol, default="+") + term).set_parse_action(parse_signed_term)

# Produces a TermList
terms = pp.Group(signed_term + pp.ZeroOrMore(symbol + term)).set_parse_action(parse_term_list)

abs_term = pp.Group(pp.Optional(floating_point_number) + "|" + terms + "|")
signed_abs_term = pp.Group(pp.Optional(symbol, default="+") + pp.Group(abs_term | term))

abs_terms = pp.Group(signed_abs_term + pp.ZeroOrMore(symbol + pp.Group(signed_abs_term | term)))

equality_expression = pp.Group(abs_terms + "==" + abs_terms)

leq_expression = pp.Group(abs_terms + pp.OneOrMore("<=" + abs_terms))

geq_expression = pp.Group(abs_terms + pp.OneOrMore(">=" + abs_terms))

expression = pp.Group(equality_expression | leq_expression | geq_expression)
