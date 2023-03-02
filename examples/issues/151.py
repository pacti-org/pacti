
from pacti.terms.polyhedra import PolyhedralContractCompound
from pacti.iocontract import Var

c1 = PolyhedralContractCompound.from_string(
    InputVars=["x"],
    OutputVars=["y"],
    assumptions=[["x <= 2"], ["-x <= -4"]],
    guarantees=[["y <= 2"], ["-y <= -3"]]
    )

print(c1)

c2 = PolyhedralContractCompound.from_string(
    InputVars=["i"],
    OutputVars=["o"],
    assumptions=[["i <= 5"], ["-i <= -7"]],
    guarantees=[["o - i <= 2"], ["i - o <= -3"], ["i <= 5"]]
    )

print(c2)

c_merge = c1.merge(c2)
print(c_merge)

print(c1.g.contains_behavior({Var("x"):3, Var("y"):0}))
print(c1.g.contains_behavior({Var("x"):3, Var("y"):2.5}))
print(c1.a.contains_behavior({Var("x"):5, Var("y"):0}))
print(c1.a.contains_behavior({Var("x"):3, Var("y"):2.5}))
