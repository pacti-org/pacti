
from pacti.terms.polyhedra import PolyhedralContract

c1 = PolyhedralContract.from_file("example.json")

print(c1[0])
print(c1[1])
