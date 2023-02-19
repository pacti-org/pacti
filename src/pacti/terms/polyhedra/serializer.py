"""
Consists of loader functions that can read a JSON dictionary contract
or write a IOContract to a JSON file.
"""
import json
import re

from typing import Optional, Tuple, Union
import numpy as np
import sympy

from pacti.iocontract import IoContract
from pacti.iocontract.iocontract import Var
from pacti.terms.polyhedra.polyhedra import PolyhedralTerm

numeric = Union[int, float]

def write_contract(contract: Union[IoContract, list[IoContract]], filename: str = None) -> list[dict]:
    """
    Converts a pacti.IoContract to a dictionary. If a list of iocontracts is passed,
    then a list of dicts is returned.
    If a filename is provided, a JSON file is written, otherwise only dictionaries are returned.
    Arguments:
        contract: Contract input of type IoContract or list of IoContracts.
        filename: Name of file to write the output contract, defaults to None in which case,
            no file is written.
                                    
    Returns:
        contract_dict: A dictionary for the given IoContract.
    """
    if isinstance(contract, IoContract):
        contract = [contract]
    contract_list = []
    for c_i in contract:
        if not isinstance(c_i, IoContract):
            return ValueError("A IoContract is expected.")
        contract_dict = {}
        contract_dict["InputVars"] = [str(var) for var in c_i.inputvars]
        contract_dict["OutputVars"] = [str(var) for var in c_i.outputvars]
        contract_dict["assumptions"] = [
            {"constant":float(term.constant), \
             "coefficients": {str(k): float(v) for k, v in term.variables.items()}}
            for term in c_i.a.terms
        ]
        contract_dict["guarantees"] = [
            {"constant":float(term.constant), \
             "coefficients": {str(k): float(v) for k, v in term.variables.items()}}
            for term in c_i.g.terms
        ]
        contract_list.append(contract_dict)
    if filename:
        with open(filename, "w+", encoding='utf-8') as f_i:
            count = 0
            f_i.write("{\n")
            for c_dict in contract_list:
                data = json.dumps(c_dict)
                f_i.write('"contract' + str(count) + '"' + ":")
                f_i.write(data)
                if c_dict != contract_list[-1]:
                    f_i.write(",\n")
                count += 1
            f_i.write("\n}")
    return contract_list


float_closeness_relative_tolerance: float = 1e-05
float_closeness_absolute_tolerance: float = 1e-08

def number2string(n: numeric) -> str:
    if isinstance(n, sympy.core.numbers.Float):
        f: sympy.core.numbers.Float = n
        return str(f.num)
    else:
        return str(n)

def are_numbers_approximatively_equal(v1: numeric, v2: numeric) -> bool:
   if isinstance(v1, int) & isinstance(v2, int):
      return v1 == v2
   else:
      f1=float(v1)
      f2=float(v2)
      return np.isclose(f1, f2, rtol=float_closeness_relative_tolerance, atol=float_closeness_absolute_tolerance, equal_nan=True)

def internal_pt_to_string(terms: list[PolyhedralTerm]) -> Optional[Tuple[str, list[PolyhedralTerm]]]:
   if not terms:
      return None
   
   tp = terms[0]

   ts = terms[1:]
   for tn in ts:
      if are_polyhedral_terms_opposite(tp, tn):
         # tp has the form: LHS
         # tn has the form: -(LHS)
         if are_numbers_approximatively_equal(tp.constant, -tn.constant):
            # inverse of rule 4
            # rewrite as 2 terms given input match: LHS = RHS
            # pos: LHS <= RHS
            # neg: -(LHS) <= -(RHS)
            s = tp._lhs_str() + " = " + number2string(tp.constant)
            ts.remove(tn)
            return s, ts
         
         else:
            if are_numbers_approximatively_equal(tp.constant, 0.0) & are_numbers_approximatively_equal(tn.constant, 0.0):
                # inverse of rule 3
                # rewrite as 2 terms given input match: | LHS | = 0
                # pos: LHS <= 0
                # neg: -(LHS) <= 0
                s = "|" + tp._lhs_str() + "| = 0"
                ts.remove(tn)
                return s, ts
            elif are_numbers_approximatively_equal(tp.constant, tn.constant):
                # inverse of rule 2
                # rewrite as 2 terms given input match: | LHS | <= RHS
                # pos: LHS <= RHS
                # neg: -(LHS) <= RHS
                s = "|" + tp._lhs_str() + "| <= " + number2string(tp.constant)
                ts.remove(tn)
                return s, ts
         
   s = tp._lhs_str() + " <= " + number2string(tp.constant)
   return s, ts


