#!python

import os
import iocontract
import json
import click
import logging
import polyhedralterm


def getVarset(aList):
    return set([iocontract.Var(varstr) for varstr in aList])


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
            reqs.append([polyhedralterm.PolyhedralTerm(term['coefficients'], term['constant']) for term in c[key]])
        cont = iocontract.IoContract(inputVars=getVarset(c['InputVars']), outputVars=getVarset(c['OutputVars']),
            assumptions=polyhedralterm.PolyhedralTermSet(set(reqs[0])), guarantees=polyhedralterm.PolyhedralTermSet(set(reqs[1])))
        contracts.append(cont)
    logging.info("Contract1:\n" + str(contracts[0]))
    logging.info("Contract2:\n" + str(contracts[1]))
    if data['operation'] == 'composition':
        logging.info("Composed contract:\n" + str(contracts[0].compose(contracts[1])))
    elif data['operation'] == 'quotient':
        logging.info("Contract quotient:\n" + str(contracts[0].quotient(contracts[1])))
    else:
        logging.info("Operation not supported")


 
if __name__ == '__main__':
    FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
    FORMAT1 = "[%(levelname)s:%(funcName)s()] %(message)s"
    FORMAT2 = '%(asctime)s:%(levelname)s:%(name)s:%(message)s'
    logging.basicConfig(filename='log.log', filemode='w', level = logging.INFO, format = FORMAT2)
    readInputFile()