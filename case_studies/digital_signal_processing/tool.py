"""Tool.py

The underlying data structure for dsp example
"""

import math

DEBUG = True


class PortWordLength(object):
    """Class PortWordLength

    Serve as the data structure for holding information of a port/signal
    """

    def __init__(self, n: int = 0, p: int = 0, e: float = 0, name: str = "", value: str | None = None):
        """
        Constructor of PortWordLength

        Args:
            n: number of bits of the port
            p: number of bits of the integer parts
            e: known error of the source to this port
            name: name of the port
            value: if not None, the port is a constant with value defined by it
        """
        self._n: int = n  # wordlength
        self._p: int = p  # wordlength
        self._e: float = e  # error known for this port
        self._name: str = name  # name of the port
        if value is not None:
            assert isinstance(value, str)
            assert len(value) == n
        self._value: str | None = value  # actual value for constant port.

    @property
    def n(self) -> int:
        """
        Obtain n from the port

        Returns:
            The number of bits for the port (n)
        """
        return self._n

    @property
    def a(self) -> float:
        """
        Obtain the maximum bounds of the port

        Returns:
            The maximum bounds of the port
        """
        if self._value is None:
            return get_actual_possible_value(self)

        return self.value_num()

    @property
    def p(self) -> int:
        """
        Obtain p of the port

        Returns:
            The number of bits for the integer parts (p)
        """
        return self._p

    @property
    def e(self) -> float:
        """Obtain error of the port

        Returns:
            The error bound of the source to the port
        """
        return self._e

    @e.setter
    def e(self, val: float) -> None:
        """
        Set known source error to the port

        Args:
            e: The known error source to the port
        """
        self._e = val

    @property
    def name(self) -> str:
        """
        Obtain the name of the port

        Returns:
            The name of the port
        """
        return self._name

    @name.setter
    def name(self, val: str) -> None:
        """
        Set name of the port

        Args:
            name: The name of the port
        """
        self._name = val

    @property
    def value(self) -> str | None:
        """
        Obtain the constant value set for the port

        Returns:
            The constant value set for the port
        """
        return self._value

    @value.setter
    def value(self, val: str) -> None:
        """
        Set constant value for the port

        Args:
            value: the constant value to be set for the port
        """
        self._value = val

    def to_string(self) -> str:
        """
        Convert the port to string expression

        Returns:
            The string expression of the port
        """
        return f"Port: {self.name}, (n, p) = ({self.n}, {self.p}), e = {self.e}, a = {self.a}"

    def value_num(self) -> float:
        """
        Convert string constant value to number

        Returns:
            The constant value of the port in floating number
        """
        return float(int(str(self.value), base=2) * 2 ** (-(self.n - self.p)))


def port_add(in1: PortWordLength, in2: PortWordLength, out: PortWordLength) -> None:
    """
    Add the value of in1 and in2 and store it in out

    Args:
        in1: PortWordLength object, one of the two the input ports
        in2: PortWordLength object, one of the two the input ports
        out: PortWordLength object, the output ports
    """
    ideal_result = in1.value_num() + in2.value_num()
    actual_result = float_to_bin(ideal_result, out)
    out.value = actual_result


def port_mult(in1: PortWordLength, in2: PortWordLength, out: PortWordLength) -> None:
    """
    Multiply the value of in1 and in2 and store it in out

    Args:
        in1: PortWordLength object, one of the two the input ports
        in2: PortWordLength object, one of the two the input ports
        out: PortWordLength object, the output ports
    """
    ideal_result = in1.value_num() * in2.value_num()
    actual_result = float_to_bin(ideal_result, out)
    out.value = actual_result


def float_to_bin(x: float, word_length: PortWordLength) -> str:
    """
    Convert float number to binary string

    Args:
        x: the float number to be convert
        word_length: PortWordLength, the port that will hold this float number.

    Returns:
        The string of the value holding the floating point
    """
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
            frac_str += "1"
            frac_part -= 1
        else:
            frac_str += "0"

    return bin_str + frac_str


def get_actual_possible_value(in_port: PortWordLength) -> float:
    """
    Compute the maximum bound based on the port wordlength

    Args:
        in_port: PortWordLength, the port for computing maximum bound.

    Returns:
        The maximum bound given the word length
    """
    return float((1 - (2**-in_port.n)) * 2**in_port.p)
