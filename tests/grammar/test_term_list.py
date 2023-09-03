import unittest

import pyparsing as pp

from pacti.terms.polyhedra.syntax.data import (
    PolyhedralSyntaxAbsoluteTerm,
    PolyhedralSyntaxAbsoluteTermList,
    PolyhedralSyntaxTermList,
)
from pacti.terms.polyhedra.syntax.grammar import *


class TestTermList(unittest.TestCase):
    def test_term_list1(self) -> None:
        t0 = pp.ParseResults(PolyhedralSyntaxTermList(constant=3.0, factors={}))
        t1 = terms.parse_string("1+2", parse_all=True)
        t2 = terms.parse_string("3", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        s2 = f"{t2}"
        self.assertEqual(s0, s1)
        self.assertEqual(s0, s2)
        self.assertTrue(isinstance(t1[0], PolyhedralSyntaxTermList))

    def test_term_list2(self) -> None:
        t0 = pp.ParseResults(PolyhedralSyntaxTermList(constant=0, factors={"x": 3.0}))
        t1 = terms.parse_string("x+2x", parse_all=True)
        t2 = terms.parse_string("3x", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        s2 = f"{t2}"
        self.assertEqual(s0, s1)
        self.assertEqual(s0, s2)
        self.assertTrue(isinstance(t1[0], PolyhedralSyntaxTermList))

    def test_term_list3(self) -> None:
        t0 = pp.ParseResults(PolyhedralSyntaxTermList(constant=1.0, factors={"x": 1.0}))
        t1 = terms.parse_string("2(x+1)-(2-1+x)", parse_all=True)
        t2 = terms.parse_string("x+1", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        s2 = f"{t2}"
        self.assertEqual(s0, s1)
        self.assertEqual(s0, s2)
        self.assertTrue(isinstance(t1[0], PolyhedralSyntaxTermList))

    def test_term_list4(self) -> None:
        t0 = pp.ParseResults(PolyhedralSyntaxTermList(constant=-6.0, factors={"t": 8.0}))
        t1 = terms.parse_string("2(3(t -1)+t)", parse_all=True)
        t2 = terms.parse_string("8t-6", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        s2 = f"{t2}"
        self.assertEqual(s0, s1)
        self.assertEqual(s0, s2)
        self.assertTrue(isinstance(t1[0], PolyhedralSyntaxTermList))

    def test_abs_term1(self) -> None:
        t0 = pp.ParseResults(
            PolyhedralSyntaxAbsoluteTerm(term_list=PolyhedralSyntaxTermList(constant=3.0, factors={}), coefficient=None)
        )
        t1 = abs_term.parse_string("|1+2|", parse_all=True)
        t2 = abs_term.parse_string("|3|", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        s2 = f"{t2}"
        self.assertEqual(s0, s1)
        self.assertEqual(s0, s2)
        self.assertTrue(isinstance(t1[0], PolyhedralSyntaxAbsoluteTerm))

    def test_abs_term2(self) -> None:
        t0 = pp.ParseResults(
            PolyhedralSyntaxAbsoluteTerm(
                term_list=PolyhedralSyntaxTermList(constant=0, factors={"x": 3.0}), coefficient=4.0
            )
        )
        t1 = abs_term.parse_string("4|x+2x|", parse_all=True)
        t2 = abs_term.parse_string("4|3x|", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        s2 = f"{t2}"
        self.assertEqual(s0, s1)
        self.assertEqual(s0, s2)
        self.assertTrue(isinstance(t1[0], PolyhedralSyntaxAbsoluteTerm))

    def test_parse1(self) -> None:
        t0 = pp.ParseResults(PolyhedralSyntaxTermList(constant=4.0, factors={"x": 1.0, "y": 2.0, "z": -3.0}))
        t1 = terms.parse_string("x+2y-3z+4", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)
        self.assertTrue(isinstance(t1[0], PolyhedralSyntaxTermList))
        self.assertTrue(t1[0].is_positive())

    def test_parse2(self) -> None:
        t0 = pp.ParseResults(PolyhedralSyntaxTermList(constant=4.0, factors={"x": 1.0, "y": 2.0, "z": -3.0}))
        t1 = terms.parse_string("1+x+1+3y-2z+2-y-z", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)
        self.assertTrue(isinstance(t1[0], PolyhedralSyntaxTermList))
        self.assertTrue(t1[0].is_positive())

    def test_add1(self) -> None:
        tl1 = PolyhedralSyntaxTermList(constant=0, factors={"x": 1.0, "y": 2.0, "z": -3.0})
        tl2 = PolyhedralSyntaxTermList(constant=-1.0, factors={"x": -1.0, "y": -1.0, "t": 1.0})

        add0 = PolyhedralSyntaxTermList(constant=-1.0, factors={"y": 1.0, "t": 1.0, "z": -3.0})
        add1 = tl1.add(tl2)
        s0 = f"{add0}"
        s1 = f"{add1}"
        self.assertEqual(s0, s1)

    def test_parse3(self) -> None:
        t0 = pp.ParseResults(PolyhedralSyntaxTermList(constant=8.0, factors={"x": 1.0, "y": 2.0, "z": -7.0}))
        t1 = terms.parse_string("1+x+1+3(y-2z+2)-y-z", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)
        self.assertTrue(isinstance(t1[0], PolyhedralSyntaxTermList))
        self.assertTrue(t1[0].is_positive())

    def test_parse4(self) -> None:
        t0 = pp.ParseResults(PolyhedralSyntaxTermList(constant=6.0, factors={"x": 1.0, "y": 1.0, "z": -5.0}))
        t1 = terms.parse_string("1+x+1+3(y-2z+2)-(2+y-2z)-y-z", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)
        self.assertTrue(isinstance(t1[0], PolyhedralSyntaxTermList))
        self.assertTrue(t1[0].is_positive())

    def test_parse5a(self) -> None:
        t0 = pp.ParseResults(PolyhedralSyntaxTermList(constant=-6.0, factors={"t": 8.0}))
        t1 = terms.parse_string("2(3(t -1)+t)", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)
        self.assertTrue(isinstance(t1[0], PolyhedralSyntaxTermList))
        self.assertFalse(t1[0].is_positive())

    def test_parse5b1(self) -> None:
        t0 = pp.ParseResults(
            PolyhedralSyntaxAbsoluteTermList(
                term_list=PolyhedralSyntaxTermList(constant=-6.0, factors={"t": 8.0}), absolute_term_list=[]
            )
        )
        t1 = paren_abs_or_terms.parse_string("2(3(t -1)+t)", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)
        self.assertTrue(isinstance(t1[0], PolyhedralSyntaxAbsoluteTermList))

    def test_parse5b2(self) -> None:
        t0 = pp.ParseResults(
            PolyhedralSyntaxAbsoluteTermList(
                term_list=PolyhedralSyntaxTermList(constant=-6.0, factors={"t": 8.0}), absolute_term_list=[]
            )
        )
        t1 = first_abs_or_term.parse_string("2(3(t -1)+t)", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)
        self.assertTrue(isinstance(t1[0], PolyhedralSyntaxTermList))

    def test_parse5b(self) -> None:
        t0 = pp.ParseResults(
            PolyhedralSyntaxAbsoluteTermList(
                term_list=PolyhedralSyntaxTermList(constant=-6.0, factors={"t": 8.0}), absolute_term_list=[]
            )
        )
        t1 = first_paren_abs_or_terms.parse_string("2(3(t -1)+t)", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)
        self.assertTrue(isinstance(t1[0], PolyhedralSyntaxAbsoluteTermList))

    def test_parse5c(self) -> None:
        t0 = pp.ParseResults(
            PolyhedralSyntaxAbsoluteTermList(
                term_list=PolyhedralSyntaxTermList(constant=-6.0, factors={"t": 8.0}), absolute_term_list=[]
            )
        )
        t1 = multi_paren_abs_or_terms.parse_string("2(3(t -1)+t)", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)
        self.assertTrue(isinstance(t1[0], PolyhedralSyntaxAbsoluteTermList))

    def test_parse6a(self) -> None:
        t0 = pp.ParseResults(
            PolyhedralSyntaxAbsoluteTermList(
                term_list=PolyhedralSyntaxTermList(constant=0, factors={}),
                absolute_term_list=[
                    PolyhedralSyntaxAbsoluteTerm(
                        coefficient=None, term_list=PolyhedralSyntaxTermList(constant=0, factors={"x": 1.0, "y": -1.0})
                    )
                ],
            )
        )
        t1 = multi_paren_abs_or_terms.parse_string("|x - y|", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)
        self.assertTrue(isinstance(t1[0], PolyhedralSyntaxAbsoluteTermList))

    def test_parse6b(self) -> None:
        t0 = pp.ParseResults(
            PolyhedralSyntaxAbsoluteTermList(
                term_list=PolyhedralSyntaxTermList(constant=-6.0, factors={"t": 8.0}),
                absolute_term_list=[
                    PolyhedralSyntaxAbsoluteTerm(
                        coefficient=3.0, term_list=PolyhedralSyntaxTermList(constant=0, factors={"x": 1.0, "y": -1.0})
                    )
                ],
            )
        )
        t1 = multi_paren_abs_or_terms.parse_string("2(3(t -1)+t) + 2|x - y| + |x - y|", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)
        self.assertTrue(isinstance(t1[0], PolyhedralSyntaxAbsoluteTermList))

    def test_parse7(self) -> None:
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
        t1 = multi_paren_abs_or_terms.parse_string(
            "(|-x + 3| + |t+5(y + t)-(y+t)| - z) + 2 (|t+5(y + t)-(y+t)| - 3z )", parse_all=True
        )
        t2 = multi_paren_abs_or_terms.parse_string("-7z + |-x + 3| + 3|4y+5t|", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        s2 = f"{t2}"
        self.assertEqual(s0, s1)
        self.assertEqual(s0, s2)
        self.assertTrue(isinstance(t1[0], PolyhedralSyntaxAbsoluteTermList))


if __name__ == "__main__":
    unittest.main()
