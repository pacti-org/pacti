import time
import joblib
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

from generators import *

parallelism=True
run5=True
run20=True

# Now, let's apply the Latin hypercube generator to sample the scenario hyperparameters.
from scipy.stats import qmc

d = 12
n5 = 200
n20 = 200
#n20 = 100
#n20 = 50

mean_sampler = qmc.LatinHypercube(d=d)
mean_sample5: np.ndarray = mean_sampler.random(n=n5)
mean_sample20: np.ndarray = mean_sampler.random(n=n20)
l_bounds = [
    2.0,  # power: min dns cons
    4.0,  # power: min chrg gen
    0.3,  # power: min sbo cons
    0.2,  # power: min tcm_h cons
    0.1,  # power: min tcm_dv cons
    5.0,  # science: min dsn speed
    2.0,  # science: min sbo gen
    1.0,  # nav: min dsn noise
    1.0,  # nav: min chrg noise
    0.3,  # nav: min sbo imp
    1.2,  # nav: min tcm_dv noise
    0.3,  # nav: min tcm_dv progress
]
u_bounds = [
    2.2,  # power: max dns cons
    4.5,  # power: max chrg gen
    0.4,  # power: max sbo cons
    0.3,  # power: max tcm_h cons
    0.2,  # power: max tcm_dv cons
    6.0,  # science: max dsn speed
    10.0,  # science: max sbo gen
    1.2,  # nav: max dsn noise
    1.2,  # nav: max chrg noise
    0.8,  # nav: max sbo imp
    1.4,  # nav: max tcm_dv noise
    0.5,  # nav: max tcm_dv progress
]
scaled_mean_sample5: np.ndarray = qmc.scale(sample=mean_sample5, l_bounds=l_bounds, u_bounds=u_bounds)
scaled_mean_sample20: np.ndarray = qmc.scale(sample=mean_sample20, l_bounds=l_bounds, u_bounds=u_bounds)

o5 = 20
o20 = 20
dev_sampler = qmc.LatinHypercube(d=d)
dev_sample5: np.ndarray = dev_sampler.random(n=o5)
dev_sample20: np.ndarray = dev_sampler.random(n=o20)

tuple2float = tuple[float, float]

nb_contracts5 = 23
nb_compose5 = 12
nb_merge5 = 10



nb_contracts20 = 115
nb_compose20 = 63
nb_merge20 = 50


m = 300
#m = 30
op_sampler: qmc.LatinHypercube = qmc.LatinHypercube(d=5)
op_sample: np.ndarray = op_sampler.random(n=m)
op_l_bounds = [
    # 60.0,  # power: low range of initial soc
    80.0,  # power: low range of initial soc
    10.0,  # power: low range of exit soc at each step
    5.0,  # alloc: low range of delta t
    60.0,  # sci: low range of d
    40.0,  # nav: low range of u
]
op_u_bounds = [
    # 90.0,  # power: high range of initial soc
    95.0,  # power: high range of initial soc
    # 50.0,  # power: low range of exit soc at each step
    30.0,  # power: low range of exit soc at each step
    200.0,  # alloc: high range of delta t
    100.0,  # sci: high range of  d
    90.0,  # nav: high range of  u
]
scaled_op_sample: np.ndarray = qmc.scale(sample=op_sample, l_bounds=op_l_bounds, u_bounds=op_u_bounds)


def make_op_requirements5(reqs: np.ndarray) -> PolyhedralContract:
    return PolyhedralContract.from_string(
        input_vars=[
            "duration_dsn1",
            "duration_charging2",
            "duration_sbo3",
            "duration_tcm_h4",
            "duration_tcm_dv5",
            "soc1_entry",
            "c1_entry",
            "d1_entry",
            "u1_entry",
            "r1_entry",
        ],
        output_vars=[f"output_soc{i}" for i in range(1, 6)],
        assumptions=[
            f"soc1_entry={reqs[0]}",
            f"-duration_dsn1 <= -{reqs[2]}",
            f"-duration_charging2 <= -{reqs[2]}",
            f"-duration_sbo3 <= -{reqs[2]}",
            f"-duration_tcm_h4 <= -{reqs[2]}",
            f"-duration_tcm_dv5 <= -{reqs[2]}",
            "c1_entry=0",
            f"d1_entry={reqs[3]}",
            f"u1_entry={reqs[4]}",
            "r1_entry=100",
        ],
        guarantees=[f"-output_soc{i} <= -{reqs[1]}" for i in range(1, 6)],
    )


