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

from typing import Tuple, Union

numeric = Union[int, float]

epsilon = 1e-8

nb_contracts = 0
nb_merge = 0
nb_compose = 0


def reset_nb_counts():
    global nb_contracts
    nb_contracts = 0
    global nb_merge
    nb_merge = 0
    global nb_compose
    nb_compose = 0


def print_counts():
    print(f"{nb_contracts} contracts; {nb_compose} compositions; {nb_merge} merges.")


# Power viewpoint


# Parameters:
# - s: index of the timeline variables
# - generation: (min, max) rate of battery charge during the task instance
def CHRG_power(s: int, generation: tuple[float, float]) -> PolyhedralContract:
    global nb_contracts
    nb_contracts += 1
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
            # Upper bound on entry soc
            f"soc{s}_entry <= 100.0",
            # Lower bound on entry soc
            f"-soc{s}_entry <= 0",
            # Battery should not overcharge
            f"soc{s}_entry + {generation[1]}*duration_charging{s} <= 100",
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
    global nb_contracts
    nb_contracts += 1
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
            # Upper bound on entry soc
            f"soc{s}_entry <= 100.0",
            # Lower bound on entry soc
            f"-soc{s}_entry <= 0",
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


power_variables = ["soc"]


def generate_power_scenario(
    s: int,
    dsn_cons: tuple[float, float],
    chrg_gen: tuple[float, float],
    sbo_cons: tuple[float, float],
    tcmh_cons: tuple[float, float],
    tcmdv_cons: tuple[float, float],
    rename_outputs: bool = False,
) -> PolyhedralContract:
    global nb_compose
    nb_compose += 4  # scenario_sequence

    s1 = power_consumer(s=s, task="dsn", consumption=dsn_cons)
    s2 = CHRG_power(s=s + 1, generation=chrg_gen)
    s3 = power_consumer(s=s + 2, task="sbo", consumption=sbo_cons)
    s4 = power_consumer(s=s + 3, task="tcm_h", consumption=tcmh_cons)
    s5 = power_consumer(s=s + 4, task="tcm_dv", consumption=tcmdv_cons)

    steps2 = scenario_sequence(c1=s1, c2=s2, variables=power_variables, c1index=s)
    steps3 = scenario_sequence(c1=steps2, c2=s3, variables=power_variables, c1index=s + 1)
    steps4 = scenario_sequence(c1=steps3, c2=s4, variables=power_variables, c1index=s + 2)
    steps5 = scenario_sequence(c1=steps4, c2=s5, variables=power_variables, c1index=s + 3)

    if rename_outputs:
        return steps5.rename_variables([(f"soc{s+4}_exit", f"output_soc{s+4}")])
    else:
        return steps5



# Science & communication viewpoint


# - s: start index of the timeline variables
# - speed: (min, max) downlink rate during the task instance
def DSN_data(s: int, speed: tuple[float, float]) -> PolyhedralContract:
    global nb_contracts
    nb_contracts += 1
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
    global nb_contracts
    nb_contracts += 1
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
    global nb_contracts
    nb_contracts += 1
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


science_variables = ["d", "c"]


def generate_science_scenario(
    s: int, dsn_speed: tuple[float, float], sbo_gen: tuple[float, float], rename_outputs: bool = False
) -> PolyhedralContract:
    global nb_contracts
    nb_contracts += 7  # nochange_contract
    global nb_merge
    nb_merge += 5
    global nb_compose
    nb_compose += 4  # scenario_sequence

    s1 = DSN_data(s=s, speed=dsn_speed).merge(nochange_contract(s=s, name="c"))
    s2 = nochange_contract(s=s + 1, name="d").merge(nochange_contract(s=s + 1, name="c"))
    s3 = SBO_science_storage(s=s + 2, generation=sbo_gen).merge(SBO_science_comulative(s=s + 2, generation=sbo_gen))
    s4 = nochange_contract(s=s + 3, name="d").merge(nochange_contract(s=s + 3, name="c"))
    s5 = nochange_contract(s=s + 4, name="d").merge(nochange_contract(s=s + 4, name="c"))

    steps2 = scenario_sequence(c1=s1, c2=s2, variables=science_variables, c1index=s)
    steps3 = scenario_sequence(c1=steps2, c2=s3, variables=science_variables, c1index=s + 1)
    steps4 = scenario_sequence(c1=steps3, c2=s4, variables=science_variables, c1index=s + 2)
    steps5 = scenario_sequence(c1=steps4, c2=s5, variables=science_variables, c1index=s + 3)

    if rename_outputs:
        return steps5.rename_variables(
            [
                (f"d{s+3}_exit", f"output_d{s+3}"),
                (f"c{s+3}_exit", f"output_c{s+3}"),
                (f"d{s+4}_exit", f"output_d{s+4}"),
                (f"c{s+4}_exit", f"output_c{s+4}"),
            ]
        )
    else:
        return steps5


