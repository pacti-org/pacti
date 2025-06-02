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

import pyeda.boolalg.expr as edaexpr  # noqa: WPS301 allow dotted import
import pyeda.boolalg.exprnode as edaexprnode  # noqa: WPS301 allow dotted import

from pacti.iocontract import TacticStatistics, Term, TermList, Var
from pacti.utils.lists import list_intersection

from ipdb import set_trace as st
#from pacti.diagnostics_config import DIAGNOSTICSFILE as DFILE
DFILE = "kjhnkgbskjhgvbskjhg___"

numeric = Union[int, float]


def _rename_expr(  # noqa: WPS231  too much cognitive complexity
    expression: edaexpr.Expression, oldvarstr: str, newvarstr: str
) -> edaexpr.Expression:
    oldvar = edaexpr.exprvar(oldvarstr)
    newvar = edaexpr.exprvar(newvarstr)
    ret_val: edaexpr.Expression
    if isinstance(expression, edaexpr.Atom):
        if isinstance(expression, edaexpr.Variable) and expression == oldvar:
            ret_val = newvar
        elif isinstance(expression, edaexpr.Complement) and expression == edaexpr.Not(oldvar):
            ret_val = edaexpr.Not(newvar)
        else:
            ret_val = copy.copy(expression)
    elif isinstance(expression, edaexpr.NotOp):
        nxs = edaexpr.Expression.box(_rename_expr(expression.xs[0], oldvarstr, newvarstr)).node
        ret_val = edaexpr._expr(edaexprnode.not_(nxs))
    elif isinstance(expression, edaexpr.ImpliesOp):
        nxs = [edaexpr.Expression.box(_rename_expr(x, oldvarstr, newvarstr)).node for x in expression.xs]
        ret_val = edaexpr._expr(edaexprnode.impl(*nxs))
    elif isinstance(expression, edaexpr.AndOp):
        nxs = [edaexpr.Expression.box(_rename_expr(x, oldvarstr, newvarstr)).node for x in expression.xs]
        ret_val = edaexpr._expr(edaexprnode.and_(*nxs))
    elif isinstance(expression, edaexpr.OrOp):
        nxs = [edaexpr.Expression.box(_rename_expr(x, oldvarstr, newvarstr)).node for x in expression.xs]
        ret_val = edaexpr._expr(edaexprnode.or_(*nxs))
    elif isinstance(expression, edaexpr.EqualOp):
        nxs = [edaexpr.Expression.box(_rename_expr(x, oldvarstr, newvarstr)).node for x in expression.xs]
        ret_val = edaexpr._expr(edaexprnode.eq(*nxs))
    else:
        raise ValueError()
    return ret_val


def _subst_var(  # noqa: WPS231  too much cognitive complexity
    expression: edaexpr.Expression, oldvarstr: str, substval: numeric
) -> edaexpr.Expression:
    oldvar = edaexpr.exprvar(oldvarstr)
    if substval == 1:
        newvar = edaexpr.expr('1')
    elif substval == 0:
        newvar = edaexpr.expr('0')
    else:
        raise ValueError()
    ret_val: edaexpr.Expression
    if isinstance(expression, edaexpr.Atom):
        if isinstance(expression, edaexpr.Variable) and expression == oldvar:
            ret_val = newvar
        elif isinstance(expression, edaexpr.Complement) and expression == edaexpr.Not(oldvar):
            ret_val = edaexpr.Not(newvar)
        else:
            ret_val = copy.copy(expression)
    elif isinstance(expression, edaexpr.NotOp):
        nxs = edaexpr.Expression.box(_subst_var(expression.xs[0], oldvarstr, substval)).node
        ret_val = edaexpr._expr(edaexprnode.not_(nxs))
    elif isinstance(expression, edaexpr.ImpliesOp):
        nxs = [edaexpr.Expression.box(_subst_var(x, oldvarstr, substval)).node for x in expression.xs]
        ret_val = edaexpr._expr(edaexprnode.impl(*nxs))
    elif isinstance(expression, edaexpr.AndOp):
        nxs = [edaexpr.Expression.box(_subst_var(x, oldvarstr, substval)).node for x in expression.xs]
        ret_val = edaexpr._expr(edaexprnode.and_(*nxs))
    elif isinstance(expression, edaexpr.OrOp):
        nxs = [edaexpr.Expression.box(_subst_var(x, oldvarstr, substval)).node for x in expression.xs]
        ret_val = edaexpr._expr(edaexprnode.or_(*nxs))
    elif isinstance(expression, edaexpr.EqualOp):
        nxs = [edaexpr.Expression.box(_subst_var(x, oldvarstr, substval)).node for x in expression.xs]
        ret_val = edaexpr._expr(edaexprnode.eq(*nxs))
    else:
        raise ValueError()
    return ret_val


