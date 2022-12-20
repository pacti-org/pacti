"""
Consists of loader functions that can read a JSON dictionary contract
or write a IOContract to a JSON file.
"""
import json
from gear.iocontract import IoContract
from gear.iocontract.utils import getVarlist
from gear.terms.polyhedra import PolyhedralTerm, PolyhedralTermList


def read_contract(contract):
    """
    Converts a contract written as JSON dictionary to gear.iocontract type.
    If a list of JSON contracts are passed, a corresponding list of iocontracts is returned.
    Arguments:
        * contract (dict, list): A JSON dict describing the contract in the Gear syntax.
                                 May be a list of such dictionaries.
    Returns:
        * iocontract (gear.IoContract): An input-output Gear contract object
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
            inputVars=getVarlist(c_i["InputVars"]),
            outputVars=getVarlist(c_i["OutputVars"]),
            assumptions=PolyhedralTermList(list(reqs[0])),
            guarantees=PolyhedralTermList(list(reqs[1])),
        )
        list_iocontracts.append(iocont)
    if len(list_iocontracts) == 1:
        return list_iocontracts[0]
    else:
        return list_iocontracts


def write_contract(contract, filename: str=None):
    """
    Converts a gear.IoContract to a dictionary. If a list of iocontracts is passed,
    then a list of dicts is returned.
    If a filename is provided, a JSON file is written, otherwise only dictionaries are returned.
    Arguments:
        * contract (gear.IoContract, list): Contract input of type IoContract
                                                       or list of IoContracts.
        * filename (str, optional): Name of file to write the output contract,
                                    defaults to None in which case,
                                    no file is written.
    Returns:
        * contract_dict (dict): A dictionary for the given IoContract
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
