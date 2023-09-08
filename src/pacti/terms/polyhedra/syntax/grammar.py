"""Grammar for polyhedral terms."""

from functools import reduce
from typing import List, cast

import pyparsing as pp

from pacti.terms.polyhedra.syntax.data import (  # noqa: WPS235, WPS450 too many imported names, _combine_or_append is protected
    PolyhedralSyntaxAbsoluteTerm,
    PolyhedralSyntaxAbsoluteTermList,
    PolyhedralSyntaxAbsoluteTermOrTerm,
    PolyhedralSyntaxEqlExpression,
    PolyhedralSyntaxExpression,
    PolyhedralSyntaxIneqExpression,
    PolyhedralSyntaxOperator,
    PolyhedralSyntaxTermList,
    _combine_or_append,
)


def _parse_only_variable(tokens: pp.ParseResults) -> PolyhedralSyntaxTermList:
    assert len(tokens) == 1
    v = tokens[0]
    assert isinstance(v, str)
    return PolyhedralSyntaxTermList(constant=0, factors={v: 1.0})


def _parse_number_and_variable(tokens: pp.ParseResults) -> PolyhedralSyntaxTermList:
    number = tokens[0]
    assert isinstance(number, float)
    variable_term = tokens[len(tokens) - 1]  # noqa: WPS530 Found implicit negative index
    assert isinstance(variable_term, PolyhedralSyntaxTermList)
    assert variable_term.constant == 0
    for k in variable_term.factors:
        variable_term.factors[k] *= number
    return variable_term


def _parse_term(tokens: pp.ParseResults) -> PolyhedralSyntaxTermList:
    assert len(tokens) == 1
    t0 = tokens[0]
    assert isinstance(t0, pp.ParseResults)
    tl = t0[0]
    if isinstance(tl, PolyhedralSyntaxTermList):
        return tl
    if isinstance(tl, float):
        return PolyhedralSyntaxTermList(constant=tl, factors={})
    raise ValueError(f"_parse_term should involve either a TermList or a float, got: {type(tl)}")


def _parse_first_term(tokens: pp.ParseResults) -> PolyhedralSyntaxTermList:
    assert len(tokens) == 1
    group = tokens[0]
    if len(group) == 2:
        sign = group[0]
        assert isinstance(sign, str)
        tl = group[1]
        assert isinstance(tl, PolyhedralSyntaxTermList)
        if sign == "-":
            return tl.negate()
        return tl
    tl = group[0]
    assert isinstance(tl, PolyhedralSyntaxTermList)
    return tl


def _parse_signed_term(tokens: pp.ParseResults) -> PolyhedralSyntaxTermList:
    assert len(tokens) == 1
    group = tokens[0]
    sign = group[0]
    assert isinstance(sign, str)
    tl = group[1]
    assert isinstance(tl, PolyhedralSyntaxTermList)
    if sign == "-":
        return tl.negate()
    return tl


def _parse_term_list(tokens: pp.ParseResults) -> PolyhedralSyntaxTermList:
    assert len(tokens) == 1
    group = tokens[0]
    return reduce(PolyhedralSyntaxTermList.add, group, PolyhedralSyntaxTermList(constant=0, factors={}))


def _parse_paren_terms(tokens: pp.ParseResults) -> PolyhedralSyntaxTermList:
    assert len(tokens) == 1
    group = tokens[0]
    tl = group[1]
    assert isinstance(tl, PolyhedralSyntaxTermList)
    return tl


def _parse_factor_paren_terms(tokens: pp.ParseResults) -> PolyhedralSyntaxTermList:
    assert len(tokens) == 1
    group = tokens[0]
    f = group[0]
    assert isinstance(f, float)
    pt = group[len(group) - 1]  # noqa: WPS530 Found implicit negative index
    assert isinstance(pt, PolyhedralSyntaxTermList)
    pt.constant *= f
    for k in pt.factors:
        pt.factors[k] *= f
    return pt


