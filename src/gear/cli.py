#!python

import json
import logging
import os

import click

from gear.iocontract import IoContract
from gear.iocontract.utils import getVarlist
from gear.terms.polyhedra import PolyhedralTerm, PolyhedralTermList


class FileDataFormatException(Exception):
    pass
class ContractFormatException(FileDataFormatException):
    pass 

def check_contract(contract, contract_name):
    if not isinstance(contract, dict):
        raise ContractFormatException(f"Each contract should be a dictionary")
    keywords = ["assumptions", "guarantees", "InputVars", "OutputVars"]
    str_list_kw = ["InputVars", "OutputVars"]
    for kw in keywords:
        if kw not in contract:
            raise ContractFormatException(f"Keyword \"{kw}\" not found in contract {contract_name}")
        value = contract[kw]
        if not isinstance(value, list):
            raise ContractFormatException(f"The \"{kw}\" in contract {contract_name} should be a list")
        if kw in str_list_kw:
            for str_item in value:
                if not isinstance(str_item, str):
                    raise ContractFormatException(f"The Variables in contract {contract_name} should be defined as strings")
        else:
            for index, clause in enumerate(value):
                check_clause(clause, f"{contract_name}:{kw}{index}")


def check_clause(clause, clause_id):
    keywords = ["constant", "coefficients"]
    for kw in keywords:
        if kw not in clause:
            ContractFormatException(f"Keyword \"{kw}\" not found in {clause_id}")
        value = clause[kw]
        if kw == "coefficients":
            if not isinstance(value, dict):
                raise ContractFormatException(f"The \"{kw}\" in {clause_id} should be a dictionary")

def check_file_data(data):
    if not isinstance(data, dict):
        raise Exception(f"The input should be a dictionary")
    keywords = ["contract1", "contract2", "operation"]
    kw_contracts = ["contract1", "contract2"]
    for kw in keywords:
        if kw not in data:
            raise FileDataFormatException(f"Keyword \"{kw}\" not found in the input")
        value = data[kw]
        if kw in kw_contracts:
            check_contract(contract=value, contract_name=kw)

@click.command()
@click.argument("inputfilename")
@click.argument("outputfilename")
def readInputFile(inputfilename, outputfilename):
    if not os.path.isfile(inputfilename):
        raise Exception(f"The path {inputfilename} is not a file.")
    with open(inputfilename) as f:
        data = json.load(f)
        check_file_data(data=data)
    contracts = []
    for contKey in ["contract1", "contract2"]:
        c = data[contKey]
        check_contract(contract=c, contract_name=contKey)
        reqs = []
        for key in ["assumptions", "guarantees"]:
            reqs.append([PolyhedralTerm(term["coefficients"], term["constant"]) for term in c[key]])
        cont = IoContract(
            inputVars=getVarlist(c["InputVars"]),
            outputVars=getVarlist(c["OutputVars"]),
            assumptions=PolyhedralTermList(list(reqs[0])),
            guarantees=PolyhedralTermList(list(reqs[1])),
        )
        contracts.append(cont)
    print("Contract1:\n" + str(contracts[0]))
    print("Contract2:\n" + str(contracts[1]))
    if data["operation"] == "composition":
        result = contracts[0].compose(contracts[1])
        print("Composed contract:\n" + str(result))
    elif data["operation"] == "quotient":
        result = contracts[0].quotient(contracts[1])
        print("Contract quotient:\n" + str(result))
    elif data["operation"] == "merge":
        result = contracts[0].merge(contracts[1])
        print("Merged contract:\n" + str(result))
    else:
        print("Operation not supported")
    # now store the result in the provided file
    data = {}
    data["InputVars"] = [str(var) for var in result.inputvars]
    data["OutputVars"] = [str(var) for var in result.outputvars]
    data["assumptions"] = [
        {"constant": str(term.constant), "coefficients": {str(k): str(v) for k, v in term.variables.items()}}
        for term in result.a.terms
    ]
    data["guarantees"] = [
        {"constant": str(term.constant), "coefficients": {str(k): str(v) for k, v in term.variables.items()}}
        for term in result.g.terms
    ]
    data = {"contract_comp": data}
    with open(outputfilename, "w") as f:
        json.dump(data, f)


def main():
    FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
    FORMAT1 = "[%(levelname)s:%(funcName)s()] %(message)s"
    FORMAT2 = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(filename="../gear.log", filemode="w", level=logging.INFO, format=FORMAT2)
    readInputFile()


if __name__ == "__main__":
    main()
