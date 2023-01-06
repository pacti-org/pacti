from gear.terms.polyhedra.loaders import readContract, writeContract
from tool import PortWordLength
import numpy as np

def truncation_error_same_position(pi, po):
    assert(pi.p == po.p)
    if pi.n > po.n:
        return 2 ** po.p * (2 ** (-po.n) - 2 ** (-pi.n))
    else :
        return 0

def truncate(pi, po):
    # separate the bits into two parts, before binary point and after binary point
    bits_before_point = pi.value[:pi.p]
    bits_after_point = pi.value[pi.p:]
    
    # truncate or appending 0 
    if po.p >= pi.p:
        bits_before_point = ("0" * (po.p - pi.p)) + bits_before_point
    else:
        bits_before_point = bits_before_point[pi.p - po.p:]

    if po.n - po.p >= pi.n - pi.p:
        bits_after_point = bits_after_point + "0" * (po.n - po.p - pi.n + pi.p)
    else:
        bits_after_point = bits_after_point[:(po.n - po.p)]

    # combine the both parts
    ret = bits_before_point + bits_after_point
    po.set_value(value = ret)
    return po.value

def truncation_error(pi, po):
    # remove uneccesary most significant bits
    # Remider: The assumption must hold!!
    pi_adjusted = PortWordLength(n=pi.n - pi.p + po.p, p=po.p)
    # return the truncation error as in case 1
    return truncation_error_same_position(pi=pi_adjusted, po=po)

def get_assumption_value(pi, po):
    if pi.p > po.p:
        return 2 ** po.p
    else:
        return float("inf") # no additional assumption needed

def check_assumption_value(pi, po):
    assumption_value = get_assumption_value(pi, po)
    print(f"Assumption: {pi.name} < {assumption_value}")
    if not pi.value_num() < assumption_value:
        print("Assumption failed, truncation of MSB occurs")
        return False
    else:
        print(f"Assumption Satisfied ({pi.name} = {pi.value_num()} < {assumption_value})")
        return True
        
def compute_required_word_length_add(in1: PortWordLength, in2:PortWordLength) -> PortWordLength:
    new_n = max(in1.n, in2.n - in2.p + in1.p) - min(0, in1.p - in2.p) + 1
    new_p = max(in1.p, in2.p) + 1
    return PortWordLength(n=new_n, p=new_p)

def error_truncation_add(p1, p2, po):
    print(f"Input {p1.name}: (n={p1.n}, p={p1.p})")
    print(f"Input {p2.name}: (n={p2.n}, p={p2.p})")
    p_ideal = compute_required_word_length_add(in1=p1, in2=p2)
    print(f"Ideal Output: (n={p_ideal.n}, p={p_ideal.p})")
    print(f"Actual Output ({po.name}): (n={po.n}, p={po.p})")

    assumption_value = get_assumption_value(pi=p_ideal, po=po)
    print(f"Assumption: {p1.name} + {p2.name} < {assumption_value}")
    return truncation_error(pi=p_ideal, po=po)
    
def compute_required_word_length_mult(in1: PortWordLength, in2:PortWordLength) -> PortWordLength:
    new_n = in1.n + in2.n
    new_p = in1.p + in2.p
    return PortWordLength(n=new_n, p=new_p)

def error_truncation_mult(p1, p2, po):
    print(f"Input {p1.name}: (n={p1.n}, p={p1.p})")
    print(f"Input {p2.name}: (n={p2.n}, p={p2.p})")
    p_ideal = compute_required_word_length_mult(in1=p1, in2=p2)
    print(f"Ideal Output: (n={p_ideal.n}, p={p_ideal.p})")
    print(f"Actual Output ({po.name}): (n={po.n}, p={po.p})")

    assumption_value = get_assumption_value(pi=p_ideal, po=po)
    print(f"Assumption: {p1.name} * {p2.name} < {assumption_value}")
    return truncation_error(pi=p_ideal, po=po)

def error_propagation_add(p1, p2, po):
    return p1.e + p2.e

def get_actual_possible_value(in_port: PortWordLength):
    return (1 - (2 ** -in_port.n) )* 2 ** in_port.p

def error_propagation_mult(p1, p2, po):
    return p1.a * p2.e + p2.a * p1.e + p1.e * p2.e