def _parse_absolute_term(tokens: pp.ParseResults) -> PolyhedralSyntaxAbsoluteTerm:
    assert len(tokens) == 1
    group = tokens[0]
    if len(group) == 3:
        # group[0] = "|"
        # group[2] = "|"
        term_list = group[1]
        assert isinstance(term_list, PolyhedralSyntaxTermList)
        return PolyhedralSyntaxAbsoluteTerm(term_list=term_list, coefficient=None)

    coefficient = group[0]
    assert isinstance(coefficient, float)
    term_list = group[len(group) - 2]  # noqa: WPS530 Found implicit negative index
    assert isinstance(term_list, PolyhedralSyntaxTermList)
    return PolyhedralSyntaxAbsoluteTerm(term_list=term_list, coefficient=coefficient)


def _parse_signed_abs_term(tokens: pp.ParseResults) -> PolyhedralSyntaxAbsoluteTerm:
    assert len(tokens) == 1
    group = tokens[0]
    sign = group[0]
    assert isinstance(sign, str)
    term = group[1]
    assert isinstance(term, PolyhedralSyntaxAbsoluteTerm)
    if sign == "-":
        term = term.negate()
    return term


def _parse_first_abs_term(tokens: pp.ParseResults) -> PolyhedralSyntaxAbsoluteTerm:
    assert len(tokens) == 1
    group = tokens[0]
    if len(group) == 2:
        symbol = group[0]
        term = group[1]
    else:
        symbol = "+"
        term = group[0]
    assert isinstance(term, PolyhedralSyntaxAbsoluteTerm)
    if symbol == "-":
        term = term.negate()
    return term


def _to_absolute_term_or_term(tokens: pp.ParseResults) -> PolyhedralSyntaxAbsoluteTermOrTerm:
    if isinstance(tokens, PolyhedralSyntaxAbsoluteTerm):
        return tokens
    elif isinstance(tokens, PolyhedralSyntaxTermList):
        return tokens
    raise ValueError(f"Expecting either an AbsoluteTerm or a Term; got: {type(tokens)}")


def _parse_abs_or_term(tokens: pp.ParseResults) -> PolyhedralSyntaxAbsoluteTermOrTerm:
    assert len(tokens) == 1
    group = tokens[0]
    assert len(group) == 1
    tokens = group[0]
    return _to_absolute_term_or_term(tokens)


def _parse_abs_or_terms(tokens: pp.ParseResults) -> PolyhedralSyntaxAbsoluteTermList:
    assert len(tokens) == 1
    group = tokens[0]

    term_list: PolyhedralSyntaxTermList = PolyhedralSyntaxTermList(constant=0)
    absolute_term_list: List[PolyhedralSyntaxAbsoluteTerm] = []

    for term in group:
        if isinstance(term, PolyhedralSyntaxTermList):
            term_list = term_list.add(term)
        elif isinstance(term, PolyhedralSyntaxAbsoluteTerm):
            absolute_term_list = _combine_or_append(absolute_term_list, term)

    return PolyhedralSyntaxAbsoluteTermList(term_list=term_list, absolute_term_list=absolute_term_list)


def _parse_paren_abs_or_terms(tokens: pp.ParseResults) -> PolyhedralSyntaxAbsoluteTermList:
    assert len(tokens) == 1
    group = tokens[0]
    if len(group) == 3:
        atl = group[1]
        assert isinstance(atl, PolyhedralSyntaxAbsoluteTermList)
        return atl
    f = group[0]
    assert isinstance(f, float)
    atl = group[len(group) - 2]  # noqa: WPS530 Found implicit negative index
    assert isinstance(atl, PolyhedralSyntaxAbsoluteTermList)
    atl.term_list.constant *= f
    for k in atl.term_list.factors:
        atl.term_list.factors[k] *= f
    for at in atl.absolute_term_list:
        if at.coefficient is None:
            at.coefficient = f
        else:
            at.coefficient *= f
    return atl


