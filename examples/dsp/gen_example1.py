from tool import *
import json


def form_contract(in_port1, in_port2, out_port, operation):
    ret_contract = {}
    ret_contract["input_vars"] = [f"{in_port1.name}_a", f"{in_port1.name}_e",
                                 f"{in_port2.name}_a", f"{in_port2.name}_e"]
    ret_contract["output_vars"] = [f"{out_port.name}_a", f"{out_port.name}_e"]
    a_bound = get_assumption_bound(in_port_1=in_port1, in_port_2=in_port2, out_port=out_port, operation_length_fn=operation)
    ret_contract["assumptions"] =  [{"coefficients":{f"{in_port1.name}_a":1, f"{in_port2.name}_a":1},
                                   "constant":a_bound}]
    if operation == "add":
        error_bound = get_guarantee_bound(in_port_1=in_port1, in_port_2=in_port2, out_port=out_port, operation_length_fn=operation)
        actual_val_bound = get_actual_possible_value(in_port=out_port)
        ret_contract["guarantees"] =  [{"coefficients":{f"{in_port1.name}_e":-1, f"{in_port2.name}_e":-1, f"{out_port.name}_e": 1},
                                    "constant":error_bound},
                                    {"coefficients":{f"{out_port.name}_a": 1}, "constant":actual_val_bound},
                                    ]
    elif operation == "mult":
        pass

    return ret_contract
    
def write_gear_input(contracts: list, json_path: str):
    input_json = {}
    for i, contract in enumerate(contracts):
        input_json[f"contract{i+1}"] = contract
    input_json["operation"] = "composition"
    with open(json_path, "w") as file:
        json.dump(input_json, file, indent=4, sort_keys=True)


if __name__ == "__main__":
    contracts = []
    p1 = PortWordLength(n=5, p=2, name = "p1")
    p2 = PortWordLength(n=5, p=3, name = "p2")
    p3 = PortWordLength(n=5, p=3, name = "p3")
    c1 = form_contract(in_port1=p1, in_port2=p2, out_port=p3, operation="add")
    contracts.append(c1)
    p4 = PortWordLength(n=7, p=3, name = "p4")
    p5 = PortWordLength(n=6, p=3, name = "p5")
    c2 = form_contract(in_port1=p3, in_port2=p4, out_port=p5, operation="add")
    contracts.append(c2)
    write_gear_input(contracts, "./examples/dsp/example1.json")
    pass #TODO