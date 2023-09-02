
from pacti.terms.polyhedra import PolyhedralIoContract, PolyhedralTermList, PolyhedralTerm
from pacti.iocontract import Var


contract = PolyhedralIoContract.from_strings(
    input_vars=["x"],
    output_vars=["y"],
    assumptions=["x <= 2"],
    guarantees=["2x + 3y <= 7", "2y - 3x <= 8"])
print(contract)

x = Var("x")
y = Var("y")
print(contract.a.contains_behavior({x:5}))
print(contract.a.contains_behavior({x:0}))
print(contract.g.contains_behavior({x:0, y:2}))
print(contract.g.contains_behavior({x:0, y:5}))


# now verify component
t1 = PolyhedralTerm(variables={x:1},constant=3)
t2 = PolyhedralTerm(variables={x:-1},constant=-3)
t3 = PolyhedralTerm(variables={y:1},constant=2)
t4 = PolyhedralTerm(variables={y:-1},constant=-2)
component = PolyhedralTermList([t1,t2,t3,t4])

print(contract.contains_environment(component))
print(contract.contains_implementation(component))