def _parse_first_or_addl_paren_abs_or_terms(  # noqa: WPS231
    tokens: pp.ParseResults,
) -> PolyhedralSyntaxAbsoluteTermList:
    assert len(tokens) == 1
    group = tokens[0]

    if len(group) == 2:
        symbol = group[0]
        term = group[1]
    else:
        symbol = "+"
        term = group[0]

    term_list: PolyhedralSyntaxTermList = PolyhedralSyntaxTermList(constant=0)
    absolute_term_list: List[PolyhedralSyntaxAbsoluteTerm] = []

    if isinstance(term, PolyhedralSyntaxTermList):
        term_list = term_list.add(term)
        if symbol == "-":
            term_list = term_list.negate()
    elif isinstance(term, PolyhedralSyntaxAbsoluteTerm):
        if symbol == "-":
            term = term.negate()
        absolute_term_list = _combine_or_append(absolute_term_list, term)
    elif isinstance(term, PolyhedralSyntaxAbsoluteTermList):
        if symbol == "-":
            term = term.negate()
        current = PolyhedralSyntaxAbsoluteTermList(term_list=term_list, absolute_term_list=absolute_term_list).add(term)
        term_list = current.term_list
        absolute_term_list = current.absolute_term_list

    return PolyhedralSyntaxAbsoluteTermList(term_list=term_list, absolute_term_list=absolute_term_list)


def _parse_multi_paren_abs_or_terms(tokens: pp.ParseResults) -> PolyhedralSyntaxAbsoluteTermList:
    assert len(tokens) == 1
    group = tokens[0]

    term_list: PolyhedralSyntaxTermList = PolyhedralSyntaxTermList(constant=0)
    absolute_term_list: List[PolyhedralSyntaxAbsoluteTerm] = []

    for term in group:
        if isinstance(term, PolyhedralSyntaxTermList):
            term_list = term_list.add(term)
        elif isinstance(term, PolyhedralSyntaxAbsoluteTerm):
            absolute_term_list = _combine_or_append(absolute_term_list, term)
        elif isinstance(term, PolyhedralSyntaxAbsoluteTermList):
            current = PolyhedralSyntaxAbsoluteTermList(term_list=term_list, absolute_term_list=absolute_term_list).add(
                term
            )
            term_list = current.term_list
            absolute_term_list = current.absolute_term_list

    return PolyhedralSyntaxAbsoluteTermList(term_list=term_list, absolute_term_list=absolute_term_list)


def _parse_equality_expression(tokens: pp.ParseResults) -> PolyhedralSyntaxExpression:
    assert len(tokens) == 1
    group = tokens[0]
    lhs = group[0]
    assert group[1] in {"==", "="}
    rhs = group[2]
    if isinstance(lhs, PolyhedralSyntaxTermList) & isinstance(rhs, PolyhedralSyntaxTermList):
        return PolyhedralSyntaxEqlExpression(lhs=lhs, rhs=rhs)  # (VS-Code) # type: ignore
    raise ValueError(f"lhs and rhs should be PolyhedralSyntaxTermList, got: {type(lhs)}, {type(rhs)}")


def _parse_expression_sides(op: PolyhedralSyntaxOperator, tokens: pp.ParseResults) -> PolyhedralSyntaxExpression:
    sides: List[PolyhedralSyntaxAbsoluteTermList] = []
    for s in tokens.asList():
        if isinstance(s, PolyhedralSyntaxAbsoluteTermList):
            sides.append(s)
    return PolyhedralSyntaxIneqExpression(operator=op, sides=sides)


def _parse_leq_expression(tokens: pp.ParseResults) -> PolyhedralSyntaxExpression:
    assert len(tokens) == 1
    group = tokens[0]
    assert group[1] == "<="
    return _parse_expression_sides(PolyhedralSyntaxOperator.leq, group)


def _parse_geq_expression(tokens: pp.ParseResults) -> PolyhedralSyntaxExpression:
    assert len(tokens) == 1
    group = tokens[0]
    assert group[1] == ">="
    return _parse_expression_sides(PolyhedralSyntaxOperator.geq, group)


def _parse_expression(tokens: pp.ParseResults) -> PolyhedralSyntaxExpression:
    assert len(tokens) == 1
    group = tokens[0]
    e = group[0]
    if isinstance(e, PolyhedralSyntaxExpression):
        return e
    raise ValueError(f"Expected an Expression, got: {type(e)}")


