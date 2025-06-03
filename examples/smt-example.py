
import z3

from z3 import *
x = Bool("x")
x_2 = Int("x")
y = Bool("y")
y_2 = Bool("y")
print(f"Expression is {simplify(y & y_2)}")
s = Solver()
s.add(And([x,Not(x)]))
print(type(And([x,Not(x)])))
print(type(s.check()))
print(80*"*")
t = Tactic('qe')
ee = simplify(t(ForAll([x],Implies(x,y)))[0][0])
print(ee)

from pacti.contracts import SmtIoContract
from pacti.terms.smt import SmtTerm
import copy

i = z3.Real("i")
o = z3.Real("o")
op = z3.Real("op")

it = SmtTerm(i <= 2)
print(it)


print(80*"*")
c1 = SmtIoContract.from_z3_terms(
    input_vars=['i'],
    output_vars=['o'],
    assumptions=[i <= 2],
    guarantees=[o == i])


c2 = SmtIoContract.from_z3_terms(
    input_vars=['o'],
    output_vars=['op'],
    assumptions=[o <= 1],
    guarantees=[op == o])

c3 = c1.compose(c2)

print(c3)