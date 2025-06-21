"""
Support for SMT constraints.

Module provides support for SMT expressions as constraints.
"""

from __future__ import annotations

import copy
from functools import reduce
from typing import Dict, List, Optional, Tuple, Union

import z3

from pacti.iocontract import TacticStatistics, Term, TermList, Var
from pacti.utils.lists import list_diff, list_intersection, list_remove_indices, list_union

numeric = Union[int, float]


def _get_smt_real_variable(name: str) -> z3.ArithRef:
    return z3.Real(name)


def _rename_expr(expression: z3.BoolRef, oldvarstr: str, newvarstr: str) -> z3.BoolRef:
    oldvar = _get_smt_real_variable(oldvarstr)
    newvar = _get_smt_real_variable(newvarstr)
    return z3.substitute(expression, (oldvar, newvar))


def _replace_var_with_val(expression: z3.BoolRef, varstr: str, value: numeric) -> z3.BoolRef:
    vartomodify = _get_smt_real_variable(varstr)
    valuetoapply = z3.RealVal(value)
    return z3.substitute(expression, (vartomodify, valuetoapply))


def _is_tautology(expression: z3.BoolRef) -> bool:
    """
    Tell whether term is a tautology.

    Args:
        expression: An SMT expression to verify.

    Returns:
        True if the term is a tautology.

    Raises:
        ValueError: analysis failed.
    """
    try:
        return not _is_sat(z3.Not(expression))
    except ValueError as e:
        raise ValueError(e)


def _is_sat(expression: z3.BoolRef) -> bool:
    """
    Tell whether term is SAT.

    Args:
        expression: An SMT expression to verify.

    Returns:
        True if satisfiable.

    Raises:
        ValueError: analysis failed.
    """
    s = z3.Solver()
    s.add(expression)
    result = s.check()
    if result == z3.sat:
        return True
    elif result == z3.unknown:
        raise ValueError("SMT solver could not check formula")
    return False


def _get_z3_literals(z3expression: z3.BoolRef) -> List[str]:
    if not z3.is_bool(z3expression) and not z3.is_arith(z3expression):
        raise ValueError(f"Expression was type {type(z3expression)}")
    children = z3expression.children()
    if len(children) == 0:
        if z3.is_rational_value(z3expression) or z3.is_algebraic_value(z3expression):
            return []
        return [str(z3expression)]
    return reduce(lambda a, b: a + b, map(_get_z3_literals, z3expression.children()))


def _eliminate_quantifiers(expression: z3.QuantifierRef) -> z3.BoolRef:
    t = z3.Tactic("qe")
    simplified_term = t(expression)[0]
    if len(simplified_term) > 0:
        full_term = z3.simplify(z3.And(*simplified_term))
    else:
        full_term = z3.RealVal(1) == z3.RealVal(1)
    return full_term


def _elim_by_refinement(
    expr_to_refine: z3.BoolRef, context_expr: z3.BoolRef, variables_to_elim: List[str]
) -> z3.BoolRef:
    elimination_term: z3.BoolRef = z3.Implies(context_expr, expr_to_refine)
    quantified_atoms = [_get_smt_real_variable(atm) for atm in variables_to_elim]
    full_term = z3.ForAll(quantified_atoms, elimination_term)
    return _eliminate_quantifiers(full_term)


def _elim_by_relaxing(expr_to_refine: z3.BoolRef, context_expr: z3.BoolRef, variables_to_elim: List[str]) -> z3.BoolRef:
    elimination_term: z3.BoolRef = z3.And(context_expr, expr_to_refine)
    quantified_atoms = [_get_smt_real_variable(atm) for atm in variables_to_elim]
    full_term = z3.Exists(quantified_atoms, elimination_term)
    return _eliminate_quantifiers(full_term)


def _elim_variables(
    expr_to_refine: z3.BoolRef, context_expr: z3.BoolRef, variables_to_elim: List[str], refine: bool
) -> z3.BoolRef:
    if refine:
        new_expr = _elim_by_refinement(expr_to_refine, context_expr, variables_to_elim)
    else:
        new_expr = _elim_by_relaxing(expr_to_refine, context_expr, variables_to_elim)
    return new_expr


