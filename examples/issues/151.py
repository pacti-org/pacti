
from pacti.terms.polyhedra import PolyhedralIoContractCompound
from pacti.iocontract import Var
from pacti import read_contracts_from_file, write_contracts_to_file

c1 = PolyhedralIoContractCompound.from_strings(
    input_vars=["x"],
    output_vars=["y"],
    assumptions=[["x <= 2"], ["-x <= -4"]],
    guarantees=[["y <= 2"], ["-y <= -3"]]
    )

print(c1)

c2 = PolyhedralIoContractCompound.from_strings(
    input_vars=["i"],
    output_vars=["o"],
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

write_contracts_to_file([c1,c2],["c1","c2"], "compound.json")
conts, _ = read_contracts_from_file("compound.json")

print("************")
print(c1)
print(conts[0])

print(c1 == conts[1])