import json

import gear.iocontract as iocontract
import gear.polyhedralterm as polyhedralterm
from gear.gear import getVarlist


def readContract(contract):
    """
    Converts a contract written as JSON dictionary to gear.iocontract type.
    If a list of JSON contracts are passed, a corresponding list of iocontracts is returned.
    Arguments:
        * contract (dict, list): A JSON dict describing the contract in the Gear syntax.
                                 May be a list of such dictionaries.
    Returns:
        * iocontract (gear.iocontract.IoContract): An input-output Gear contract object
    """
    if type(contract) is not list:
        contract = [contract]
    list_iocontracts = []
    for c in contract:
        if type(c) is not dict:
            raise ValueError("A dict type contract is expected.")
        reqs = []
        for key in ["assumptions", "guarantees"]:
            reqs.append([polyhedralterm.PolyhedralTerm(term["coefficients"], term["constant"]) for term in c[key]])
        iocont = iocontract.IoContract(
            inputVars=getVarlist(c["InputVars"]),
            outputVars=getVarlist(c["OutputVars"]),
            assumptions=polyhedralterm.PolyhedralTermList(list(reqs[0])),
            guarantees=polyhedralterm.PolyhedralTermList(list(reqs[1])),
        )
        list_iocontracts.append(iocont)
    if len(list_iocontracts) == 1:
        return list_iocontracts[0]
    else:
        return list_iocontracts


def writeContract(contract, filename: str=None):
    """
    Converts a gear.iocontract.IoContract to a dictionary. If a list of iocontracts is passed,
    then a list of dicts is returned.
    If a filename is provided, a JSON file is written, otherwise only dictionaries are returned.
    Arguments:
        * contract (gear.iocontract.IoContract, list): Contract input of type iocontract.IoContract
                                                       or list of IoContracts.
        * filename (str, optional): Name of file to write the output contract, defaults to None in which case,
                                    no file is written.
    Returns:
        * contract_dict (dict): A dictionary for the given IoContract
    """
    if type(contract) is iocontract.IoContract:
        contract = [contract]
    contract_list = []
    for c in contract:
        if not isinstance(c, iocontract.IoContract):
            return ValueError("A IoContract is expected.")
        contract_dict = {}
        contract_dict["InputVars"] = [str(var) for var in c.inputvars]
        contract_dict["OutputVars"] = [str(var) for var in c.outputvars]
        contract_dict["assumptions"] = [
            {"constant":term.constant, "coefficients": {str(k): v for k, v in term.variables.items()}}
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