# Patterns for the syntax of constant numbers.

internal_plus_pattern = re.compile(r'^\s*\+\s*$')
internal_minus_pattern = re.compile(r'^\s*\-\s*$')
internal_signed_number = re.compile(r'^\s*(?P<sign>[+-])?\s*(?P<float>(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)\s*$')


# Patterns for the syntax of variables with numeric coefficients

internal_variable_pattern = re.compile(
    r'^'
    r'\s*(?P<coefficient>[+-]\s*((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)?)'
    r'\s*(?P<multiplication>\*)?'
    r'\s*(?P<variable>[a-zA-Z]\w*)'
    r'(?P<variables>(\s*[+-]\s*(((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?(\s*\*\s*)?)?)?\s*[a-zA-Z]\w*)*)'
    r'\s*$')


# Patterns for polyhedral term syntax

internal_polyhedral_term_canonical_pattern = re.compile(
    r'^'
    r'\s*(?P<coefficient>([+-]?(\s*(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)?)?)'
    r'\s*(?P<multiplication>\*)?'
    r'\s*(?P<variable>[a-zA-Z]\w*)'
    r'(?P<variables>(\s*[+-]\s*((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?\s*\*?)?\s*[a-zA-Z]\w*)*)'
    r'\s*<='
    r'\s*(?P<constant>[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)'
    r'$')

internal_polyhedral_term_absolute_less_than_pattern = re.compile(
    r'^'
    r'\s*\|'
    r'(?P<LHS>([+-]?(\s*(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)?)?\s*\*?\s*[a-zA-Z]\w*(\s*[+-]\s*((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?\s*\*?)?\s*[a-zA-Z]\w*)*)'
    r'\s*\|'
    r'\s*<='
    r'\s*(?P<RHS>[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)'
    r'$')

internal_polyhedral_term_absolute_zero_pattern = re.compile(
    r'^'
    r'\s*\|'
    r'(?P<LHS>([+-]?(\s*(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)?)?\s*\*?\s*[a-zA-Z]\w*(\s*[+-]\s*((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?\s*\*?)?\s*[a-zA-Z]\w*)*)'
    r'\s*\|'
    r'\s*='
    r'\s*0'
    r'$')

internal_polyhedral_term_equality_pattern = re.compile(
    r'^'
    r'(?P<LHS>([+-]?(\s*(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)?)?\s*\*?\s*[a-zA-Z]\w*(\s*[+-]\s*((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?\s*\*?)?\s*[a-zA-Z]\w*)*)'
    r'\s*='
    r'\s*(?P<RHS>[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)'
    r'$')

# opposite terms means:
# - same set of variables
# - the variable coefficients of self are approximatively the negative of those of other.
def are_polyhedral_terms_opposite(self: PolyhedralTerm, other: PolyhedralTerm) -> bool:
    for var in other.variables.keys():
        if not self.contains_var(var):
            return False
        
    for var, value in self.variables.items():
        if not other.contains_var(var):
            return False
        if not are_numbers_approximatively_equal(-value, other.variables[var]):
            return False
    return True

def internal_parse_constant(val: str) -> numeric:
    if "" == val:
        return 1.0
    elif internal_plus_pattern.match(val):
        return 1.0
    elif internal_minus_pattern.match(val):
        return -1.0
    else:
        m=internal_signed_number.match(val)
        if not m:
            raise ValueError(f"Constant syntax mismatch: {val}")
        
        s=m.group('sign')
        n=float(m.group('float'))

        if s == '-':
            return -n
        else:
            return n

def internal_add_variable(terms: str, variables: dict[Var, numeric], v: str, c: str) -> dict[Var, numeric]:
    if variables.__contains__(v):
        raise(ValueError(f"Multiple coefficients involving the same variable: {v} in: {terms}"))

    n=internal_parse_constant(c)
    variables.update({v:n})
    
