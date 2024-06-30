"""
Support for linear inequality constraints, i.e., polyhedra.

Module provides support for linear inequalities as constraints, i.e.,
the constraints are of the form $\\sum_{i} a_i x_i \\le c$, where the
$x_i$ are variables and the $a_i$ and $c$ are constants.
"""

from __future__ import annotations

import copy
import re
from typing import Dict, List, Optional, Tuple, Union

import pyeda.boolalg

from pacti.iocontract import TacticStatistics, Term, TermList, Var
from pacti.utils.lists import list_intersection

numeric = Union[int, float]


class PropositionalTerm(Term):
    """Polyhedral terms are linear inequalities over a list of variables."""

    # Constructor: get (i) a dictionary whose keys are variables and whose
    # values are the coefficients of those variables in the term, and (b) a
    # constant. The term is assumed to be in the form \Sigma_i a_i v_i +
    # constant <= 0
    def __init__(self, expression: str | pyeda.boolalg.expr.Expression):
        """
        Constructor for PropositionalTerm.

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
            variables: A dictionary mapping Var keys to numeric values.
            constant: A numeric value on the right of the inequality.

        Raises:o
            ValueError: Unsupported argument type.
        """
        self.expression: pyeda.boolalg.expr.Expression
        if isinstance(expression, pyeda.boolalg.expr.Expression):
            self.expression = copy.copy(expression)
        elif isinstance(expression, str):
            if expression == "":
                self.expression = pyeda.boolalg.expr.expr("1")
            else:
                # extract the uninterpreted terms
                new_expr = copy.copy(expression)
                atoms = re.findall(r"\w+\s*\(.*?\)", new_expr)
                tvars = [f"_xtempvar{i}" for i in range(len(atoms))]
                for i, atom in enumerate(atoms):
                    new_expr = new_expr.replace(atom, tvars[i])
                eda_expression = pyeda.boolalg.expr.Expression(new_expr)
                for i, atom in enumerate(atoms):
                    eda_expression = PropositionalTerm._rename_expr(eda_expression, tvars[i], atom)
                self.expression = eda_expression
        else:
            raise ValueError()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            raise ValueError()
        return str(self) == str(other)

    def __str__(self) -> str:
        return str(self.expression)

    def __hash__(self) -> int:
        return hash(str(self))

    def __repr__(self) -> str:
        return "<Term {0}>".format(self)

    def copy(self) -> PropositionalTerm:
        """
        Generates copy of polyhedral term.

        Returns:
            Copy of term.
        """
        newterm = PropositionalTerm("")
        newterm.expression = copy.copy(self.expression)
        return newterm

    def rename_variable(self, source_var: Var, target_var: Var) -> PropositionalTerm:
        """
        Rename a variable in a term.

        Args:
            source_var: The variable to be replaced.
            target_var: The new variable.

        Returns:
            A term with `source_var` replaced by `target_var`.
        """
        ret_expr = PropositionalTerm._rename_expr(self.expression, source_var.name, target_var.name)
        return PropositionalTerm(ret_expr)

    @classmethod
    def _rename_expr(
        cls, expression: pyeda.boolalg.expr.Expression, oldvarstr: str, newvarstr: str
    ) -> pyeda.boolalg.expr.Expression:
        oldvar = pyeda.boolalg.expr.exprvar(oldvarstr)
        newvar = pyeda.boolalg.expr.exprvar(newvarstr)
        if isinstance(expression, pyeda.boolalg.expr.Atom):
            if isinstance(expression, pyeda.boolalg.expr.Variable):
                if expression == oldvar:
                    return newvar
            if isinstance(expression, pyeda.boolalg.expr.Complement):
                if expression == pyeda.boolalg.expr.Not(oldvar):
                    return pyeda.boolalg.expr.Not(newvar)
            return expression
        elif isinstance(expression, pyeda.boolalg.expr.NotOp):
            nxs = pyeda.boolalg.expr.Expression.box(
                PropositionalTerm._rename_expr(expression.xs[0], oldvar, newvar)
            ).node
            return pyeda.boolalg.expr._expr(pyeda.boolalg.exprnode.not_(nxs))
        elif isinstance(expression, pyeda.boolalg.expr.ImpliesOp):
            nxs = [
                pyeda.boolalg.expr.Expression.box(PropositionalTerm._rename_expr(x, oldvar, newvar)).node
                for x in expression.xs
            ]
            return pyeda.boolalg.expr._expr(pyeda.boolalg.exprnode.impl(*nxs))
        elif isinstance(expression, pyeda.boolalg.expr.AndOp):
            nxs = [
                pyeda.boolalg.expr.Expression.box(PropositionalTerm._rename_expr(x, oldvar, newvar)).node
                for x in expression.xs
            ]
            return pyeda.boolalg.expr._expr(pyeda.boolalg.exprnode.and_(*nxs))
        elif isinstance(expression, pyeda.boolalg.expr.OrOp):
            nxs = [
                pyeda.boolalg.expr.Expression.box(PropositionalTerm._rename_expr(x, oldvar, newvar)).node
                for x in expression.xs
            ]
            return pyeda.boolalg.expr._expr(pyeda.boolalg.exprnode.or_(*nxs))
        raise ValueError()

    @property
    def atoms(self) -> List[str]:  # noqa: A003
        """
        Atoms appearing in term.

        Returns:
            List of atoms referenced in term.
        """
        return [x.name for x in self.expression.inputs]

    @property
    def vars(self) -> List[Var]:  # noqa: A003
        """
        Variables appearing in term.

        Returns:
            List of variables referenced in term.
        """
        atoms = self.atoms
        variables : List[Var] = []
        for atom in atoms:
            variables = variables + PropositionalTerm._get_atom_variables(atom)
        return variables

    @classmethod
    def _get_atom_variables(cls, atom: str) -> List[Var]:
        variables = []
        m = re.match(r"(\w+)\s*\((.*?)\)", atom)
        if m:
            # observe that we are not yet using the name of the
            # uninterpreted function, which is stored in m.group(1)
            args = m.group(2).split(",")
            for arg in args:
                variables.append(Var(arg.strip()))
        else:
            variables.append(Var(atom))
        return variables

    @classmethod
    def _atom_has_variables(cls, atom: str, var_list: List[Var]) -> bool:
        atoms_vars = PropositionalTerm._get_atom_variables(atom)
        return len(list_intersection(atoms_vars, var_list)) > 0

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


