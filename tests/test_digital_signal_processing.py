from pacti.terms.polyhedra import PolyhedralContract


####################################################
#Copy from tool.py in case_studies
import copy
import math

DEBUG = True

class PortWordLength(object):
    def __init__(self, n: int = 0, p: int = 0, e: float = 0, a: float = None, name: str = "", value = None):
        self._n = n # wordlength
        self._p = p # wordlength
        self._e = e # error known for this port
        self._a = a # maximum possible value for this port
        self._name = name # name of the port
        if value is not None:
            assert(isinstance(value, str))
            assert(len(value) == n)
        self._value = value # actual value for constant port.
    @property
    def n(self):
        return self._n

    @property
    def a(self):
        if self._value is None:
            return get_actual_possible_value(self)
        else:
            return self.value_num()
    
    @property
    def p(self):
        return self._p

    @property
    def e(self):
        return self._e
    
    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    def set_value(self, value: str):
        self._value = value

    def set_e(self, e: float):
        self._e = e

    def set_a(self, a: float):
        self._a = a

    def set_name(self, name: str):
        self._name = name

    def to_string(self):
        return f"Port: {self.name}, (n, p) = ({self.n}, {self.p}), e = {self.e}, a = {self.a}"

    def value_num(self):
        return int(self.value, base=2) * 2 ** (- (self.n - self.p))


def port_add(in1, in2, out):
    ideal_result = in1.value_num() + in2.value_num()
    actual_result = float_to_bin(ideal_result, out)
    out.set_value(actual_result)

def port_mult(in1, in2, out):
    ideal_result = in1.value_num() * in2.value_num()
    actual_result = float_to_bin(ideal_result, out)
    out.set_value(actual_result)

def float_to_bin(x, word_length: PortWordLength):
    frac_part, int_part = math.modf(x)
    p = word_length.p
    # get integer part
    if int_part == 0:
        bin_str = ""
    else:
        bin_str = bin(int(int_part))[2:]
        if len(bin_str) > p:
            print("The port unable to hold the number, significant bits lost")
        else:
            bin_str = bin_str.zfill(p)
    # get fractional part
    frac_str = ""
    req_length = word_length.n - word_length.p
    while len(frac_str) != req_length:
        frac_part *= 2
        if frac_part >= 1:
            frac_str += '1'
            frac_part -= 1
        else:
            frac_str += '0'

    return bin_str + frac_str


def get_actual_possible_value(in_port: PortWordLength):
    return (1 - (2 ** -in_port.n) )* 2 ** in_port.p
########################################################################################
#### Copy from Jupyter Notebook
def truncation_error_same_position(pi, po):
    assert(pi.p == po.p)
    if pi.n > po.n:
        return 2 ** po.p * (2 ** (-po.n) - 2 ** (-pi.n))
    else :
        return 0

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

def compute_required_word_length_add(in1: PortWordLength, in2:PortWordLength) -> PortWordLength:
    new_n = max(in1.n, in2.n - in2.p + in1.p) - min(0, in1.p - in2.p) + 1
    new_p = max(in1.p, in2.p) + 1
    return PortWordLength(n=new_n, p=new_p)

def compute_required_word_length_mult(in1: PortWordLength, in2:PortWordLength) -> PortWordLength:
    new_n = in1.n + in2.n
    new_p = in1.p + in2.p
    return PortWordLength(n=new_n, p=new_p)


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
    if assumption_value != float("inf"):
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
                                #{"coefficients":{f"{out_port.name}_a": 1}, "constant":in_port1.a + in_port2.a},
                                {"coefficients":{f"{out_port.name}_a": 1, f"{in_port1.name}_a": -1, f"{in_port2.name}_a": -1}, "constant":0}
                                ]
    return ret_contract


def form_contract_mult_const(in_port1, in_port_const, out_port):
    ret_contract = {}
    # define input/output vars
    ret_contract["InputVars"] = [f"{in_port1.name}_a", f"{in_port1.name}_e"]
    ret_contract["OutputVars"] = [f"{out_port.name}_a", f"{out_port.name}_e"]
    # get assumption
    ideal_out_port = compute_required_word_length_mult(in1=in_port1, in2=in_port_const)
    assumption_value = get_assumption_value(pi=ideal_out_port, po=out_port)
    # write assumption in the contract
    if assumption_value != float("inf"):
        print(assumption_value)
        ret_contract["assumptions"] =  [{"coefficients":{f"{in_port1.name}_a": in_port_const.a},
                                    "constant":assumption_value}]
    else:
        ret_contract["assumptions"] = []
    # get guarantee
    print(ideal_out_port.to_string())
    e_t = truncation_error(pi=ideal_out_port, po=out_port)

    # write guarantee in the contract, note the propagation is encoded in the polyhedral constraints
    ret_contract["guarantees"] =  [{"coefficients":
                                    {   f"{in_port1.name}_e":-in_port_const.a+in_port_const.e, 
                                        f"{in_port1.name}_a":-in_port_const.e,
                                        f"{out_port.name}_e": 1},
                                    "constant":e_t},
                                    {"coefficients":{f"{out_port.name}_a": 1}, "constant":out_port.a},
                                    #{"coefficients":{f"{out_port.name}_a": 1}, "constant":in_port_const.a * in_port1.a},
                                    {"coefficients":{f"{out_port.name}_a": 1, f"{in_port1.name}_a": -in_port_const.a}, "constant":0}
                                    ]
    return ret_contract

