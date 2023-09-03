# Syntax for Pacti's PolyhedralTerms

The `pacti.contracts.PolyhedralIoContract.from_strings()` API invokes a parser for `pacti.terms.polyhedra.PolyhedralTerm` to construct the assumptions and guarantees of a `PolyhedralIoContract`. The syntactic `expression` of a `PolyhedralTerm` is defined by the following BNF grammar in the `pacti.terms.polyhedra.syntax.grammar` module:

```text

variable = ('a'..'z' | 'A'..'Z'), ('a'..'z' | 'A'..'Z' | '0'..'9' | '_')*;

floating_point_number = '0'..'9'+, ("." , '0'..'9'+)?, (("e" | "E"), ("-" | "+")?, '0'..'9'+)?;

number_and_variable = floating_point_number, ("*" , variable)?;

term = variable | floating_point_number | number_and_variable | (floating_point_number '*'?)? "(" terms ")";

first_term = ("-" | "+")?, term;

signed_term = ("-" | "+") , term;

terms = first_term, signed_term*;

abs_term = floating_point_number?, "|", terms, "|";

positive_abs_term = "+", abs_term;

first_abs_term = ("+", abs_term)?;

first_abs_or_term = first_abs_term | first_term;

addl_abs_or_term = positive_abs_term | signed_term;

abs_or_terms = first_abs_or_term, addl_abs_or_term*;

paren_abs_or_terms = (floating_point_number, '*'?)?  "(", abs_or_terms, ")";

first_paren_abs_or_terms = "+"? paren_abs_or_terms | first_abs_or_term;

addl_paren_abs_or_terms = "+", paren_abs_or_terms | first_abs_or_term;

multi_paren_abs_or_terms = first_paren_abs_or_terms, addl_paren_abs_or_terms*;

equality_operator = "==" | "=";

equality_expression = multi_paren_abs_or_terms , equality_operator , multi_paren_abs_or_terms;

leq_expression = multi_paren_abs_or_terms , ("<=" , multi_paren_abs_or_terms)+;

geq_expression = multi_paren_abs_or_terms , (">=" , multi_paren_abs_or_terms)+;

expression = equality_expression | leq_expression | geq_expression;
```

Parsing rules produce an intermediate representation that facilitates performing symbolic simplifications as described below:

- The parsing of a `term`, `first_term`, `signed_term`, or `terms` each produces a `pacti.terms.polyhedra.syntax.grammar.PolyhedralSyntaxTermList`, which represents the simplified combination of:
  - An additive `constant` floating-point number.
  - A `factors` dictionary of variables (keys) and their multiplicative coefficients (values).

  This parsing handles parenthesized terms with an optional multiplicative factor.

  Examples:
  - `1+2` is equivalent to `3`, yielding:
    - A `TermList` with `constant=3` and no `factors`.
  - `x+2x` is equivalent to `3x`, yielding:
    - A `TermList` with `constant=0` and `factors={'x'=3}`.
  - `2(x+1)-(2-1+x)` is equivalent to `x+1`, yielding:
    - A `TermList` with `constant=1` and `factors={'x'=1}`.
  - `2(3(t -1)+t)` is equivalent to `8t-6`, yielding:
    - A `TermList` with `constant=-6` and `factors={'t'=7}`.

- The parsing of `abs_term`, `positive_abs_term`, or `first_abs_term` each produces a `pacti.terms.polyhedra.syntax.grammar.PolyhedralSyntaxAbsoluteTerm`, which represents:
  - An optional multiplicative `coefficient` floating-point number.
  - A `term_list`, which is the simplified `pacti.terms.polyhedra.grammar.PolyhedralSyntaxTermList` of all terms between the absolute bars.

  Examples:
  - `|1+2|` is equivalent to `|3|`, yielding:
    - An `AbsoluteTerm` with no `coefficient` and a `term_list` with `constant=3` and no `factors`.
  - `4|x+2x|` is equivalent to `4|3x|`, yielding:
    - An `AbsoluteTerm` with `coefficient=4` and a `term_list` with `constant=0` and no `factors={'x'=3}`.
  
- The parsing of `first_abs_or_term` or `addl_abs_or_term` each produces a `pacti.terms.polyhedra.syntax.grammar.PolyhedralSyntaxAbsoluteTermOrTerm`, which represents the union of `PolyhedralSyntaxAbsoluteTerm` and `PolyhedralSyntaxTermList` as the constituents of the side of an `expression`.

- The parsing of `abs_or_terms` produces a `pacti.terms.polyhedra.grammar.PolyhedralSyntaxAbsoluteTermList`, which represents the simplified additive list of `PolyhedralSyntaxAbsoluteTerm` and `PolyhedralSyntaxTermList` via:
  - A `term_list`, which is a `pacti.terms.polyhedra.syntax.grammar.PolyhedralSyntaxTermList` that additively represents all `PolyhedralSyntaxTermList` contituents.
  - A `absolute_term_list`, which is the additively-reduced list of `PolyhedralSyntaxAbsoluteTerm` constituents.

