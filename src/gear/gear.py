#!python

import os
import gear.iocontract as iocontract
import json
import click
import logging
import gear.polyhedralterm as polyhedralterm


def getVarset(aList):
    return set([iocontract.Var(varstr) for varstr in aList])


@click.command()
@click.argument('inputfilename')
@click.argument('outputfilename')
def readInputFile(inputfilename,outputfilename):
    assert os.path.isfile(inputfilename)
    with open(inputfilename) as f:
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
    print("Contract1:\n" + str(contracts[0]))
    print("Contract2:\n" + str(contracts[1]))
    if data['operation'] == 'composition':
        data = {'contract_composition'}
        result = contracts[0].compose(contracts[1])
        print("Composed contract:\n" + str(result))
    elif data['operation'] == 'quotient':
        data = {'contract_quotient'}
        result = contracts[0].quotient(contracts[1])
        print("Contract quotient:\n" + str(result))
    else:
        print("Operation not supported")
    # now store the result in the provided file
    data = {}
    data['InputVars']  = [str(var) for var in result.inputvars]
    data['OutputVars'] = [str(var) for var in result.outputvars]
    data['assumptions'] = [{'constant':str(term.constant), 'coefficients':{str(k):str(v) for k,v in term.variables.items()}} for term in result.a.terms]
    data['guarantees'] = [{'constant':str(term.constant), 'coefficients':{str(k):str(v) for k,v in term.variables.items()}} for term in result.g.terms]
    data = {'contract_comp':data}
    with open(outputfilename, 'w') as f:
        json.dump(data, f)
    
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
    if type(contract) is dict:
        contract = [contract]
    list_iocontracts = []
    for c in contract:
        if type(c) is not dict:
            return ValueError('A dict type contract is expected.')
        reqs = []
        for key in ['assumptions', 'guarantees']:
            reqs.append([polyhedralterm.PolyhedralTerm(term['coefficients'], term['constant']) for term in c[key]])
            iocont = iocontract.IoContract(inputVars=getVarset(c['InputVars']),
                                           outputVars=getVarset(c['OutputVars']),
                                           assumptions=polyhedralterm.PolyhedralTermSet(set(reqs[0])),
                                           guarantees=polyhedralterm.PolyhedralTermSet(set(reqs[1])))
            list_iocontracts.append(iocont)
    if len(list_iocontracts) == 1:
        return list_iocontracts[0]
    else:
        return list_iocontracts

def writeContract(contract, filename: str = None):
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
    if type(contract) is dict:
        contract = [contract]
    contract_list = []
    for c in contract:
        if not isinstance(c, iocontract.IoContract):
            return ValueError('A IoContract is expected.')
        contract_dict = {}
        contract_dict['InputVars']  = [str(var) for var in contract.inputvars]
        contract_dict['OutputVars'] = [str(var) for var in contract.outputvars]
        contract_dict['assumptions'] = [{'constant':str(term.constant), 'coefficients':{str(k):str(v)\
                                    for k,v in term.variables.items()}} for term in contract.a.terms]
        contract_dict['guarantees'] = [{'constant':str(term.constant), 'coefficients':{str(k):str(v)\
                                    for k,v in term.variables.items()}} for term in contract.g.terms]
        contract_list.append(contract_dict)
    if filename:
        for c_dict in contract_list:
            with open(filename, 'w+') as f:
                json.dump(c_dict, f)
    if len(contract_list) == 1:
        return contract_list[0]
    else:
        return contract_list

def main():
    FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
    FORMAT1 = "[%(levelname)s:%(funcName)s()] %(message)s"
    FORMAT2 = '%(asctime)s:%(levelname)s:%(name)s:%(message)s'
    logging.basicConfig(filename='gear.log', filemode='w', level = logging.INFO, format = FORMAT2)
    readInputFile()

if __name__ == '__main__':
    main()