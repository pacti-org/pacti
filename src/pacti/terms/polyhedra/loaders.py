import json

import sympy
from sympy.parsing.sympy_parser import parse_expr

from pacti.iocontract import IoContract, Var
from pacti.iocontract.utils import getVarlist
from pacti.terms.polyhedra.polyhedra import PolyhedralTerm, PolyhedralTermList
from pacti.utils.string_contract import StrContract


def readContract(contract: dict | list[dict]) -> list[IoContract]:
    """
    Converts a contract written as JSON dictionary to pacti.iocontract type.
    If a list of JSON contracts are passed, a corresponding list of iocontracts is returned.

    Args:
        contract: A JSON dict describing the contract in the Pacti syntax. 
            May be a list of such dictionaries.

    Returns:
        list_iocontracts: A list of input-output Pacti contract objects
    """
    if type(contract) is not list:
        contract = [contract]
    list_iocontracts = []
    for c in contract:
        if type(c) is not dict:
            raise ValueError("A dict type contract is expected.")
        reqs = []
        for key in ["assumptions", "guarantees"]:
            reqs.append([PolyhedralTerm(term["coefficients"], term["constant"]) for term in c[key]])
        iocont = IoContract(
            input_vars=getVarlist(c["InputVars"]),
            output_vars=getVarlist(c["OutputVars"]),
            assumptions=PolyhedralTermList(list(reqs[0])),
            guarantees=PolyhedralTermList(list(reqs[1])),
        )
        list_iocontracts.append(iocont)
    if len(list_iocontracts) == 1:
        return list_iocontracts[0]
    else:
        return list_iocontracts


def writeContract(contract: IoContract | list[IoContract], filename: str = None) -> list[dict]:
    """
    Converts a pacti.IoContract to a dictionary. If a list of iocontracts is passed,
    then a list of dicts is returned.
    If a filename is provided, a JSON file is written, otherwise only dictionaries are returned.
    Args:
        contract: Contract input of type IoContract or list of IoContracts.
        filename: Name of file to write the output contract, defaults to None in which case, no file is written.
    Returns:
        contract_dict: A dictionary for the given IoContract.
    """
    if type(contract) is IoContract:
        contract = [contract]
    contract_list = []
    for c in contract:
        if not isinstance(c, IoContract):
            return ValueError("A IoContract is expected.")
        contract_dict = {}
        contract_dict["InputVars"] = [str(var) for var in c.inputvars]
        contract_dict["OutputVars"] = [str(var) for var in c.outputvars]
        contract_dict["assumptions"] = [
            {"constant": term.constant, "coefficients": {str(k): v for k, v in term.variables.items()}}
            for term in c.a.terms
        ]
        contract_dict["guarantees"] = [
            {"constant": term.constant, "coefficients": {str(k): v for k, v in term.variables.items()}}
            for term in c.g.terms
        ]
        contract_list.append(contract_dict)
    if filename:
        with open(filename, "w+") as f:
            count = 0
            for c_dict in contract_list:
                f.write('"contract' + str(count) + '"' + "=")
                json.dump(c_dict, f)
                f.write("\n")
                count += 1
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
