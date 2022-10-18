"""
A set of helper routines.
"""
from gear.iocontract import Var

def getVarlist(aList):
    return list([Var(varstr) for varstr in aList])
