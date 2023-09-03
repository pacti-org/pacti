"""File IO for Pacti."""

import json
import os
from typing import Any, Dict, List, Tuple

from pacti import iocontract
from pacti.contracts import PolyhedralIoContract, PolyhedralIoContractCompound
from pacti.terms import polyhedra


def read_contracts_from_file(  # noqa: WPS231 too much cognitive complexity
    file_name: str,
) -> Tuple[List[iocontract.IoContract], List[str]]:
    """
    Read contracts from a file.

    Args:
        file_name: Name of file to read.

    Raises:
        ValueError: Unsupported contract attempted to be read.

    Returns:
        A list of contracts with the elements of the file.
    """
    if not os.path.isfile(file_name):
        raise ValueError(f"The path {file_name} is not a file.")
    with open(file_name) as f:
        file_data = json.load(f)
    # make sure that data is an array of dictionaries
    assert isinstance(file_data, list)
    for entry in file_data:
        assert isinstance(entry, dict)
        assert "type" in entry
    # we load each contract according to the type
    contracts: List[Any] = []
    names = []
    for entry in file_data:
        if entry["type"] == "PolyhedralIoContract_machine":
            polyhedra.serializer.validate_contract_dict(entry["data"], entry["name"], machine_representation=True)
            contracts.append(PolyhedralIoContract.from_dict(entry["data"]))
            names.append(entry["name"])
        elif entry["type"] == "PolyhedralIoContract":
            polyhedra.serializer.validate_contract_dict(entry["data"], entry["name"], machine_representation=False)
            contracts.append(PolyhedralIoContract.from_strings(**entry["data"]))
            names.append(entry["name"])
        elif entry["type"] == "PolyhedralIoContractCompound":
            contracts.append(PolyhedralIoContractCompound.from_strings(**entry["data"]))
            names.append(entry["name"])
        else:
            raise ValueError()

    return contracts, names


def write_contracts_to_file(  # noqa: WPS231 too much cognitive complexity
    contracts: List[iocontract.IoContract],
    names: List[str],
    file_name: str,
    machine_representation: bool = False,
) -> None:
    """
    Write contracts to a file.

    Args:
        contracts: The contracts to write.
        names: The names of the contracts to keep in written file.
        file_name: Name of file to write.
        machine_representation: Whether the resulting file should be optimized for machine processing.

    Raises:
        ValueError: Unsupported contract type.
    """
    data = []
    assert len(contracts) == len(names)
    for i, c in enumerate(contracts):
        entry: Dict[str, Any] = {}
        if isinstance(c, PolyhedralIoContract):
            entry["name"] = names[i]
            if machine_representation:
                entry["type"] = "PolyhedralIoContract_machine"
                entry["data"] = c.to_machine_dict()

            else:
                entry["type"] = "PolyhedralIoContract"
                entry["data"] = c.to_dict()
        elif isinstance(c, PolyhedralIoContractCompound):
            entry["name"] = names[i]
            if machine_representation:
                raise ValueError("Unsupported representation")
            entry["type"] = "PolyhedralIoContractCompound"
            entry["data"] = c.to_dict()

        else:
            raise ValueError("Unsupported argument type")
        data.append(entry)

    with open(file_name, "w") as f:
        f.write(json.dumps(data, indent=2))
