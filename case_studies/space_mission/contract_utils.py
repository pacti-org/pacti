"""Helper module for the space mission case study."""
from pacti.terms.polyhedra import PolyhedralContract

from pacti import write_contracts_to_file, read_contracts_from_file
from typing import Optional
import json
import uuid
import pathlib

here=pathlib.Path(__file__).parent.resolve()


epsilon = 0

def nochange_contract(s: int, name: str) -> PolyhedralContract:
    """
    Constructs a no-change contract between entry/exit variables derived from the name and step index.

    Args:
        s: step index
        name: name of the variable

    Returns:
        A no-change contract.
    """
    return PolyhedralContract.from_string(
        input_vars=[f"{name}{s}_entry"],
        output_vars=[f"{name}{s}_exit"],
        assumptions=[
            f"-{name}{s}_entry <= 0",
        ],
        guarantees=[
            # f"-{name}{s}_exit <= 0",
            f"| {name}{s}_exit - {name}{s}_entry | <= 0",
            # f"{name}{s}_exit <= 100",
        ],

    )


def scenario_sequence(

    c1: PolyhedralContract, c2: PolyhedralContract, variables: list[str], c1index: int, c2index: Optional[int] = None,
    file_name: Optional[str] = None,

) -> PolyhedralContract:
    """
    Composes c1 with a c2 modified to rename its entry variables according to c1's exit variables

    Args:
        c1: preceding step in the scenario sequence
        c2: next step in the scenario sequence
        variables: list of entry/exit variable names for renaming
        c1index: the step number for c1's variable names
        c2index: the step number for c2's variable names; defaults ti c1index+1 if unspecified

    Returns:
        c1 composed with a c2 modified to rename its c2index-entry variables
        to c1index-exit variables according to the variable name correspondences
        with a post-composition renaming of c1's exit variables to fresh outputs
        according to the variable names.
    """
    if not c2index:
        c2index = c1index + 1
    c2_inputs_to_c1_outputs = [(f"{v}{c2index}_entry", f"{v}{c1index}_exit") for v in variables]
    keep_c1_outputs = [f"{v}{c1index}_exit" for v in variables]
    renamed_c1_outputs = [(f"{v}{c1index}_exit", f"output_{v}{c1index}") for v in variables]

    c2_with_inputs_renamed = c2.rename_variables(c2_inputs_to_c1_outputs)
    # try:
    c12_with_outputs_kept = c1.compose(c2_with_inputs_renamed, vars_to_keep=keep_c1_outputs)
    # except ValueError:
    #     print(keep_c1_outputs)
    #     example=f"{here}/json/example-{uuid.uuid4()}.json"
    #     write_contracts_to_file([c1,c2_with_inputs_renamed],["c1","c2"], example, machine_representation=True)
    #     conts,_ = read_contracts_from_file(example)
    #     print("**********************")
    #     print(c1)
    #     print("**********************")
    #     print(conts[0])
    #     assert c1 == conts[0]
    #     assert c2_with_inputs_renamed == conts[1]
    #     print("Exiting on error")
    #     raise ValueError()

    c12 = c12_with_outputs_kept.rename_variables(renamed_c1_outputs)

    if file_name:
        write_contracts_to_file(
            contracts=[c1, c2_with_inputs_renamed, c12_with_outputs_kept], 
            names=["c1", "c2_with_inputs_renamed", "c12_with_outputs_kept"],
            file_name=file_name)

    return c12


# For converting large images to base64, use: https://www.base64encoder.io/image-to-base64-converter/
# The strings below correspond to "Base64 Encoded String"

# The format for the inline figures as follows:
#
# variable = ""  # noqa: E501


with open(f"{here}/images.json") as f:
    file_data = json.load(f)

figure_space_mission_scenario = file_data["figure_space_mission_scenario"]
figure_space_mission_segments = file_data["figure_space_mission_segments"]
figure_task_schedule_contracts = file_data["figure_task_schedule_contracts"]
pacti_interactive_scenario_plot_concept = file_data["pacti_interactive_scenario_plot_concept"]
