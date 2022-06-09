

from numpy import polymul
from ppl import Variable, Constraint_System, C_Polyhedron, Variables_Set
x = Variable(0)
y = Variable(1)
cs = Constraint_System()
cs.insert(2*x >= y)
cs.insert(y >= 1)
#cs.remove_space_dimensions(Variables_Set(1))
poly_from_constraints = C_Polyhedron(cs)
vars = Variables_Set()
vars.insert(x)
poly_from_constraints.remove_higher_space_dimensions(1)
print(poly_from_constraints.minimized_constraints())

C_Polyhedron