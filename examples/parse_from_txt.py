from pathlib import Path
import os

from pacti.terms.polyhedra import string_to_polyhedra_contract
from pacti.utils.parser import parse_contracts

contract_txt_path = Path(os.path.dirname(__file__)) / "contracts_example.txt"

string_contracts = parse_contracts(contract_txt_path)

io_contracts = []

for c in string_contracts:

    io_contract = string_to_polyhedra_contract(c)

    print(io_contract)