tuple2 = Tuple[Optional[numeric], Optional[numeric]]


def check_tuple(t: tuple2) -> tuple2:
    if t[0] is None:
        a = -1
    else:
        a = t[0]
    if t[1] is None:
        b = -1
    else:
        b = t[1]
    return (a, b)


def schedulability_analysis5(scenario: tuple[list[tuple2float], PolyhedralContract], reqs: np.ndarray):
    op_req = make_op_requirements5(reqs)
    fsoc = " + ".join([f"0.05 output_soc{i}" for i in range(1, 6)])
    try:
        c = scenario[1].merge(op_req)
        max_soc = c.optimize(fsoc, maximize=True)
        if max_soc is None:
            max_soc = -1

        min_soc = c.optimize(fsoc, maximize=False)
        if min_soc is None:
            min_soc = -1

        u = check_tuple(c.get_variable_bounds("output_u5"))
        r = check_tuple(c.get_variable_bounds("output_r5"))
        c = check_tuple(c.get_variable_bounds("output_c5"))

        return (scenario[0], reqs, scenario[1], op_req, min_soc, max_soc, u, r, c)
    except ValueError:
        return None


import itertools
import pickle

if run5:
    t0a = time.time()
    if parallelism:
        scenarios5: Optional[list[tuple[list[tuple2float], PolyhedralContract]]] = joblib.Parallel(n_jobs=joblib.cpu_count())(
            joblib.delayed(make_scenario)(1, mean, dev, True) for mean, dev in zip(scaled_mean_sample5, dev_sample5)
        )
    else:
        scenarios5: list[tuple[list[tuple2float], PolyhedralContract]] = [make_scenario(1, mean, dev, True) for mean, dev in zip(scaled_mean_sample5, dev_sample5)]
    t1a = time.time()

    print(f"All {n5} hyperparameter variations of the 5-step scenario sequence generated in {t1a-t0a} seconds.")
    print(
        f"Total count of Pacti operations: {nb_contracts5} contracts; {nb_merge5} merges; and {nb_compose5} compositions."
    )

    t2a = time.time()
    if parallelism:
        all_results5: Optional[list[tuple[list[tuple2float], PolyhedralContract]]] = joblib.Parallel(n_jobs=joblib.cpu_count())(
            joblib.delayed(schedulability_analysis5)(scenario, req) for scenario in scenarios5 for req in scaled_op_sample
        )
    else:
        all_results5: list[tuple[list[tuple2float], PolyhedralContract]] = [schedulability_analysis5(scenario, req) for scenario in scenarios5 for req in scaled_op_sample]
    t3a = time.time()
    results5 = [x for x in all_results5 if x is not None]
    print(
        f"Found {len(results5)} admissible schedules out of {m*n5} combinations generated from {m} variations of operational requirements for each of the {n5} scenarios.\nTotal time {t3a-t2a} seconds."
    )

    f5 = open("case_studies/space_mission/data/results5.data", "wb")
    pickle.dump(results5, f5)
    f5.close()


