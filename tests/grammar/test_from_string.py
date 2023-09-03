import unittest
from typing import List

from pacti.iocontract import Var
from pacti.terms.polyhedra import PolyhedralTerm, serializer
from pacti.utils.errors import PolyhedralSyntaxConvexException, PolyhedralSyntaxException


class TestFromString(unittest.TestCase):
    def test1(self) -> None:
        pts: List[PolyhedralTerm] = serializer.polyhedral_termlist_from_string("|i| <= 1.23456789e-5")
        self.assertTrue(len(pts) == 2)

    def test2(self) -> None:
        pts: List[PolyhedralTerm] = serializer.polyhedral_termlist_from_string("x = 0")
        self.assertTrue(len(pts) == 2, f"{len(pts)}")

    def test3(self) -> None:
        pts: List[PolyhedralTerm] = serializer.polyhedral_termlist_from_string(
            "0.002757617728531856DHBA - xRFP = -0.02031855955678674"
        )
        self.assertTrue(len(pts) == 2)

    def test4(self) -> None:
        pts: List[PolyhedralTerm] = serializer.polyhedral_termlist_from_string("x = 0")
        self.assertTrue(len(pts) == 2)

    def test5(self) -> None:
        pts: List[PolyhedralTerm] = serializer.polyhedral_termlist_from_string("-x + y <= 0")
        self.assertTrue(len(pts) == 1, f"{len(pts)}")
        pt: PolyhedralTerm = pts[0]
        self.assertTrue(pt.constant == 0, f"{pt.constant}")
        self.assertTrue(pt.get_coefficient(Var("x")), -1)
        self.assertTrue(pt.get_coefficient(Var("y")), 1)

    def test_exception1a(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException) as e:
            serializer.polyhedral_termlist_from_string("|x| = 0")
        assert "|x| = 0" in str(e.exception)

    def test_exception1b(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("0 = |x|")

    def test_exception1c(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("0 = |x|*y")

    def test_exception1d(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("0 = |x|*3")

    def test_exception2a(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("x * y <= 0")

    def test_exception2b(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("x / y <= 0")

    def test_exception2c(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("x ** y <= 0")

    def test_exception2d(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("x + + y <= 0")

    def test_exception2e(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("x ++ y <= 0")

    def test_exception2f(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("x + + 1 <= 0")

    def test_exception2g(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("x ++ 1 <= 0")

    def test_exception2h(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("x - - y <= 0")

    def test_exception2i(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("x -- y <= 0")

    def test_exception2j(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("x - - 1 <= 0")

    def test_exception2k(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("x -- 1 <= 0")

    def test_exception2l(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("x + - y <= 0")

    def test_exception2m(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("x +- y <= 0")

    def test_exception2n(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("x + - 1 <= 0")

    def test_exception2o(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("x +- 1 <= 0")

    def test_exception2p(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("x - + y <= 0")

    def test_exception2q(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("x -+ y <= 0")

    def test_exception2r(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("x - + 1 <= 0")

    def test_exception2s(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("x -+ 1 <= 0")

    def test_exception3a(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("- -x <= 0")

    def test_exception3b(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("- +x <= 0")

    def test_exception3c(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("+ -x <= 0")

    def test_exception3d(self) -> None:
        with self.assertRaises(PolyhedralSyntaxException):
            serializer.polyhedral_termlist_from_string("+ +x <= 0")

    def test_convex1a(self) -> None:
        pts: List[PolyhedralTerm] = serializer.polyhedral_termlist_from_string("|x1| <= 10")
        self.assertTrue(len(pts) == 2, f"{len(pts)}")

    def test_convex1b(self) -> None:
        with self.assertRaises(PolyhedralSyntaxConvexException) as e:
            serializer.polyhedral_termlist_from_string("-|x1| <= 0")
        assert "-|x1| <= 0" in str(e.exception)

    def test_convex2a(self) -> None:
        pts: List[PolyhedralTerm] = serializer.polyhedral_termlist_from_string("|x1| + |x2| <= 10")
        self.assertTrue(len(pts) == 4, f"{len(pts)}")

    def test_convex2b(self) -> None:
        with self.assertRaises(PolyhedralSyntaxConvexException):
            serializer.polyhedral_termlist_from_string("-|x1| + |x2| <= 0")

    def test_convex2c(self) -> None:
        with self.assertRaises(PolyhedralSyntaxConvexException):
            serializer.polyhedral_termlist_from_string("|x1| - |x2| <= 0")

    def test_convex2d(self) -> None:
        pts: List[PolyhedralTerm] = serializer.polyhedral_termlist_from_string("-|x1| + |x2| <= 10 - 2|x1|")
        self.assertTrue(len(pts) == 4, f"{len(pts)}")

    def test_convex3a(self) -> None:
        pts: List[PolyhedralTerm] = serializer.polyhedral_termlist_from_string("|x1| + |x2| + |x3| <= 10")
        self.assertTrue(len(pts) == 8, f"{len(pts)}")

    def test_convex3b(self) -> None:
        pts: List[PolyhedralTerm] = serializer.polyhedral_termlist_from_string("|x1| + |x2| <= 10 - |x3|")
        self.assertTrue(len(pts) == 8, f"{len(pts)}")

    def test_convex3c(self) -> None:
        with self.assertRaises(PolyhedralSyntaxConvexException):
            serializer.polyhedral_termlist_from_string("|x1| + |x2| <= 10 + |x3|")

    def test_convex3d(self) -> None:
        pts: List[PolyhedralTerm] = serializer.polyhedral_termlist_from_string("|x1| <= 10 - (|x2| + |x3|)")
        self.assertTrue(len(pts) == 8, f"{len(pts)}")

    def test_convex3e(self) -> None:
        with self.assertRaises(PolyhedralSyntaxConvexException):
            serializer.polyhedral_termlist_from_string("|x1| <= 10 - (|x2| - |x3|)")

    def test_convex3f(self) -> None:
        pts: List[PolyhedralTerm] = serializer.polyhedral_termlist_from_string("|x1| + 2|x3| <= 10 - (|x2| - |x3|)")
        self.assertTrue(len(pts) == 8, f"{len(pts)}")


if __name__ == "__main__":
    unittest.main()
