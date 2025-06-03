
import z3
from pacti.contracts import SmtIoContract
from pacti.terms.smt import SmtTerm
import copy

i = z3.Real("i")
o = z3.Real("o")
op = z3.Real("op")



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

print(80*"*")
print(f"Composing contract \n{c1}")
print(80*"*")
print(f"with contract \n{c2}")
print(80*"*")
print(f"Result \n{c3}")