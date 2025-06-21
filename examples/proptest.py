
from pacti.contracts import PropositionalIoContract
from pacti.iocontract import Var


c1 = PropositionalIoContract.from_strings(
    input_vars=['a', 'x', 'y'], 
    output_vars=['b'], 
    assumptions=['a', 'x & ~y'], 
    guarantees=['F(b)', "a => ~b"])

c2 = PropositionalIoContract.from_strings(
    input_vars=['b'], 
    output_vars=['c'], 
    assumptions=['F(b)'], 
    guarantees=['c & ~ b', 'c'])


c3, G = c1.compose_diagnostics(c2)
print(c3)



for i in [0,1]:
    for j in [0,1]:
        behavior = {Var('b') : i, Var('c') : j}
        print(f"Testing behavior {behavior}")
        print(c2.g.contains_behavior(behavior))


