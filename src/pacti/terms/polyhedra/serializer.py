"""Consists of loader functions that can read a JSON dictionary contract or write a IOContract to a JSON file."""
import re
from typing import Tuple, Union

import numpy as np
import sympy
from typing_extensions import TypedDict

from pacti.iocontract import Var
from pacti.terms.polyhedra.polyhedra import PolyhedralTerm
from pacti.utils.errors import ContractFormatError

numeric = Union[int, float]
ser_pt = dict[str, Union[float, dict[str, float]]]
ser_contract = TypedDict(
    "ser_contract",
    {"input_vars": list[str], "output_vars": list[str], "assumptions": list[ser_pt], "guarantees": list[ser_pt]},
)


def validate_contract_dict(  # noqa: WPS231 too much cognitive complexity
    contract, contract_name, machine_representation: bool
):
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


def _check_clause(clause, clause_id):
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
        return str(f.num)
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


def _lhs_str(term) -> str:  # noqa: WPS231
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


def polyhedral_term_list_to_strings(  # noqa: WPS231 too much cognitive complexity
    terms: list[PolyhedralTerm],
) -> Tuple[str, list[PolyhedralTerm]]:
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


# Patterns for the syntax of constant numbers.

internal_plus_pattern = re.compile(r"^\s*\+\s*$")
internal_minus_pattern = re.compile(r"^\s*\-\s*$")
internal_signed_number = re.compile(r"^\s*(?P<sign>[+-])?\s*(?P<float>(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)\s*$")


# Patterns for the syntax of variables with numeric coefficients

internal_variable_pattern = re.compile(
    "^"
    r"\s*(?P<coefficient>[+-]\s*((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)?)"
    r"\s*(?P<multiplication>\*)?"
    r"\s*(?P<variable>[a-zA-Z]\w*)"
    r"(?P<variables>(\s*[+-]\s*(((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?(\s*\*\s*)?)?)?\s*[a-zA-Z]\w*)*)"
    r"\s*$"
)


# Patterns for polyhedral term syntax

internal_polyhedral_term_canonical_pattern = re.compile(
    "^"
    r"\s*(?P<coefficient>([+-]?(\s*(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)?)?)"
    r"\s*(?P<multiplication>\*)?"
    r"\s*(?P<variable>[a-zA-Z]\w*)"
    r"(?P<variables>(\s*[+-]\s*((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?\s*\*?)?\s*[a-zA-Z]\w*)*)"
    r"\s*<="
    r"\s*(?P<constant>[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)"
    "$"
)

internal_polyhedral_term_absolute_less_than_pattern = re.compile(  # noqa: WPS118 Found too long name
    "^"
    r"\s*\|"
    r"(?P<LHS>([+-]?(\s*(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)?)?\s*\*?\s*"
    r"[a-zA-Z]\w*(\s*[+-]\s*((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?\s*\*?)?\s*[a-zA-Z]\w*)*)"
    r"\s*\|"
    r"\s*<="
    r"\s*(?P<RHS>[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)"
    "$"
)

internal_polyhedral_term_absolute_zero_pattern = re.compile(  # noqa: WPS118 Found too long name
    "^"
    r"\s*\|"
    r"(?P<LHS>([+-]?(\s*(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)?)?\s*\*?\s*"
    r"[a-zA-Z]\w*(\s*[+-]\s*((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?\s*\*?)?\s*[a-zA-Z]\w*)*)"
    r"\s*\|"
    r"\s*="
    r"\s*0"
    "$"
)

internal_polyhedral_term_equality_pattern = re.compile(
    "^"
    r"(?P<LHS>([+-]?(\s*(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)?)?\s*\*?\s*"
    r"[a-zA-Z]\w*(\s*[+-]\s*((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?\s*\*?)?\s*[a-zA-Z]\w*)*)"
    r"\s*="
    r"\s*(?P<RHS>[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)"
    "$"
)


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


def _internal_parse_constant(val: str) -> numeric:
    if val == "":
        return 1.0
    elif internal_plus_pattern.match(val):
        return 1.0
    elif internal_minus_pattern.match(val):
        return -1.0
    m = internal_signed_number.match(val)
    if not m:
        raise ValueError(f"Constant syntax mismatch: {val}")

    s = m.group("sign")
    n = float(m.group("float"))

    if s == "-":
        return -n
    return n


