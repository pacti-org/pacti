from pacti.terms.polyhedra import *

c = PolyhedralContract.from_string(
    input_vars=[
        "x",
        "y",
    ],
    output_vars=["a", "b"],
    assumptions=[
        "x + y <= 0",
    ],
    guarantees=[
        "2x + 2y <= 5",
        "x - y <= 0",
        "| a + b | <= 0",
    ],
)


print(f"c=\n{c}")
