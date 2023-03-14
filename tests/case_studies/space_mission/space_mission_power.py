# ---
# jupyter:
#   jupytext:
#     formats: case_studies///ipynb,tests/case_studies///py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.14.4
#   kernelspec:
#     display_name: .venv
#     language: python
#     name: python3
# ---

# %%
# %matplotlib widget

#from IPython import display
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

varPrefixes=["t", "soc", "d", "c", "u", "r", "temp"]
epsilon = 1e-3


# %% [markdown]
# ## Power viewpoint modeling
#
# ### CHARGING Task
#
# Objective: charge the spacecraft battery
#
# As summarized in [the qualitative impacts table](#qualitative-impacts), this function affects this viewpoint with impacts that are linear with the duration of the task:
# - the battery charges proportionally to a generation rate.

# %%
# Parameters:
# - s: start index of the timeline variables
# - generation: (min, max) rate of battery charge during the task instance
# - epsilon: approximately zero
def CHARGING_power(s: int, generation: tuple[float, float], epsilon: float) -> PolyhedralContract:
  spec = PolyhedralContract.from_string(
    input_vars = [
      f"soc{s}_entry",          # initial battery SOC
      f"duration_charging{s}",  # variable task duration
    ],
    output_vars = [
      f"soc{s}_exit",           # final battery SOC
    ],
    assumptions = [
      # Task has a positive scheduled duration
      f"-duration_charging{s} <= 0",

      # Battery SOC must be positive
      f"-soc{s}_entry <= 0",
    ],
    guarantees = [
      # duration*generation(min) <= soc{exit} - soc{entry} <= duration*generation(max)
      f" soc{s}_exit - soc{s}_entry - {generation[1]}*duration_charging{s} <= 0",
      f"-soc{s}_exit + soc{s}_entry + {generation[0]}*duration_charging{s} <= 0",

      # Battery cannot exceed maximum SOC
      f"soc{s}_exit <= 100.0",
      
      # Battery should not completely discharge
      f"-soc{s}_exit <= 0",
    ])
  return spec

charging1_power = CHARGING_power(s=2, generation=(3.0, 4.0), epsilon=epsilon)
print(f"Contract charging1_power:\n\n{charging1_power}")

_ = plot_guarantees(contract=charging1_power,
                x_var=Var("duration_charging2"),
                y_var=Var("soc2_exit"),
                var_values={
                  Var("soc2_entry"):42,
                },
                x_lims=(0,100),
                y_lims=(0,100))


# %% [markdown]
# ### Power-consuming Tasks (DSN, SBO, TCM)

# %%
# Parameters:
# - s: start index of the timeline variables
# - consumption: (min, max) rate of battery discharge during the task instance
def power_consumer(s: int, task: str, consumption: tuple[float, float]) -> PolyhedralContract:
  spec = PolyhedralContract.from_string(
    input_vars = [
      f"soc{s}_entry",          # initial battery SOC
      f"duration_{task}{s}",    # variable task duration
    ],
    output_vars = [
      f"soc{s}_exit",           # final battery SOC
    ],
    assumptions = [
      # Task has a positive scheduled duration
      f"-duration_{task}{s} <= 0",

      # Battery has enough energy for worst-case consumption throughout the task instance
      f"-soc{s}_entry + {consumption[1]}*duration_{task}{s} <= 0",
    ],
    guarantees = [
      # duration*consumption(min) <= soc{entry} - soc{exit} <= duration*consumption(max)
      f" soc{s}_entry - soc{s}_exit - {consumption[1]}*duration_{task}{s} <= 0",
      f"-soc{s}_entry + soc{s}_exit + {consumption[0]}*duration_{task}{s} <= 0",

      # Battery cannot exceed maximum SOC
      f"soc{s}_exit <= 100.0",
      
      # Battery should not completely discharge
      f"-soc{s}_exit <= 0",
    ])
  return spec


# %% [markdown]
# ### DSN Task
#
# Objective: downlink science data to Earth.
#
# As summarized in [the qualitative impacts table](#qualitative-impacts), this function affects this viewpoint with impacts that are linear with the duration of the task:
# - the battery discharges proportionally to a consumption rate.
#

# %%
dsn1_power = power_consumer(s=1, task="dsn", consumption=(3.8, 4.2))
print(f"Contract dsn1_power:\n\n{dsn1_power}")

_ = plot_guarantees(contract=dsn1_power,
                x_var=Var("duration_dsn1"),
                y_var=Var("soc1_exit"),
                var_values={
                  Var("soc1_entry"):80,
                },
                x_lims=(0,20),
                y_lims=(0,80))

