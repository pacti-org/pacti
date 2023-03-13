from pacti.terms.polyhedra import *


def test_empty_contract() -> None:
    c = PolyhedralContract.from_string(input_vars=[], output_vars=[], assumptions=[], guarantees=[])
    assert 0 == len(c.inputvars)
    assert 0 == len(c.outputvars)
    assert 0 == len(c.a.terms)
    assert 0 == len(c.g.terms)


def test_simple_contract_a() -> None:
    c = PolyhedralContract.from_string(input_vars=["x"], output_vars=[], assumptions=["-3x <= 0"], guarantees=[])
    assert 1 == len(c.inputvars)
    assert "x" == c.inputvars[0].name
    assert 0 == len(c.outputvars)
    assert 1 == len(c.a.terms)

    t0 = c.a.terms[0]
    assert isinstance(t0, PolyhedralTerm)
    p0 = t0
    assert p0.contains_var(c.inputvars[0])
    assert -3.0 == p0.get_coefficient(c.inputvars[0])
    assert p0.pacti_id[1] == "Rule1a"

    assert 0 == len(c.g.terms)


def test_simple_contract_g() -> None:
    c = PolyhedralContract.from_string(input_vars=[], output_vars=["x"], assumptions=[], guarantees=["-3x <= 0"])
    assert 0 == len(c.inputvars)
    assert 1 == len(c.outputvars)
    assert "x" == c.outputvars[0].name
    assert 0 == len(c.a.terms)

    assert 1 == len(c.g.terms)

    t0 = c.g.terms[0]
    assert isinstance(t0, PolyhedralTerm)
    p0 = t0
    assert p0.contains_var(c.outputvars[0])
    assert -3.0 == p0.get_coefficient(c.outputvars[0])
    assert p0.pacti_id[1] == "Rule1a"


# | LHS | <= RHS
def test_pattern2_contract_a() -> None:
    c = PolyhedralContract.from_string(input_vars=["x"], output_vars=[], assumptions=["|x| <= 0"], guarantees=[])
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
    assert p0.pacti_id[1] == "Rule2a.left"

    assert p1.contains_var(c.inputvars[0])
    assert -1.0 == p1.get_coefficient(c.inputvars[0])
    assert p1.pacti_id[1] == "Rule2a.right"

    assert p0.pacti_id[0] == p1.pacti_id[0]

    assert 0 == len(c.g.terms)


def test_pattern2_contract_g() -> None:
    c = PolyhedralContract.from_string(input_vars=[], output_vars=["x"], assumptions=[], guarantees=["|x| <= 0"])
    assert 0 == len(c.inputvars)
    assert 1 == len(c.outputvars)
    assert "x" == c.outputvars[0].name

    assert 0 == len(c.a.terms)
    assert 2 == len(c.g.terms)

    t0 = c.g.terms[0]
    assert isinstance(t0, PolyhedralTerm)
    p0 = t0

    t1 = c.g.terms[1]
    assert isinstance(t1, PolyhedralTerm)
    p1 = t1

    assert p0.contains_var(c.outputvars[0])
    assert 1.0 == p0.get_coefficient(c.outputvars[0])
    assert p0.pacti_id[1] == "Rule2a.left"

    assert p1.contains_var(c.outputvars[0])
    assert -1.0 == p1.get_coefficient(c.outputvars[0])
    assert p1.pacti_id[1] == "Rule2a.right"

    assert p0.pacti_id[0] == p1.pacti_id[0]


# | LHS | = 0
def test_pattern3_contract_a() -> None:
    c = PolyhedralContract.from_string(input_vars=["x"], output_vars=[], assumptions=["|x| = 0"], guarantees=[])
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
    assert p0.pacti_id[1] == "Rule2b.left"

    assert p1.contains_var(c.inputvars[0])
    assert -1.0 == p1.get_coefficient(c.inputvars[0])
    assert p1.pacti_id[1] == "Rule2b.right"

    assert p0.pacti_id[0] == p1.pacti_id[0]

    assert 0 == len(c.g.terms)