# Grammar rules

# Produces a float
floating_point_number = (
    pp.Combine(
        pp.Or([pp.Word(pp.nums) + pp.Optional("." + pp.Optional(pp.Word(pp.nums))), "." + pp.Word(pp.nums)])
        + pp.Optional(pp.CaselessLiteral("E") + pp.Optional(pp.oneOf("+ -")) + pp.Word(pp.nums))
    )
    .set_parse_action(lambda t: float(t[0]))  # noqa: WPS348
    .set_name("floating_point_number")  # noqa: WPS348
)

# Basic arithmetic operations
plus, minus, mult, div = map(pp.Literal, "+-*/")

# Using infixNotation to manage precedence of operations
arithmetic_expr = pp.infixNotation(
    floating_point_number,
    [
        (mult | div, 2, pp.opAssoc.LEFT, lambda s, l, t: t[0][0] * t[0][2] if t[0][1] == "*" else t[0][0] / t[0][2]),
        (plus | minus, 2, pp.opAssoc.LEFT, lambda s, l, t: t[0][0] + t[0][2] if t[0][1] == "+" else t[0][0] - t[0][2]),
    ],
)

paren_arith_expr = pp.Group(pp.Suppress("(") + arithmetic_expr + pp.Suppress(")")).setParseAction(lambda t: t[0][0])

variable = pp.Word(pp.alphas, pp.alphanums + "_").set_name("variable")
symbol = pp.oneOf("+ -").set_name("symbol")

# Define a forward declaration for parenthesized terms
paren_terms = cast(pp.Forward, pp.Forward().set_name("paren_terms"))

# Define term options with corresponding parse actions

# Produces a PolyhedralSyntaxTermList
only_variable = variable.set_parse_action(_parse_only_variable)

# Produces a PolyhedralSyntaxTermList
number_and_variable = ((floating_point_number ^ paren_arith_expr) + pp.Optional("*") + variable).set_parse_action(
    _parse_number_and_variable
)

# Produces a float
only_number = floating_point_number ^ paren_arith_expr

# Add support for parenthesized terms
# Produces a PolyhedralSyntaxTermList
only_variable |= paren_terms

# Produces a PolyhedralSyntaxTermList
number_and_variable |= pp.Group(
    (floating_point_number ^ paren_arith_expr) + pp.Optional("*") + paren_terms
).set_parse_action(_parse_factor_paren_terms)

# Produces a PolyhedralSyntaxTermList
only_number |= paren_terms

# Produces a PolyhedralSyntaxTermList
term = pp.Group(only_variable | number_and_variable | only_number).set_parse_action(_parse_term).set_name("term")

# Produces a PolyhedralSyntaxTermList
first_term = (
    pp.Group(pp.Optional(symbol, default="+") + term).set_parse_action(_parse_first_term).set_name("first_term")
)

# Produces a PolyhedralSyntaxTermList
signed_term = pp.Group(symbol + term).set_parse_action(_parse_signed_term).set_name("signed_term")

# Produces a PolyhedralSyntaxTermList
terms = pp.Group(first_term + pp.ZeroOrMore(signed_term)).set_parse_action(_parse_term_list).set_name("terms")

# Define the rule for parenthesized terms
# Produces a PolyhedralSyntaxTermList
paren_terms <<= pp.Group("(" + terms + ")").set_parse_action(_parse_paren_terms).set_name("paren_terms_contents")

# Produces an PolyhedralSyntaxAbsoluteTerm
abs_term = (
    pp.Group(pp.Optional((floating_point_number ^ paren_arith_expr) + pp.Optional("*")) + "|" + terms + "|")
    .set_parse_action(_parse_absolute_term)  # noqa: WPS348
    .set_name("abs_term")  # noqa: WPS348
)

# Produces an PolyhedralSyntaxAbsoluteTerm
signed_abs_term = (
    pp.Group(symbol + abs_term)
    .set_parse_action(_parse_signed_abs_term)  # noqa: WPS348
    .set_name("signed_abs_term")  # noqa: WPS348
)

