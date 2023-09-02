import unittest

import pyparsing as pp

from pacti.terms.polyhedra.syntax.data import (
    PolyhedralSyntaxAbsoluteTerm,
    PolyhedralSyntaxAbsoluteTermList,
    PolyhedralSyntaxTermList,
)
from pacti.terms.polyhedra.syntax.grammar import abs_or_terms


class TestAbsoluteTermList(unittest.TestCase):
    def test_parse1(self) -> None:
        t0 = pp.ParseResults(
            PolyhedralSyntaxAbsoluteTermList(
                term_list=PolyhedralSyntaxTermList(factors={"z": -7.0}, constant=0),
                absolute_term_list=[
                    PolyhedralSyntaxAbsoluteTerm(
                        term_list=PolyhedralSyntaxTermList(constant=3.0, factors={"x": -1.0}), coefficient=None
                    ),
                    PolyhedralSyntaxAbsoluteTerm(
                        term_list=PolyhedralSyntaxTermList(constant=0, factors={"y": 4.0, "t": 5.0}), coefficient=3.0
                    ),
                ],
            )
        )
        t1 = abs_or_terms.parse_string("|-x + 3| + 3 |4y + 5t| - 7z", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)

    def test_parse2(self) -> None:
        t0 = pp.ParseResults(
            PolyhedralSyntaxAbsoluteTermList(
                term_list=PolyhedralSyntaxTermList(factors={"z": -7.0}, constant=0),
                absolute_term_list=[
                    PolyhedralSyntaxAbsoluteTerm(
                        term_list=PolyhedralSyntaxTermList(constant=3.0, factors={"x": -1.0}), coefficient=None
                    ),
                    PolyhedralSyntaxAbsoluteTerm(
                        term_list=PolyhedralSyntaxTermList(constant=0, factors={"y": 4.0, "t": 5.0}), coefficient=3.0
                    ),
                ],
            )
        )
        t1 = abs_or_terms.parse_string("z + |-1 + 2x + 4 - 3x| + 3 |4y + 5t| - 8z", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)

    def test_parse3(self) -> None:
        t0 = pp.ParseResults(
            PolyhedralSyntaxAbsoluteTermList(
                term_list=PolyhedralSyntaxTermList(factors={"z": -7.0}, constant=0),
                absolute_term_list=[
                    PolyhedralSyntaxAbsoluteTerm(
                        term_list=PolyhedralSyntaxTermList(constant=3.0, factors={"x": -1.0}), coefficient=None
                    ),
                    PolyhedralSyntaxAbsoluteTerm(
                        term_list=PolyhedralSyntaxTermList(constant=0, factors={"y": 4.0, "t": 5.0}), coefficient=3.0
                    ),
                ],
            )
        )
        t1 = abs_or_terms.parse_string("z + |-1 + 2x + 4 - 3x| + 2 |4y + 5t| + |4y + 5t| - 8z", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)

    def test_parse4(self) -> None:
        t0 = pp.ParseResults(
            PolyhedralSyntaxAbsoluteTermList(
                term_list=PolyhedralSyntaxTermList(factors={"z": -7.0}, constant=0),
                absolute_term_list=[
                    PolyhedralSyntaxAbsoluteTerm(
                        term_list=PolyhedralSyntaxTermList(constant=0, factors={"y": 3.0, "t": 5.0}), coefficient=5.0
                    )
                ],
            )
        )
        t1 = abs_or_terms.parse_string("|2y + 5t + y| - 7z + 4 |4y + 5t -y|", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)

    def test_expand1(self) -> None:
        tl = PolyhedralSyntaxTermList(factors={"z": -7.0}, constant=0)
        at1 = PolyhedralSyntaxAbsoluteTerm(
            term_list=PolyhedralSyntaxTermList(constant=3.0, factors={"x": -1.0}), coefficient=None
        )
        tp1 = at1.to_term_list()
        tn1 = at1.negate().to_term_list()
        at2 = PolyhedralSyntaxAbsoluteTerm(
            term_list=PolyhedralSyntaxTermList(constant=0, factors={"y": 4.0, "t": 5.0}), coefficient=-3.0
        )
        tp2 = at2.to_term_list()
        tn2 = at2.negate().to_term_list()
        atl = PolyhedralSyntaxAbsoluteTermList(term_list=tl, absolute_term_list=[at1, at2])
        e0 = [tl.add(tp1).add(tp2), tl.add(tp1).add(tn2), tl.add(tn1).add(tp2), tl.add(tn1).add(tn2)]
        e1 = atl.expand()
        s0 = f"{e0}"
        s1 = f"{e1}"
        self.assertEqual(s0, s1)


if __name__ == "__main__":
    unittest.main()
