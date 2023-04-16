# Syntax for Pacti's PolyhedralTerms

The `pacti.terms.polyhedra.PolyhedralContract.from_string()` API invokes a parser for `pacti.terms.polyhedra.PolyhedralTerm` to construct the assumptions and guarantees of a `PolyhedralContract`. The syntactic `expression` of a `PolyhedralTerm` is defined by the following BNF grammar in the `pacti.terms.polyhedra.grammar` module:

```text

variable = ('a'..'z' | 'A'..'Z'), ('a'..'z' | 'A'..'Z' | '0'..'9' | '_')*;

floating_point_number = '0'..'9'+, ("." , '0'..'9'+)?, (("e" | "E"), ("-" | "+")?, '0'..'9'+)?;

number_and_variable = floating_point_number, ("*" , variable)?;

term = variable | floating_point_number | number_and_variable;

first_term = ("-" | "+")?, term;

signed_term = ("-" | "+") , term;

terms = first_term, signed_term*;

abs_term = floating_point_number?, "|" , terms , "|";

positive_abs_term = "+" , abs_term;

first_abs_term = ("+" , abs_term)?;

first_abs_or_term = first_abs_term | first_term;

addl_abs_or_term = positive_abs_term | signed_term;

abs_or_terms = first_abs_or_term, addl_abs_or_term*;

equality_operator = "==" | "=";

equality_expression = abs_or_terms, equality_operator, abs_or_terms;

leq_expression = abs_or_terms, ("<=" , abs_or_terms)+;

geq_expression = abs_or_terms, (">=" , abs_or_terms)+;

expression = equality_expression | leq_expression | geq_expression;
```

Parsing rules produce an intermediate representation that facilitates performing symbolic simplifications as described below:

- The parsing of a `term`, `first_term`, or `signed_term` each produces a `pacti.terms.polyhedra.grammar.Term`, which represents:
   - A multiplicative `coefficient` floating-point number.
   - An optional `variable` name.

- The parsing of a `terms` produces a `pacti.terms.polyhedra.grammar.TermList`, which represents the simplified combination of:
   - An additive `constant` floating-point number.
   - A `factors` dictionary of variables (keys) and their multiplicative coefficients (values).

- The parsing of `abs_term`, `positive_abs_term`, or `first_abs_term` each produces a `pacti.terms.polyhedra.grammar.AbsoluteTerm`, which represents:
    - An optional multiplicative `coefficient` floating-point number.
    - A `term_list`, which is the simplified `pacti.terms.polyhedra.grammar.TermList` of all terms between the absolute bars.

- The parsing of `first_abs_or_term` or `addl_abs_or_term` each produces a `pacti.terms.polyhedra.grammar.AbsoluteTermOrTerm`, which represents the union of `AbsoluteTerm` and `Term` as the constituents of the side of an `expression`.

- The parsing of `abs_or_terms` produces a `pacti.terms.polyhedra.grammar.AbsoluteTermList`, which represents the simplified additive list of `AbsoluteTerm` and `Term` via:
   - A `term_list`, which is a `pacti.terms.polyhedra.grammar.TermList` that additively represents all `Term` contituents.
   - A `absolute_term_list`, which is the additively-reduced list of `AbsoluteTerm` constituents.

- The parsing of `expression` produces an `pacti.terms.polyhedra.grammar.Expression` that, in the serializer module, is converted to a `pacti.terms.polyhedra.PolyhedralTerm`. The parser handles three forms of `expression`:
   - The parsing of `equality_expression` handles the syntax of equality expressions of the form: `LHS ('==' | '=') RHS` where `LHS` and `RHS` are parsed as `abs_or_terms`.
   - The parsing of `leq_expression` handles the syntax of less-than-or-equal expressions of the form: `LEQ1 ( '<=' LEQi )+` where all `LEQi` for `i=1..n (n>1)` are parsed as `abs_or_terms`.
   - The parsing of `geq_expression` handles the syntax of greater-than-or-equal expressions of the form: `GEQ1 ('>=' GEQi )+` where all `GEQi` for `i=1..n (n>1)` are parsed as `abs_or_terms`.

The `pacti.terms.polyhedra.serializer` module provides the conversion of `pacti.terms.polyhedra.grammar.Expression` to `pacti.terms.polyhedra.PolyhedralTerm` according to the form of the `expression`:

- An `equality_expression` converts the two `AbsoluteTermList` sides `LHS` and `RHS` into `pts`, a list of `PolyhedralTerm`, as follows:

   - The expansion of a `AbsoluteTermList` that has `n` `AbsoluteTerm` is a `2^n` list of `TermList` resulting from all positive/negative combinations of the `TermList` of each `AbsoluteTerm`. This expansion is performed as follows:
  
  - If the `LHS` is not a constant (i.e, it has either `TermList` factors or at least one `AbsoluteTerm`), create an `AbsoluteTermList`, `lhs_minus_rhs` as `LHS + (-RHS)` and expand it.
     - Append to `pts` each expansion of `lhs_minus_rhs`
     - If `lhs_minus_rhs` has non-absolute terms, append to `pts` the negation of each expansion as well.
  
  - If the `RHS` is not a constant (i.e, it has either `TermList` factors or at least one `AbsoluteTerm`), create an `AbsoluteTermList`, `rhs_minus_lhs` as `RHS + (-lHS)` and expand it.
     - Append to `pts` each expansion of `rhs_minus_lhs`
     - If `rhs_minus_lhs` has non-absolute terms, append to `pts` the negation of each expansion as well.
  
- An `leq_expression` converts a list of `n` `AbsoluteTermList` sides, `LEQi` for `i=1..n`, interleaved with `<=` operators into `n-1` `PolyhedralTerm` as `LEQi - LEQi+1 <= 0` for `i=1..n-1`.

- A `geq_expression` converts a list of `n` `AbsoluteTermList` sides, `GEQi` for `i=1..n`, interleaved with `>=` operators into `n-1` `PolyhedralTerm` as `- GEQi + +GEQi+1 <= 0` for `i=1..n-1`.