class PropositionalTermList(TermList):  # noqa: WPS338
    """A TermList of PolyhedralTerm instances."""

    def __init__(self, terms: Optional[List[PropositionalTerm]] = None):
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
        elif all(isinstance(t, PropositionalTerm) for t in terms):
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

    def to_str_list(self) -> List[str]:
        """
        Convert termlist into a list of strings.

        Returns:
            A list of strings corresponding to the terms of the termlist.
        """
        return [str(term.expression) for term in self.terms]

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
        raise ValueError("Not implemented")

    def elim_vars_by_refining(
        self,
        context: PropositionalTermList,
        vars_to_elim: list,
        simplify: bool = True,
        tactics_order: Optional[List[int]] = None,
    ) -> Tuple[PropositionalTermList, TacticStatistics]:
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
            new_term: PropositionalTerm
            if list_intersection(vars_to_elim, term.vars):
                atoms_to_elim = []
                for atom in term.atoms:
                    if PropositionalTerm._atom_has_variables(atom, vars_to_elim):
                        atoms_to_elim.append(atom)
                context_expr = pyeda.boolalg.expr.And(*context.terms)
                elimination_term: pyeda.boolalg.expr.Expression = pyeda.boolalg.expr.Implies(context_expr, term)
                elimination_term = elimination_term.consensus(
                    vs=[pyeda.boolalg.expr.exprvar(atm) for atm in atoms_to_elim]
                )
                # make sure the result is not empty
                test_expr: pyeda.boolalg.expr.Expression = pyeda.boolalg.expr.And(context_expr, elimination_term)
                if not test_expr.satisfy_one():
                    raise ValueError(
                        f"The variables {vars_to_elim} cannot be eliminated from the term {term} in the context {context}"
                    )
                new_term = PropositionalTerm(elimination_term)
            else:
                new_term = term.copy()
            new_terms.append(new_term)
        return (PropositionalTermList(new_terms), [])

    def elim_vars_by_relaxing(
        self,
        context: PropositionalTermList,
        vars_to_elim: list,
        simplify: bool = True,
        tactics_order: Optional[List[int]] = None,
    ) -> Tuple[PropositionalTermList, TacticStatistics]:
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

        Raises:
            ValueError: Constraints have empty intersection with context.
        """
        new_terms = []
        for term in self.terms:
            new_term: PropositionalTerm
            if list_intersection(vars_to_elim, term.vars):
                atoms_to_elim = []
                for atom in term.atoms:
                    if PropositionalTerm._atom_has_variables(atom, vars_to_elim):
                        atoms_to_elim.append(atom)
                context_expr = pyeda.boolalg.expr.And(*context.terms)
                elimination_term: pyeda.boolalg.expr.Expression = pyeda.boolalg.expr.And(context_expr, term)
                elimination_term = elimination_term.smoothing(
                    vs=[pyeda.boolalg.expr.exprvar(atm) for atm in atoms_to_elim]
                )
                # make sure the result is not empty
                # test_expr : pyeda.boolalg.expr.Expression = pyeda.boolalg.expr.And(context_expr, elimination_term)
                # if not test_expr.satisfy_one():
                #    raise ValueError(f"The variables {vars_to_elim} cannot be eliminated
                #    from the term {term} in the context {context}")
                new_term = PropositionalTerm(elimination_term)
            else:
                new_term = term.copy()
            new_terms.append(new_term)
        return (PropositionalTermList(new_terms), [])

    def simplify(self, context: Optional[PropositionalTermList] = None) -> PropositionalTermList:
        """
        Remove redundant terms in the PolyhedralTermList using the provided context.

        Example:
            Suppose the TermList is $\\{x - 2y \\le 5, x - y \\le 0\\}$ and
            the context is $\\{x + y \\le 0\\}$. Then the TermList could be
            simplified to $\\{x - y \\le 0\\}$.

        Args:
            context:
                The TermList providing the context for the simplification.

        Returns:
            A new PolyhedralTermList with redundant terms removed using the provided context.
        """
        return copy.copy(self)

    def refines(self, other: PropositionalTermList) -> bool:
        """
        Tells whether the argument is a larger specification.

        Args:
            other:
                TermList against which we are comparing self.

        Returns:
            self <= other
        """
        test_expr: pyeda.boolalg.expr.Expression = pyeda.boolalg.expr.Implies(
            pyeda.boolalg.expr.And(*self.terms), pyeda.boolalg.expr.And(*other.terms)
        )
        if pyeda.boolalg.expr.Not(test_expr).satisfy_one():
            return False
        return True

    def is_empty(self) -> bool:
        """
        Tell whether the argument has no satisfying assignments.

        Returns:
            True if constraints cannot be satisfied.
        """
        test_expr: pyeda.boolalg.expr.Expression = pyeda.boolalg.expr.And(*self.terms)
        if test_expr.satisfy_one():
            return False
        return True
