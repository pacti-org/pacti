"""Transformations between polyhedral structures and strings."""
from typing import Dict, List, Tuple, Union

import numpy as np
import pyparsing as pp
import sympy

from pacti.terms.polyhedra.polyhedra import PolyhedralTerm
from pacti.terms.polyhedra.syntax.data import (
    PolyhedralSyntaxAbsoluteTerm,
    PolyhedralSyntaxAbsoluteTermList,
    PolyhedralSyntaxEqlExpression,
    PolyhedralSyntaxExpression,
    PolyhedralSyntaxIneqExpression,
    PolyhedralSyntaxOperator,
    PolyhedralSyntaxTermList,
)
from pacti.terms.polyhedra.syntax.grammar import expression
from pacti.utils.errors import ContractFormatError, PolyhedralSyntaxConvexException, PolyhedralSyntaxException

numeric = Union[int, float]


def validate_contract_dict(  # noqa: WPS231 too much cognitive complexity
    contract: Dict, contract_name: str, machine_representation: bool
) -> None:
    """
    Tell whether a contract dictionary can be read as a polyhedral contract.

    Args:
        contract: a dictionary to be analyzed.
        contract_name: a name for the contract (used for error reporting).
        machine_representation: the provided dictionary is machine-optimized.

    Raises:
        ContractFormatError: the provided contract is not well-formed.
    """
    if not isinstance(contract, dict):
        print(contract)
        raise ContractFormatError("Each contract should be a dictionary")
    keywords = ["assumptions", "guarantees", "input_vars", "output_vars"]
    str_list_kw = ["input_vars", "output_vars"]
    if not machine_representation:
        str_list_kw += ["assumptions", "guarantees"]
    for kw in keywords:
        if kw not in contract:
            raise ContractFormatError(f'Keyword "{kw}" not found in contract {contract_name}')
        value = contract[kw]
        if not isinstance(value, list):
            raise ContractFormatError(f'The "{kw}" in contract {contract_name} should be a list')
        if kw in str_list_kw:
            for str_item in value:
                if not isinstance(str_item, str):
                    raise ContractFormatError(f"The {kw} in contract {contract_name} should be defined as strings")
        elif machine_representation:
            for index, clause in enumerate(value):
                _check_clause(clause, f"{contract_name}:{kw}{index}")


def _check_clause(clause: dict, clause_id: str) -> None:
    keywords = ["constant", "coefficients"]
    for kw in keywords:
        if kw not in clause:
            ContractFormatError(f'Keyword "{kw}" not found in {clause_id}')
        value = clause[kw]
        if kw == "coefficients":
            if not isinstance(value, dict):
                raise ContractFormatError(f'The "{kw}" in {clause_id} should be a dictionary')


float_closeness_relative_tolerance: float = 1e-5
float_closeness_absolute_tolerance: float = 1e-8


def _number_to_string(n: numeric) -> str:
    if isinstance(n, sympy.core.numbers.Float):
        f: sympy.core.numbers.Float = n
        return f"{f.num:.4g}"
    elif isinstance(n, float):
        return f"{n:.4g}"
    return str(n)


def _are_numbers_approximatively_equal(v1: numeric, v2: numeric) -> bool:
    if isinstance(v1, int) & isinstance(v2, int):
        return v1 == v2
    f1 = float(v1)
    f2 = float(v2)
    return bool(
        np.isclose(
            f1, f2, rtol=float_closeness_relative_tolerance, atol=float_closeness_absolute_tolerance, equal_nan=True
        )
    )


def _lhs_str(term: PolyhedralTerm) -> str:  # noqa: WPS231
    varlist = list(term.variables.items())
    varlist.sort(key=lambda x: str(x[0]))
    # res = " + ".join([str(coeff) + "*" + var.name for var, coeff in varlist])
    # res += " <= " + str(self.constant)
    res = ""
    first = True
    for var, coeff in varlist:  # noqa: VNE002
        if _are_numbers_approximatively_equal(coeff, 1.0):
            if first:
                res += var.name
            else:
                res += " + " + var.name
        elif _are_numbers_approximatively_equal(coeff, -1.0):
            if first:
                res += "-" + var.name
            else:
                res += " - " + var.name
        elif not _are_numbers_approximatively_equal(coeff, float(0)):
            if coeff > 0:
                if first:
                    res += _number_to_string(coeff) + " " + var.name
                else:
                    res += " + " + _number_to_string(coeff) + " " + var.name
            else:
                if first:
                    res += _number_to_string(coeff) + " " + var.name
                else:
                    res += " - " + _number_to_string(-coeff) + " " + var.name
        first = False
    # res += " <= " + _number_to_string(self.constant)
    return res


