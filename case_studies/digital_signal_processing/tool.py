import copy

DEBUG = True

class PortWordLength(object):
    def __init__(self, n: int = 0, p: int = 0, e: float = 0, a: float = None, name: str = "", value = None):
        self._n = n
        self._p = p
        self._e = e
        self._a = a
        self._name = name
        if value is not None:
            assert(isinstance(value, str))
            assert(len(value) == n)
        self._value = value
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


def get_actual_possible_value(in_port: PortWordLength):
    return (1 - (2 ** -in_port.n) )* 2 ** in_port.p

def compute_required_word_length_add(in1: PortWordLength, in2:PortWordLength) -> PortWordLength:
    new_n = max(in1.n, in2.n - in2.p + in1.p) - min(0, in1.p - in2.p) + 1
    new_p = max(in1.p, in2.p) + 1
    if DEBUG:
        print("Find add length")
        print("in1: ",in1.to_string())
        print("in2: ",in2.to_string())
        print(f"(n*, p*) = ({new_n}, {new_p})")
    return PortWordLength(n=new_n, p=new_p)

def compute_required_word_length_mult(in1: PortWordLength, in2:PortWordLength) -> PortWordLength:
    new_n = in1.n + in2.n
    new_p = in1.p + in2.p
    if DEBUG:
        print("Find add length")
        print("in1: ",in1.to_string())
        print("in2: ",in2.to_string())
        print(f"(n*, p*) = ({new_n}, {new_p})")
    return PortWordLength(n=new_n, p=new_p)

def correct_under_msb_assumption(in_port: PortWordLength, desired_port: PortWordLength) -> PortWordLength:
    p_working = in_port.p
    n_shifted = desired_port.n - desired_port.p + p_working
    return PortWordLength(n=n_shifted, p=p_working)

def get_assumption_bound(in_port_1: PortWordLength, in_port_2: PortWordLength, out_port: PortWordLength, operation_length_fn) -> float:
    """ Return 2^k for the condition "the sum of two inputs does not loss MSB when out_port has less p" """
    p_out = out_port.p
    if isinstance(operation_length_fn, str):
        if operation_length_fn == "add":
            operation_length_fn = compute_required_word_length_add
        elif operation_length_fn == "mult":
            operation_length_fn = compute_required_word_length_mult
    theoretical_out = operation_length_fn(in1=in_port_1, in2=in_port_2)
    if theoretical_out.p > p_out:
        return 2 ** p_out #TODO: this should be less than instead of less than or equal
    else:
        return 0

def shift_theorectical_port_under_assumption(theo_port: PortWordLength, out_port: PortWordLength) -> PortWordLength:
    return PortWordLength(n=theo_port.n - theo_port.p + out_port.p, p=out_port.p)

def get_guarantee_bound(in_port_1: PortWordLength, in_port_2: PortWordLength, out_port: PortWordLength, operation_length_fn) -> float:
    """ Return the error based on the in/out fixed-point length"""
    if isinstance(operation_length_fn, str):
        if operation_length_fn == "add":
            operation_length_fn = compute_required_word_length_add
        elif operation_length_fn == "mult":
            operation_length_fn = compute_required_word_length_mult
    theoretical_out = operation_length_fn(in1=in_port_1, in2=in_port_2)

    if DEBUG:
        print("Theoretical out: ", theoretical_out.to_string() )
    theoretical_out = shift_theorectical_port_under_assumption(theo_port=theoretical_out, out_port=out_port)
    if theoretical_out.n > out_port.n:
        return 2 ** out_port.p * (2 ** (-out_port.n) - 2 ** (-theoretical_out.n))
    else:
        return 0