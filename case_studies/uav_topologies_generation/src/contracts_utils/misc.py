from pacti.iocontract import IoContract


def get_equalized_alphabets(c1: IoContract, c2: IoContract) -> tuple[IoContract, IoContract]:
    input_int = set(c1.inputvars) | set(c2.inputvars)
    output_uni = set(c1.outputvars) | set(c2.outputvars)

    c1_mod = IoContract(input_vars=list(input_int), assumptions=c1.a, output_vars=list(output_uni), guarantees=c1.g)

    c2_mod = IoContract(input_vars=list(input_int), assumptions=c2.a, output_vars=list(output_uni), guarantees=c2.g)

    return c1_mod, c2_mod


def get_equalized_abstracted_contracts(c1: IoContract, c2: IoContract) -> tuple[IoContract, IoContract]:
    """
    It takes computes the intersection input variables of c1 and c2 (i.e. 'input_int') and
     the union of the output variables 'output_uni'. It then modifies c1 and c2 by:
        * Keeping only the assumptions that refer to variables in 'input_int;
        * Extending the guarantees to all the variables in 'output_uni'

    """

    input_int = set(c1.inputvars) & set(c2.inputvars)
    output_uni = set(c1.outputvars) | set(c2.outputvars)

    new_a1 = c1.a.get_terms_with_vars(list(input_int))
    new_a2 = c2.a.get_terms_with_vars(list(input_int))

    c1_mod = IoContract(input_vars=list(input_int), assumptions=new_a1, output_vars=list(output_uni), guarantees=c1.g)

    c2_mod = IoContract(input_vars=list(input_int), assumptions=new_a2, output_vars=list(output_uni), guarantees=c2.g)

    return c1_mod, c2_mod