def make_op_requirements20(reqs: np.ndarray) -> PolyhedralContract:
    return PolyhedralContract.from_string(
        input_vars=[
            "duration_dsn1",
            "duration_charging2",
            "duration_sbo3",
            "duration_tcm_h4",
            "duration_tcm_dv5",
            "duration_dsn6",
            "duration_charging7",
            "duration_sbo8",
            "duration_tcm_h9",
            "duration_tcm_dv10",
            "duration_dsn11",
            "duration_charging12",
            "duration_sbo13",
            "duration_tcm_h14",
            "duration_tcm_dv15",
            "duration_dsn16",
            "duration_charging17",
            "duration_sbo18",
            "duration_tcm_h19",
            "duration_tcm_dv20",
            "soc1_entry",
            "c1_entry",
            "d1_entry",
            "u1_entry",
            "r1_entry",
        ],
        output_vars=[f"output_soc{i}" for i in range(1, 21)],
        assumptions=[
            f"-duration_dsn1 <= -{reqs[2]}",
            f"-duration_charging2 <= -{reqs[2]}",
            f"-duration_sbo3 <= -{reqs[2]}",
            f"-duration_tcm_h4 <= -{reqs[2]}",
            f"-duration_tcm_dv5 <= -{reqs[2]}",
            f"-duration_dsn6 <= -{reqs[2]}",
            f"-duration_charging7 <= -{reqs[2]}",
            f"-duration_sbo8 <= -{reqs[2]}",
            f"-duration_tcm_h9 <= -{reqs[2]}",
            f"-duration_tcm_dv10 <= -{reqs[2]}",
            f"-duration_dsn11 <= -{reqs[2]}",
            f"-duration_charging12 <= -{reqs[2]}",
            f"-duration_sbo13 <= -{reqs[2]}",
            f"-duration_tcm_h14 <= -{reqs[2]}",
            f"-duration_tcm_dv15 <= -{reqs[2]}",
            f"-duration_dsn16 <= -{reqs[2]}",
            f"-duration_charging17 <= -{reqs[2]}",
            f"-duration_sbo18 <= -{reqs[2]}",
            f"-duration_tcm_h19 <= -{reqs[2]}",
            f"-duration_tcm_dv20 <= -{reqs[2]}",
            f"soc1_entry={reqs[0]}",
            "c1_entry=0",
            f"d1_entry={reqs[2]}",
            f"u1_entry={reqs[3]}",
            "r1_entry=100",
        ],
        guarantees=[f"-output_soc{i} <= -{reqs[1]}" for i in range(1, 21)],
    )


def schedulability_analysis20(scenario: tuple[list[tuple2float], PolyhedralContract], reqs: np.ndarray):
    op_req = make_op_requirements20(reqs)
    fsoc = " + ".join([f"0.05 output_soc{i}" for i in range(1, 21)])
    try:
        c = scenario[1].merge(op_req)
        max_soc = c.optimize(fsoc, maximize=True)
        if max_soc is None:
            max_soc = -1

        min_soc = c.optimize(fsoc, maximize=False)
        if min_soc is None:
            min_soc = -1

        u = check_tuple(c.get_variable_bounds("output_u20"))
        r = check_tuple(c.get_variable_bounds("output_r20"))
        c = check_tuple(c.get_variable_bounds("output_c20"))
        return (scenario[0], reqs, scenario[1], op_req, min_soc, max_soc, u, r, c)
    except ValueError:
        return None

if run20:
    t0b = time.time()
    if parallelism:
        scenarios20: Optional[list[tuple[list[tuple2float], PolyhedralContract]]] = joblib.Parallel(n_jobs=joblib.cpu_count())(
            joblib.delayed(long_scenario)(mean, dev) for mean, dev in zip(scaled_mean_sample20, dev_sample20)
        )
    else:
        scenarios20: list[tuple[list[tuple2float], PolyhedralContract]] = [long_scenario(mean, dev) for mean, dev in zip(scaled_mean_sample20, dev_sample20)]
    t1b = time.time()
    print(f"All {n20} hyperparameter variations of the 20-step scenario sequence generated.\nTotal time {t1b-t0b} seconds using a maximum of {joblib.cpu_count()} concurrent jobs.")
    print(
        f"Total count of Pacti operations: {nb_contracts20} contracts; {nb_merge20} merges; and {nb_compose20} compositions."
    )

    t2b = time.time()
    if parallelism:
        all_results20 = joblib.Parallel(n_jobs=joblib.cpu_count())(
            joblib.delayed(schedulability_analysis20)(scenario, req) for scenario in scenarios20 for req in scaled_op_sample
        )
    else:
        all_results20 = [schedulability_analysis20(scenario, req) for scenario in scenarios20 for req in scaled_op_sample]
    t3b = time.time()
    results20 = [x for x in all_results20 if x is not None]
    print(
        f"Found {len(results20)} admissible schedules out of {m*n20} combinations generated from {m} variations of operational requirements for each of the {n20} scenarios.\nTotal time {t3b-t2b} seconds using a maximum of {joblib.cpu_count()} concurrent jobs."
    )

    f20 = open("case_studies/space_mission/data/results20.data", "wb")
    pickle.dump(results20, f20)
    f20.close()
