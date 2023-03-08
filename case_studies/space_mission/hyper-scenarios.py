import time
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

nb_contracts=0
nb_merge=0
nb_compose=0

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

nb_contracts+=5
nb_compose+=4
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


# Science & communication viewpoint

# - s: start index of the timeline variables
# - speed: (min, max) downlink rate during the task instance
def DSN_data(s: int, speed: tuple[float, float]) -> PolyhedralContract:
    spec = PolyhedralContract.from_string(
        input_vars=[
            f"d{s}_entry",  # initial data volume
            f"duration_dsn{s}",  # variable task duration
        ],
        output_vars=[
            f"d{s}_exit",  # final data volume
        ],
        assumptions=[
            # Task has a positive scheduled duration
            f"-duration_dsn{s} <= 0",
            # downlink data upper bound
            f" d{s}_entry <= 100",
            # downlink data lower bound
            f"-d{s}_entry <= 0",
        ],
        guarantees=[
            # duration*speed(min) <= d{entry} - d{exit} <= duration*speed(max)
            f" d{s}_entry - d{s}_exit - {speed[1]}*duration_dsn{s} <= 0",
            f"-d{s}_entry + d{s}_exit + {speed[0]}*duration_dsn{s} <= 0",
            # downlink cannot continue if there is no data left.
            f"-d{s}_exit <= 0",
        ],
    )
    return spec


# Parameters:
# - s: start index of the timeline variables
# - generation: (min, max) rate of small body observations during the task instance
def SBO_science_storage(s: int, generation: tuple[float, float]) -> PolyhedralContract:
    spec = PolyhedralContract.from_string(
        input_vars=[
            f"d{s}_entry",  # initial data storage volume
            f"duration_sbo{s}",  # knob variable for SBO duration
        ],
        output_vars=[
            f"d{s}_exit",  # final data storage volume
        ],
        assumptions=[
            # Task has a positive scheduled duration
            f"-duration_sbo{s} <= 0",
            # There is enough data storage available
            f"d{s}_entry + {generation[1]}*duration_sbo{s} <= 100",
            # downlink data lower bound
            f"-d{s}_entry <= 0",
        ],
        guarantees=[
            # duration*generation(min) <= d{exit} - d{entry} <= duration*generation(max)
            f" d{s}_exit - d{s}_entry - {generation[1]}*duration_sbo{s} <= 0",
            f"-d{s}_exit + d{s}_entry + {generation[0]}*duration_sbo{s} <= 0",
            # Data volume cannot exceed the available storage capacity
            f"d{s}_exit <= 100",
        ],
    )
    return spec


def SBO_science_comulative(s: int, generation: tuple[float, float]) -> PolyhedralContract:
    spec = PolyhedralContract.from_string(
        input_vars=[
            f"c{s}_entry",  # initial cumulative data volume
            f"duration_sbo{s}",  # knob variable for SBO duration
        ],
        output_vars=[
            f"c{s}_exit",  # final cumulative data volume
        ],
        assumptions=[
            # Task has a positive scheduled duration
            f"-duration_sbo{s} <= 0",
            # cumulative data lower bound
            f"-c{s}_entry <= 0",
        ],
        guarantees=[
            # duration*generation(min) <= c{exit} - c{entry} <= duration*generation(max)
            f" c{s}_exit - c{s}_entry - {generation[1]}*duration_sbo{s} <= 0",
            f"-c{s}_exit + c{s}_entry + {generation[0]}*duration_sbo{s} <= 0",
        ],
    )
    return spec

nb_contracts+=10
nb_merge+=5
nb_compose+=4
def generate_science_scenario(dsn_speed: tuple[float, float], sbo_gen: tuple[float, float]) -> PolyhedralContract:
    s1 = DSN_data(s=1, speed=dsn_speed).merge(nochange_contract(s=1, name="c"))
    s2 = nochange_contract(s=2, name="d").merge(nochange_contract(s=2, name="c"))
    s3 = SBO_science_storage(s=3, generation=sbo_gen).merge(SBO_science_comulative(s=3, generation=sbo_gen))
    s4 = nochange_contract(s=4, name="d").merge(nochange_contract(s=4, name="c"))
    s5 = nochange_contract(s=5, name="d").merge(nochange_contract(s=5, name="c"))

    steps2 = scenario_sequence(c1=s1, c2=s2, variables=["d", "c"], c1index=1)
    steps3 = scenario_sequence(c1=steps2, c2=s3, variables=["d", "c"], c1index=2)
    steps4 = scenario_sequence(c1=steps3, c2=s4, variables=["d", "c"], c1index=3)
    steps5 = scenario_sequence(c1=steps4, c2=s5, variables=["d", "c"], c1index=4).rename_variables(
        [("d4_exit", "output_d4"), ("c4_exit", "output_c4"), ("d5_exit", "output_d5"), ("c5_exit", "output_c5")]
    )
    return steps5

