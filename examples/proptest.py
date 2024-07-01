

from pacti.contracts import PropositionalIoContract




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


c3 = c1.compose(c2)
print(c3)
