from pacti.contracts import PolyhedralIoContract


def test1_simplified() -> None:
    c = PolyhedralIoContract.from_strings(
        input_vars=["x"], output_vars=[], assumptions=["|x| <= 10"], guarantees=["x <= 100"], simplify=True
    )
    assert 1 == len(c.inputvars)
    assert "x" == c.inputvars[0].name

    assert 0 == len(c.outputvars)
    assert 2 == len(c.a.terms)
    assert 0 == len(c.g.terms)


def test1_not_simplified() -> None:
    c = PolyhedralIoContract.from_strings(
        input_vars=["x"], output_vars=[], assumptions=["|x| <= 10"], guarantees=["x <= 100"], simplify=False
    )
    assert 1 == len(c.inputvars)
    assert "x" == c.inputvars[0].name

    assert 0 == len(c.outputvars)
    assert 2 == len(c.a.terms)
    assert 1 == len(c.g.terms)


if __name__ == "__main__":
    test1_simplified()
    test1_not_simplified()
