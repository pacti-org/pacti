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