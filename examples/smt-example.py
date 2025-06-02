
import z3

from z3 import *
x = Bool("x")
y = Bool("y")
s = Solver()
s.add(And([x,Not(x)]))
print(type(s.check()))
