
import json
import os
import pacti.terms.polyhedra
from typing import Tuple


def read_contracts_from_file(file_name: str) -> Tuple[list,list[str]]:
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
            pacti.terms.polyhedra.serializer.validate_contract_dict(entry["data"], entry["name"], machine_representation=True)
            contracts.append(pacti.terms.polyhedra.PolyhedralContract.from_dict(entry["data"]))
            names.append(entry["name"])
        elif entry["type"] == "PolyhedralContract":
            pacti.terms.polyhedra.serializer.validate_contract_dict(entry["data"], entry["name"], machine_representation=False)
            contracts.append(pacti.terms.polyhedra.PolyhedralContract.from_string(**entry["data"]))
        else:
            raise ValueError()

    return contracts, names


def write_contracts_to_file(contracts : list, names : list[str], file_name: str, machine_representation: bool = False) -> None:
    data = []
    assert len(contracts) == len(names)
    for i,c in enumerate(contracts):
        entry = {}
        if isinstance(c, pacti.terms.polyhedra.PolyhedralContract):
            entry['name'] = names[i]
            if machine_representation:
                entry['type'] = "PolyhedralContract_machine"
                c_temp = {}
                c_temp['InputVars'] = [str(x) for x in c.inputvars]
                c_temp['OutputVars'] = [str(x) for x in c.outputvars]

                c_temp['assumptions'] = [
                    {"constant": float(term.constant), "coefficients": {str(k): float(v) for k, v in term.variables.items()}}
                    for term in c.a.terms
                ]

                c_temp['guarantees'] = [
                    {"constant": float(term.constant), "coefficients": {str(k): float(v) for k, v in term.variables.items()}}
                    for term in c.g.terms
                ]

                entry['data'] =  c_temp

            else:
                entry['type'] = "PolyhedralContract"
                c_temp = {}
                c_temp['InputVars'] = [str(x) for x in c.inputvars]
                c_temp['OutputVars'] = [str(x) for x in c.outputvars]
                c_temp['assumptions'] = c.a.to_str_list()
                c_temp['guarantees'] = c.g.to_str_list()
                entry['data'] = c_temp
        else:
            assert False
        data.append(entry)

    with open(file_name, "w") as f:
        f.write(json.dumps(data,indent=2))
    
    