# Produces an PolyhedralSyntaxAbsoluteTerm
first_abs_term = (
    pp.Group(pp.Optional(symbol, default="+") + abs_term)
    .set_parse_action(_parse_first_abs_term)  # noqa: WPS348
    .set_name("first_abs_term")  # noqa: WPS348
)

# Produces an PolyhedralSyntaxAbsoluteTermOrTerm
first_abs_or_term = (
    pp.Group(first_abs_term | first_term)
    .set_parse_action(_parse_abs_or_term)  # noqa: WPS348
    .set_name("first_abs_or_term")  # noqa: WPS348
)

# Produces an PolyhedralSyntaxAbsoluteTermOrTerm
addl_abs_or_term = (
    pp.Group(signed_abs_term | signed_term)
    .set_parse_action(_parse_abs_or_term)  # noqa: WPS348
    .set_name("addl_abs_or_term")  # noqa: WPS348
)

# Produces an PolyhedralSyntaxAbsoluteTermList
abs_or_terms = (
    pp.Group(first_abs_or_term + pp.ZeroOrMore(addl_abs_or_term))
    .set_parse_action(_parse_abs_or_terms)  # noqa: WPS348
    .set_name("abs_or_terms")  # noqa: WPS348
)

# Produces an PolyhedralSyntaxAbsoluteTermList
paren_abs_or_terms = (
    pp.Group(pp.Optional((floating_point_number ^ paren_arith_expr) + pp.Optional("*")) + "(" + abs_or_terms + ")")
    .set_parse_action(_parse_paren_abs_or_terms)  # noqa: WPS348
    .set_name("paren_abs_or_terms")  # noqa: WPS348
)

# Produces an PolyhedralSyntaxAbsoluteTermList
first_paren_abs_or_terms = (
    pp.Group(pp.Optional(symbol, default="+") + paren_abs_or_terms | first_abs_or_term)
    .set_parse_action(_parse_first_or_addl_paren_abs_or_terms)  # noqa: WPS348
    .set_name("first_paren_abs_or_terms")  # noqa: WPS348
)

# Produces an PolyhedralSyntaxAbsoluteTermList
addl_paren_abs_or_terms = (
    pp.Group(symbol + paren_abs_or_terms | addl_abs_or_term)
    .set_parse_action(_parse_first_or_addl_paren_abs_or_terms)  # noqa: WPS348
    .set_name("addl_paren_abs_or_terms")  # noqa: WPS348
)

# Produces an PolyhedralSyntaxAbsoluteTermList
multi_paren_abs_or_terms = (
    pp.Group(first_paren_abs_or_terms + pp.ZeroOrMore(addl_paren_abs_or_terms))
    .set_parse_action(_parse_multi_paren_abs_or_terms)  # noqa: WPS348
    .set_name("multi_paren_abs_or_terms")  # noqa: WPS348
)

equality_operator = pp.Or([pp.Literal("=="), pp.Literal("=")])

# Produces an PolyhedralSyntaxExpression
equality_expression = (
    pp.Group(terms + equality_operator + terms)
    .set_parse_action(_parse_equality_expression)  # noqa: WPS348
    .set_name("equality_expression")  # noqa: WPS348
)

# Produces an PolyhedralSyntaxExpression
leq_expression = (
    pp.Group(multi_paren_abs_or_terms + pp.OneOrMore("<=" + multi_paren_abs_or_terms))
    .set_parse_action(_parse_leq_expression)  # noqa: WPS348
    .set_name("leq_expression")  # noqa: WPS348
)

# Produces an PolyhedralSyntaxExpression
geq_expression = (
    pp.Group(multi_paren_abs_or_terms + pp.OneOrMore(">=" + multi_paren_abs_or_terms))
    .set_parse_action(_parse_geq_expression)  # noqa: WPS348
    .set_name("geq_expression")  # noqa: WPS348
)

# Produces an PolyhedralSyntaxExpression
expression = (
    pp.Group(equality_expression | leq_expression | geq_expression)
    .set_parse_action(_parse_expression)  # noqa: WPS348
    .set_name("expression")  # noqa: WPS348
)
