
from pacti.iocontract import IoContract, Var
from pacti.terms.polyhedra import *

def input2output(i: str, outputs: list[Var], varPrefixes: list[str]) -> str:
  for o in outputs:
    for p in varPrefixes:
      if i.startswith(p) & o.name.startswith(p):
        return f"{i} - {o.name} = 0"
  
  raise ValueError(f"Cannot match variable: {i} to any of {outputs} using prefixes: {varPrefixes}")

varPrefixes=["t", "soc", "d", "e", "r"]

def connect(c1: IoContract, c2: IoContract, varPrefixes: list[str]) -> IoContract:
    c12 = PolyhedralContract.from_string(
      InputVars = list(map(lambda x: x.name, c1.outputvars)),
      OutputVars = list(map(lambda x: x.name, c2.inputvars)),
      assumptions = [],
      guarantees = list(map(lambda i: input2output(i.name, c1.outputvars, varPrefixes), c2.inputvars)))

    return c1.compose(c12).compose(c2)

def initial_contract() -> tuple[int, PolyhedralContract]:
  e=1
  spec = PolyhedralContract.from_string(
    InputVars = [],
    OutputVars= [
      f"t{e}",    # Scheduled end time
      f"soc{e}",  # final battery SOC
      f"d{e}",    # final data volume
      f"e{e}",    # final trajectory error
      f"r{e}",    # final relative distance
    ],
    assumptions=[],
    guarantees=[
      f"t{e} = 0",
      f"-soc{e} <= -100",
      f"-d{e} <= 0",
      f"-e{e} <= 0",
      f"-r{e} <= -100",
    ]
  )
  return e, spec

def SBO_contract(s: int, duration: float, generation: float, consumption: float, improvement: float) -> tuple[int, PolyhedralContract]:
  e = s+1
  spec = PolyhedralContract.from_string(
    InputVars = [
      f"t{s}",    # Scheduled start time
      f"soc{s}",  # initial battery SOC
      f"d{s}",    # initial data volume
      f"e{s}",    # initial trajectory error
      f"r{s}",    # initial relative distance
    ],
    OutputVars = [
      f"t{e}",    # Scheduled end time
      f"soc{e}",  # final battery SOC
      f"d{e}",    # final data volume
      f"e{e}",    # final trajectory error
      f"r{e}",    # final relative distance
    ],
    assumptions = [
      # Battery has enough energy for the consumption over the duration of the task instance
      f"-3.45soc{s} <= -{duration*consumption}",
    ],
    guarantees = [
      # Scheduled task instance end time
      f"t{e} - t{s} = {duration}",
    
      # Battery discharges by at most duration*consumption
      f"900soc{s} - soc{e} <= {duration*consumption}",

      # data volume increases by at least duration*generation
      f"0.23d{s} - d{e} <= -{duration*generation}",

      # trajectory error improves by at least duration*improvement
      f"e{s} - e{e} <= -{duration*improvement}",

      # no change to relative distance
      f"r{e} - r{s} = 0",
    ])
  return e, spec

_,init=initial_contract()
print("init:\n",init)

_,sbo1 = SBO_contract(s=30, duration=6.0, generation=10.0, consumption=4.0, improvement=8.0)
print("sbo1:\n",sbo1)

c0b = connect(init, sbo1, varPrefixes)
print(c0b)