- The parsing of `paren_abs_or_terms`, `first_paren_abs_or_terms`, `addl_paren_abs_or_terms`, or `multi_paren_abs_or_terms` each produces a `pacti.terms.polyhedra.syntax.grammar.PolyhedralSyntaxAbsoluteTermList` by handling parentheses with an optional positive multiplicative factor.

  Examples:
  - `2(3(t -1)+t) + 2|x - y| + |x - y|` is equivalent to `-6+8t+3|x-y|`, yielding:
    - A `PolyhedralSyntaxAbsoluteTermList` with:
      - A `term_list` with `constant=-6` and `factors={'t': 8}`
      - An `absolute_term_list` with a single `AbsoluteTerm` with:
        - `coefficient=3` and a `term_list` with `constant=0` and `factors={'x':1, 'y':-1}`.
  - `(|-x + 3| + |t+5(y + t)-(y+t)| - z) + 2(|t+5(y + t)-(y+t)| - 3z)` is equivalent to `-7z + |-x + 3| + 3|4y+5t|`, yielding:
    - A `PolyhedralSyntaxAbsoluteTermList` with:
      - A `term_list` with `constant=0` and `factors={'z': -7}`
      - An `absolute_term_list` with two `PolyhedralSyntaxAbsoluteTerm` with:
        - `coefficient=None` and a `term_list` with `constant=-3` and `factors={'x':-1}`;
        - `coefficient=3.0` and a `term_list` with `constant=0` and `factors={'y':4, 't':5}`.

- The parsing of `expression` produces an `pacti.terms.polyhedra.syntax.grammar.PolyhedralSyntaxExpression` that, in the serializer module, is converted to a `pacti.terms.polyhedra.PolyhedralTerm`. The parser handles three forms of `expression`:
  - The parsing of `equality_expression` handles the syntax of equality expressions of the form: `LHS ('==' | '=') RHS` where `LHS` and `RHS` are parsed as `terms`,
    which allows for parenthesis around terms but excludes absolute value terms.
  - The parsing of `leq_expression` handles the syntax of less-than-or-equal expressions of the form: `LEQ_1 ( '<=' LEQ_i )+` where all `LEQ_i` for `i=1..n (n>1)` are parsed as `multi_paren_abs_or_terms`.
  - The parsing of `geq_expression` handles the syntax of greater-than-or-equal expressions of the form: `GEQ_1 ('>=' GEQ_i )+` where all `GEQ_i` for `i=1..n (n>1)` are parsed as `multi_paren_abs_or_terms`.

The `pacti.terms.polyhedra.serializer` module provides the conversion of `pacti.terms.polyhedra.syntax.grammar.PolyhedralSyntaxExpression` to `pacti.terms.polyhedra.PolyhedralTerm` according to the form of the `expression`:

- An `equality_expression` converts the two `PolyhedralSyntaxAbsoluteTermList` sides `LHS` and `RHS` into `pts`, a list of `PolyhedralTerm`, as follows:

  - The expansion of a `PolyhedralSyntaxAbsoluteTermList` that has `n` `AbsoluteTerm` is a `2^n` list of `PolyhedralSyntaxTermList` resulting from all positive/negative combinations of the `PolyhedralSyntaxTermList` of each `PolyhedralSyntaxAbsoluteTerm`. This expansion is performed as follows:
  
  - If the `LHS` is not a constant (i.e, it has either `PolyhedralSyntaxTermList` factors or at least one `PolyhedralSyntaxAbsoluteTerm`), create an `PolyhedralSyntaxAbsoluteTermList`, `lhs_minus_rhs` as `LHS + (-RHS)` and expand it.
    - Append to `pts` each expansion of `lhs_minus_rhs`
    - If `lhs_minus_rhs` has non-absolute terms, append to `pts` the negation of each expansion as well.
  
  - If the `RHS` is not a constant (i.e, it has either `PolyhedralSyntaxTermList` factors or at least one `PolyhedralSyntaxAbsoluteTerm`), create an `PolyhedralSyntaxAbsoluteTermList`, `rhs_minus_lhs` as `RHS + (-lHS)` and expand it.
    - Append to `pts` each expansion of `rhs_minus_lhs`
    - If `rhs_minus_lhs` has non-absolute terms, append to `pts` the negation of each expansion as well.
  
- An `leq_expression` converts a list of `n` `PolyhedralSyntaxAbsoluteTermList` sides, `LEQ_i` for `i=1..n`, interleaved with `<=` operators into `n-1` `PolyhedralTerm` as `LEQ_i - LEQ_i+1 <= <constant_i+1 - constant_i>` for `i=1..n-1`.

- A `geq_expression` converts a list of `n` `PolyhedralSyntaxAbsoluteTermList` sides, `GEQ_i` for `i=1..n`, interleaved with `>=` operators into `n-1` `PolyhedralTerm` as `- GEQ_i + GEQ_i+1 <= <constant_i - constant_i+1>` for `i=1..n-1`.