# Verify we get the same contract as the notebook...
# print(generate_science_scenario(dsn_speed=(5.2, 5.5), sbo_gen=(3.0, 4.0)))

# Navigation viewpoint


def uncertainty_generating_nav(s: int, noise: tuple[float, float]) -> PolyhedralContract:
    global nb_contracts
    nb_contracts += 1
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
            f"| r{s}_exit - r{s}_entry | <= {epsilon}",
            # Lower-bound on the trajectory estimation uncertainty
            f"-u{s}_exit <= 0",
        ],
    )
    return spec


# Parameters:
# - s: start index of the timeline variables
# - improvement: rate of trajectory estimation uncertainty improvement during the task instance
def SBO_nav_uncertainty(s: int, improvement: tuple[float, float]) -> PolyhedralContract:
    global nb_contracts
    nb_contracts += 1
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
    global nb_contracts
    nb_contracts += 1
    spec = PolyhedralContract.from_string(
        input_vars=[
            f"u{s}_entry",  # initial trajectory estimation uncertainty
            f"duration_tcm_dv{s}",  # knob variable for TCM deltav duration
        ],
        output_vars=[
            f"u{s}_exit",  # final trajectory estimation uncertainty
        ],
        assumptions=[
            # Task has a positive scheduled duration
            f"-duration_tcm_dv{s} <= 0",
            # 0 <= u{s}_entry <= 100
            f"-u{s}_entry <= 0",
            f" u{s}_entry <= 100",
        ],
        guarantees=[
            # upper bound u{s}_exit <= 100
            f"u{s}_exit <= 100",
            # noise(min) <= u{exit} - u{entry} <= noise(max)
            f" u{s}_exit - u{s}_entry - {noise[1]} duration_tcm_dv{s} <= 0",
            f"-u{s}_exit + u{s}_entry + {noise[0]} duration_tcm_dv{s} <= 0",
            # Lower-bound on the trajectory estimation uncertainty
            f"-u{s}_exit <= 0",
        ],
    )
    return spec


def TCM_navigation_deltav_progress(s: int, progress: tuple[float, float]) -> PolyhedralContract:
    global nb_contracts
    nb_contracts += 1
    spec = PolyhedralContract.from_string(
        input_vars=[
            f"r{s}_entry",  # initial trajectory relative distance
            f"duration_tcm_dv{s}",  # knob variable for TCM deltav duration
        ],
        output_vars=[
            f"r{s}_exit",  # final trajectory relative distance
        ],
        assumptions=[
            # upper bound on trajectory relative distance
            f"r{s}_entry <= 100",
        ],
        guarantees=[
            # upper bound r{s}_exit <= 100
            f"r{s}_exit <= 100",
            # duration*improvement(min) <= r{entry} - r{exit} <= duration*improvement(max)
            f" r{s}_entry - r{s}_exit - {progress[1]}*duration_tcm_dv{s} <= 0",
            f"-r{s}_entry + r{s}_exit + {progress[0]}*duration_tcm_dv{s} <= 0",
            # lower bound on trajectory relative distance
            f"-r{s}_exit <= 0",
        ],
    )
    return spec


navigation_variables = ["u", "r"]


def generate_navigation_scenario(
    s: int,
    dsn_noise: tuple[float, float],
    chrg_noise: tuple[float, float],
    sbo_imp: tuple[float, float],
    tcm_dv_noise: tuple[float, float],
    tcm_dv_progress: tuple[float, float],
    rename_outputs: bool = False,
) -> PolyhedralContract:
    global nb_contracts
    nb_contracts += 3  # nochange_contract
    global nb_merge
    nb_merge += 3
    global nb_compose
    nb_compose += 4  # scenario_sequence
    s1 = uncertainty_generating_nav(s=s, noise=dsn_noise)
    s2 = uncertainty_generating_nav(s=s + 1, noise=chrg_noise)
    s3 = SBO_nav_uncertainty(s=s + 2, improvement=sbo_imp).merge(nochange_contract(s=s + 2, name="r"))
    s4 = nochange_contract(s=s + 3, name="u").merge(nochange_contract(s=s + 3, name="r"))
    s5 = TCM_navigation_deltav_uncertainty(s=s + 4, noise=tcm_dv_noise).merge(
        TCM_navigation_deltav_progress(s=s + 4, progress=tcm_dv_progress)
    )

    steps2 = scenario_sequence(c1=s1, c2=s2, variables=navigation_variables, c1index=s)
    steps3 = scenario_sequence(c1=steps2, c2=s3, variables=navigation_variables, c1index=s + 1)
    steps4 = scenario_sequence(c1=steps3, c2=s4, variables=navigation_variables, c1index=s + 2)
    steps5 = scenario_sequence(c1=steps4, c2=s5, variables=navigation_variables, c1index=s + 3)

    if rename_outputs:
        return steps5.rename_variables(
            [
                (f"u{s+3}_exit", f"output_u{s+3}"),
                (f"r{s+3}_exit", f"output_r{s+3}"),
                (f"u{s+4}_exit", f"output_u{s+4}"),
                (f"r{s+4}_exit", f"output_r{s+4}"),
            ]
        )
    else:
        return steps5

