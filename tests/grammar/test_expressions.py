import unittest

import pyparsing as pp

from pacti.terms.polyhedra.syntax.data import *
from pacti.terms.polyhedra.syntax.grammar import *


class TestExpressions(unittest.TestCase):
    def test1(self) -> None:
        t0 = pp.ParseResults(
            PolyhedralSyntaxIneqExpression(
                operator=PolyhedralSyntaxOperator.leq,
                sides=[
                    PolyhedralSyntaxAbsoluteTermList(
                        term_list=PolyhedralSyntaxTermList(factors={"z": -7.0}, constant=0),
                        absolute_term_list=[
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=3.0, factors={"x": -1.0}), coefficient=None
                            ),
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=0, factors={"y": 4.0, "t": 5.0}),
                                coefficient=3.0,
                            ),
                        ],
                    ),
                    PolyhedralSyntaxAbsoluteTermList(
                        term_list=PolyhedralSyntaxTermList(factors={"t": 8.0}, constant=0),
                        absolute_term_list=[
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=0, factors={"x": 1.0, "y": -1.0}),
                                coefficient=None,
                            )
                        ],
                    ),
                ],
            )
        )
        t1 = expression.parse_string("|-x + 3| + 3 |4y + 5t| - 7z <= 8t + |x - y|", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)

    def test2(self) -> None:
        t0 = pp.ParseResults(
            PolyhedralSyntaxIneqExpression(
                operator=PolyhedralSyntaxOperator.leq,
                sides=[
                    PolyhedralSyntaxAbsoluteTermList(
                        term_list=PolyhedralSyntaxTermList(factors={"z": -7.0}, constant=0),
                        absolute_term_list=[
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=3.0, factors={"x": -1.0}), coefficient=None
                            ),
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=0, factors={"y": 4.0, "t": 5.0}),
                                coefficient=3.0,
                            ),
                        ],
                    ),
                    PolyhedralSyntaxAbsoluteTermList(
                        term_list=PolyhedralSyntaxTermList(factors={"t": 8.0}, constant=0),
                        absolute_term_list=[
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=0, factors={"x": 1.0, "y": -1.0}),
                                coefficient=None,
                            )
                        ],
                    ),
                    PolyhedralSyntaxAbsoluteTermList(
                        term_list=PolyhedralSyntaxTermList(factors={"t": -2.0}, constant=0),
                        absolute_term_list=[
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=0, factors={"x": -1.0, "y": -1.0}),
                                coefficient=None,
                            )
                        ],
                    ),
                ],
            )
        )
        t1 = expression.parse_string(
            "|-x + 3| + 3 |4y + 5t| - 7z <= 8t + |x - y| <= -2t + |y - 2y - x|", parse_all=True
        )
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)

    def test3(self) -> None:
        t0 = pp.ParseResults(
            PolyhedralSyntaxIneqExpression(
                operator=PolyhedralSyntaxOperator.leq,
                sides=[
                    PolyhedralSyntaxAbsoluteTermList(
                        term_list=PolyhedralSyntaxTermList(factors={"z": -7.0}, constant=0),
                        absolute_term_list=[
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=3.0, factors={"x": -1.0}), coefficient=None
                            ),
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=0, factors={"y": 4.0, "t": 5.0}),
                                coefficient=3.0,
                            ),
                        ],
                    ),
                    PolyhedralSyntaxAbsoluteTermList(
                        term_list=PolyhedralSyntaxTermList(factors={"t": 8.0}, constant=0),
                        absolute_term_list=[
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=0, factors={"x": 1.0, "y": -1.0}),
                                coefficient=None,
                            )
                        ],
                    ),
                    PolyhedralSyntaxAbsoluteTermList(
                        term_list=PolyhedralSyntaxTermList(factors={"t": -2.0}, constant=0),
                        absolute_term_list=[
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=0, factors={"x": -1.0, "y": -1.0}),
                                coefficient=None,
                            )
                        ],
                    ),
                ],
            )
        )
        t1 = expression.parse_string(
            "|-x + 3| + 3 |t+4(y + t)| - 7z <= 8t + |x - y| <= -2t + |y - 2y - x|", parse_all=True
        )
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)

    def test4(self) -> None:
        t0 = pp.ParseResults(
            PolyhedralSyntaxIneqExpression(
                operator=PolyhedralSyntaxOperator.leq,
                sides=[
                    PolyhedralSyntaxAbsoluteTermList(
                        term_list=PolyhedralSyntaxTermList(factors={"z": -7.0}, constant=0),
                        absolute_term_list=[
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=3.0, factors={"x": -1.0}), coefficient=None
                            ),
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=0, factors={"y": 4.0, "t": 5.0}),
                                coefficient=3.0,
                            ),
                        ],
                    ),
                    PolyhedralSyntaxAbsoluteTermList(
                        term_list=PolyhedralSyntaxTermList(factors={"t": 8.0}, constant=0),
                        absolute_term_list=[
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=0, factors={"x": 1.0, "y": -1.0}),
                                coefficient=None,
                            )
                        ],
                    ),
                    PolyhedralSyntaxAbsoluteTermList(
                        term_list=PolyhedralSyntaxTermList(factors={"t": -2.0}, constant=0),
                        absolute_term_list=[
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=0, factors={"x": -1.0, "y": -1.0}),
                                coefficient=None,
                            )
                        ],
                    ),
                ],
            )
        )
        t1 = expression.parse_string(
            "|-x + 3| + 3 |t+5(y + t)-(y+t)| - 7z <= 8t + |x - y| <= -2t + |y - 2y - x|", parse_all=True
        )
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)

    def test5(self) -> None:
        t0 = pp.ParseResults(
            PolyhedralSyntaxIneqExpression(
                operator=PolyhedralSyntaxOperator.leq,
                sides=[
                    PolyhedralSyntaxAbsoluteTermList(
                        term_list=PolyhedralSyntaxTermList(factors={"z": -7.0}, constant=0),
                        absolute_term_list=[
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=3.0, factors={"x": -1.0}), coefficient=None
                            ),
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=0, factors={"y": 4.0, "t": 5.0}),
                                coefficient=3.0,
                            ),
                        ],
                    ),
                    PolyhedralSyntaxAbsoluteTermList(
                        term_list=PolyhedralSyntaxTermList(factors={"t": 8.0}, constant=-6.0),
                        absolute_term_list=[
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=0, factors={"x": 1.0, "y": -1.0}),
                                coefficient=None,
                            )
                        ],
                    ),
                    PolyhedralSyntaxAbsoluteTermList(
                        term_list=PolyhedralSyntaxTermList(factors={"t": -2.0}, constant=0),
                        absolute_term_list=[
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=0, factors={"x": -1.0, "y": -1.0}),
                                coefficient=None,
                            )
                        ],
                    ),
                ],
            )
        )
        t1 = expression.parse_string(
            "|-x + 3| + 3 |t+5(y + t)-(y+t)| - 7z <= 2(3(t -1)+t) + |x - y| <= -2t + |y - 2y - x|", parse_all=True
        )
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)

    def test6(self) -> None:
        t0 = pp.ParseResults(
            PolyhedralSyntaxIneqExpression(
                operator=PolyhedralSyntaxOperator.leq,
                sides=[
                    PolyhedralSyntaxAbsoluteTermList(
                        term_list=PolyhedralSyntaxTermList(factors={"z": -7.0}, constant=0),
                        absolute_term_list=[
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=3.0, factors={"x": -1.0}), coefficient=None
                            ),
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=0, factors={"y": 4.0, "t": 5.0}),
                                coefficient=3.0,
                            ),
                        ],
                    ),
                    PolyhedralSyntaxAbsoluteTermList(
                        term_list=PolyhedralSyntaxTermList(factors={"t": 8.0}, constant=-6.0),
                        absolute_term_list=[
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=0, factors={"x": 1.0, "y": -1.0}),
                                coefficient=None,
                            )
                        ],
                    ),
                    PolyhedralSyntaxAbsoluteTermList(
                        term_list=PolyhedralSyntaxTermList(factors={"t": -2.0}, constant=0),
                        absolute_term_list=[
                            PolyhedralSyntaxAbsoluteTerm(
                                term_list=PolyhedralSyntaxTermList(constant=0, factors={"x": -1.0, "y": -1.0}),
                                coefficient=None,
                            )
                        ],
                    ),
                ],
            )
        )
        t1 = expression.parse_string(
            "(|-x + 3| + |t+5(y + t)-(y+t)| - z) + 2 (|t+5(y + t)-(y+t)| - 3z ) <= 2(3(t -1)+t) + |x - y| <= -2t + |y - 2y - x|",
            parse_all=True,
        )
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)


if __name__ == "__main__":
    unittest.main()
