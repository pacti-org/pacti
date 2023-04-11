import unittest
import pyparsing as pp
from pacti.terms.polyhedra.grammar import abs_or_term, signed_abs_or_term, AbsoluteTerm, TermList


class TestAbsoluteTermOrTerm(unittest.TestCase):
    def test1a(self) -> None:
        t0 = pp.ParseResults(
            AbsoluteTerm(term_list=TermList(constant=4.0, factors={"x": 1.0, "y": 2.0, "z": -3.0}), coefficient=None)
        )
        t1 = abs_or_term.parse_string("|x+2y-3z+4|", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)
        self.assertTrue(isinstance(t1[0], AbsoluteTerm))
        self.assertTrue(t1[0].is_positive())
        self.assertTrue(t1[0].term_list.is_positive())

    def test1b(self) -> None:
        t0 = pp.ParseResults(
            AbsoluteTerm(term_list=TermList(constant=-4.0, factors={"x": -1.0, "y": 2.0, "z": -3.0}), coefficient=None)
        )
        t1 = signed_abs_or_term.parse_string("|-x+2y-3z+4-8|", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)
        self.assertTrue(isinstance(t1[0], AbsoluteTerm))
        self.assertTrue(t1[0].is_positive())
        self.assertFalse(t1[0].term_list.is_positive())

    def test1c(self) -> None:
        t0 = pp.ParseResults(
            AbsoluteTerm(term_list=TermList(constant=4.0, factors={"x": 1.0, "y": 2.0, "z": -3.0}), coefficient=-1.0)
        )
        t1 = signed_abs_or_term.parse_string("-|x+2y-3z+4|", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)
        self.assertTrue(isinstance(t1[0], AbsoluteTerm))
        self.assertFalse(t1[0].is_positive())
        self.assertTrue(t1[0].term_list.is_positive())

    def test2a(self) -> None:
        t0 = pp.ParseResults(
            AbsoluteTerm(term_list=TermList(constant=4.0, factors={"x": -1.0, "y": 2.0, "z": -3.0}), coefficient=2.0)
        )
        t1 = abs_or_term.parse_string("2|-x+2y-3z+4|", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)
        self.assertTrue(isinstance(t1[0], AbsoluteTerm))
        self.assertTrue(t1[0].is_positive())
        self.assertTrue(t1[0].term_list.is_positive())

    def test2b(self) -> None:
        t0 = pp.ParseResults(
            AbsoluteTerm(term_list=TermList(constant=4.0, factors={"x": -1.0, "y": 2.0, "z": -3.0}), coefficient=2.0)
        )
        t1 = signed_abs_or_term.parse_string("2|-x+2y-3z+4|", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)
        self.assertTrue(isinstance(t1[0], AbsoluteTerm))
        self.assertTrue(t1[0].is_positive())
        self.assertTrue(t1[0].term_list.is_positive())

    def test2c(self) -> None:
        t0 = pp.ParseResults(
            AbsoluteTerm(term_list=TermList(constant=-4.0, factors={"x": 1.0, "y": 2.0, "z": -3.0}), coefficient=-2.0)
        )
        t1 = signed_abs_or_term.parse_string("- 2|-8+x+2y-3z+4|", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)
        self.assertTrue(isinstance(t1[0], AbsoluteTerm))
        self.assertFalse(t1[0].is_positive())
        self.assertFalse(t1[0].term_list.is_positive())


if __name__ == "__main__":
    unittest.main()
