import unittest
import pyparsing as pp
from pacti.terms.polyhedra.grammar import terms, Term, TermList


class TestTermList(unittest.TestCase):
    def test_parse1(self) -> None:
        t0 = pp.ParseResults(TermList(constant=4.0, factors={"x": 1.0, "y": 2.0, "z": -3.0}))
        t1 = terms.parse_string("x+2y-3z+4", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)
        self.assertTrue(isinstance(t1[0], TermList))
        self.assertTrue(t1[0].is_positive())

    def test_parse2(self) -> None:
        t0 = pp.ParseResults(TermList(constant=4.0, factors={"x": 1.0, "y": 2.0, "z": -3.0}))
        t1 = terms.parse_string("1+x+1+3y-2z+2-y-z", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)
        self.assertTrue(isinstance(t1[0], TermList))
        self.assertTrue(t1[0].is_positive())

    def test_combine1(self) -> None:
        tl1 = TermList(constant=0, factors={"x": 1.0, "y": 2.0, "z": -3.0})
        t2 = Term(coefficient=2.0, variable=None)

        c0 = TermList(constant=2.0, factors={"x": 1.0, "y": 2.0, "z": -3.0})
        c1 = tl1.combine(t2)
        s0 = f"{c0}"
        s1 = f"{c1}"
        self.assertEqual(s0, s1)

    def test_combine2(self) -> None:
        tl1 = TermList(constant=0, factors={"x": 1.0, "y": 2.0, "z": -3.0})
        t2 = Term(coefficient=2.0, variable="x")

        c0 = TermList(constant=0, factors={"x": 3.0, "y": 2.0, "z": -3.0})
        c1 = tl1.combine(t2)
        s0 = f"{c0}"
        s1 = f"{c1}"
        self.assertEqual(s0, s1)

    def test_add1(self) -> None:
        tl1 = TermList(constant=0, factors={"x": 1.0, "y": 2.0, "z": -3.0})
        tl2 = TermList(constant=-1.0, factors={"x": -1.0, "y": -1.0, "t": 1.0})

        add0 = TermList(constant=-1.0, factors={"y": 1.0, "t": 1.0, "z": -3.0})
        add1 = tl1.add(tl2)
        s0 = f"{add0}"
        s1 = f"{add1}"
        self.assertEqual(s0, s1)


if __name__ == "__main__":
    unittest.main()
