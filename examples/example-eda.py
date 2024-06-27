
from pyeda.inter import *



f = expr("a & b | a & c | b & c | ~a")
fast = f.to_ast()

g = expr("a")


print(f"The variables in f are: {f.inputs}")
print(type(f.inputs))
print(str(f))

f2 = f.consensus(vs=[Variable('a')])