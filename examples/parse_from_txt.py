from pathlib import Path
import os

from gear.utils.parser import parse_contracts
from gear.utils.polyhedra_contracts import create_polyhedrea_contarct

contract_txt_path = Path(os.path.dirname(__file__)) / "contracts_example.txt"

string_contracts = parse_contracts(contract_txt_path)

io_contracts = []

for c in string_contracts:

    io_contract = create_polyhedrea_contarct(c)

    print(io_contract)
