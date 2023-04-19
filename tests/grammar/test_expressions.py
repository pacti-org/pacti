import unittest
import pyparsing as pp
from pacti.terms.polyhedra.grammar import expression, AbsoluteTerm, AbsoluteTermList, Expression, Operator, TermList


class TestExpressions(unittest.TestCase):
    def test1(self) -> None:
        t0 = pp.ParseResults(
            Expression(
                operator=Operator.eql,
                sides=[
                    AbsoluteTermList(
                        term_list=TermList(factors={"z": -7.0}, constant=0),
                        absolute_term_list=[
                            AbsoluteTerm(term_list=TermList(constant=3.0, factors={"x": -1.0}), coefficient=None),
                            AbsoluteTerm(
                                term_list=TermList(constant=0, factors={"y": 4.0, "t": 5.0}), coefficient=3.0
                            ),
                        ],
                    ),
                    AbsoluteTermList(
                        term_list=TermList(factors={"t": 8.0}, constant=0),
                        absolute_term_list=[
                            AbsoluteTerm(
                                term_list=TermList(constant=0, factors={"x": 1.0, "y": -1.0}), coefficient=None
                            )
                        ],
                    ),
                ],
            )
        )
        t1 = expression.parse_string("|-x + 3| + 3 |4y + 5t| - 7z == 8t + |x - y|", parse_all=True)
        s0 = f"{t0}"
        s1 = f"{t1}"
        self.assertEqual(s0, s1)

    def test2(self) -> None:
        t0 = pp.ParseResults(
            Expression(
                operator=Operator.leq,
                sides=[
                    AbsoluteTermList(
                        term_list=TermList(factors={"z": -7.0}, constant=0),
                        absolute_term_list=[
                            AbsoluteTerm(term_list=TermList(constant=3.0, factors={"x": -1.0}), coefficient=None),
                            AbsoluteTerm(
                                term_list=TermList(constant=0, factors={"y": 4.0, "t": 5.0}), coefficient=3.0
                            ),
                        ],
                    ),
                    AbsoluteTermList(
                        term_list=TermList(factors={"t": 8.0}, constant=0),
                        absolute_term_list=[
                            AbsoluteTerm(
                                term_list=TermList(constant=0, factors={"x": 1.0, "y": -1.0}), coefficient=None
                            )
                        ],
                    ),
                    AbsoluteTermList(
                        term_list=TermList(factors={"t": -2.0}, constant=0),
                        absolute_term_list=[
                            AbsoluteTerm(
                                term_list=TermList(constant=0, factors={"x": -1.0, "y": -1.0}), coefficient=None
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
            Expression(
                operator=Operator.leq,
                sides=[
                    AbsoluteTermList(
                        term_list=TermList(factors={"z": -7.0}, constant=0),
                        absolute_term_list=[
                            AbsoluteTerm(term_list=TermList(constant=3.0, factors={"x": -1.0}), coefficient=None),
                            AbsoluteTerm(
                                term_list=TermList(constant=0, factors={"y": 4.0, "t": 5.0}), coefficient=3.0
                            ),
                        ],
                    ),
                    AbsoluteTermList(
                        term_list=TermList(factors={"t": 8.0}, constant=0),
                        absolute_term_list=[
                            AbsoluteTerm(
                                term_list=TermList(constant=0, factors={"x": 1.0, "y": -1.0}), coefficient=None
                            )
                        ],
                    ),
                    AbsoluteTermList(
                        term_list=TermList(factors={"t": -2.0}, constant=0),
                        absolute_term_list=[
                            AbsoluteTerm(
                                term_list=TermList(constant=0, factors={"x": -1.0, "y": -1.0}), coefficient=None
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
            Expression(
                operator=Operator.leq,
                sides=[
                    AbsoluteTermList(
                        term_list=TermList(factors={"z": -7.0}, constant=0),
                        absolute_term_list=[
                            AbsoluteTerm(term_list=TermList(constant=3.0, factors={"x": -1.0}), coefficient=None),
                            AbsoluteTerm(
                                term_list=TermList(constant=0, factors={"y": 4.0, "t": 5.0}), coefficient=3.0
                            ),
                        ],
                    ),
                    AbsoluteTermList(
                        term_list=TermList(factors={"t": 8.0}, constant=0),
                        absolute_term_list=[
                            AbsoluteTerm(
                                term_list=TermList(constant=0, factors={"x": 1.0, "y": -1.0}), coefficient=None
                            )
                        ],
                    ),
                    AbsoluteTermList(
                        term_list=TermList(factors={"t": -2.0}, constant=0),
                        absolute_term_list=[
                            AbsoluteTerm(
                                term_list=TermList(constant=0, factors={"x": -1.0, "y": -1.0}), coefficient=None
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
            Expression(
                operator=Operator.leq,
                sides=[
                    AbsoluteTermList(
                        term_list=TermList(factors={"z": -7.0}, constant=0),
                        absolute_term_list=[
                            AbsoluteTerm(term_list=TermList(constant=3.0, factors={"x": -1.0}), coefficient=None),
                            AbsoluteTerm(
                                term_list=TermList(constant=0, factors={"y": 4.0, "t": 5.0}), coefficient=3.0
                            ),
                        ],
                    ),
                    AbsoluteTermList(
                        term_list=TermList(factors={"t": 8.0}, constant=-6.0),
                        absolute_term_list=[
                            AbsoluteTerm(
                                term_list=TermList(constant=0, factors={"x": 1.0, "y": -1.0}), coefficient=None
                            )
                        ],
                    ),
                    AbsoluteTermList(
                        term_list=TermList(factors={"t": -2.0}, constant=0),
                        absolute_term_list=[
                            AbsoluteTerm(
                                term_list=TermList(constant=0, factors={"x": -1.0, "y": -1.0}), coefficient=None
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

if __name__ == "__main__":
    unittest.main()
