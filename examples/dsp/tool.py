

class PortWordLength(object):
    def __init__(self, n: int = 0, p: int = 0):
        self._n = n
        self._p = p
    @property
    def n(self):
        return self._n
    
    @property
    def p(self):
        return self._p



def compute_required_word_length_add(in1: PortWordLength, in2:PortWordLength) -> PortWordLength:
    new_n = max(in1.n, in2.n - in2.p + in1.p) + min(0, in1.p - in2.p) + 1
    new_p = max(in1.p, in2.p) + 1
    return PortWordLength(n=new_n, p=new_p)

def correct_under_msb_assumption(in_port: PortWordLength, desired_port: PortWordLength) -> PortWordLength:
    p_working = in_port.p
    n_shifted = desired_port.n - desired_port.p + p_working
    return PortWordLength(n=n_shifted, p=p_working)

def get_assumption_bound(in_port_1: PortWordLength, in_port_2: PortWordLength, out_port: PortWordLength):
    pass #TODO