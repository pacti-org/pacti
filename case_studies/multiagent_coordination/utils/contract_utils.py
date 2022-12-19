def collision_quadrant_2():

    contract = {
    "InputVars": ["x_A_0", "y_A_0","x_B_0", "y_B_0", "t_0", "current_distance"],
    "OutputVars": ["x_A_1", "y_A_1", "x_B_1", "y_B_1", "t_1"],
    "assumptions": [
    # Assume no collision
    {"constant": -1, "coefficients": {"current_distance": -1}}
    ],
    "guarantees": [
      # collision constraints (for each set of robots)
      {"constant": -1, "coefficients": {"x_A_1": -1, "x_B_1": 1, "y_A_1": -1, "y_B_1": 1}}
     ]

    }
    return contract

def collision_quadrant_3():

    contract = {
    "InputVars": ["x_A_0", "y_A_0","x_B_0", "y_B_0", "t_0", "current_distance"],
    "OutputVars": ["x_A_1", "y_A_1", "x_B_1", "y_B_1", "t_1"],
    "assumptions": [
    # Assume no collision
    {"constant": -1, "coefficients": {"current_distance": -1}}
    ],
    "guarantees": [
      # collision constraints (for each set of robots)
      {"constant": -1, "coefficients": {"x_A_1": 1, "x_B_1": -1, "y_A_1": -1, "y_B_1": 1}}
     ]

    }
    return contract

def collision_quadrant_4():

    contract = {
    "InputVars": ["x_A_0", "y_A_0","x_B_0", "y_B_0", "t_0", "current_distance"],
    "OutputVars": ["x_A_1", "y_A_1", "x_B_1", "y_B_1", "t_1"],
    "assumptions": [
    # Assume no collision
    {"constant": -1, "coefficients": {"current_distance": -1}}
    ],
     "guarantees": [
     # collision constraints (for each set of robots)
     {"constant": -1, "coefficients": {"x_A_1": -1, "x_B_1": 1, "y_A_1": 1, "y_B_1": -1}}
    ]
    }
    return contract
    
