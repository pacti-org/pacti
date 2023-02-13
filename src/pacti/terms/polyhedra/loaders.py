"""
Consists of loader functions that can read a JSON dictionary contract
or write a IOContract to a JSON file.
"""
import json
import re
from sympy.parsing.sympy_parser import parse_expr

from functools import reduce
from pacti.iocontract import IoContract, Var
from pacti.iocontract.utils import getVarlist
from pacti.terms.polyhedra.polyhedra import areNumbersApproximativelyEqual, PolyhedralTerm, PolyhedralTermList
from pacti.utils.string_contract import StrContract

from typing import Any, Union

numeric = Union[int, float]

def read_polyhedralTermList(kind: str, l: Union[list[dict], list[str]]) -> PolyhedralTermList:
   if all(isinstance(x, dict) for x in l):
      return PolyhedralTermList(list(PolyhedralTerm(x["coefficients"], float(x["constant"])) for x in l))
   elif all(isinstance(x, str) for x in l):
      return PolyhedralTermList(l)
   else:
      raise ValueError(f"{kind} must be either a list of dicts or strings.")
   
def read_contract(contract: Union[dict, list[dict]]) -> list[IoContract]:
    """
    Converts a contract written as JSON dictionary to pacti.iocontract type.
    If a list of JSON contracts are passed, a corresponding list of iocontracts is returned.

    Args:
        contract: A JSON dict describing the contract in the Pacti syntax. 
            May be a list of such dictionaries.

    Returns:
        list_iocontracts: A list of input-output Pacti contract objects
    """
    if not isinstance(contract, list):
        contract = [contract]
    list_iocontracts = []
    for c_i in contract:
        if not isinstance(c_i, dict):
            raise ValueError("A dict type contract is expected.")
        a=read_polyhedralTermList("Assumptions", c_i["assumptions"])
        g=read_polyhedralTermList("Guarantees", c_i["guarantees"])
        iocont = IoContract(
            input_vars=getVarlist(c_i["InputVars"]),
            output_vars=getVarlist(c_i["OutputVars"]),
            assumptions=a,
            guarantees=g,
        )
        list_iocontracts.append(iocont)
    if len(list_iocontracts) == 1:
        return list_iocontracts[0]
    else:
        return list_iocontracts


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
    if len(contract_list) == 1:
        return contract_list[0]
    else:
        return contract_list

def string_to_polyhedra_contract(contract: StrContract) -> IoContract:
    """
    Converts a StrContract to a pacti.iocontract type.
    Args:
        contract: a StrContract object
    Returns:
        io_contract: An input-output Pacti contract object
    """
    io_contract = IoContract(
        assumptions=PolyhedralTermList(contract.assumptions),
        guarantees=PolyhedralTermList(contract.guarantees),
        input_vars=[Var(x) for x in contract.inputs],
        output_vars=[Var(x) for x in contract.outputs]
    )
    return io_contract