def _internal_add_variable(terms: str, variables: dict[str, numeric], v: str, c: str) -> None:
    if v in variables:
        raise (ValueError(f"Multiple coefficients involving the same variable: {v} in: {terms}"))

    n = _internal_parse_constant(c)
    variables.update({v: n})


def _internal_parse_variables(variables: dict[str, numeric], terms: str) -> None:
    t = internal_variable_pattern.match(terms)
    if not t:
        raise (ValueError(f"Polyhedral variable syntax mismatch: {terms}"))

    v = t.group("variable")
    c = t.group("coefficient")
    _internal_add_variable(terms, variables, v, c)

    rest = t.group("variables")
    if rest:
        _internal_parse_variables(variables, rest)
    else:
        variables


def _internal_pt_from_canonical_match(m: re.Match[str]) -> PolyhedralTerm:
    variables: dict[str, numeric] = {}

    v = m.group("variable")
    c = m.group("coefficient")
    _internal_add_variable(m.group(0), variables, v, c)

    rest = m.group("variables")
    if rest:
        _internal_parse_variables(variables, rest)

    constant = float(m.group("constant"))
    return PolyhedralTerm({Var(k): v for k, v in variables.items()}, constant)


# rewrite as 2 terms given input match: | LHS | <= RHS
# pos: LHS <= RHS
# neg: -(LHS) <= RHS
# result is [pos,neg]
def _internal_pt_from_absolute_less_than_match(m: re.Match[str]) -> list[PolyhedralTerm]:
    s1 = f"{m.group('LHS')} <= {m.group('RHS')}"
    m1 = internal_polyhedral_term_canonical_pattern.match(s1)
    if not m1:
        raise ValueError(f"Invalid 'LHS <= RHS' syntax in: {s1}")

    pos: PolyhedralTerm = _internal_pt_from_canonical_match(m1)
    neg: PolyhedralTerm = pos.copy()
    for key, value in neg.variables.items():
        neg.variables.update({key: -value})
    return [pos, neg]


# rewrite as 2 terms given input match: | LHS | = 0
# pos: LHS <= 0
# neg: -(LHS) <= 0
# result is [pos,neg]
def _internal_pt_from_absolute_zero_match(m: re.Match[str]) -> list[PolyhedralTerm]:
    s1 = f"{m.group('LHS')} <= 0"
    m1 = internal_polyhedral_term_canonical_pattern.match(s1)
    if not m1:
        raise ValueError(f"Invalid 'LHS <= 0' syntax in: {s1}")

    pos: PolyhedralTerm = _internal_pt_from_canonical_match(m1)
    neg: PolyhedralTerm = pos.copy()
    for key, value in neg.variables.items():
        neg.variables.update({key: -value})
    return [pos, neg]


# rewrite as 2 terms given input match: LHS = RHS
# pos: LHS <= RHS
# neg: -(LHS) <= -(RHS)
# result is [pos,neg]
def _internal_pt_from_equality_match(m: re.Match[str]) -> list[PolyhedralTerm]:
    s1 = f"{m.group('LHS')} <= {m.group('RHS')}"
    m1 = internal_polyhedral_term_canonical_pattern.match(s1)
    if not m1:
        raise ValueError(f"Invalid 'LHS <= RHS' syntax in: {s1}")

    pos: PolyhedralTerm = _internal_pt_from_canonical_match(m1)
    neg: PolyhedralTerm = pos.copy()
    for key, value in neg.variables.items():
        neg.variables.update({key: -value})
    neg.constant = -neg.constant
    return [pos, neg]


def polyhedral_termlist_from_string(str_rep: str) -> list[PolyhedralTerm]:
    """
    Transform a linear expression into a polyhedral termlist.

    Args:
        str_rep: The linear expression passed as a string.

    Returns:
        A PolyhedralTermList representing the input expression.

    Raises:
        ValueError: constraint syntax invalid.
    """
    m1 = internal_polyhedral_term_canonical_pattern.match(str_rep)
    m2 = internal_polyhedral_term_absolute_less_than_pattern.match(str_rep)
    m3 = internal_polyhedral_term_absolute_zero_pattern.match(str_rep)
    m4 = internal_polyhedral_term_equality_pattern.match(str_rep)
    if m1:
        return [_internal_pt_from_canonical_match(m1)]

    elif m2:
        return _internal_pt_from_absolute_less_than_match(m2)

    elif m3:
        return _internal_pt_from_absolute_zero_match(m3)

    elif m4:
        return _internal_pt_from_equality_match(m4)

    raise ValueError(f"Polyhedral term syntax mismatch: {str_rep}")
