
from typing import List
from pacti.terms.polyhedra import serializer, PolyhedralTerm

for s in [
    # "|x| <= 0",
    # "|x| >= 0",
    "|x| = 0",
    "|x| + |y| = 0",
    # "|x| + y <= 0",
    # "|x| + y >= 0",
    "|x| + y = 0",
    "2x + |u - v| = 6",
    # "2x + | y | - 3 |v-w| = 10",
    "x + 1 >= 2x - 2",
    # "2x - 5 ( | y | - 3 |v-w| ) = 10",
    # "|x| + y + |z| <= 0",
    # "|x| + y + |z| >= 0",
    # "|x| + y + |z| = 0",
    # "|-x + 3| - 3 |4y + 5t| - 7z <= 8t + |x - y|",
    # "|-x + 3| - 3 |4y + 5t| - 7z == 8t + |x - y|",
    # "|- 2 -x + 3 + 6x | <= - 3 |4y + 5t -y | - 7z <= 8t + |x - y| <= 10",
    # "|- 2 -x + 3 + 6x | <= |4y + 5t -y | - 7z - 4 |4y + 5t -y |<= 8t + |x - y| <= 10",
]:
    print(f"\nexpression: {s}")
    pts: List[PolyhedralTerm] = serializer.polyhedral_termlist_from_string(s)
    print(f"yields: {len(pts)} Polyhedral Terms")
    for pt in pts:
        print(f"\t{pt}")
