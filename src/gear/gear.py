#!python

import json
import logging
import os

import click

import gear.iocontract as iocontract
import gear.polyhedralterm as polyhedralterm


def getVarlist(aList):
    return list([iocontract.Var(varstr) for varstr in aList])


@click.command()
@click.argument("inputfilename")
@click.argument("outputfilename")
def readInputFile(inputfilename, outputfilename):
    assert os.path.isfile(inputfilename)
    with open(inputfilename) as f:
        data = json.load(f)
    contracts = []
    for contKey in ["contract1", "contract2"]:
        c = data[contKey]
        reqs = []
        for key in ["assumptions", "guarantees"]:
            reqs.append([polyhedralterm.PolyhedralTerm(term["coefficients"], term["constant"]) for term in c[key]])
        cont = iocontract.IoContract(
            inputVars=getVarlist(c["InputVars"]),
            outputVars=getVarlist(c["OutputVars"]),
            assumptions=polyhedralterm.PolyhedralTermList(list(reqs[0])),
            guarantees=polyhedralterm.PolyhedralTermList(list(reqs[1])),
        )
        contracts.append(cont)
    print("Contract1:\n" + str(contracts[0]))
    print("Contract2:\n" + str(contracts[1]))
    if data["operation"] == "composition":
        data = {"contract_composition"}
        result = contracts[0].compose(contracts[1])
        print("Composed contract:\n" + str(result))
    elif data["operation"] == "quotient":
        data = {"contract_quotient"}
        result = contracts[0].quotient(contracts[1])
        print("Contract quotient:\n" + str(result))
    elif data["operation"] == "merge":
        data = {"contract_merge"}
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
    logging.basicConfig(filename="gear.log", filemode="w", level=logging.INFO, format=FORMAT2)
    readInputFile()


if __name__ == "__main__":
    main()