def internal_parse_variables(variables: dict[Var, numeric], terms: str) -> dict[Var, numeric]:
    t=internal_variable_pattern.match(terms)
    if not t:
        raise(ValueError(f"Polyhedral variable syntax mismatch: {terms}"))
    
    v=t.group('variable')
    c=t.group('coefficient')
    internal_add_variable(terms, variables, v, c)

    rest=t.group('variables')
    if rest:
        internal_parse_variables(variables, rest)
    else:
        variables

def internal_pt_from_canonical_match(m: re.Match[str]) -> PolyhedralTerm:
    variables: dict[Var, numeric] = {}

    v=m.group('variable')
    c=m.group('coefficient')
    internal_add_variable(m.group(0), variables, v, c)

    rest=m.group('variables')
    if rest:
        internal_parse_variables(variables, rest)

    constant=float(m.group('constant'))
    return PolyhedralTerm(variables, constant)


# rewrite as 2 terms given input match: | LHS | <= RHS
# pos: LHS <= RHS
# neg: -(LHS) <= RHS
# result is [pos,neg]
def internal_pt_from_absolute_less_than_match(m: re.Match[str]) -> list[PolyhedralTerm]:
    s1=f"{m.group('LHS')} <= {m.group('RHS')}"
    m1=internal_polyhedral_term_canonical_pattern.match(s1)
    if not m1:
        raise ValueError(f"Invalid 'LHS <= RHS' syntax in: {s1}")
    
    pos: PolyhedralTerm = internal_pt_from_canonical_match(m1)
    neg: PolyhedralTerm = pos.copy()
    for key, value in neg.variables.items():
        neg.variables.update({key: -value})
    return [pos,neg]

# rewrite as 2 terms given input match: | LHS | = 0
# pos: LHS <= 0
# neg: -(LHS) <= 0
# result is [pos,neg]
def internal_pt_from_absolute_zero_match(m: re.Match[str]) -> list[PolyhedralTerm]:
    s1=f"{m.group('LHS')} <= 0"
    m1=internal_polyhedral_term_canonical_pattern.match(s1)
    if not m1:
        raise ValueError(f"Invalid 'LHS <= 0' syntax in: {s1}")
    
    pos: PolyhedralTerm = internal_pt_from_canonical_match(m1)
    neg: PolyhedralTerm = pos.copy()
    for key, value in neg.variables.items():
        neg.variables.update({key: -value})
    return [pos,neg]

# rewrite as 2 terms given input match: LHS = RHS
# pos: LHS <= RHS
# neg: -(LHS) <= -(RHS)
# result is [pos,neg]
def internal_pt_from_equality_match(m: re.Match[str]) -> list[PolyhedralTerm]:
    s1=f"{m.group('LHS')} <= {m.group('RHS')}"
    m1=internal_polyhedral_term_canonical_pattern.match(s1)
    if not m1:
        raise ValueError(f"Invalid 'LHS <= RHS' syntax in: {s1}")
    
    pos: PolyhedralTerm = internal_pt_from_canonical_match(m1)
    neg: PolyhedralTerm = pos.copy()
    for key, value in neg.variables.items():
        neg.variables.update({key: -value})
    neg.constant = - neg.constant
    return [pos,neg]

def internal_pt_from_string(str_rep: str) -> list[PolyhedralTerm]:
    
    m1=internal_polyhedral_term_canonical_pattern.match(str_rep)
    m2=internal_polyhedral_term_absolute_less_than_pattern.match(str_rep)
    m3=internal_polyhedral_term_absolute_zero_pattern.match(str_rep)
    m4=internal_polyhedral_term_equality_pattern.match(str_rep)
    if m1:
        return [internal_pt_from_canonical_match(m1)]

    elif m2:
        return internal_pt_from_absolute_less_than_match(m2)
        
    elif m3:
        return internal_pt_from_absolute_zero_match(m3)
        
    elif m4:
        return internal_pt_from_equality_match(m4)
        
    else:
        raise ValueError(f"Polyhedral term syntax mismatch: {str_rep}")