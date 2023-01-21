"""
Consists of loader functions that can read a JSON dictionary contract
or write a IOContract to a JSON file.
"""
import json

import sympy
from sympy.parsing.sympy_parser import parse_expr

from pacti.iocontract import IoContract, Var
from pacti.iocontract.utils import getVarlist
from pacti.terms.polyhedra.polyhedra import PolyhedralTerm, PolyhedralTermList
from pacti.utils.string_contract import StrContract


def read_contract(contract: dict | list[dict]) -> list[IoContract]:
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
        reqs = []
        for key in ["assumptions", "guarantees"]:
            reqs.append([PolyhedralTerm(term["coefficients"], \
                        float(term["constant"])) for term in c_i[key]])
        iocont = IoContract(
            input_vars=getVarlist(c_i["InputVars"]),
            output_vars=getVarlist(c_i["OutputVars"]),
            assumptions=PolyhedralTermList(list(reqs[0])),
            guarantees=PolyhedralTermList(list(reqs[1])),
        )
        list_iocontracts.append(iocont)
    if len(list_iocontracts) == 1:
        return list_iocontracts[0]
    else:
        return list_iocontracts


def write_contract(contract: IoContract | list[IoContract], filename: str = None) -> list[dict]:
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


def pt_from_string(str_rep: str) -> PolyhedralTerm:
    # print(str_rep)
    expr = parse_expr(str_rep)
    # assert isinstance(expr, sympy.core.relational.LessThan)
    # print(str_rep)
    # print(expr)
    constant = expr.args[1]
    # print(type(constant))
    variables = {}
    for k, v in expr.args[0].as_coefficients_dict().items():
        if k == 1:
            pass
        elif isinstance(k, sympy.core.symbol.Symbol):
            variables[str(k)] = v
        elif isinstance(k, sympy.core.mul.Mul):
            if isinstance(k.args[1], k, sympy.core.symbol.Symbol):
                print(k.args[0])
                variables[str(k.args[1])] = k.args[0]
            elif isinstance(k.args[0], k, sympy.core.symbol.Symbol):
                print(k.args[1])
                variables[str(k.args[0])] = k.args[1]
        else:
            raise ValueError
    return PolyhedralTerm(variables, constant)


def string_to_polyhedra_contract(contract: StrContract) -> IoContract:
    """
    Converts a StrContract to a pacti.iocontract type.
    Args:
        contract: a StrContract object
    Returns:
        io_contract: An input-output Pacti contract object
    """
    assumptions: list[PolyhedralTerm] = list(map(lambda x: pt_from_string(x), contract.assumptions))
    guarantees: list[PolyhedralTerm] = list(map(lambda x: pt_from_string(x), contract.guarantees))
    inputs: list[Var] = [Var(x) for x in contract.inputs]
    outputs: list[Var] = [Var(x) for x in contract.outputs]

    io_contract = IoContract(
        assumptions=PolyhedralTermList(assumptions),
        guarantees=PolyhedralTermList(guarantees),
        input_vars=inputs,
        output_vars=outputs,
    )
    return io_contract
