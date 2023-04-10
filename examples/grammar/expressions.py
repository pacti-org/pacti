from pacti.terms.polyhedra.grammar import *

for s in [
    "|-x + 3|",
    "|4y + 5t -y |",
    "|4y - y + 5t |",
    "|-5 -x + 3 + 4x|",
    "2.0|-x + 3|",
    "5t + |-x + 3|",
    "|-x + 3| + 5t",
    "-1 + |-x + 3| + 5t",
    "-1 + 2|-x + 3| + 5t",
    "-5 + 3|-x + 3| + 5t",
    "|-x + 3| - 3 |4y + 5t| - 7z",
]:
    print(f"\nabs_terms: {s}")
    r = abs_or_terms.parse_string(s, parse_all=True)
    print(r)


for s in [
    "|-x + 3| - 3 |4y + 5t| - 7z <= 8t + |x - y|",
    "|-x + 3| - 3 |4y + 5t| - 7z == 8t + |x - y|",
    "|- 2 -x + 3 + 6x | <= - 3 |4y + 5t -y | - 7z <= 8t + |x - y| <= 10",
]:
    print(f"\nexpression: {s}")
    result = expression.parseString(s, parse_all=True)
    print(result)
