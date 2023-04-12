import unittest
import pyparsing as pp
from typing import List
from pacti.terms.polyhedra.grammar import expression, AbsoluteTerm, AbsoluteTermList, Expression, Operator, TermList
from pacti.terms.polyhedra import serializer, PolyhedralTerm


class TestFromString(unittest.TestCase):
    def test1(self) -> None:
        pts: List[PolyhedralTerm] = serializer.polyhedral_termlist_from_string("|i| <= 1.23456789e-5")
        self.assertTrue(len(pts) == 2)

    def test2(self) -> None:
        pts: List[PolyhedralTerm] = serializer.polyhedral_termlist_from_string("|x| = 0")
        self.assertTrue(len(pts) == 4, f"{len(pts)}")

    def test3(self) -> None:
        pts: List[PolyhedralTerm] = serializer.polyhedral_termlist_from_string(
            "0.002757617728531856DHBA - xRFP = -0.02031855955678674"
        )
        self.assertTrue(len(pts) == 2)

    def test4(self) -> None:
        pts: List[PolyhedralTerm] = serializer.polyhedral_termlist_from_string("x = 0")
        self.assertTrue(len(pts) == 2)

if __name__ == "__main__":
    unittest.main()
