from pacti.terms.polyhedra import PolyhedralContract

def collision_quadrant_2():
    contract = PolyhedralContract.from_string(
    InputVars = ["x_A_0", "y_A_0","x_B_0", "y_B_0", "t_0", "current_distance"],
    OutputVars= ["x_A_1", "y_A_1", "x_B_1", "y_B_1", "t_1"]
                 ,
    assumptions=[
      f"-current_distance <= -1",
    ],
    guarantees=[
      f"- x_A_1 + x_B_1 - y_A_1 + y_B_1 <= -1",
    ]
    )
    return contract


def collision_quadrant_3():
    contract = PolyhedralContract.from_string(
    InputVars = ["x_A_0", "y_A_0","x_B_0", "y_B_0", "t_0", "current_distance"],
    OutputVars= ["x_A_1", "y_A_1", "x_B_1", "y_B_1", "t_1"]
                 ,
    assumptions=[
      f"-current_distance <= -1",
    ],
    guarantees=[
      f"x_A_1 - x_B_1 - y_A_1 + y_B_1 <= -1",
    ]
    )
    return contract


def collision_quadrant_4():
    contract = PolyhedralContract.from_string(
    InputVars = ["x_A_0", "y_A_0","x_B_0", "y_B_0", "t_0", "current_distance"],
    OutputVars= ["x_A_1", "y_A_1", "x_B_1", "y_B_1", "t_1"]
                 ,
    assumptions=[
      f"-current_distance <= -1",
    ],
    guarantees=[
      f"- x_A_1 + x_B_1 + y_A_1 - y_B_1 <= -1",
    ]
    )
    return contract