# opposite terms means:
# - same set of variables
# - the variable coefficients of self are approximatively the negative of those of other.
def _are_polyhedral_terms_opposite(self: PolyhedralTerm, other: PolyhedralTerm) -> bool:
    for var in other.variables.keys():
        if not self.contains_var(var):
            return False

    for var, value in self.variables.items():
        if not other.contains_var(var):
            return False
        if not _are_numbers_approximatively_equal(-value, other.variables[var]):
            return False
    return True


def polyhedral_term_list_to_strings(  # noqa: WPS231 too much cognitive complexity
    terms: List[PolyhedralTerm],
) -> Tuple[str, List[PolyhedralTerm]]:
    """
    Convert a list of polyhedral terms into a list of strings, one term at a time.

    Args:
        terms: the list of terms.

    Returns:
        String representation of the first constraint and list of items not yet serialized.
    """
    if not terms:
        return "", []

    tp = terms[0]

    ts = terms[1:]
    for tn in ts:
        if _are_polyhedral_terms_opposite(tp, tn):
            # tp has the form: LHS
            # tn has the form: -(LHS)
            if _are_numbers_approximatively_equal(tp.constant, -tn.constant):
                # inverse of rule 4
                # rewrite as 2 terms given input match: LHS = RHS
                # pos: LHS <= RHS
                # neg: -(LHS) <= -(RHS)
                s = _lhs_str(tp) + " = " + _number_to_string(tp.constant)
                ts.remove(tn)
                return s, ts

            else:
                condition = _are_numbers_approximatively_equal(
                    tp.constant, float(0)
                ) and _are_numbers_approximatively_equal(tn.constant, float(0))
                if condition:
                    # inverse of rule 3
                    # rewrite as 2 terms given input match: | LHS | = 0
                    # pos: LHS <= 0
                    # neg: -(LHS) <= 0
                    s = "|" + _lhs_str(tp) + "| = 0"
                    ts.remove(tn)
                    return s, ts
                elif _are_numbers_approximatively_equal(tp.constant, tn.constant):
                    # inverse of rule 2
                    # rewrite as 2 terms given input match: | LHS | <= RHS
                    # pos: LHS <= RHS
                    # neg: -(LHS) <= RHS
                    s = "|" + _lhs_str(tp) + "| <= " + _number_to_string(tp.constant)
                    ts.remove(tn)
                    return s, ts

    s = _lhs_str(tp) + " <= " + _number_to_string(tp.constant)
    return s, ts


def _eql_expression_to_polyhedral_terms(e: PolyhedralSyntaxEqlExpression) -> List[PolyhedralTerm]:
    """
    Convert equality expression.

    Args:
        e: Expression

    Returns:
        The list of PolyhedralTerms resulting from expanding the following conversion from:
            lhs == rhs
        into:
            lhs - rhs <= 0
            -(lhs - rhs) <= 0
    """
    pts: List[PolyhedralTerm] = []

    lhs_minus_rhs: PolyhedralSyntaxTermList = e.lhs.add(e.rhs.negate())
    pts.append(lhs_minus_rhs.to_polyhedral_term())

    rhs_minus_lhs: PolyhedralSyntaxTermList = e.rhs.add(e.lhs.negate())
    pts.append(rhs_minus_lhs.to_polyhedral_term())

    return pts


def _check_absolute_terms(str_rep: str, absolute_term_list: List[PolyhedralSyntaxAbsoluteTerm]) -> None:
    negative_absolute_terms: List[str] = []
    for at in absolute_term_list:
        if not at.is_positive():
            negative_absolute_terms.append(str(at))
    if len(negative_absolute_terms) > 0:
        raise PolyhedralSyntaxConvexException(str_rep, negative_absolute_terms)