def form_contract_input(in_port):
    ret_contract = {}
    # define input/output vars
    ret_contract["InputVars"] = []
    ret_contract["OutputVars"] = [f"{in_port.name}_a", f"{in_port.name}_e"]
    # get assumption
    ret_contract["assumptions"] = []
    ret_contract["guarantees"] =  [ {"coefficients": {f"{in_port.name}_a": 1}, "constant": in_port.a},
                                    {"coefficients": {f"{in_port.name}_a": -1}, "constant": 0},
                                    {"coefficients": {f"{in_port.name}_e": 1}, "constant": in_port.e},
                                    {"coefficients": {f"{in_port.name}_e": -1}, "constant": -in_port.e}]
    return ret_contract


def test_example1_catch_error():
    p1 = PortWordLength(n=5, p=2, name = "p1")
    p2 = PortWordLength(n=5, p=3, name = "p2")
    p3 = PortWordLength(n=5, p=3, name = "p3")
    c1 = form_contract_add(in_port1=p1, in_port2=p2, out_port=p3)

    p4 = PortWordLength(n=7, p=3, name = "p4")
    p5 = PortWordLength(n=6, p=3, name = "p5")
    c2 = form_contract_add(in_port1=p3, in_port2=p4, out_port=p5)

    contract1 = PolyhedralContract.from_dict(c1)
    contract2 = PolyhedralContract.from_dict(c2)

    contract_sys = contract1.compose(contract2)

    c_p1 = form_contract_input(in_port=p1)
    c_p2 = form_contract_input(in_port=p2)
    c_p4 = form_contract_input(in_port=p4)

    contract_p1 = PolyhedralContract.from_dict(c_p1)
    contract_p2 = PolyhedralContract.from_dict(c_p2)
    contract_p4 = PolyhedralContract.from_dict(c_p4)
    
    catch_error = False
    try: 
        contract_sys = contract1.compose(contract2)
        contract_sys = contract_p1.compose(contract_sys)
        contract_sys = contract_p2.compose(contract_sys)
        contract_sys = contract_p4.compose(contract_sys)
        print("Contract Sys:\n" + str(contract_sys))
        return contract_sys
    except ValueError as e:
        print("Composition Error")
        catch_error = True
        print(e)

    assert(catch_error)


def test_example1_pass_with_inputs():
    p1 = PortWordLength(n=5, p=2, name = "p1")
    p2 = PortWordLength(n=5, p=3, name = "p2")
    p3 = PortWordLength(n=5, p=3, name = "p3")
    c1 = form_contract_add(in_port1=p1, in_port2=p2, out_port=p3)

    p4 = PortWordLength(n=7, p=3, name = "p4")
    p5 = PortWordLength(n=6, p=3, name = "p5")
    c2 = form_contract_add(in_port1=p3, in_port2=p4, out_port=p5)

    contract1 = PolyhedralContract.from_dict(c1)
    contract2 = PolyhedralContract.from_dict(c2)

    contract_sys = contract1.compose(contract2)

    p1.set_value("10000")
    p2.set_value("01111")
    p4.set_value("0000001")

    c_p1 = form_contract_input(in_port=p1)
    c_p2 = form_contract_input(in_port=p2)
    c_p4 = form_contract_input(in_port=p4)

    contract_p1 = PolyhedralContract.from_dict(c_p1)
    contract_p2 = PolyhedralContract.from_dict(c_p2)
    contract_p4 = PolyhedralContract.from_dict(c_p4)
    
    no_error = True
    try: 
        contract_sys = contract1.compose(contract2)
        contract_sys = contract_p1.compose(contract_sys)
        contract_sys = contract_p2.compose(contract_sys)
        contract_sys = contract_p4.compose(contract_sys)
        print("Contract Sys:\n" + str(contract_sys))
        return contract_sys
    except ValueError as e:
        print("Composition Error")
        no_error = False
        print(e)

    assert(no_error)


def get_optimization_specs():
    p1 = PortWordLength(n=5, p=2, name = "p1")
    p2 = PortWordLength(n=5, p=3, name = "p2")
    p4 = PortWordLength(n=7, p=3, name = "p4")

    p1.set_value("10000")
    p2.set_value("01111")
    p4.set_value("0000000")

    ret_contract = {}
    ret_contract["InputVars"] = []
    ret_contract["OutputVars"] = ["p5_a", "p5_e"]
    ret_contract["assumptions"] = []
    ret_contract["guarantees"] = [
                                  {"coefficients": {f"p5_e": 1}, "constant": 0.1}]
    contract_spec = PolyhedralContract.from_dict(ret_contract)

    c_p1 = form_contract_input(in_port=p1)
    c_p2 = form_contract_input(in_port=p2)
    c_p4 = form_contract_input(in_port=p4)

    contract_p1 = PolyhedralContract.from_dict(c_p1)
    contract_p2 = PolyhedralContract.from_dict(c_p2)
    contract_p4 = PolyhedralContract.from_dict(c_p4)

    tmp_c1 = contract_spec.quotient(contract_p1)

    tmp_c2 = tmp_c1.quotient(contract_p2)
    tmp_c3 = tmp_c2.quotient(contract_p4)
    quotient_ret = tmp_c3
    return quotient_ret, contract_spec