def form_contract_add(in_port1, in_port2, out_port):
    ret_contract = {}
    # define input/output vars
    ret_contract["InputVars"] = [f"{in_port1.name}_a", f"{in_port1.name}_e",
                                 f"{in_port2.name}_a", f"{in_port2.name}_e"]
    ret_contract["OutputVars"] = [f"{out_port.name}_a", f"{out_port.name}_e"]
    # get assumption
    ideal_out_port = compute_required_word_length_add(in1=in_port1, in2=in_port2)
    assumption_value = get_assumption_value(pi=ideal_out_port, po=out_port)
    # write assumption in the contract
    if assumption_value is not float("inf"):
        ret_contract["assumptions"] =  [{"coefficients":{f"{in_port1.name}_a":1, f"{in_port2.name}_a":1},
                                    "constant":assumption_value}]
    else:
        ret_contract["assumptions"] = []
    # get guarantee
    e_t = truncation_error(pi=ideal_out_port, po=out_port)

    # write guarantee in the contract, note the propagation is encoded in the polyhedral constraints
    ret_contract["guarantees"] =  [{"coefficients":{f"{in_port1.name}_e":-1, f"{in_port2.name}_e":-1, f"{out_port.name}_e": 1},
                                "constant":e_t},
                                {"coefficients":{f"{out_port.name}_a": 1}, "constant":out_port.a},
                                {"coefficients":{f"{out_port.name}_a": 1}, "constant":in_port1.a + in_port2.a},
                                {"coefficients":{f"{out_port.name}_a": 1, f"{in_port1.name}_a": -1, f"{in_port2.name}_a": -1}, "constant":0}
                                ]
    return ret_contract


def form_contract_mult_const(in_port1, in_port_const, out_port):
    ret_contract = {}
    # define input/output vars
    ret_contract["InputVars"] = [f"{in_port1.name}_a", f"{in_port1.name}_e"]
    ret_contract["OutputVars"] = [f"{out_port.name}_a", f"{out_port.name}_e"]
    # get assumption
    ideal_out_port = compute_required_word_length_add(in1=in_port1, in2=in_port_const)
    assumption_value = get_assumption_value(pi=ideal_out_port, po=out_port)
    # write assumption in the contract
    if assumption_value is not float("inf"):
        ret_contract["assumptions"] =  [{"coefficients":{f"{in_port1.name}_a": in_port_const.a},
                                    "constant":assumption_value}]
    else:
        ret_contract["assumptions"] = []
    # get guarantee
    e_t = truncation_error(pi=ideal_out_port, po=out_port)

    # write guarantee in the contract, note the propagation is encoded in the polyhedral constraints
    ret_contract["guarantees"] =  [{"coefficients":
                                    {   f"{in_port1.name}_e":-in_port_const.a-in_port_const.e, 
                                        f"{in_port1.name}_a":-in_port_const.e,
                                        f"{out_port.name}_e": 1},
                                    "constant":e_t},
                                    {"coefficients":{f"{out_port.name}_a": 1}, "constant":out_port.a},
                                    {"coefficients":{f"{out_port.name}_a": 1}, "constant":in_port_const.a * in_port1.a},
                                    {"coefficients":{f"{out_port.name}_a": 1, f"{in_port1.name}_a": -in_port_const.a}, "constant":0}
                                    ]
    return ret_contract

p1 = PortWordLength(n=7, p=3, name="p1")
p2 = PortWordLength(n=5, p=2, name="p2")
p3 = PortWordLength(n=5, p=3, name="p3")
c1 = form_contract_add(in_port1=p1, in_port2=p2, out_port=p3)
print(c1)
contract1 = readContract(c1)
print(str(contract1))


# p4 = PortWordLength(n=7, p=3, name="p4")
# p5 = PortWordLength(n=5, p=2, e=0.03, value="11011", name="p5") # const
# p6 = PortWordLength(n=5, p=3, name="p6")
# c2 = form_contract_mult_const(in_port1=p4, in_port_const=p5, out_port=p6)
# contract2 = readContract(c2)
# print(str(contract2))

# exp
# exp
c1 = {'InputVars': [], 
'OutputVars': ['t1', 't2'], 
'assumptions': [], 
'guarantees': [ {'coefficients': {'t1': 1}, 'constant': 0.1}, 
                {'coefficients': {'t1': -1}, 'constant': 0.},
                {'coefficients': {'t2': 1}, 'constant': 0.2}, 
                {'coefficients': {'t2': -1}, 'constant': 0.}
              ]}

c2 = {'InputVars': ['t1', 't2'], 
'OutputVars': ['o1'], 
'assumptions': [], 
'guarantees': [{'coefficients': {'o1': 1, 't1': 1, 't2':-1}, 'constant': 10}]}

contract1 = readContract(c1)
contract2 = readContract(c2)
system = contract1.compose(contract2)
print(str(system))
