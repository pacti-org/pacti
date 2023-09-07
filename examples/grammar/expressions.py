from pacti.terms.polyhedra.syntax.grammar import *


for s in [
    "x",
    "(2/3)x",
    "(2x+1)",
    "1+10+2x",
    "1+2x-10",
    "1+2x-10",
    "3(2x+1)",
    "-x+2(1+x)",
    "(4y + 5t)+2(4y + 5t)",
    "(4y + 5t)+2(4(y) + 5t)",
    "(4y + 5t)+2(4(y+t) + t)"
]:
    print(f"\nterms: {s}")
    tokens = terms.parse_string(s, parse_all=True)
    print(tokens)


for s in [
    "|x|",
    "|1+x|",
    "|1-(x-y)|",
    "|1-(x-y)-y|",
    "|1-(x-y)+y|",
    "|-x|",
    "|1-x|",
    "|x + 3|",
]:
    print(f"\nabs_term: {s}")
    tokens = abs_term.parse_string(s, parse_all=True)
    print(tokens)


for s in [
    "|-x + 3|",
    "(|-x + 3|)",
    "1|-x + 3|",
    "|4*y + 5t -y |",
    "3|4y + 5t -y |",
    "(|4y + 5t -y |)",
    "2*(|4y + 5t -y |)",
    "2(|4y + 5t -y |)",
    "3|-(4y + 5t) -y |",
    "|4y - y + 5t |",
    "|-5 -x + 3 + 4x|",
    "2.0|-x + 3|",
    "|-x + 3|",
]:
    print(f"\nfirst_paren_abs_or_terms: {s}")
    tokens = first_paren_abs_or_terms.parse_string(s, parse_all=True)
    print(tokens)


for s in [
    "|-x + 3|",
    "+|-x + 3|",
    "|4y + 5t -y |",
    "3|4y + 5t -y |",
    "(|4y + 5t -y |)",
    "2(|4y + 5t -y |)+(|4y + 5t -y |)",
    "2*(|4y + 5t -y |)+(|4y + 5t -y |)",
    "|4y - y + 5t |",
    "|-5 -x + 3 + 4x|",
    "2.0|-x + 3|",
    "5t + |-x + 3|",
    "|-x + 3| + 5t",
    "-1 + |-x + 3| + 5t",
    "t -1 + 2|-x + 3| + 4t",
    "-5 + 3|-x + 3| + 5t",
    "|-x + 3| + 3 |4y + 5t| - 7z",
]:
    print(f"\nmulti_paren_abs_or_terms: {s}")
    tokens = multi_paren_abs_or_terms.parse_string(s, parse_all=True)
    print(tokens)


for s in [
    "2|x| <= 0",
    "2|x| <= (1/3)",
    "2|x| <= (1/3-2)",
    "|x| <= 2|x|",
    "3|x| + y >= 3|y|",
    "|-x + 3| + 3 |4y + 5t| - 7z <= 8t - |x - y|",
    "|-x + 3| + 2(|4y + 5t| - 7z) + (|4y + 5t| - 7z) <= 8t - |x - y|",
    "|-x + 3| + 3 |(4*y + 5t)+2(4y + 5t)| - 7z <= 8t - |x - y|",
    "|- 2 -x + 3 + 6x | <= + 3 |4y + 5t -y | - 7z <= 8t - |x - y| <= 10",
    "|- 2 -x + 3 + 6x | <= - |4y + 5t -y | - 7z - 4 |4y + 5t -y |<= 8t - |x - y| <= 10",
]:
    print(f"\nexpression: {s}")
    result = expression.parseString(s, parse_all=True)
    print(result)