def create_example1_by_p3(p3_n, p3_p):
    p1 = PortWordLength(n=5, p=2, name = "p1")
    p2 = PortWordLength(n=5, p=3, name = "p2")
    p3 = PortWordLength(n=p3_n, p=p3_p, name = "p3")
    c1 = form_contract_add(in_port1=p1, in_port2=p2, out_port=p3)

    p4 = PortWordLength(n=7, p=3, name = "p4")
    p5 = PortWordLength(n=6, p=3, name = "p5")
    c2 = form_contract_add(in_port1=p3, in_port2=p4, out_port=p5)

    p1.set_value("10000")
    p2.set_value("01111")
    p4.set_value("0000000")

    contract1 = PolyhedralContract.from_dict(c1)
    contract2 = PolyhedralContract.from_dict(c2)
    return contract1, contract2, p1, p2, p3, p4, p5

def test_optimization():
    quotient_ret, contract_specs = get_optimization_specs()
    ret = None
    for n in range(5, 10):
        #print(n)
        p = 3 # keep the same number of bits (2) before binary point
        contract1, contract2, p1, p2, p3, p4, p5 = create_example1_by_p3(p3_n=n, p3_p=p)
        try:
            contract_sys = contract1.compose(contract2)
            #contract_sys = compose_all(contract1, contract2, p1, p2, p3, p4, p5)
            #print(str(contract_sys))
        except ValueError as e:
            continue

        if contract_sys.refines(quotient_ret):
            ret = n
            break

    assert(ret == 6)

def test_example_2():
    in1 = PortWordLength(n=6, p=0, e=0, name="in1")
    in2 = PortWordLength(n=6, p=0, e=0, name="in2")
    in3 = PortWordLength(n=6, p=0, e=0, name="in3")
    const1 = PortWordLength(n=6, p=0, name="const1")
    const2 = PortWordLength(n=6, p=0, name="const2")
    const3 = PortWordLength(n=6, p=0, name="const3")
    mult_out1 = PortWordLength(n=6, p=0, name="mult_out1")
    mult_out2 = PortWordLength(n=6, p=0, name="mult_out2")
    mult_out3 = PortWordLength(n=6, p=0, name="mult_out3")
    add_out1 = PortWordLength(n=6, p=0, name="add_out1")
    add_out2 = PortWordLength(n=6, p=0, name="add_out2")

    const1.set_value(float_to_bin(0.2, const1))
    const2.set_value(float_to_bin(0.6, const2))
    const3.set_value(float_to_bin(0.2, const3))
    const1.set_e(0.2 - const1.value_num())
    const2.set_e(0.6 - const2.value_num())
    const3.set_e(0.2 - const3.value_num())

    print(f"truncated coefficient: 0.2 to {const1.value_num()}")
    print(f"truncated coefficient: 0.6 to {const2.value_num()}")
    print(f"truncated coefficient: 0.2 to {const3.value_num()}")

    c1 = form_contract_mult_const(in_port1=in1, in_port_const=const1, out_port=mult_out1)
    c2 = form_contract_mult_const(in_port1=in2, in_port_const=const2, out_port=mult_out2)
    c3 = form_contract_mult_const(in_port1=in3, in_port_const=const3, out_port=mult_out3)

    ci1 = form_contract_input(in_port=in1)
    ci2 = form_contract_input(in_port=in2)
    ci3 = form_contract_input(in_port=in3)

    contract1 = PolyhedralContract.from_dict(c1)
    contract2 = PolyhedralContract.from_dict(c2)
    contract3 = PolyhedralContract.from_dict(c3)
    contract_i1 = PolyhedralContract.from_dict(ci1)
    contract_i2 = PolyhedralContract.from_dict(ci2)
    contract_i3 = PolyhedralContract.from_dict(ci3)
    c4 = form_contract_add(in_port1 = mult_out1, in_port2=mult_out2, out_port=add_out1)
    c5 = form_contract_add(in_port1 = add_out1, in_port2=mult_out3, out_port=add_out2)
    contract4 = PolyhedralContract.from_dict(c4)
    contract5 = PolyhedralContract.from_dict(c5)

    contract_system = contract_i1.compose(contract1)
    contract_system = contract_system.compose(contract_i2)
    contract_system = contract_system.compose(contract2)
    contract_system = contract_system.compose(contract_i3)
    contract_system = contract_system.compose(contract3)
    contract_system = contract_system.compose(contract4)
    contract_system = contract_system.compose(contract5)

    # TODO check result of contract 