# %% [markdown]
# ### SBO Task (Small body observations)
#
# Objective: Acquire small body observations (science data & navigation)
#
# As summarized in [the qualitative impacts table](#qualitative-impacts), this function affects this viewpoint with impacts that are linear with the duration of the task:
# - the battery discharges proportionally to a consumption rate.

# %%
sbo1_power = power_consumer(s=3, task="sbo", consumption=(1.0, 1.4))
print(f"Contract sbo1_power:\n\n{sbo1_power}")

_ = plot_guarantees(contract=sbo1_power,
                x_var=Var("duration_sbo3"),
                y_var=Var("soc3_exit"),
                var_values={
                  Var("soc3_entry"):80,
                },
                x_lims=(0,100),
                y_lims=(0,100))

# %% [markdown]
# ### TCM Task (Perform a Trajectory Correction Maneuver)
#
# Objective: Perform a delta-V maneuver to bring the spacecraft trajectory closer to that of the small body.
#
# As summarized in [the qualitative impacts table](#qualitative-impacts), this function affects this viewpoint with impacts that are linear with the duration of the task:
# - Power: the thrusters must be heated before firing them, thereby discharging the battery proportionally to a consumption rate.
#
# Since heating the thruster must happen just before firing them, this task is modeled as the composition of two subtasks: Heating and DeltaV.
#
# #### TCM Heating SubTask
#

# %%
tcm1_heating_power = power_consumer(s=4, task="tcm_heating", consumption=(0.7, 0.8))
print(f"Contract tcm1_heating_power:\n\n{tcm1_heating_power}")

_ = plot_guarantees(contract=tcm1_heating_power,
                x_var=Var("duration_tcm_heating4"),
                y_var=Var("soc4_exit"),
                var_values={
                  Var("soc4_entry"):80,
                },
                x_lims=(0,100),
                y_lims=(0,100))

# %% [markdown]
# #### TCM DeltaV SubTask
#

# %%
tcm1_deltav_power = power_consumer(s=5, task="tcm_deltav", consumption=(0.5, 0.6))
print(f"Contract tcm1_deltav_power:\n\n{tcm1_deltav_power}")

_ = plot_guarantees(contract=tcm1_deltav_power,
                x_var=Var("duration_tcm_deltav5"),
                y_var=Var("soc5_exit"),
                var_values={
                  Var("soc5_entry"):80,
                },
                x_lims=(0,100),
                y_lims=(0,100))

# %% [markdown]
# #### Composing TCM SubTasks
#
# Algebraic composition allows us to capture the requirement that a TCM Heating subtask must always precede a TCM DeltaV subtask by composing them.

# %%
tcm1_power=scenario_sequence(c1=tcm1_heating_power, c2=tcm1_deltav_power, variables=["soc"], c1index=4)
print(f"========= tcm1_power\n{tcm1_power}")
tcm1_power.get_variable_bounds("soc5_exit")

# %% [markdown]
# ### Power Schedule Analysis
#
# Let's consider a simple 4-step schedule of the following sequence of task instances, which we compose:
# - DSN
# - CHARGING
# - SBO
# - TCM

# %%
steps12=scenario_sequence(c1=dsn1_power, c2=charging1_power, variables=["soc"], c1index=1)
print(f"---- Steps 1,2\n{steps12}")
steps12.get_variable_bounds("output_soc1")

# %%
steps123=scenario_sequence(c1=steps12, c2=sbo1_power, variables=["soc"], c1index=2)
print(f"---- Steps 1,2,3\n{steps123}")
print(steps123.get_variable_bounds("soc3_exit"))
print(steps123.get_variable_bounds("duration_dsn1"))
print(steps123.get_variable_bounds("duration_charging2"))
print(steps123.get_variable_bounds("duration_sbo3"))

# %%
steps1234=scenario_sequence(c1=steps123, c2=tcm1_power, variables=["soc"], c1index=3)
print(f"---- Steps 1,2,3,4\n{steps1234}")
print(steps1234.get_variable_bounds("duration_dsn1"))
print(steps1234.get_variable_bounds("duration_charging2"))
print(steps1234.get_variable_bounds("duration_sbo3"))
print(steps1234.get_variable_bounds("duration_tcm_heating4"))
print(steps1234.get_variable_bounds("duration_tcm_deltav5"))

# %% [markdown]
# #### Power Schedule constraints

# %%
scenario_power=steps1234.rename_variables([("soc5_exit", "output_soc5")])
print(f"scenario_power={scenario_power}")

# %% tags=["remove_cell"]
write_contracts_to_file(contracts=[scenario_power], names=["scenario_power"], file_name="json/scenario_power.json")
