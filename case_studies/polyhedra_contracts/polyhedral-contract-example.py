
from pacti.iocontract import IoContract
from pacti.terms.polyhedra import *

c0=PolyhedralContract.readFromString(
  InputVars=[],
  OutputVars=[],
  assumptions=[],
  guarantees=[]
)
print("\nEmpty Polhedra Contract pretty-printing")
print(c0)


def DSN_contract(s: int, tstart: float, duration: float, min_soc: float, consumption: float) -> tuple[int, list[IoContract]]:
  e = s+1
  spec = PolyhedralContract.readFromString(
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
      # Scheduled task instance start time
      f"t{s} = {tstart}",

      # Battery has enough energy for the duration of the task
      f"-2soc{s} <= -{min_soc + duration*consumption}",

      # There is some science data to downlink
      f"-d{s} <= -1"
    ],
    guarantees = [
      # Scheduled task instance end time
      f"|t{e} - t{s}| <= {duration}",

      # Battery SOC discharge
      f"3soc{e} - 5soc{s} <= {duration*consumption}",

      # All science data has been downlinked by the end of the task
      f"1.3d{e} = 0",

      # no change to trajectory error
      f"e{e} - .8e{s} = 0",

      # no change to relative distance
      f"3.1r{e} - r{s} = 0",
    ])
  return e, spec

_,d1=DSN_contract(s=1, tstart=0.0, duration=10.0, min_soc=75.0, consumption=30.0)
print("IoContract rendering:")
print(d1)