# Verify we get the same contract as the notebook...
# print(generate_science_scenario(dsn_speed=(5.2, 5.5), sbo_gen=(3.0, 4.0)))

# Navigation viewpoint

def uncertainty_generating_nav(s: int, noise: tuple[float, float]) -> PolyhedralContract:
    spec = PolyhedralContract.from_string(
        input_vars=[
            f"u{s}_entry",  # initial trajectory estimation uncertainty
            f"r{s}_entry",  # initial relative trajectory distance
        ],
        output_vars=[
            f"u{s}_exit",  # final trajectory estimation uncertainty
            f"r{s}_exit",  # final relative trajectory distance
        ],
        assumptions=[
            # 0 <= u{s}_entry <= 100
            f"-u{s}_entry <= 0",
            f" u{s}_entry <= 100",
            # 0 <= r{s}_entry <= 100
            f"-r{s}_entry <= 0",
            f" r{s}_entry <= 100",
        ],
        guarantees=[
            # upper bound u{s}_exit <= 100
            f"u{s}_exit <= 100",
            # noise(min) <= u{exit} - u{entry} <= noise(max)
            f" u{s}_exit - u{s}_entry <=  {noise[1]}",
            f"-u{s}_exit + u{s}_entry <= -{noise[0]}",
            # no change to relative trajectory distance
            f"r{s}_exit - r{s}_entry = 0",
        ],
    )
    return spec

# Parameters:
# - s: start index of the timeline variables
# - improvement: rate of trajectory estimation uncertainty improvement during the task instance
def SBO_nav_uncertainty(s: int, improvement: tuple[float, float]) -> PolyhedralContract:
    spec = PolyhedralContract.from_string(
        input_vars=[
            f"u{s}_entry",  # initial trajectory uncertainty
            f"duration_sbo{s}",  # knob variable for SBO duration
        ],
        output_vars=[
            f"u{s}_exit",  # final trajectory uncertainty
        ],
        assumptions=[
            # Task has a positive scheduled duration
            f"-duration_sbo{s} <= 0",
            # Upper-bound on the trajectory estimation uncertainty
            f"u{s}_entry <= 100",
        ],
        guarantees=[
            # upper bound u{s}_exit <= 100
            f"u{s}_exit <= 100",
            # duration*improvement(min) <= u{entry} - u{exit} <= duration*improvement(max)
            f" u{s}_entry - u{s}_exit - {improvement[1]}*duration_sbo{s} <= 0",
            f"-u{s}_entry + u{s}_exit + {improvement[0]}*duration_sbo{s} <= 0",
            # Lower-bound on the trajectory estimation uncertainty
            f"-u{s}_exit <= 0",
        ],
    )
    return spec

def TCM_navigation_deltav_uncertainty(s: int, noise: tuple[float, float]) -> PolyhedralContract:
    spec = PolyhedralContract.from_string(
        input_vars=[
            f"u{s}_entry",  # initial trajectory estimation uncertainty
            f"duration_tcm_deltav{s}",  # knob variable for TCM deltav duration
        ],
        output_vars=[
            f"u{s}_exit",  # final trajectory estimation uncertainty
        ],
        assumptions=[
            # Task has a positive scheduled duration
            f"-duration_tcm_deltav{s} <= 0",
            # 0 <= u{s}_entry <= 100
            f"-u{s}_entry <= 0",
            f" u{s}_entry <= 100",
        ],
        guarantees=[
            # upper bound u{s}_exit <= 100
            f"u{s}_exit <= 100",
            # noise(min) <= u{exit} - u{entry} <= noise(max)
            f" u{s}_exit - u{s}_entry - {noise[1]} duration_tcm_deltav{s} <= 0",
            f"-u{s}_exit + u{s}_entry + {noise[0]} duration_tcm_deltav{s} <= 0",
        ],
    )
    return spec

