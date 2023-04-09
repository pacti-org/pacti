from pacti.terms.polyhedra.grammar import *

for s in [
    "|-x + 3|",
    "2.0|-x + 3|",
    "5t + |-x + 3|",
    "|-x + 3| + 5t",
    "-1 + |-x + 3| + 5t",
    "-1 + 2|-x + 3| + 5t",
    "-5 + 3|-x + 3| + 5t",
    "|-x + 3| - 3 |4y + 5t| - 7z",
]:
    print(f"\nabs_terms: {s}")
    r = abs_terms.parse_string(s, parse_all=True)
    print(r)


# The generated html is missing the styles to show shapes with a different color than the background.
# https://github.com/pyparsing/pyparsing/blob/efb796099fd77d003dcd49df6a75d1dcc19cefb1/docs/_static/sql_railroad.html#L21-L52

# expression.create_diagram(output_html="expression.html", show_groups=True)

for s in [
    "|-x + 3| - 3 |4y + 5t| - 7z <= 8t + |x - y|",
    "|-x + 3| - 3 |4y + 5t| - 7z == 8t + |x - y|",
    "|-x + 3| - 3 |4y + 5t| - 7z <= 8t + |x - y| <= 10",
]:
    print(f"\nexpression: {s}")
    result = expression.parseString(s, parse_all=True)
    print(result)