def _is_tautology(expression: edaexpr.Expression) -> bool:
        """
        Tell whether term is a tautology.

        Returns:
            True is tautology.
        """
        ret_val = edaexpr.Not(expression).satisfy_one()
        if ret_val is None:  # noqa: WPS531 Found simplifiable returning `if` condition in a function
            return True
        return False



def _get_atom_variables(atom: str) -> List[Var]:
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


def _atom_has_variables(atom: str, var_list: List[Var]) -> bool:
    atoms_vars = _get_atom_variables(atom)
    return len(list_intersection(atoms_vars, var_list)) > 0


def _expr_to_str(expression: edaexpr.Expression) -> str:  # noqa: WPS231  too much cognitive complexity
    ret_val: str
    if isinstance(expression, edaexpr.Atom):
        if isinstance(expression, edaexpr.Variable):
            ret_val = expression.name
        elif isinstance(expression, edaexpr.Complement):
            ret_val = f"~ {expression.inputs[0].name}"
        elif isinstance(expression, edaexpr.Constant):
            ret_val = f" {str(int(expression.VALUE))} "
        else:
            ValueError("Wrong datatype")
    elif isinstance(expression, edaexpr.NotOp):
        ret_val = f"~({_expr_to_str(expression.xs[0])})"
    elif isinstance(expression, edaexpr.ImpliesOp):
        ret_list = [f"({_expr_to_str(x)})" for x in expression.xs]
        ret_val = f"{ret_list[0]} => {ret_list[1]}"
    elif isinstance(expression, edaexpr.AndOp):
        ret_list = [f"({_expr_to_str(x)})" for x in expression.xs]
        ret_val = " & ".join(ret_list)
    elif isinstance(expression, edaexpr.OrOp):
        ret_list = [f"({_expr_to_str(x)})" for x in expression.xs]
        ret_val = " | ".join(ret_list)
    elif isinstance(expression, edaexpr.EqualOp):
        ret_list = [f"({_expr_to_str(x)})" for x in expression.xs]
        ret_val = " = ".join(ret_list)
    else:
        raise ValueError(f"Type: {type(expression)}")
    return ret_val