def TCM_navigation_deltav_progress(s: int, progress: tuple[float, float]) -> PolyhedralContract:
    spec = PolyhedralContract.from_string(
        input_vars=[
            f"r{s}_entry",  # initial trajectory relative distance
            f"duration_tcm_deltav{s}",  # knob variable for TCM deltav duration
        ],
        output_vars=[
            f"r{s}_exit",  # final trajectory relative distance
        ],
        assumptions=[
            # upper bound on trajectory relative distance
            f"r{s}_entry <= 100",
        ],
        guarantees=[
            # duration*improvement(min) <= r{entry} - r{exit} <= duration*improvement(max)
            f" r{s}_entry - r{s}_exit - {progress[1]}*duration_tcm_deltav{s} <= 0",
            f"-r{s}_entry + r{s}_exit + {progress[0]}*duration_tcm_deltav{s} <= 0",
            # lower bound on trajectory relative distance
            f"-r{s}_exit <= 0",
        ],
    )
    return spec

nb_contracts+=8
nb_merge+=3
nb_compose+=4
def generate_navigation_scenario(
    dsn_noise: tuple[float, float],
    chrg_noise: tuple[float, float],
    sbo_imp: tuple[float, float],
    tcm_dv_noise: tuple[float, float],
    tcm_dv_progress: tuple[float, float],
) -> PolyhedralContract:
    s1 = uncertainty_generating_nav(s=1, noise=dsn_noise)
    s2 = uncertainty_generating_nav(s=2, noise=chrg_noise)
    s3 = SBO_nav_uncertainty(s=3, improvement=sbo_imp).merge(nochange_contract(s=3, name="r"))
    s4 = nochange_contract(s=4, name="u").merge(nochange_contract(s=4, name="r"))
    s5 = TCM_navigation_deltav_uncertainty(s=5, noise=tcm_dv_noise).merge(
        TCM_navigation_deltav_progress(s=5, progress=tcm_dv_progress)
    )

    steps2 = scenario_sequence(c1=s1, c2=s2, variables=["u", "r"], c1index=1)
    steps3 = scenario_sequence(c1=steps2, c2=s3, variables=["u", "r"], c1index=2)
    steps4 = scenario_sequence(c1=steps3, c2=s4, variables=["u", "r"], c1index=3)
    steps5 = scenario_sequence(c1=steps4, c2=s5, variables=["u", "r"], c1index=4).rename_variables(
        [("u4_exit", "output_u4"), ("r4_exit", "output_r4"), ("u5_exit", "output_u5"), ("r5_exit", "output_r5")]
    )
    return steps5

# print(
#     generate_navigation_scenario(
#         dsn_noise=(1.0, 2.0),
#         chrg_noise=(1.0, 2.0),
#         sbo_imp=(0.4, 0.6),
#         tcm_dv_noise=(1.5, 1.6),
#         tcm_dv_progress=(0.4, 0.5),
#     )
# )

# Now, let's apply the Latin hypercube generator to sample the scenario hyperparameters.
from scipy.stats import qmc

d = 12
n = 200

mean_sampler = qmc.LatinHypercube(d=d)
mean_sample = mean_sampler.random(n=n)
l_bounds = [
    3.0,  # power: min dns cons
    2.5,  # power: min chrg gen
    0.5,  # power: min sbo cons
    0.5,  # power: min tcm_h cons
    0.5,  # power: min tcm_dv cons
    5.0,  # science: min dsn speed
    3.0,  # science: min sbo gen
    1.0,  # nav: min dsn noise
    1.0,  # nav: min chrg noise
    0.3,  # nav: min sbo imp
    1.2,  # nav: min tcm_dv noise
    0.3,  # nav: min tcm_dv progress
]
u_bounds = [
    5.0,  # power: max dns cons
    5.0,  # power: max chrg gen
    1.5,  # power: max sbo cons
    1.5,  # power: max tcm_h cons
    1.5,  # power: max tcm_dv cons
    6.0,  # science: max dsn speed
    4.0,  # science: max sbo gen
    2.0,  # nav: max dsn noise
    2.0,  # nav: max chrg noise
    0.8,  # nav: max sbo imp
    1.8,  # nav: max tcm_dv noise
    0.8,  # nav: max tcm_dv progress
]
scaled_mean_sample = qmc.scale(sample=mean_sample, l_bounds=l_bounds, u_bounds=u_bounds)

dev_sampler = qmc.LatinHypercube(d=d)
dev_sample = dev_sampler.random(n=n)

def make_range(mean: float, dev: float) -> tuple[float, float]:
    delta = mean * dev
    return (mean - delta, mean + delta)

