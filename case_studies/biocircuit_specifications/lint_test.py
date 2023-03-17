from pacti.terms.polyhedra import PolyhedralContract, create_sensor_contracts
import matplotlib.pyplot as plt
from synbio_utils import display_sensor_contracts
import pandas as pd
# Import Python symbolic computation library: sympy
import sympy
# Import utility functions for this case study
from synbio_utils import display_sensor_contracts, remove_quantization_errors
# Import pacti PolyhedralContract parent for operations on guarantees
import pacti.terms.polyhedra as gtp
import numpy as np


def create_top_level_contracts():
    pass

sensor_names = []
df = pd.DataFrame()
sensor_library_params = {}
sensor_library = {}
dCas9_contract_off = None
dCas9_contract_on = None
yleak_atc = 0
yleak_sal = 0
ymax_atc = 0
ymax_sal = 0
leak_RFP = np.max([yleak_atc, yleak_sal])
max_RFP = np.max([ymax_atc, ymax_sal])
input1_params = {}
input2_params = {}


sal_params = {"start":sal_start, "K":sal_K}
atc_params = {"start":atc_start, "K":atc_K}
RFP_params = {"max":max_RFP, "leak":leak_RFP}
ctop_off_off, ctop_on_off, ctop_off_on, ctop_on_on = create_top_level_contracts(
    input1="Sal", input2="aTc", output="RFP",
    input1_params=sal_params, input2_params=atc_params, output_params=RFP_params
    )
