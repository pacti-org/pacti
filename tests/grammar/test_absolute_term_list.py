import unittest
import pyparsing as pp
from pacti.terms.polyhedra.grammar import abs_or_terms, AbsoluteTerm, AbsoluteTermList, TermList


class TestAbsoluteTermList(unittest.TestCase):
    def test1(self) -> None:
        t0 = pp.ParseResults(
            AbsoluteTermList(
                term_list=TermList(factors={"z": -7.0}, constant=0),
                absolute_term_list=[
                    AbsoluteTerm(term_list=TermList(constant=3.0, factors={"x": -1.0}), coefficient=None),
                    AbsoluteTerm(term_list=TermList(constant=0, factors={"y": 4.0, "t": 5.0}), coefficient=-3.0),
                ],
            )
        )
        t1 = abs_or_terms.parse_string("|-x + 3| - 3 |4y + 5t| - 7z", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)

    def test2(self) -> None:
        t0 = pp.ParseResults(
            AbsoluteTermList(
                term_list=TermList(factors={"z": -7.0}, constant=0),
                absolute_term_list=[
                    AbsoluteTerm(term_list=TermList(constant=3.0, factors={"x": -1.0}), coefficient=None),
                    AbsoluteTerm(term_list=TermList(constant=0, factors={"y": 4.0, "t": 5.0}), coefficient=-3.0),
                ],
            )
        )
        t1 = abs_or_terms.parse_string("z + |-1 + 2x + 4 - 3x| - 3 |4y + 5t| - 8z", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)

    def test3(self) -> None:
        t0 = pp.ParseResults(
            AbsoluteTermList(
                term_list=TermList(factors={"z": -7.0}, constant=0),
                absolute_term_list=[
                    AbsoluteTerm(term_list=TermList(constant=3.0, factors={"x": -1.0}), coefficient=None),
                    AbsoluteTerm(term_list=TermList(constant=0, factors={"y": 4.0, "t": 5.0}), coefficient=-3.0),
                ],
            )
        )
        t1 = abs_or_terms.parse_string("z + |-1 + 2x + 4 - 3x| - 2 |4y + 5t| - |4y + 5t| - 8z", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)

    def test4(self) -> None:
        t0 = pp.ParseResults(
            AbsoluteTermList(
                term_list=TermList(factors={"z": -7.0}, constant=0),
                absolute_term_list=[
                    AbsoluteTerm(term_list=TermList(constant=0, factors={"y": 3.0, "t": 5.0}), coefficient=-3.0)
                ],
            )
        )
        t1 = abs_or_terms.parse_string("|2y + 5t + y| - 7z - 4 |4y + 5t -y|", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)


if __name__ == "__main__":
    unittest.main()
