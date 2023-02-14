from pacti.terms.polyhedra import *

def test_empty_contract():
  c=PolyhedralContract.from_string(
    InputVars=[],
    OutputVars=[],
    assumptions=[],
    guarantees=[]
  )
  assert 0 == len(c.inputvars)
  assert 0 == len(c.outputvars)
  assert 0 == len(c.a.terms)
  assert 0 == len(c.g.terms)

def test_simple_contract():
  c=PolyhedralContract.from_string(
    InputVars=["x"],
    OutputVars=[],
    assumptions=["-3x <= 0"],
    guarantees=[]
  )
  assert 1 == len(c.inputvars)
  assert "x" == c.inputvars[0].name
  assert 0 == len(c.outputvars)
  assert 1 == len(c.a.terms)

  t0 = c.a.terms[0]
  assert isinstance(t0, PolyhedralTerm)
  p0: PolyhedralTerm = t0
  assert p0.contains_var(c.inputvars[0])
  assert -3.0 == p0.get_coefficient(c.inputvars[0])
  assert 0 == len(c.g.terms)

# | LHS | <= RHS
def test_pattern2_contract():
  c=PolyhedralContract.from_string(
    InputVars=["x"],
    OutputVars=[],
    assumptions=["|x| <= 0"],
    guarantees=[]
  )
  assert 1 == len(c.inputvars)
  assert "x" == c.inputvars[0].name
  assert 0 == len(c.outputvars)
  assert 2 == len(c.a.terms)

  t0 = c.a.terms[0]
  assert isinstance(t0, PolyhedralTerm)
  p0: PolyhedralTerm = t0

  t1 = c.a.terms[1]
  assert isinstance(t1, PolyhedralTerm)
  p1: PolyhedralTerm = t1

  assert p0.contains_var(c.inputvars[0])
  assert 1.0 == p0.get_coefficient(c.inputvars[0])
  assert p1.contains_var(c.inputvars[0])
  assert -1.0 == p1.get_coefficient(c.inputvars[0])

  assert 0 == len(c.g.terms)

# | LHS | = 0
def test_pattern3_contract():
  c=PolyhedralContract.from_string(
    InputVars=["x"],
    OutputVars=[],
    assumptions=["|x| = 0"],
    guarantees=[]
  )
  assert 1 == len(c.inputvars)
  assert "x" == c.inputvars[0].name
  assert 0 == len(c.outputvars)
  assert 2 == len(c.a.terms)

  t0 = c.a.terms[0]
  assert isinstance(t0, PolyhedralTerm)
  p0: PolyhedralTerm = t0

  t1 = c.a.terms[1]
  assert isinstance(t1, PolyhedralTerm)
  p1: PolyhedralTerm = t1

  assert p0.contains_var(c.inputvars[0])
  assert 1.0 == p0.get_coefficient(c.inputvars[0])
  assert p1.contains_var(c.inputvars[0])
  assert -1.0 == p1.get_coefficient(c.inputvars[0])
  
  assert 0 == len(c.g.terms)


# LHS = RHS
def test_pattern4_contract():
  c=PolyhedralContract.from_string(
    InputVars=["x"],
    OutputVars=[],
    assumptions=["x = 1"],
    guarantees=[]
  )
  assert 1 == len(c.inputvars)
  assert "x" == c.inputvars[0].name
  assert 0 == len(c.outputvars)
  assert 2 == len(c.a.terms)
  t0 = c.a.terms[0]
  assert isinstance(t0, PolyhedralTerm)
  p0: PolyhedralTerm = t0

  t1 = c.a.terms[1]
  assert isinstance(t1, PolyhedralTerm)
  p1: PolyhedralTerm = t1

  assert p0.contains_var(c.inputvars[0])
  assert 1.0 == p0.get_coefficient(c.inputvars[0])
  assert 1.0 == p0.constant
  
  assert p1.contains_var(c.inputvars[0])
  assert -1.0 == p1.get_coefficient(c.inputvars[0])
  assert -1.0 == p1.constant
  
  assert 0 == len(c.g.terms)
