

from pacti.contracts import PropositionalIoContract

from pacti.terms.propositions import PropositionalTerm


t = PropositionalTerm("a")



c1 = PropositionalIoContract.from_strings(
    input_vars=['a'], 
    output_vars=['b'], 
    assumptions=['a'], 
    guarantees=['F(b)', "a => ~b"])

c2 = PropositionalIoContract.from_strings(
    input_vars=['b'], 
    output_vars=['c'], 
    assumptions=['F(b)'], 
    guarantees=['c & ~ b'])


c3 = c1.compose(c2)
print(c3)
