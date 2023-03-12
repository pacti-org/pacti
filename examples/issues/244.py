
from pacti import read_contracts_from_file

import logging

FORMAT = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
logging.basicConfig(filename="../pacti.log", filemode="w", level=logging.DEBUG, format=FORMAT)

contracts, names = read_contracts_from_file("244.json")

logging.debug("***************************")
c1 = contracts[0]
c2 = contracts[1]
c3 = c1.compose(c2, vars_to_keep=["soc10_exit"])

print(c3.a)