# 23 contracts
# 12 compose
# 8 merge
def make_scenario(means, devs) -> PolyhedralContract:
    scenario_pwr = generate_power_scenario(
        dsn_cons=make_range(means[0], devs[0]),
        chrg_gen=make_range(means[1], devs[1]),
        sbo_cons=make_range(means[2], devs[2]),
        tcmh_cons=make_range(means[3], devs[3]),
        tcmdv_cons=make_range(means[4], devs[4]),
    )

    scenario_sci = generate_science_scenario(
        dsn_speed=make_range(means[5], devs[5]), 
        sbo_gen=make_range(means[6], devs[6])
    )

    scenario_nav = generate_navigation_scenario(
        dsn_noise=make_range(means[7], devs[7]),
        chrg_noise=make_range(means[8], devs[8]),
        sbo_imp=make_range(means[9], devs[9]),
        tcm_dv_noise=make_range(means[10], devs[10]),
        tcm_dv_progress=make_range(means[11], devs[11]),
    )

    return scenario_pwr.merge(scenario_sci).merge(scenario_nav)


t0 = time.time()
scenarios = Parallel(n_jobs=32)(delayed(make_scenario)(mean, dev) for mean, dev in zip(scaled_mean_sample, dev_sample))
t1 = time.time()
print(f"All {n} scenarios generated in {t1-t0} seconds.")
print(f"Each scenario required creating {nb_contracts} contracts combined via {nb_merge} merge and {nb_compose} compose operations.")

# print(scenarios)
# print([make_scenario(mean, dev) for mean, dev in zip(scaled_mean_sample, dev_sample)])

def make_op_requirements(reqs) -> PolyhedralContract:
    return PolyhedralContract.from_string(
    input_vars=[
        "soc1_entry",
        "duration_dsn1",
        "duration_charging2",
        "duration_sbo3",
        "duration_tcm_heating4",
        "duration_tcm_deltav5",
        "c1_entry",
        "d1_entry",
        "u1_entry",
        "r1_entry",
    ],
    output_vars=[
        "output_c5",
        "output_d5",
    ],
    assumptions=[
        f"soc1_entry={reqs[0]}",
        f"-duration_dsn1 <= -{reqs[1]}",
        f"-duration_charging2 <= -{reqs[1]}",
        f"-duration_sbo3 <= -{reqs[1]}",
        f"-duration_tcm_heating4 <= -{reqs[1]}",
        f"-duration_tcm_deltav5 <= -{reqs[1]}",
        "c1_entry=0",
        f"d1_entry={reqs[2]}",
        f"u1_entry={reqs[3]}",
        "r1_entry=100",
    ],
    guarantees=[])

def schedulability_analysis(scenario: PolyhedralContract, reqs):
    op_req=make_op_requirements(reqs)
    try:
        c = scenario.merge(op_req)
        max_soc = c.optimize("0.2 output_soc1 + 0.2 output_soc2 + 0.2 output_soc3 + 0.2 output_soc4 + 0.2 output_soc5", maximize=True)
        min_soc = c.optimize("0.2 output_soc1 + 0.2 output_soc2 + 0.2 output_soc3 + 0.2 output_soc4 + 0.2 output_soc5", maximize=False)
        u = c.get_variable_bounds("output_u5")
        r = c.get_variable_bounds("output_r5")
        c = c.get_variable_bounds("output_c5")
        return (scenario, reqs, min_soc, max_soc, u, r, c)
    except (ValueError):
        return None
    
m=200
op_sampler = qmc.LatinHypercube(d=4)
op_sample = op_sampler.random(n=m)
op_l_bounds = [
    60.0,   # power: min soc
    10.0,   # alloc: min delta t
    60.0,   # sci: min d
    40.0,   # nav: min u
]
op_u_bounds = [
    90.0,   # power: max soc
    50.0,   # alloc: max delta t
    100.0,  # sci: max d
    90.0,   # nav: max u
]
scaled_op_sample = qmc.scale(sample=op_sample, l_bounds=op_l_bounds, u_bounds=op_u_bounds)

import itertools

t2=time.time()
all_results = Parallel(n_jobs=32)(delayed(schedulability_analysis)(scenario, req) for scenario in scenarios for req in scaled_op_sample)
t3=time.time()
results = [ x for x in all_results if x is not None ]
print(f"Found {len(results)} admissible schedules out of {m*n} combinations generated from {m} variations of operational requirements for each of the {n} scenarios in {t3-t1} seconds.")

# pickle store the data...
