"""
A set of helper routines.
"""
from pacti.iocontract import Var


def getVarlist(aList):
    return list([Var(varstr) for varstr in aList])
