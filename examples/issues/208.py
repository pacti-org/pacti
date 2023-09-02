from pacti.contracts import PolyhedralIoContract

import logging

FORMAT = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
logging.basicConfig(filename="../pacti.log", filemode="w", level=logging.DEBUG, format=FORMAT)

c1 = PolyhedralIoContract.from_dict(
    {"InputVars": ["soc1_entry", "duration_dsn1", "duration_pwr2"], "OutputVars": ["soc2_exit", "output_soc1"], "assumptions": [{"constant": 0.0, "coefficients": {"duration_pwr2": -1.0}}, {"constant": 0.0, "coefficients": {"duration_dsn1": -1.0}}, {"constant": 0.0, "coefficients": {"duration_dsn1": 4.2, "soc1_entry": -1.0}}], "guarantees": [{"constant": 0.0, "coefficients": {"soc1_entry": 1.0, "duration_dsn1": -4.2, "output_soc1": -1.0}}, {"constant": 0.0, "coefficients": {"soc1_entry": -1.0, "duration_dsn1": 3.8, "output_soc1": 1.0}}, {"constant": 0.0, "coefficients": {"output_soc1": -1.0, "soc2_exit": 1.0, "duration_pwr2": -4.0}}, {"constant": 0.0, "coefficients": {"output_soc1": 1.0, "soc2_exit": -1.0, "duration_pwr2": 3.0}}, {"constant": 100.0, "coefficients": {"soc2_exit": 1.0}}]}
)

c2 = PolyhedralIoContract.from_dict(
    {"InputVars": ["duration_sbo3", "soc2_exit"], "OutputVars": ["soc3_exit"], "assumptions": [{"constant": 0.0, "coefficients": {"duration_sbo3": -1.0}}, {"constant": 0.0, "coefficients": {"duration_sbo3": 1.4, "soc2_exit": -1.0}}], "guarantees": [{"constant": 0.0, "coefficients": {"soc3_exit": -1.0, "duration_sbo3": -1.4, "soc2_exit": 1.0}}, {"constant": 0.0, "coefficients": {"soc3_exit": 1.0, "duration_sbo3": 1.0, "soc2_exit": -1.0}}, {"constant": 100.0, "coefficients": {"soc3_exit": 1.0}}]}
)

print(c1.compose(c2))
