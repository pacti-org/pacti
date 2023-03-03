import json
import os
from typing import Tuple

import pacti.terms.polyhedra


def read_contracts_from_file(file_name: str) -> Tuple[list[pacti.terms.polyhedra.PolyhedralContract], list[str]]:
    if not os.path.isfile(file_name):
        raise Exception(f"The path {file_name} is not a file.")
    with open(file_name) as f:
        file_data = json.load(f)
    # make sure that data is an array of dictionaries
    assert isinstance(file_data, list)
    for entry in file_data:
        assert isinstance(entry, dict)
        assert "type" in entry
    # we load each contract according to the type
    contracts = []
    names = []
    for entry in file_data:
        if entry["type"] == "PolyhedralContract_machine":
            pacti.terms.polyhedra.serializer.validate_contract_dict(
                entry["data"], entry["name"], machine_representation=True
            )
            contracts.append(pacti.terms.polyhedra.PolyhedralContract.from_dict(entry["data"]))
            names.append(entry["name"])
        elif entry["type"] == "PolyhedralContract":
            pacti.terms.polyhedra.serializer.validate_contract_dict(
                entry["data"], entry["name"], machine_representation=False
            )
            contracts.append(pacti.terms.polyhedra.PolyhedralContract.from_string(**entry["data"]))
        else:
            raise ValueError()

    return contracts, names


def write_contracts_to_file(
    contracts: list[pacti.terms.polyhedra.PolyhedralContract],
    names: list[str],
    file_name: str,
    machine_representation: bool = False,
) -> None:
    data = []
    assert len(contracts) == len(names)
    for i, c in enumerate(contracts):
        entry = {}
        if isinstance(c, pacti.terms.polyhedra.PolyhedralContract):
            entry["name"] = names[i]
            if machine_representation:
                entry["type"] = "PolyhedralContract_machine"
                entry["data"] = c.to_machine_dict()

            else:
                entry["type"] = "PolyhedralContract"
                entry["data"] = c.to_dict()
        else:
            assert False
        data.append(entry)

    with open(file_name, "w") as f:
        f.write(json.dumps(data, indent=2))