tuple2float = tuple[float, float]



def make_range(mean: float, dev: float) -> tuple2float:
    delta = mean * dev
    return (mean - delta, mean + delta)

# def generate_power_scenario_experiment(
#     s: int,
#     dsn_cons: tuple[float, float],
#     chrg_gen: tuple[float, float],
#     sbo_cons: tuple[float, float],
#     tcmh_cons: tuple[float, float],
#     tcmdv_cons: tuple[float, float],
#     rename_outputs: bool = False,
# ) -> PolyhedralContract:
#     global nb_compose
#     nb_compose += 4  # scenario_sequence

#     s1 = power_consumer(s=s, task="dsn", consumption=dsn_cons)
#     s2 = CHRG_power(s=s + 1, generation=chrg_gen)
#     s3 = power_consumer(s=s + 2, task="sbo", consumption=sbo_cons)
#     s4 = power_consumer(s=s + 3, task="tcm_h", consumption=tcmh_cons)
#     s5 = power_consumer(s=s + 4, task="tcm_dv", consumption=tcmdv_cons)

#     steps2 = scenario_sequence(c1=s1, c2=s2, variables=power_variables, c1index=s)
#     steps3 = scenario_sequence(c1=steps2, c2=s3, variables=power_variables, c1index=s + 1)
#     # steps4 = scenario_sequence(c1=steps3, c2=s4, variables=power_variables, c1index=s + 2)
#     # steps5 = scenario_sequence(c1=steps4, c2=s5, variables=power_variables, c1index=s + 3)

#     # if rename_outputs:
#     #     return steps5.rename_variables([(f"soc{s+4}_exit", f"output_soc{s+4}")])
#     # else:
#     #     return steps5

#     write_contracts_to_file(
#         contracts=[steps2, s3, steps3], 
#         names=["dsn_charging", "sbo", "dsn_charging_sbo"],
#         file_name="power_composition_problem.json")
#     return steps3

# def make_power_scenario(
#     s: int, means: np.ndarray, devs: np.ndarray, rename_outputs: bool = False
# ) -> tuple[list[tuple2float], PolyhedralContract]:
#     global nb_merge
#     nb_merge += 2

#     ranges = [make_range(m, d) for (m, d) in zip(means, devs)]
#     scenario_pwr = generate_power_scenario_experiment(
#         s,
#         dsn_cons=ranges[0],
#         chrg_gen=ranges[1],
#         sbo_cons=ranges[2],
#         tcmh_cons=ranges[3],
#         tcmdv_cons=ranges[4],
#         rename_outputs=rename_outputs,
#     )

#     return (ranges, scenario_pwr)

def make_scenario(
    s: int, means: np.ndarray, devs: np.ndarray, rename_outputs: bool = False
) -> tuple[list[tuple2float], PolyhedralContract]:
    global nb_merge
    nb_merge += 2

    ranges = [make_range(m, d) for (m, d) in zip(means, devs)]
    scenario_pwr = generate_power_scenario(
        s,
        dsn_cons=ranges[0],
        chrg_gen=ranges[1],
        sbo_cons=ranges[2],
        tcmh_cons=ranges[3],
        tcmdv_cons=ranges[4],
        rename_outputs=rename_outputs,
    )

    scenario_sci = generate_science_scenario(s, dsn_speed=ranges[5], sbo_gen=ranges[6], rename_outputs=rename_outputs)

    scenario_nav = generate_navigation_scenario(
        s,
        dsn_noise=ranges[7],
        chrg_noise=ranges[8],
        sbo_imp=ranges[9],
        tcm_dv_noise=ranges[10],
        tcm_dv_progress=ranges[11],
        rename_outputs=rename_outputs,
    )

    return (ranges, scenario_pwr.merge(scenario_sci).merge(scenario_nav))

all_variables = power_variables + science_variables + navigation_variables


def long_scenario(means: np.ndarray, devs: np.ndarray) -> tuple[list[tuple2float], PolyhedralContract]:
    global nb_compose
    nb_compose += 3  # scenario_sequence

    ranges, l1 = make_scenario(s=1, means=means, devs=devs, rename_outputs=False)
    _, l2 = make_scenario(s=6, means=means, devs=devs, rename_outputs=False)
    _, l3 = make_scenario(s=11, means=means, devs=devs, rename_outputs=False)
    _, l4 = make_scenario(s=16, means=means, devs=devs, rename_outputs=True)

    l12 = scenario_sequence(c1=l1, c2=l2, variables=all_variables, c1index=5)
    l123 = scenario_sequence(c1=l12, c2=l3, variables=all_variables, c1index=10)
    l1234 = scenario_sequence(c1=l123, c2=l4, variables=all_variables, c1index=15)

    return (ranges, l1234)


