from pacti.iocontract import IoContract, Var
from pacti.terms.polyhedra import *

def input2output(i: str, outputs: list[Var], varPrefixes: list[str]) -> str:
  for o in outputs:
    for p in varPrefixes:
      if i.startswith(p) & o.name.startswith(p):
        return f"{i} - {o.name} = 0"
  
  raise ValueError(f"Cannot match variable: {i} to any of {outputs} using prefixes: {varPrefixes}")

def connect(c1: IoContract, c2: IoContract, varPrefixes: list[str]) -> IoContract:
    c12 = PolyhedralContract.readFromString(
      InputVars = list(map(lambda x: x.name, c1.outputvars)),
      OutputVars = list(map(lambda x: x.name, c2.inputvars)),
      assumptions = [],
      guarantees = list(map(lambda i: input2output(i.name, c1.outputvars, varPrefixes), c2.inputvars)))

    return c1.compose(c12).compose(c2)
    