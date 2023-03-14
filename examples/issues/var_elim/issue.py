


from pacti import read_contracts_from_file
import logging

FORMAT = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
logging.basicConfig(filename="../pacti.log", filemode="w", level=logging.DEBUG, format=FORMAT)

conts, _ = read_contracts_from_file("var_elim.json")

result = conts[0].compose(conts[1])