class PropositionalTerm(Term):
    """Polyhedral terms are linear inequalities over a list of variables."""

    # Constructor: get (i) a dictionary whose keys are variables and whose
    # values are the coefficients of those variables in the term, and (b) a
    # constant. The term is assumed to be in the form \Sigma_i a_i v_i +
    # constant <= 0
    def __init__(self, expression: str | edaexpr.Expression):  # noqa: WPS231  too much cognitive complexity
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
            expression: A boolean expression involving uninterpreted atoms.

        Raises:
            ValueError: Unsupported argument type.
        """
        self.expression: edaexpr.Expression
        if isinstance(expression, edaexpr.Expression):
            self.expression = copy.copy(expression)
        elif isinstance(expression, str):
            if expression == "":
                self.expression = edaexpr.expr("1")
            else:
                # extract the uninterpreted terms
                new_expr = copy.copy(expression)
                atoms = re.findall(r"\w+\s*\(.*?\)", new_expr)
                tvars = [f"_xtempvar{i}" for i in range(len(atoms))]
                for i, atom in enumerate(atoms):
                    new_expr = new_expr.replace(atom, tvars[i])
                eda_expression = edaexpr.expr(new_expr)
                for i, atom in enumerate(atoms):
                    eda_expression = _rename_expr(eda_expression, tvars[i], atom)
                self.expression = eda_expression
        else:
            raise ValueError()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            raise ValueError()
        return str(self) == str(other)
    
    @staticmethod
    def add_globally(constraint : str):
        return 'G(' + constraint + ')'

    def __str__(self) -> str:
        #return PropositionalTerm.add_globally(_expr_to_str(self.expression))
        return _expr_to_str(self.expression)

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
        return [x.name for x in self.expression.inputs]

    @property
    def vars(self) -> List[Var]:  # noqa: A003
        """
        Variables appearing in term.

        Returns:
            List of variables referenced in term.
        """
        atoms = self.atoms
        variables: List[Var] = []
        for atom in atoms:
            variables = variables + _get_atom_variables(atom)
        return variables

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
        ret_expr = _rename_expr(self.expression, source_var.name, target_var.name)
        return PropositionalTerm(ret_expr)

    def is_tautology(self) -> bool:
        """
        Tell whether term is a tautology.

        Returns:
            True is tautology.
        """        
        return _is_tautology(self.expression)


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
        # this code is here to calm down the linter
        if isinstance(self, str):
            return False
        expr = edaexpr.And(*[xs.expression for xs in self.terms])
        new_expr = copy.copy(expr)
        for key in behavior.keys():
            new_expr = _subst_var(new_expr, key.name, behavior[key])
        return _is_tautology(new_expr)

    def elim_vars_by_refining(  # noqa: WPS231  too much cognitive complexity
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
        diag_dict = {}
        # print("REFINING")
    
        for term in self.terms:
            new_term: PropositionalTerm

            if list_intersection(vars_to_elim, term.vars):
                atoms_to_elim = []
                for atom in term.atoms:
                    if _atom_has_variables(atom, vars_to_elim):
                        atoms_to_elim.append(atom)
                # put diagnostics loop here
                print(f"term: {term}")
                # st()
                print(f"context: {context}")
                idxs_to_remove = []
                run = 0

                context_expr = edaexpr.And(*[xs.expression for xs in context.terms])
                elimination_term: edaexpr.Expression = edaexpr.Implies(context_expr, term.expression)
                quantified_atoms = [edaexpr.exprvar(atm) for atm in atoms_to_elim]
                full_term = elimination_term.consensus(vs=quantified_atoms).simplify()
                print(f"full term: {full_term}")


                for i, context_term in enumerate(context.terms):
                    print(f"Run: {run}, checking if context term {context_term} is relevant")
                    # remove i from context, remove all indexes in idxs_to_remove
                    skip_indxs = set(idxs_to_remove)
                    skip_indxs.add(i)
                    new_context = [value for idx, value in enumerate(context.terms) if idx not in skip_indxs]
                    # original quantifier elimination using new_context
                    context_expr = edaexpr.And(*[xs.expression for xs in new_context])
                    elimination_term: edaexpr.Expression = edaexpr.Implies(context_expr, term.expression)
                    quantified_atoms = [edaexpr.exprvar(atm) for atm in atoms_to_elim]
                    elimination_term = elimination_term.consensus(vs=quantified_atoms).simplify()

                    if full_term == elimination_term:
                        print(f"Full term is the same as elimination term full = {full_term}, elim term = {elimination_term}")
                        idxs_to_remove.append(i)
                        print(f"removing {i}")
                        # st()
                    else:
                        print(f"Full term is different from elimination term term full = {full_term}, elim term = {elimination_term}")
                        print(f"keeping {i}")
                        # st()
                    run += 1

                relevant_context = [value for idx, value in enumerate(context.terms) if idx not in idxs_to_remove]
                relevant_context.append(term)
                diag_dict.update({PropositionalTerm(full_term): relevant_context})
                # st()
                with open(DFILE, "a") as file:
                    file.write(f"Computed new term: {full_term} from term: {term} and context: {[relevant_context]}\n")
                print(f"Computed new term: {full_term} from term: {term} and context: {[relevant_context]}")

                elimination_term = copy.copy(full_term) # set the result back to the original term

                # make sure the result is not empty
                test_expr: edaexpr.Expression = edaexpr.And(context_expr, elimination_term)
                if not test_expr.satisfy_one():
                    raise ValueError(
                        f"The variables {vars_to_elim} cannot be eliminated from the term {term} in the context {context}"
                    )
                new_term = PropositionalTerm(elimination_term)
            else:
                new_term = term.copy()
                print(f'keeping term {term}')
                try:
                    diag_dict.update({PropositionalTerm(term): [term]})
                except ValueError:
                    diag_dict.update({term: [term]})
            new_terms.append(new_term)
        return (PropositionalTermList(new_terms), []), diag_dict

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
        """
        new_terms = []
        diag_dict = {}
        # print("RELAXING")

        for term in self.terms:
            new_term: PropositionalTerm
            if list_intersection(vars_to_elim, term.vars):
                atoms_to_elim = []
                for atom in term.atoms:
                    if _atom_has_variables(atom, vars_to_elim):
                        atoms_to_elim.append(atom)

                # put diagnostics loop here
                print(f"term: {term}")
                print(f"context: {context}")
                idxs_to_remove = []
                run = 0

                context_expr = edaexpr.And(*[xs.expression for xs in context.terms])
                elimination_term: edaexpr.Expression = edaexpr.And(context_expr, term.expression)
                full_term = elimination_term.smoothing(
                    vs=[edaexpr.exprvar(atm) for atm in atoms_to_elim]
                ).simplify()
                print(f"full term: {full_term}")

                for i, context_term in enumerate(context.terms):
                    print(f"run: {run}, checking if context term {context_term} is relevant")
                    # remove i from context, remove all indexes in idxs_to_remove
                    skip_indxs = set(idxs_to_remove)
                    skip_indxs.add(i)
                    new_context = [value for idx, value in enumerate(context.terms) if idx not in skip_indxs]
                    # original quantifier elimination using new_context
                    context_expr = edaexpr.And(*[xs.expression for xs in new_context])
                    elimination_term: edaexpr.Expression = edaexpr.And(context_expr, term.expression)
                    elimination_term_final = elimination_term.smoothing(
                        vs=[edaexpr.exprvar(atm) for atm in atoms_to_elim]
                    ).simplify()

                    if full_term == elimination_term_final:
                        print(f"Full term is the same as elimination term full = {full_term}, elim term = {elimination_term_final}")
                        idxs_to_remove.append(i)
                        print(f"removing {i}")
                        # st()
                    else:
                        print(f"Full term is different from elimination term term full = {full_term}, elim term = {elimination_term_final}")
                        print(f"keeping {i}")
                        # st()
                    run += 1
                relevant_context = [value for idx, value in enumerate(context.terms) if idx not in idxs_to_remove]
                relevant_context.append(term) # add the original transformed term
                diag_dict.update({PropositionalTerm(full_term): relevant_context})
                # write to diagnostics file
                with open(DFILE, "a") as file:
                    file.write(f"Computed new term: {full_term} from term: {term} and context: {[relevant_context]}\n")
                print(f"Computed new term: {full_term} from term: {term} and context: {[relevant_context]}")

                elimination_term_final = copy.copy(full_term)  # set the result back to the original term

                # make sure the result is not empty
                # test_expr : edaexpr.Expression = edaexpr.And(context_expr, elimination_term)
                # if not test_expr.satisfy_one():
                #    raise ValueError(f"The variables {vars_to_elim} cannot be eliminated
                #    from the term {term} in the context {context}")
                new_term = PropositionalTerm(elimination_term_final)
            else:
                new_term = term.copy()
                print(f'keeping term {term}')
                diag_dict.update({term: [term]}) # map the term to itself
            new_terms.append(new_term)
        return (PropositionalTermList(new_terms), []), diag_dict

    def simplify(self, context: Optional[PropositionalTermList] = None) -> PropositionalTermList:
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
        terms = self.terms
        new_tl = []
        one_exists = False
        others_exist = False
        one_index = 0
        for i, term in enumerate(terms):
            if term.is_tautology():
                if not one_exists:
                    new_tl.append(term)
                    one_exists = True
                    one_index = i
            else:
                new_tl.append(term)
                others_exist = True
        if others_exist and one_exists:
            del new_tl[one_index]
        return PropositionalTermList(new_tl)

    def refines(self, other: PropositionalTermList) -> bool:
        """
        Tells whether the argument is a larger specification.

        Args:
            other:
                TermList against which we are comparing self.

        Returns:
            self <= other
        """
        test_expr: edaexpr.Expression = edaexpr.Implies(edaexpr.And(*self.terms), edaexpr.And(*other.terms))
        if edaexpr.Not(test_expr).satisfy_one():  # noqa: WPS531 if condition can be simplified
            return False
        return True

    def is_empty(self) -> bool:
        """
        Tell whether the argument has no satisfying assignments.

        Returns:
            True if constraints cannot be satisfied.
        """
        test_expr: edaexpr.Expression = edaexpr.And(*self.terms)
        if test_expr.satisfy_one():  # noqa: WPS531 if condition can be simplified
            return False
        return True