class SmtTerm(Term):
    """SMT terms."""

    def __init__(self, expression: z3.BoolRef):  # noqa: WPS231  too much cognitive complexity
        """
        Constructor for SmtTerm.

        Usage:
            SMT terms are initialized by passing an SMT expression.

        Args:
            expression: A boolean expression involving uninterpreted atoms.

        Raises:
            ValueError: Unsupported argument type.
        """
        self.expression: z3.BoolRef
        if isinstance(expression, z3.BoolRef):
            self.expression = copy.deepcopy(expression)
        else:
            raise ValueError()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            raise ValueError()
        return str(self) == str(other)

    def __str__(self) -> str:
        # return SmtTerm.add_globally(_expr_to_str(self.expression))
        return str(self.expression)

    def __hash__(self) -> int:
        return hash(str(self))

    def __repr__(self) -> str:
        return "<Term {0}>".format(self)

    @property
    def atoms(self) -> List[str]:  # noqa: A003
        """
        Atoms appearing in term.

        Returns:
            List of atoms referenced in term.
        """
        return _get_z3_literals(self.expression)

    @property
    def vars(self) -> List[Var]:  # noqa: A003
        """
        Variables appearing in term.

        Returns:
            List of variables referenced in term.
        """
        return [Var(atom) for atom in self.atoms]

    def contains_var(self, var_to_seek: Var) -> bool:
        """
        Tell whether term contains a given variable.

        Args:
            var_to_seek: The variable that we are seeking in the current term.

        Returns:
            `True` if the syntax of the term refers to the given variable;
                `False` otherwise.
        """
        return var_to_seek in self.vars

    def copy(self) -> SmtTerm:
        """
        Generates copy of term.

        Returns:
            Copy of term.
        """
        expression = copy.deepcopy(self.expression)
        return SmtTerm(expression)

    def rename_variable(self, source_var: Var, target_var: Var) -> SmtTerm:
        """
        Rename a variable in a term.

        Args:
            source_var: The variable to be replaced.
            target_var: The new variable.

        Returns:
            A term with `source_var` replaced by `target_var`.
        """
        ret_expr = _rename_expr(self.expression, source_var.name, target_var.name)
        return SmtTerm(ret_expr)

    def is_tautology(self) -> bool:
        """
        Tell whether term is a tautology.

        Returns:
            True if tautology.
        """
        return _is_tautology(self.expression)

    def is_sat(self) -> bool:
        """
        Tell whether term is a satisfiable.

        Returns:
            True if satisfiable.
        """
        return _is_sat(self.expression)

    def contains_behavior(self, behavior: Dict[Var, numeric]) -> bool:
        """
        Tell whether Term contains the given behavior.

        Args:
            behavior:
                The behavior in question.

        Returns:
            True if the behavior satisfies the constraint; false otherwise.

        Raises:
            ValueError: Not all variables in the constraints were assigned values.
        """
        variables_to_substitute: List[Var] = list(behavior.keys())
        if list_diff(self.vars, variables_to_substitute):
            raise ValueError("Not all variables assigned")

        new_expression = copy.deepcopy(self.expression)
        relevant_variables: List[Var] = list_intersection(variables_to_substitute, self.vars)
        for elim_var in relevant_variables:
            new_expression = _replace_var_with_val(new_expression, elim_var.name, behavior[elim_var])
        return _is_tautology(new_expression)


