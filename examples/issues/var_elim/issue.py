


from pacti import read_contracts_from_file
from pacti.iocontract import Var
import logging

FORMAT = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
logging.basicConfig(filename="../pacti.log", filemode="w", level=logging.DEBUG, format=FORMAT)

conts, _ = read_contracts_from_file("var_elim.json")

result, _ = conts[0].compose(conts[1], vars_to_keep=[Var('d2_exit'), Var('c2_exit')])

print(result)