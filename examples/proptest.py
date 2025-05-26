

from pacti.contracts import PropositionalIoContract
from pacti.iocontract import Var



c1 = PropositionalIoContract.from_strings(
    input_vars=['a', 'x', 'y'], 
    output_vars=['b'], 
    assumptions=['G(a)', 'G(x & ~y)'], 
    guarantees=['G(F(b))', "G(a => ~b)"])

c2 = PropositionalIoContract.from_strings(
    input_vars=['b'], 
    output_vars=['c'], 
    assumptions=['G(F(b))'], 
    guarantees=['G(c & ~ b)', 'G(c)'])


c3 = c1.compose(c2)
print(c3)



for i in [0,1]:
    for j in [0,1]:
        behavior = {Var('b') : i, Var('c') : j}
        print(f"Testing behavior {behavior}")
        print(c2.g.contains_behavior(behavior))