class SmtTermList(TermList):  # noqa: WPS338
    """A TermList of SmtTerm instances."""

    def __init__(self, terms: Optional[List[SmtTerm]] = None):
        """
        Constructor for SmtTermList.

        Args:
            terms: A list of SmtTerm objects.

        Raises:
            ValueError: incorrect argument type provided.
        """
        if terms is None:
            self.terms = []
        elif all(isinstance(t, SmtTerm) for t in terms):
            self.terms = terms.copy()
        else:
            raise ValueError("SmtTermList constructor argument must be a list of SmtTerms.")

    def __str__(self) -> str:
        res = "[\n  "
        res += "\n  ".join(self.to_str_list())
        res += "\n]"
        return res

    def __hash__(self) -> int:
        return hash(tuple(self.terms))

    def __le__(self, other: SmtTermList) -> bool:
        return self.refines(other)

    def is_semantically_equivalent_to(self, other: SmtTermList) -> bool:
        """
        Tell whether two termlists are semantically equivalent.

        Args:
            other:
                The termslist against which we compare self.

        Returns:
            True if the two termlists are semantically equivalent.
        """
        return self.refines(other) and other.refines(self)

    def to_str_list(self) -> List[str]:
        """
        Convert termlist into a list of strings.

        Returns:
            A list of strings corresponding to the terms of the termlist.
        """
        return [str(term) for term in self.terms]

    def contains_behavior(self, behavior: Dict[Var, numeric]) -> bool:
        """
        Tell whether TermList contains the given behavior.

        Args:
            behavior:
                The behavior in question.

        Returns:
            True if the behavior satisfies the constraints; false otherwise.

        Raises:
            ValueError: Not all variables in the constraints were assigned values.
        """
        for term in self.terms:
            try:
                if not term.contains_behavior(behavior):
                    return False
            except ValueError as e:
                raise ValueError(e)
        return True

    def _to_smtexpr(self) -> z3.BoolRef:
        return z3.And(*[xs.expression for xs in self.terms])

    @staticmethod
    def _transform_term(  # noqa: WPS231  too much cognitive complexity
        term: SmtTerm,
        context: SmtTermList,
        vars_to_elim: list,
        refine: bool,
        simplify: bool = True,
        tactics_order: Optional[List[int]] = None,
    ) -> Tuple[SmtTerm, SmtTermList]:
        new_term: SmtTerm

        # Check whether there is something to do with this term
        if list_intersection(vars_to_elim, term.vars):
            atoms_to_elim = list(map(str, list_intersection(vars_to_elim, list_union(term.vars, context.vars))))
            reference_term = SmtTerm(_elim_variables(term.expression, context._to_smtexpr(), atoms_to_elim, refine))
            new_term = reference_term.copy()
            final_context = context.copy()

            # now check whether we can find equivalent "in-context" semantics using a reduced context
            if simplify:
                golden_compare = context | SmtTermList([reference_term])
                indices_removed: List[int] = []
                for i, _ in enumerate(context.terms):
                    test_context = SmtTermList(list_remove_indices(context.terms, indices_removed + [i]))
                    test_term = SmtTerm(
                        _elim_variables(term.expression, test_context._to_smtexpr(), atoms_to_elim, refine)
                    )
                    test_compare = context | SmtTermList([test_term])

                    if (golden_compare).is_semantically_equivalent_to(test_compare):
                        indices_removed.append(i)
                        new_term = test_term.copy()
                        final_context = test_context.copy()
        else:
            new_term = term.copy()
            final_context = context.copy()
        if not new_term.is_sat():
            raise ValueError("Computed term is empty")
        return new_term, final_context

    def _transform_termlist(  # noqa: WPS231  too much cognitive complexity
        self,
        context: SmtTermList,
        vars_to_elim: list,
        refine: bool,
        simplify: bool = True,
        tactics_order: Optional[List[int]] = None,
    ) -> Tuple[SmtTermList, TacticStatistics]:
        new_terms = []

        # only keep the context with relevant variables
        relevant_terms = []
        for term in context.terms:
            if list_intersection(term.vars, vars_to_elim):
                relevant_terms.append(term)
        relevant_context = SmtTermList(relevant_terms)

        for term in self.terms:
            try:
                new_term, _ = SmtTermList._transform_term(
                    term, relevant_context, vars_to_elim, refine, simplify, tactics_order
                )
            except ValueError as e:
                raise ValueError(e)
            new_terms.append(new_term)
        return SmtTermList(new_terms), []

    def elim_vars_by_refining(  # noqa: WPS231  too much cognitive complexity
        self,
        context: SmtTermList,
        vars_to_elim: list,
        simplify: bool = True,
        tactics_order: Optional[List[int]] = None,
    ) -> Tuple[SmtTermList, TacticStatistics]:
        """
        Eliminate variables from SmtTermList by refining it in context.

        Example:
            Suppose the current list of terms is $\\{x + y \\le 6\\}$, the
            context is $\\{y \\le 5\\}$, and the resulting terms should not
            contain variable $y$. Then the current TermList could be
            refined to $\\{x \\le 1\\}$ because $x \\le 1
            \\;\\land\\; y \\le 5 \\Rightarrow x + y \\le 6$.

        Args:
            context:
                The TermList providing the context for the refinement.
            vars_to_elim:
                Variables that should not appear in the resulting term.
            simplify:
                Whether to perform simplifications.
            tactics_order:
                Optionally, the order of tactics to invoke during transformation.

        Returns:
            A tuple of (a) a list of terms not containing any variables in `vars_to_elim`
                and which, in the context provided, imply the terms contained in the
                calling termlist; and (b) the list of tuples, for each processed term, of
                the tactic used, time spend, and tactic invocation count.

        Raises:
            ValueError: Self has empty intersection with its context.
        """
        try:
            return self._transform_termlist(
                context=context, vars_to_elim=vars_to_elim, refine=True, simplify=simplify, tactics_order=tactics_order
            )
        except ValueError as e:
            raise ValueError(e)

    def elim_vars_by_relaxing(
        self,
        context: SmtTermList,
        vars_to_elim: list,
        simplify: bool = True,
        tactics_order: Optional[List[int]] = None,
    ) -> Tuple[SmtTermList, TacticStatistics]:
        """
        Eliminate variables from SmtTemList by abstracting it in context.

        Example:
            Suppose the current list of terms is $\\{x - y \\le 6\\}$, the
            context is $\\{y \\le 5\\}$, and the resulting terms should not
            contain variable $y$. Then the current TermList could be
            relaxed to $\\{x \\le 11\\}$ because $x - y \\le 6
            \\;\\land\\; y \\le 5 \\Rightarrow x \\le 11$.

        Args:
            context:
                The TermList providing the context for the transformation.
            vars_to_elim:
                Variables that should not appear in the relaxed terms.
            simplify:
                Whether to perform simplifications.
            tactics_order:
                Optionally, the order of tactics to invoke during transformation.

        Returns:
            A tuple of (a) a list of terms not containing any variables in `vars_to_elim`
                and which, in the context provided, are implied by the terms
                contained in the calling termlist; and (b) the list of tuples, for each
                processed term, of the tactic used, time spend, and tactic invocation count.
        """
        return self._transform_termlist(
            context=context, vars_to_elim=vars_to_elim, refine=False, simplify=simplify, tactics_order=tactics_order
        )

    def simplify(self, context: Optional[SmtTermList] = None) -> SmtTermList:
        """
        Remove redundant terms in the TermList using the provided context.

        Example:
            Suppose the TermList is $\\{x - 2y \\le 5, x - y \\le 0\\}$ and
            the context is $\\{x + y \\le 0\\}$. Then the TermList could be
            simplified to $\\{x - y \\le 0\\}$.

        Args:
            context:
                The TermList providing the context for the simplification.

        Returns:
            A new TermList with redundant terms removed using the provided context.
        """
        newterms: List[SmtTerm] = []
        external_context = SmtTermList([])
        if context:
            external_context = context
        for i, term_under_analysis in enumerate(self.terms):
            useful_context = SmtTermList(newterms) | SmtTermList(self.terms[i + 1 :]) | external_context
            if not useful_context.refines(SmtTermList([term_under_analysis])):
                newterms.append(term_under_analysis.copy())
        return SmtTermList(newterms)

    def refines(self, other: SmtTermList) -> bool:
        """
        Tells whether the argument is a larger specification.

        Args:
            other:
                TermList against which we are comparing self.

        Returns:
            self <= other
        """
        antecedent = self._to_smtexpr()
        consequent = other._to_smtexpr()
        test_expr: z3.BoolRef = z3.Implies(antecedent, consequent)
        return _is_tautology(test_expr)

    def is_empty(self) -> bool:
        """
        Tell whether the argument has no satisfying assignments.

        Returns:
            True if constraints cannot be satisfied.
        """
        test_expr = self._to_smtexpr()
        if _is_sat(test_expr):  # noqa: WPS531 if condition can be simplified
            return False
        return True
