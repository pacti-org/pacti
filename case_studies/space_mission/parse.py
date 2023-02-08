from sympy.parsing.sympy_parser import (parse_expr, lambda_notation, auto_symbol, repeated_decimals, auto_number,
       factorial_notation, implicit_multiplication)
from io import StringIO
from tokenize import (generate_tokens, untokenize, TokenError,
    NUMBER, STRING, NAME, OP, ENDMARKER, ERRORTOKEN, NEWLINE)

# s="a = x"
# [(1, 'a'), (54, '='), (1, 'x'), (4, ''), (0, '')]

# s="|a| = x"
# [(54, '|'), (1, 'a'), (54, '|'), (54, '='), (1, 'x'), (4, ''), (0, '')]

# s="|a| <= x"
# [(54, '|'), (1, 'a'), (54, '|'), (54, '<='), (1, 'x'), (4, ''), (0, '')]

# s="5a <= x"
# [(2, '5'), (1, 'a'), (54, '<='), (1, 'x'), (4, ''), (0, '')]
# 5*a <= x

# s="5.001 x <= 5.2"
# [(2, '5.001'), (1, 'x'), (54, '<='), (2, '5.2'), (4, ''), (0, '')]
# 5.001*x <= 5.2

s="|x-y|<=1"
# [(54, '|'), (1, 'x'), (54, '-'), (1, 'y'), (54, '|'), (54, '<='), (2, '1'), (4, ''), (0, '')]

tokens = []
input_code = StringIO(s.strip())
for toknum, tokval, _, _, _ in generate_tokens(input_code.readline):
  tokens.append((toknum, tokval))

print(tokens)

e = parse_expr(s, transformations=(lambda_notation, auto_symbol, repeated_decimals, auto_number,
       factorial_notation, implicit_multiplication))
print(e)