def _leq_expression_to_polyhedral_terms(str_rep: str, e: PolyhedralSyntaxIneqExpression) -> List[PolyhedralTerm]:
    """Convert less-than-or-equal expression

    Args:
        str_rep:
            string representation of the expression
        e:
            Expression

    Returns:
        The list of PolyhedralTerms resulting from expanding the following conversion from:
            atl[i] <= atl[i+1] for i in [0, len(e.sides)-2]
        into:
            atl[i] - atl[i+1] <= 0 for i in [0, len(e.sides)-2]
    """
    assert len(e.sides) >= 2

    pts: List[PolyhedralTerm] = []

    # e represents the following: s1 <= s2 <= .... <= sn
    # In the loop below, we iterate over si, si+1 as follows:
    # a=s1, b=s2
    # a=s2, b=s3
    # ...
    # At each iteration, we have: 'a <= b'; which we convert as 'a - (b) <= 0'
    for a, b in zip(e.sides, e.sides[1:]):
        a_minus_b: PolyhedralSyntaxAbsoluteTermList = a.add(b.negate())
        _check_absolute_terms(str_rep, a_minus_b.absolute_term_list)
        for tl in a_minus_b.expand():
            pts.append(tl.to_polyhedral_term())

    return pts


def _geq_expression_to_polyhedral_terms(str_rep: str, e: PolyhedralSyntaxIneqExpression) -> List[PolyhedralTerm]:
    """Convert greater-than-or-equal expression

    Args:
        str_rep:
            string representation of the expression
        e:
            Expression

    Returns:
        The list of PolyhedralTerms resulting from expanding the following conversion from:
            atl[i] >= atl[i+1] for i in [0, len(e.sides)-2]
        into:
            -atl[i] + atl[i+1] <= 0 for i in [0, len(e.sides)-2]
    """
    assert len(e.sides) >= 2

    pts: List[PolyhedralTerm] = []

    # here, we have 'a >= b'; which we convert as '-(a) + b <= 0'
    for a, b in zip(e.sides, e.sides[1:]):
        minus_a_plus_b: PolyhedralSyntaxAbsoluteTermList = a.negate().add(b)
        _check_absolute_terms(str_rep, minus_a_plus_b.absolute_term_list)
        for tl in minus_a_plus_b.expand():
            pts.append(tl.to_polyhedral_term())

    return pts


def _expression_to_polyhedral_terms(str_rep: str, e: PolyhedralSyntaxExpression) -> List[PolyhedralTerm]:
    if isinstance(e, PolyhedralSyntaxEqlExpression):
        return _eql_expression_to_polyhedral_terms(e)
    if isinstance(e, PolyhedralSyntaxIneqExpression):
        if e.operator == PolyhedralSyntaxOperator.leq:
            return _leq_expression_to_polyhedral_terms(str_rep, e)
        return _geq_expression_to_polyhedral_terms(str_rep, e)

    raise AssertionError(f"Unexpected syntax type for the parsing of '{str_rep}': {type(e)}")


def polyhedral_termlist_from_string(str_rep: str) -> List[PolyhedralTerm]:
    """
    Transform a linear expression into a polyhedral termlist.

    Args:
        str_rep: The linear expression passed as a string.

    Returns:
        A PolyhedralTermList representing the input expression.

    Raises:
        PolyhedralSyntaxException: constraint syntax error w.r.t the polyhedral term grammar.
        ValueError: Number of tokens invalid.
    """
    try:
        tokens: pp.ParseResults = expression.parse_string(str_rep, parse_all=True)
    except pp.ParseBaseException as pe:
        raise PolyhedralSyntaxException(pe, str_rep)

    if len(tokens) == 1:
        e = tokens[0]
        if isinstance(e, PolyhedralSyntaxExpression):
            return _expression_to_polyhedral_terms(str_rep, e)

    raise ValueError(f"Polyhedral term syntax unrecognized in: {str_rep}")
