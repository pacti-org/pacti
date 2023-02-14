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


RelativeTolerance: float = 1e-05
AbsoluteTolerance: float = 1e-08

def number2string(n: numeric) -> str:
    if isinstance(n, sympy.core.numbers.Float):
        f: sympy.core.numbers.Float = n
        return str(f.num)
    else:
        return str(n)

def areNumbersApproximativelyEqual(v1: numeric, v2: numeric) -> bool:
   if isinstance(v1, int) & isinstance(v2, int):
      return v1 == v2
   else:
      f1=float(v1)
      f2=float(v2)
      return np.isclose(f1, f2, rtol=RelativeTolerance, atol=AbsoluteTolerance, equal_nan=True)

def onePolyhedraTermToString(terms: list[PolyhedralTerm]) -> Optional[Tuple[str, list[PolyhedralTerm]]]:
   if not terms:
      return None
   
   tp = terms[0]

   ts = terms[1:]
   for tn in ts:
      if isOppositeOfPolyhedralTerm(tp, tn):
         # tp has the form: LHS
         # tn has the form: -(LHS)
         if areNumbersApproximativelyEqual(tp.constant, -tn.constant):
            # inverse of rule 4
            # rewrite as 2 terms given input match: LHS = RHS
            # pos: LHS <= RHS
            # neg: -(LHS) <= -(RHS)
            s = str(tp) + " = " + number2string(tp.constant)
            ts.remove(tn)
            return s, ts
         
         else:
            if areNumbersApproximativelyEqual(tp.constant, 0.0):
                # inverse of rule 3
                # rewrite as 2 terms given input match: | LHS | = 0
                # pos: LHS <= 0
                # neg: -(LHS) <= 0
                s = "|" + str(tp) + "| = 0"
                ts.remove(tn)
                return s, ts
            else:
                # inverse of rule 2
                # rewrite as 2 terms given input match: | LHS | <= RHS
                # pos: LHS <= RHS
                # neg: -(LHS) <= RHS
                s = "|" + str(tp) + "| <= " + number2string(tp.constant)
                ts.remove(tn)
                return s, ts
         
   s = str(tp) + " <= " + number2string(tp.constant)
   return s, ts


# Patterns for the syntax of constant numbers.

plusPattern = re.compile(r'^\s*\+\s*$')
minusPattern = re.compile(r'^\s*\-\s*$')
signedNumber = re.compile(r'^\s*(?P<sign>[+-])?\s*(?P<float>(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)\s*$')


# Patterns for the syntax of variables with numeric coefficients

variablePattern = re.compile(
    r'^'
    r'\s*(?P<coefficient>[+-]\s*((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)?)'
    r'\s*(?P<multiplication>\*)?'
    r'\s*(?P<variable>[a-zA-Z]\w*)'
    r'(?P<variables>(\s*[+-]\s*(((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?(\s*\*\s*)?)?)?\s*[a-zA-Z]\w*)*)'
    r'\s*$')


# Patterns for polyhedral term syntax

polyhedralTermPattern1 = re.compile(
    r'^'
    r'\s*(?P<coefficient>([+-]?(\s*(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)?)?)'
    r'\s*(?P<multiplication>\*)?'
    r'\s*(?P<variable>[a-zA-Z]\w*)'
    r'(?P<variables>(\s*[+-]\s*((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?\s*\*?)?\s*[a-zA-Z]\w*)*)'
    r'\s*<='
    r'\s*(?P<constant>[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)'
    r'$')

polyhedralTermPattern2 = re.compile(
    r'^'
    r'\s*\|'
    r'(?P<LHS>([+-]?(\s*(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)?)?\s*\*?\s*[a-zA-Z]\w*(\s*[+-]\s*((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?\s*\*?)?\s*[a-zA-Z]\w*)*)'
    r'\s*\|'
    r'\s*<='
    r'\s*(?P<RHS>[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)'
    r'$')

polyhedralTermPattern3 = re.compile(
    r'^'
    r'\s*\|'
    r'(?P<LHS>([+-]?(\s*(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)?)?\s*\*?\s*[a-zA-Z]\w*(\s*[+-]\s*((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?\s*\*?)?\s*[a-zA-Z]\w*)*)'
    r'\s*\|'
    r'\s*='
    r'\s*0'
    r'$')

polyhedralTermPattern4 = re.compile(
    r'^'
    r'(?P<LHS>([+-]?(\s*(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)?)?\s*\*?\s*[a-zA-Z]\w*(\s*[+-]\s*((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?\s*\*?)?\s*[a-zA-Z]\w*)*)'
    r'\s*='
    r'\s*(?P<RHS>[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)'
    r'$')

