"""
Support for SMT constraints.

Module provides support for linear inequalities as constraints, i.e.,
the constraints are of the form $\\sum_{i} a_i x_i \\le c$, where the
$x_i$ are variables and the $a_i$ and $c$ are constants.
"""

from __future__ import annotations

import copy
from functools import reduce
from typing import Dict, List, Optional, Tuple, Union

import z3

from pacti.iocontract import TacticStatistics, Term, TermList, Var
from pacti.utils.lists import list_diff, list_intersection

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
    s = z3.Solver()
    s.add(z3.Not(expression))
    result = s.check()
    if result == z3.unsat:
        return True
    elif result == z3.unknown:
        raise ValueError("SMT solver could not check formula")
    return False


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


class SmtTerm(Term):
    """Polyhedral terms are linear inequalities over a list of variables."""

    # Constructor: get (i) a dictionary whose keys are variables and whose
    # values are the coefficients of those variables in the term, and (b) a
    # constant. The term is assumed to be in the form \Sigma_i a_i v_i +
    # constant <= 0
    def __init__(self, expression: z3.BoolRef):  # noqa: WPS231  too much cognitive complexity
        """
        Constructor for SmtTerm.

        Usage:
            Polyhedral terms are initialized as follows:

            ```
                variables = {Var('x'):2, Var('y'):3}
                constant = 3
                term = PolyhedralTerm(variables, constant)
            ```

            `variables` is a dictionary whose keys are `Var` instances,
            and `constant` is a number. Thus, our example represents the
            expression $2x + 3y \\le 3$.

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

    # @staticmethod

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
        Generates copy of polyhedral term.

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
            True is tautology.
        """
        return _is_tautology(self.expression)

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
    """A TermList of PolyhedralTerm instances."""

    def __init__(self, terms: Optional[List[SmtTerm]] = None):
        """
        Constructor for PolyhedralTermList.

        Usage:
            PolyhedralTermList objects are initialized as follows:

            ```
                term1 = PolyhedralTerm({Var('x'):2, Var('y'):3}, 3)
                term2 = PolyhedralTerm({Var('x'):-1, Var('y'):2}, 4)
                pt_list = [term1, term2]
                termlist = PolyhedralTermList(pt_list)
            ```

            Our example represents the constraints $\\{2x + 3y \\le 3, -x + 2y \\le 4\\}$.

        Args:
            terms: A list of PolyhedralTerm objects.

        Raises:
            ValueError: incorrect argument type provided.
        """
        if terms is None:
            self.terms = []
        elif all(isinstance(t, SmtTerm) for t in terms):
            self.terms = terms.copy()
        else:
            raise ValueError("PolyhedralTermList constructor argument must be a list of PolyhedralTerms.")

    def __str__(self) -> str:
        res = "[\n  "
        res += "\n  ".join(self.to_str_list())
        res += "\n]"
        return res

    def __hash__(self) -> int:
        return hash(tuple(self.terms))

    def __le__(self, other: SmtTermList) -> bool:
        return self.refines(other)

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

    def elim_vars_by_refining(  # noqa: WPS231  too much cognitive complexity
        self,
        context: SmtTermList,
        vars_to_elim: list,
        simplify: bool = True,
        tactics_order: Optional[List[int]] = None,
    ) -> Tuple[SmtTermList, TacticStatistics]:
        """
        Eliminate variables from PolyhedralTermList by refining it in context.

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
        new_terms = []

        for term in self.terms:
            new_term: SmtTerm

            if list_intersection(vars_to_elim, term.vars):
                atoms_to_elim = list_intersection(vars_to_elim, term.vars)
                context_expr = context._to_smtexpr()
                new_expr = _elim_by_refinement(term.expression, context_expr, [atm.name for atm in atoms_to_elim])
                new_term = SmtTerm(new_expr)
            else:
                new_term = term.copy()
            new_terms.append(new_term)
        return SmtTermList(new_terms), []

    def elim_vars_by_relaxing(
        self,
        context: SmtTermList,
        vars_to_elim: list,
        simplify: bool = True,
        tactics_order: Optional[List[int]] = None,
    ) -> Tuple[SmtTermList, TacticStatistics]:
        """
        Eliminate variables from PolyhedralTermList by abstracting it in context.

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
        new_terms = []

        for term in self.terms:
            new_term: SmtTerm

            if list_intersection(vars_to_elim, term.vars):
                atoms_to_elim = list_intersection(vars_to_elim, term.vars)
                context_expr = context._to_smtexpr()
                new_expr = _elim_by_relaxing(term.expression, context_expr, [atm.name for atm in atoms_to_elim])
                new_term = SmtTerm(new_expr)
            else:
                new_term = term.copy()
            new_terms.append(new_term)
        return SmtTermList(new_terms), []

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
        print(f"Checking whether \n{self} refines \n{other}")
        antecedent = self._to_smtexpr()
        consequent = other._to_smtexpr()
        print(antecedent)
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
