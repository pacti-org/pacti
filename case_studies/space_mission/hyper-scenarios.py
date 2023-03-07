from joblib import Parallel, delayed
from base64 import b64decode
from pacti import write_contracts_to_file
from pacti.terms.polyhedra import *
from pacti.iocontract import IoContract, Var
from PIL import Image
import matplotlib.pyplot as plt
import os
import numpy as np
from matplotlib import patches
import pdb
from matplotlib.collections import PatchCollection
from contract_utils import *

# Power viewpoint


# Parameters:
# - s: index of the timeline variables
# - generation: (min, max) rate of battery charge during the task instance
def CHRG_power(s: int, generation: tuple[float, float]) -> PolyhedralContract:
    spec = PolyhedralContract.from_string(
        input_vars=[
            f"soc{s}_entry",  # initial battery SOC
            f"duration_charging{s}",  # variable task duration
        ],
        output_vars=[
            f"soc{s}_exit",  # final battery SOC
        ],
        assumptions=[
            # Task has a positive scheduled duration
            f"-duration_charging{s} <= 0",
            # Battery SOC must be positive
            f"-soc{s}_entry <= 0",
        ],
        guarantees=[
            # duration*generation(min) <= soc{exit} - soc{entry} <= duration*generation(max)
            f" soc{s}_exit - soc{s}_entry - {generation[1]}*duration_charging{s} <= 0",
            f"-soc{s}_exit + soc{s}_entry + {generation[0]}*duration_charging{s} <= 0",
            # Battery cannot exceed maximum SOC
            f"soc{s}_exit <= 100.0",
            # Battery should not completely discharge
            f"-soc{s}_exit <= 0",
        ],
    )
    return spec

    # Parameters:


# - s: start index of the timeline variables
# - consumption: (min, max) rate of battery discharge during the task instance
def power_consumer(s: int, task: str, consumption: tuple[float, float]) -> PolyhedralContract:
    spec = PolyhedralContract.from_string(
        input_vars=[
            f"soc{s}_entry",  # initial battery SOC
            f"duration_{task}{s}",  # variable task duration
        ],
        output_vars=[
            f"soc{s}_exit",  # final battery SOC
        ],
        assumptions=[
            # Task has a positive scheduled duration
            f"-duration_{task}{s} <= 0",
            # Battery has enough energy for worst-case consumption throughout the task instance
            f"-soc{s}_entry + {consumption[1]}*duration_{task}{s} <= 0",
        ],
        guarantees=[
            # duration*consumption(min) <= soc{entry} - soc{exit} <= duration*consumption(max)
            f" soc{s}_entry - soc{s}_exit - {consumption[1]}*duration_{task}{s} <= 0",
            f"-soc{s}_entry + soc{s}_exit + {consumption[0]}*duration_{task}{s} <= 0",
            # Battery cannot exceed maximum SOC
            f"soc{s}_exit <= 100.0",
            # Battery should not completely discharge
            f"-soc{s}_exit <= 0",
        ],
    )
    return spec


def generate_power_scenario(
    dsn_cons: tuple[float, float],
    chrg_gen: tuple[float, float],
    sbo_cons: tuple[float, float],
    tcmh_cons: tuple[float, float],
    tcmdv_cons: tuple[float, float],
) -> PolyhedralContract:
    s1 = power_consumer(s=1, task="dsn", consumption=dsn_cons)
    s2 = CHRG_power(s=2, generation=chrg_gen)
    s3 = power_consumer(s=3, task="sbo", consumption=sbo_cons)
    s4 = power_consumer(s=4, task="tcm_h", consumption=tcmh_cons)
    s5 = power_consumer(s=5, task="tcm_dv", consumption=tcmdv_cons)

    steps2 = scenario_sequence(c1=s1, c2=s2, variables=["soc"], c1index=1)
    steps3 = scenario_sequence(c1=steps2, c2=s3, variables=["soc"], c1index=2)
    steps4 = scenario_sequence(c1=steps3, c2=s4, variables=["soc"], c1index=3)
    steps5 = scenario_sequence(c1=steps4, c2=s5, variables=["soc"], c1index=4).rename_variables(
        [("soc5_exit", "output_soc5")]
    )
    return steps5


# Now, let's apply the Latin hypercube generator to sample the scenario hyperparameters.
from scipy.stats import qmc

n=100

mean_sampler = qmc.LatinHypercube(d=5)
mean_sample = mean_sampler.random(n=n)
l_bounds = [
    3.0,  # dns min cons
    2.5,  # chrg min gen
    0.5,  # sbo min cons
    0.5,  # tcm.h min cons
    0.5,  # tcm.dv min cons
]
u_bounds = [
    5.0,  # dns max cons
    5.0,  # chrg max gen
    1.5,  # sbo max cons
    1.5,  # tcm.h max cons
    1.5,  # tcm.dv max cons
]
scaled_mean_sample = qmc.scale(sample=mean_sample, l_bounds=l_bounds, u_bounds=u_bounds)
# print(scaled_mean_sample)

dev_sampler = qmc.LatinHypercube(d=5)
dev_sample = dev_sampler.random(n=n)
# print(dev_sample)


def make_range(mean: float, dev: float) -> tuple[float, float]:
    delta = mean * dev
    return (mean - delta, mean + delta)

def make_scenario(means, devs) -> PolyhedralContract:
    return generate_power_scenario(
        dsn_cons=make_range(means[0], devs[0]),
        chrg_gen=make_range(means[1], devs[1]),
        sbo_cons=make_range(means[2], devs[2]),
        tcmh_cons=make_range(means[3], devs[3]),
        tcmdv_cons=make_range(means[4], devs[4]),
    )

# loop = asyncio.get_event_loop()
# looper = asyncio.gather(*[make_scenario(mean, dev) for mean, dev in zip(scaled_mean_sample, dev_sample)])
# results = loop.run_until_complete(looper) 

# print(results)

scenarios = Parallel(n_jobs=16)(delayed(make_scenario)(mean, dev) for mean, dev in zip(scaled_mean_sample, dev_sample))
print(scenarios)
#print([make_scenario(mean, dev) for mean, dev in zip(scaled_mean_sample, dev_sample)])