def isOppositeOfPolyhedralTerm(self, other: PolyhedralTerm) -> bool:
    for var, value in self.variables.items():
        if not other.contains_var(var):
            return False
        if not areNumbersApproximativelyEqual(-value, other.variables[var]):
            return False
    return True

def parseConstant(val: str) -> numeric:
    if "" == val:
        return 1.0
    elif plusPattern.match(val):
        return 1.0
    elif minusPattern.match(val):
        return -1.0
    else:
        m=signedNumber.match(val)
        if not m:
            raise ValueError(f"Constant syntax mismatch: {val}")
        
        s=m.group('sign')
        n=float(m.group('float'))

        if s == '-':
            return -n
        else:
            return n

def addVariable(terms: str, variables: dict[Var, numeric], v: str, c: str) -> dict[Var, numeric]:
    if variables.__contains__(v):
        raise(ValueError(f"Multiple coefficients involving the same variable: {v} in: {terms}"))

    n=parseConstant(c)
    variables.update({v:n})
    
def parseVariables(variables: dict[Var, numeric], terms: str) -> dict[Var, numeric]:
    t=variablePattern.match(terms)
    if not t:
        raise(ValueError(f"Polyhedral variable syntax mismatch: {terms}"))
    
    v=t.group('variable')
    c=t.group('coefficient')
    addVariable(terms, variables, v, c)

    rest=t.group('variables')
    if rest:
        parseVariables(variables, rest)
    else:
        variables

def pt1_from_match(m: re.Match[str]) -> PolyhedralTerm:
    variables: dict[Var, numeric] = {}

    v=m.group('variable')
    c=m.group('coefficient')
    addVariable(m.group(0), variables, v, c)

    rest=m.group('variables')
    if rest:
        parseVariables(variables, rest)

    constant=float(m.group('constant'))
    return PolyhedralTerm(variables, constant)


# rewrite as 2 terms given input match: | LHS | <= RHS
# pos: LHS <= RHS
# neg: -(LHS) <= RHS
# result is [pos,neg]
def pt2_from_match(m: re.Match[str]) -> list[PolyhedralTerm]:
    s1=f"{m.group('LHS')} <= {m.group('RHS')}"
    m1=polyhedralTermPattern1.match(s1)
    if not m1:
        raise ValueError(f"Invalid 'LHS <= RHS' syntax in: {s1}")
    
    pos: PolyhedralTerm = pt1_from_match(m1)
    neg: PolyhedralTerm = pos.copy()
    for key, value in neg.variables.items():
        neg.variables.update({key: -value})
    return [pos,neg]

# rewrite as 2 terms given input match: | LHS | = 0
# pos: LHS <= 0
# neg: -(LHS) <= 0
# result is [pos,neg]
def pt3_from_match(m: re.Match[str]) -> list[PolyhedralTerm]:
    s1=f"{m.group('LHS')} <= 0"
    m1=polyhedralTermPattern1.match(s1)
    if not m1:
        raise ValueError(f"Invalid 'LHS <= 0' syntax in: {s1}")
    
    pos: PolyhedralTerm = pt1_from_match(m1)
    neg: PolyhedralTerm = pos.copy()
    for key, value in neg.variables.items():
        neg.variables.update({key: -value})
    return [pos,neg]

# rewrite as 2 terms given input match: LHS = RHS
# pos: LHS <= RHS
# neg: -(LHS) <= -(RHS)
# result is [pos,neg]
def pt4_from_match(m: re.Match[str]) -> list[PolyhedralTerm]:
    s1=f"{m.group('LHS')} <= {m.group('RHS')}"
    m1=polyhedralTermPattern1.match(s1)
    if not m1:
        raise ValueError(f"Invalid 'LHS <= RHS' syntax in: {s1}")
    
    pos: PolyhedralTerm = pt1_from_match(m1)
    neg: PolyhedralTerm = pos.copy()
    for key, value in neg.variables.items():
        neg.variables.update({key: -value})
    neg.constant = - neg.constant
    return [pos,neg]

def pt_from_string(str_rep: str) -> list[PolyhedralTerm]:
    
    m1=polyhedralTermPattern1.match(str_rep)
    m2=polyhedralTermPattern2.match(str_rep)
    m3=polyhedralTermPattern3.match(str_rep)
    m4=polyhedralTermPattern4.match(str_rep)
    if m1:
        return [pt1_from_match(m1)]

    elif m2:
        return pt2_from_match(m2)
        
    elif m3:
        return pt3_from_match(m3)
        
    elif m4:
        return pt4_from_match(m4)
        
    else:
        raise ValueError(f"Polyhedral term syntax mismatch: {str_rep}")