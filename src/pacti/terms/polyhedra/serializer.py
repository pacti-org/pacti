"""Transformations between polyhedral structures and strings."""
from typing import Dict, List, Tuple, Union

import numpy as np
import sympy

import pyparsing as pp

from pacti.terms.polyhedra.polyhedra import PolyhedralTerm
from pacti.utils.errors import ContractFormatError
from pacti.terms.polyhedra.grammar import expression, AbsoluteTermList, Expression, Operator

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


def _eql_expression_to_polyhedral_terms(e: Expression) -> List[PolyhedralTerm]:
    """
    Convert equality expression

    Args:
        e: Expression

    Returns:
        The list of PolyhedralTerms resulting from expanding the following conversion from:
            lhs == rhs
        into:
            lhs - rhs <= 0
            -(lhs - rhs) <= 0
    """
    assert len(e.sides) == 2
    lhs: AbsoluteTermList = e.sides[0]
    rhs: AbsoluteTermList = e.sides[1]

    pts: List[PolyhedralTerm] = []

    if not lhs.is_constant():
        lhs_minus_rhs: AbsoluteTermList = lhs.add(rhs.negate())
        add_negated = len(lhs_minus_rhs.term_list.factors) > 0
        for tl in lhs_minus_rhs.expand():
            pts.append(tl.to_polyhedral_term())
            if add_negated:
                pts.append(tl.negate().to_polyhedral_term())

    if not rhs.is_constant():
        rhs_minus_lhs: AbsoluteTermList = rhs.add(lhs.negate())
        add_negated = len(rhs_minus_lhs.term_list.factors) > 0
        for tl in rhs_minus_lhs.expand():
            pts.append(tl.to_polyhedral_term())
            if add_negated:
                pts.append(tl.negate().to_polyhedral_term())

    assert len(pts) > 0

    return pts


def _leq_expression_to_polyhedral_terms(e: Expression) -> List[PolyhedralTerm]:
    """
    Convert less-than-or-equal expression

    Args:
        e: Expression

    Returns:
        The list of PolyhedralTerms resulting from expanding the following conversion from:
            atl[i] <= atl[i+1] for i in [0, len(e.sides)-2]
        into:
            atl[i] - atl[i+1] <= 0 for i in [0, len(e.sides)-2]
    """
    assert len(e.sides) >= 2

    pts: List[PolyhedralTerm] = []

    for a, b in zip(e.sides, e.sides[1:]):
        a_minus_b: AbsoluteTermList = a.add(b.negate())
        for tl in a_minus_b.expand():
            pts.append(tl.to_polyhedral_term())

    return pts


def _geq_expression_to_polyhedral_terms(e: Expression) -> List[PolyhedralTerm]:
    """
    Convert greater-than-or-equal expression

    Args:
        e: Expression

    Returns:
        The list of PolyhedralTerms resulting from expanding the following conversion from:
            atl[i] >= atl[i+1] for i in [0, len(e.sides)-2]
        into:
            -atl[i] + atl[i+1] <= 0 for i in [0, len(e.sides)-2]
    """
    assert len(e.sides) >= 2

    pts: List[PolyhedralTerm] = []

    for a, b in zip(e.sides, e.sides[1:]):
        minus_a_plus_b: AbsoluteTermList = a.negate().add(b)
        for tl in minus_a_plus_b.expand():
            pts.append(tl.to_polyhedral_term())

    return pts


def _expression_to_polyhedral_terms(e: Expression) -> List[PolyhedralTerm]:
    if e.operator == Operator.eql:
        return _eql_expression_to_polyhedral_terms(e)
    elif e.operator == Operator.leq:
        return _leq_expression_to_polyhedral_terms(e)
    return _geq_expression_to_polyhedral_terms(e)


def polyhedral_termlist_from_string(str_rep: str) -> List[PolyhedralTerm]:
    """
    Transform a linear expression into a polyhedral termlist.

    Args:
        str_rep: The linear expression passed as a string.

    Returns:
        A PolyhedralTermList representing the input expression.

    Raises:
        ValueError: constraint syntax invalid.
    """
    try:
        tokens: pp.ParseResults = expression.parse_string(str_rep, parse_all=True)
    except pp.ParseException as pe:
        raise ValueError(f"Polyhedral term syntax mismatch in: {str_rep}\n{pe.explain(depth=0)}")

    if len(tokens) == 1:
        e = tokens[0]
        if isinstance(e, Expression):
            return _expression_to_polyhedral_terms(e)

    raise ValueError(f"Polyhedral term syntax unrecognized in: {str_rep}")
