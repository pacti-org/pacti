# Syntax for Pacti's PolyhedralTerms

The `pacti.terms.polyhedra.PolyhedralContract.from_string()` API invokes a parser for `pacti.terms.polyhedra.PolyhedralTerm` to construct the assumptions and guarantees of a `PolyhedralContract`. The syntactic `expression` of a `PolyhedralTerm` is defined by the following BNF grammar:

```text
expression = equality_expression | leq_expression | geq_expression;

equality_expression = abs_or_terms, equality_operator, abs_or_terms;

equality_operator = "==" | "=";

leq_expression = abs_or_terms, ("<=" , abs_or_terms)+;

geq_expression = abs_or_terms, (">=" , abs_or_terms)+;

abs_or_terms = first_abs_or_term, addl_abs_or_term*;

first_abs_or_term = first_abs_term | first_term;

first_abs_term = ("+" , abs_term)?;

first_term = ("-" | "+")?, term;

addl_abs_or_term = positive_abs_term | signed_term;

positive_abs_term = "+" , abs_term;

signed_term = ("-" | "+") , term;

abs_term = floating_point_number?, "|" , terms , "|";

terms = first_term, signed_term*;

term = variable | floating_point_number | number_and_variable;

variable = ('a'..'z' | 'A'..'Z'), ('a'..'z' | 'A'..'Z' | '0'..'9' | '_')*;

floating_point_number = '0'..'9'+, ("." , '0'..'9'+)?, (("e" | "E"), ("-" | "+")?, '0'..'9'+)?;

number_and_variable = floating_point_number, ("*" , variable)?;
```


