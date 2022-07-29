#!python

import os
import PolyhedralContracts as PC
import json
import click
import logging


def getVarset(aList):
    return set([PC.Var(varstr) for varstr in aList])


@click.command()
@click.argument('filename')
def readInputFile(filename):
    assert os.path.isfile(filename)
    with open(filename) as f:
        data = json.load(f)
    contracts = []
    for contKey in ['contract1', 'contract2']:
        c = data[contKey]
        reqs = []
        for key in ['assumptions', 'guarantees']:
            reqs.append([PC.Term(term['coefficients'], term['constant']) for term in c[key]])
        cont = PC.IoContract(inputVars=getVarset(c['InputVars']), outputVars=getVarset(c['OutputVars']), assumptions=PC.TermList(set(reqs[0])), guarantees=PC.TermList(set(reqs[1])))
        contracts.append(cont)
    print(contracts[0])
    print(contracts[1])
    if data['operation'] == 'composition':
        print(contracts[0].compose(contracts[1]))
    else:
        print("Operation not supported")


 
if __name__ == '__main__':
    FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
    FORMAT = "[%(levelname)s:%(funcName)s()] %(message)s"
    FORMAT2 = '%(asctime)s:%(levelname)s:%(name)s:%(message)s'
    logging.basicConfig(level = logging.INFO, format = FORMAT)
    readInputFile()