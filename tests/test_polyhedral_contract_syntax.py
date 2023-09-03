from pacti.contracts import PolyhedralIoContract
from pacti.terms.polyhedra import *


def test_empty_contract() -> None:
    c = PolyhedralIoContract.from_strings(input_vars=[], output_vars=[], assumptions=[], guarantees=[])
    assert 0 == len(c.inputvars)
    assert 0 == len(c.outputvars)
    assert 0 == len(c.a.terms)
    assert 0 == len(c.g.terms)


def test_simple_contract() -> None:
    c = PolyhedralIoContract.from_strings(input_vars=["x"], output_vars=[], assumptions=["-3x <= 0"], guarantees=[])
    assert 1 == len(c.inputvars)
    assert "x" == c.inputvars[0].name
    assert 0 == len(c.outputvars)
    assert 1 == len(c.a.terms)

    t0 = c.a.terms[0]
    assert isinstance(t0, PolyhedralTerm)
    p0 = t0
    assert p0.contains_var(c.inputvars[0])
    assert -3.0 == p0.get_coefficient(c.inputvars[0])
    assert 0 == len(c.g.terms)


# | LHS | <= RHS
def test_pattern2_contract() -> None:
    c = PolyhedralIoContract.from_strings(input_vars=["x"], output_vars=[], assumptions=["|x| <= 0"], guarantees=[])
    assert 1 == len(c.inputvars)
    assert "x" == c.inputvars[0].name
    assert 0 == len(c.outputvars)
    assert 2 == len(c.a.terms)

    t0 = c.a.terms[0]
    assert isinstance(t0, PolyhedralTerm)
    p0 = t0

    t1 = c.a.terms[1]
    assert isinstance(t1, PolyhedralTerm)
    p1 = t1

    assert p0.contains_var(c.inputvars[0])
    assert 1.0 == p0.get_coefficient(c.inputvars[0])
    assert p1.contains_var(c.inputvars[0])
    assert -1.0 == p1.get_coefficient(c.inputvars[0])

    assert 0 == len(c.g.terms)


# | LHS | = 0
def test_pattern3_contract() -> None:
    c = PolyhedralIoContract.from_strings(input_vars=["x"], output_vars=[], assumptions=["|x| <= 10"], guarantees=[])
    assert 1 == len(c.inputvars)
    assert "x" == c.inputvars[0].name
    assert 0 == len(c.outputvars)
    assert 2 == len(c.a.terms)

    t0 = c.a.terms[0]
    assert isinstance(t0, PolyhedralTerm)
    p0 = t0

    t1 = c.a.terms[1]
    assert isinstance(t1, PolyhedralTerm)
    p1 = t1

    assert p0.contains_var(c.inputvars[0])
    assert 1.0 == p0.get_coefficient(c.inputvars[0])
    assert p1.contains_var(c.inputvars[0])
    assert -1.0 == p1.get_coefficient(c.inputvars[0])

    assert 0 == len(c.g.terms)


# LHS = RHS
def test_pattern4_contract() -> None:
    c = PolyhedralIoContract.from_strings(input_vars=["x"], output_vars=[], assumptions=["x = 1"], guarantees=[])
    assert 1 == len(c.inputvars)
    assert "x" == c.inputvars[0].name
    assert 0 == len(c.outputvars)
    assert 2 == len(c.a.terms)
    t0 = c.a.terms[0]
    assert isinstance(t0, PolyhedralTerm)
    p0 = t0

    t1 = c.a.terms[1]
    assert isinstance(t1, PolyhedralTerm)
    p1 = t1

    assert p0.contains_var(c.inputvars[0])
    assert 1.0 == p0.get_coefficient(c.inputvars[0])
    assert 1.0 == p0.constant

    assert p1.contains_var(c.inputvars[0])
    assert -1.0 == p1.get_coefficient(c.inputvars[0])
    assert -1.0 == p1.constant

    assert 0 == len(c.g.terms)


def test_epsilon_contract() -> None:
    c = PolyhedralIoContract.from_strings(
        input_vars=["i"], output_vars=[], assumptions=["|i| <= 1.23456789e-5"], guarantees=[]
    )

    assert 1 == len(c.inputvars)
    assert "i" == c.inputvars[0].name
    assert 0 == len(c.outputvars)
    assert 2 == len(c.a.terms)

    t0 = c.a.terms[0]
    assert isinstance(t0, PolyhedralTerm)
    p0 = t0

    t1 = c.a.terms[1]
    assert isinstance(t1, PolyhedralTerm)
    p1 = t1

    assert p0.contains_var(c.inputvars[0])
    assert 1.0 == p0.get_coefficient(c.inputvars[0])
    assert p1.contains_var(c.inputvars[0])
    assert -1.0 == p1.get_coefficient(c.inputvars[0])

    assert 1.22e-5 < p0.constant
    assert p0.constant < 1.24e-5

    assert 0 == len(c.g.terms)
