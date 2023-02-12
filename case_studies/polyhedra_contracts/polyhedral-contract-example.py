from pacti.terms.polyhedra.loaders import string_to_polyhedra_contract, polyhedra_contract_to_string
from pacti.utils.string_contract import StrContract
from pacti.iocontract import IoContract

c0=string_to_polyhedra_contract(StrContract(
  inputs=[],
  outputs=[],
  assumptions=[],
  guarantees=[]
))
print("\nEmpty Polhedra Contract pretty-printing")
p0=polyhedra_contract_to_string(c0)
print(p0)


def DSN_contract(s: int, tstart: float, duration: float, min_soc: float, consumption: float) -> tuple[int, list[IoContract]]:
  e = s+1
  spec = StrContract(
    inputs = [
      f"t{s}",    # Scheduled start time
      f"soc{s}",  # initial battery SOC
      f"d{s}",    # initial data volume
      f"e{s}",    # initial trajectory error
      f"r{s}",    # initial relative distance
    ],
    outputs = [
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
      f"-soc{s} <= -{min_soc + duration*consumption}",

      # There is some science data to downlink
      f"-d{s} <= -1"
    ],
    guarantees = [
      # Scheduled task instance end time
      f"t{e} - t{s} = {duration}",

      # Battery SOC discharge
      f"soc{e} - soc{s} <= {duration*consumption}",

      # All science data has been downlinked by the end of the task
      f"d{e} = 0",

      # no change to trajectory error
      f"e{e} - e{s} = 0",

      # no change to relative distance
      f"r{e} - r{s} = 0",
    ])
  return e, string_to_polyhedra_contract(spec)

_,d1=DSN_contract(s=1, tstart=0.0, duration=10.0, min_soc=75.0, consumption=30.0)
print("IoContract rendering:")
print(d1)

p1=polyhedra_contract_to_string(d1)
print("\nPolhedra Contract pretty-printing")
print(p1)