def test_pattern3_contract_g() -> None:
    c = PolyhedralContract.from_string(input_vars=[], output_vars=["x"], assumptions=[], guarantees=["|x| = 0"])
    assert 0 == len(c.inputvars)
    assert 1 == len(c.outputvars)
    assert "x" == c.outputvars[0].name

    assert 0 == len(c.a.terms)
    assert 2 == len(c.g.terms)

    t0 = c.g.terms[0]
    assert isinstance(t0, PolyhedralTerm)
    p0 = t0

    t1 = c.g.terms[1]
    assert isinstance(t1, PolyhedralTerm)
    p1 = t1

    assert p0.contains_var(c.outputvars[0])
    assert 1.0 == p0.get_coefficient(c.outputvars[0])
    assert p0.pacti_id[1] == "Rule2b.left"

    assert p1.contains_var(c.outputvars[0])
    assert -1.0 == p1.get_coefficient(c.outputvars[0])
    assert p1.pacti_id[1] == "Rule2b.right"

    assert p0.pacti_id[0] == p1.pacti_id[0]


# LHS = RHS
def test_pattern4_contract_a() -> None:
    c = PolyhedralContract.from_string(input_vars=["x"], output_vars=[], assumptions=["x = 1"], guarantees=[])
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
    assert p0.pacti_id[1] == "Rule3a.left"

    assert p1.contains_var(c.inputvars[0])
    assert -1.0 == p1.get_coefficient(c.inputvars[0])
    assert -1.0 == p1.constant
    assert p1.pacti_id[1] == "Rule3a.right"

    assert p0.pacti_id[0] == p1.pacti_id[0]

    assert 0 == len(c.g.terms)


def test_pattern4_contract_g() -> None:
    c = PolyhedralContract.from_string(input_vars=[], output_vars=["x"], assumptions=[], guarantees=["x = 1"])
    assert 0 == len(c.inputvars)
    assert 1 == len(c.outputvars)
    assert "x" == c.outputvars[0].name

    assert 0 == len(c.a.terms)
    assert 2 == len(c.g.terms)
    t0 = c.g.terms[0]
    assert isinstance(t0, PolyhedralTerm)
    p0 = t0

    t1 = c.g.terms[1]
    assert isinstance(t1, PolyhedralTerm)
    p1 = t1

    assert p0.contains_var(c.outputvars[0])
    assert 1.0 == p0.get_coefficient(c.outputvars[0])
    assert 1.0 == p0.constant
    assert p0.pacti_id[1] == "Rule3a.left"

    assert p1.contains_var(c.outputvars[0])
    assert -1.0 == p1.get_coefficient(c.outputvars[0])
    assert -1.0 == p1.constant
    assert p1.pacti_id[1] == "Rule3a.right"

    assert p0.pacti_id[0] == p1.pacti_id[0]


def test_simplified_guarantee() -> None:
    c = PolyhedralContract.from_string(
        input_vars=[
            "x",
            "y",
        ],
        output_vars=["a", "b"],
        assumptions=[
            "x + y <= 0",
        ],
        guarantees=[
            "2x + 2y <= 5", # will be eliminated by simplification
            "x - y <= 0",
            "| a + b | <= 0",
        ],
    )
    assert 2 == len(c.inputvars)
    assert "x" == c.inputvars[0].name
    assert "y" == c.inputvars[1].name

    assert 2 == len(c.outputvars)
    assert "a" == c.outputvars[0].name
    assert "b" == c.outputvars[1].name

    assert 1 == len(c.a.terms)
    t0 = c.a.terms[0]
    assert isinstance(t0, PolyhedralTerm)
    p0 = t0

    assert p0.contains_var(c.inputvars[0])
    assert p0.contains_var(c.inputvars[1])
    assert 1.0 == p0.get_coefficient(c.inputvars[0])
    assert 1.0 == p0.get_coefficient(c.inputvars[1])
    assert 0.0 == p0.constant
    assert p0.pacti_id[1] == "Rule1a"

    assert 3 == len(c.g.terms)
    t1 = c.g.terms[0]
    assert isinstance(t1, PolyhedralTerm)
    p1 = t1
    assert p1.pacti_id[1] == "Rule1a"

    t2a = c.g.terms[1]
    assert isinstance(t2a, PolyhedralTerm)
    p2a = t2a
    
    t2b = c.g.terms[2]
    assert isinstance(t2b, PolyhedralTerm)
    p2b = t2b
    
    assert p2b.pacti_id[0] == p2b.pacti_id[0]
    assert p2a.pacti_id[1] == "Rule2a.left"
    assert p2b.pacti_id[1] == "Rule2a.right"
