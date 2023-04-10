import unittest
import pyparsing as pp
from pacti.terms.polyhedra.grammar import terms, TermList

class TestTermListParsing(unittest.TestCase):

    def test1(self):
        t0 = pp.ParseResults(
            TermList(constant = 4.0,
                     factors = {
                        "x": 1.0,
                        "y": 2.0,
                        "z": -3.0
                     }))
        t1 = terms.parse_string("x+2y-3z+4", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)

    def test2(self):
        t0 = pp.ParseResults(
            TermList(constant = 4.0,
                     factors = {
                        "x": 1.0,
                        "y": 2.0,
                        "z": -3.0
                     }))
        t1 = terms.parse_string("1+x+1+3y-2z+2-y-z", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)

if __name__ == "__main__":
    unittest.main()
