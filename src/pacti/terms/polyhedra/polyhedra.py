"""
Support for linear inequality constraints, i.e., polyhedra.

Module provides support for linear inequalities as constraints, i.e.,
the constraints are of the form $\\sum_{i} a_i x_i \\le c$, where the
$x_i$ are variables and the $a_i$ and $c$ are constants.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import sympy
from scipy.optimize import linprog

import pacti.terms.polyhedra.serializer as serializer  # noqa: I250, WPS301
from pacti.iocontract import TacticStatistics, Term, TermList, Var
from pacti.utils.lists import list_diff, list_intersection, list_union

numeric = Union[int, float]

TACTICS_ORDER = [1, 2, 3, 4, 5]  # noqa: WPS407


class PolyhedralTerm(Term):
    """Polyhedral terms are linear inequalities over a list of variables."""

    # Constructor: get (i) a dictionary whose keys are variables and whose
    # values are the coefficients of those variables in the term, and (b) a
    # constant. The term is assumed to be in the form \Sigma_i a_i v_i +
    # constant <= 0
    def __init__(self, variables: Dict[Var, numeric], constant: numeric):
        """
        Constructor for PolyhedralTerm.

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

        Raises:
            ValueError: Unsupported argument type.
        """
        variable_dict = {}
        for key, value in variables.items():
            if value != 0:
                if isinstance(key, str):
                    raise ValueError("Unsupported argument type")
                else:
                    variable_dict[key] = float(value)
        self.variables = variable_dict
        self.constant = float(constant)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            raise ValueError()
        match = self.variables.keys() == other.variables.keys()
        if match:
            for k, v in self.variables.items():
                match = match and np.equal(v, other.variables[k])
        return match and np.equal(self.constant, other.constant)

    def __str__(self) -> str:
        varlist = list(self.variables.items())
        varlist.sort(key=lambda x: str(x[0]))
        res = " + ".join([str(coeff) + "*" + var.name for var, coeff in varlist])
        res += " <= " + str(self.constant)
        return res

    def __hash__(self) -> int:
        return hash(str(self))

    def __repr__(self) -> str:
        return "<Term {0}>".format(self)

    def __add__(self, other: object) -> PolyhedralTerm:
        if not isinstance(other, type(self)):
            raise ValueError()
        varlist = list_union(self.vars, other.vars)
        variables = {}
        for var in varlist:  # noqa: VNE002
            variables[var] = self.get_coefficient(var) + other.get_coefficient(var)
        return PolyhedralTerm(variables, self.constant + other.constant)

    def copy(self) -> PolyhedralTerm:
        """
        Generates copy of polyhedral term.

        Returns:
            Copy of term.
        """
        return PolyhedralTerm(self.variables, self.constant)

    def rename_variable(self, source_var: Var, target_var: Var) -> PolyhedralTerm:
        """
        Rename a variable in a term.

        Args:
            source_var: The variable to be replaced.
            target_var: The new variable.

        Returns:
            A term with `source_var` replaced by `target_var`.
        """
        new_term = self.copy()
        if source_var in self.vars:
            if target_var not in self.vars:
                new_term.variables[target_var] = 0
            new_term.variables[target_var] += new_term.variables[source_var]
            new_term = new_term.remove_variable(source_var)
        return new_term

    @property
    def vars(self) -> List[Var]:  # noqa: A003
        """
        Variables appearing in term with a nonzero coefficient.

        Example:
            For the term $ax + by \\le c$ with variables $x$ and
            $y$, this function returns the list $\\{x, y\\}$ if
            $a$ and $b$ are nonzero.

        Returns:
            List of variables referenced in term.
        """
        varlist = self.variables.keys()
        return list(varlist)

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

    def get_coefficient(self, var: Var) -> numeric:  # noqa: VNE002
        """
        Output the coefficient multiplying the given variable in the term.

        Args:
            var: The variable whose coefficient we are seeking.

        Returns:
            The coefficient corresponding to variable in the term.
        """
        if self.contains_var(var):
            return self.variables[var]
        return 0

    def get_polarity(self, var: Var, polarity: bool = True) -> bool:  # noqa: VNE002
        """
        Check if variable matches given polarity

        The polarity of a variable in a term is defined as the polarity of the
        coefficient that multiplies it in a term, e.g., the variables $x$
        and $y$ in the term $-2x + y \\le 3$ have negative and
        positive polarities respectively.

        Args:
            var: The variable whose polarity in the term we are seeking.
            polarity: The polarity that we are comparing against the variable's polarity.

        Returns:
            `True` if the variable's polarity matches `polarity` and
                `False` otherwise. If the variable's coefficient in the term
                is zero, return `True`.
        """
        if polarity:
            return self.variables[var] >= 0
        return self.variables[var] <= 0

    def get_sign(self, var: Var) -> int:  # noqa: VNE002
        """
        Get the sign of the variable in term.

        The sign of a variable in a term is defined as the sign of the
        coefficient that multiplies it in a term, e.g., the variables $x$
        and $y$ in the term $-2x + y \\le 3$ have $-1$ and
        $+1$ polarities respectively. $0$ has $+1$ sign.

        Args:
            var: The variable whose polarity in the term we are seeking.

        Returns:
            The sign of the variable in the term.
        """
        if self.get_polarity(var=var, polarity=True):
            return 1
        return -1

    def get_matching_vars(self, variable_polarity: Dict[Var, bool]) -> List[Var]:
        """
        Get list of variables whose polarities match the polarities requested.

        Example:

        ```
            x = Var('x')
            y = Var('y')
            z = Var('z')
            variables = {x:-2, y:3}
            constant  = 4
            term = PolyhedralTerm(variables, constant)
            polarities = {y:True}
            term.get_matching_vars(polarities)
        ```

        The last call returns `{y, z}` because the variable y matches the
        requested polarity in the term, and the variable z has a zero
        coefficient.

        Args:
            variable_polarity: A dictionary mapping Var instances to Boolean
                values indicating the polarity of the given variable.

        Returns:
            If all variables in the term match the polarities specified in the
                argument, the routine returns the matching variables.  Otherwise,
                it returns an empty list.
        """
        variable_list = []
        for var in variable_polarity.keys():  # noqa: VNE002
            if self.contains_var(var):
                if (self.get_polarity(var=var, polarity=True) == variable_polarity[var]) or (  # noqa: WPS337
                    self.get_coefficient(var) == 0
                ):
                    variable_list.append(var)
                else:
                    variable_list = []
                    break
        return variable_list

    def remove_variable(self, var: Var) -> PolyhedralTerm:
        """
        Eliminates a variable from a term.

        Args:
            var: variable to be eliminated.

        Returns:
            A new term with the variable eliminated.
        """
        if self.contains_var(var):
            that = self.copy()
            that.variables.pop(var)
            return that
        return self.copy()

    def multiply(self, factor: numeric) -> PolyhedralTerm:
        """Multiplies a term by a constant factor.

        For example, multiplying the term $2x + 3y \\le 4$ by the factor 2
        yields $4x + 6y \\le 8$.

        Args:
            factor: element by which the term is multiplied.

        Returns:
            A new term which is the result of the given term multiplied by
            `factor`.
        """
        variables = {key: factor * val for key, val in self.variables.items()}
        return PolyhedralTerm(variables, factor * self.constant)

    def substitute_variable(self, var: Var, subst_with_term: PolyhedralTerm) -> PolyhedralTerm:  # noqa: VNE002
        """
        Substitutes a specified variable in a term with a given term.

        Example:
            In the term $2x - y \\le 6$, substituting y by the term
            $x + z \\le 5$ yields $x - z \\le 1$. Observe that the
            substituting term is understood as an equality.

        Args:
            var: The term variable to be substituted.
            subst_with_term: The term used to replace var.

        Returns:
            A new term in which the variable is substituted with the given term
                understood as an equality.
        """
        if self.contains_var(var):
            term = subst_with_term.multiply(self.get_coefficient(var))
            logging.debug("Term is %s", term)
            that = self.remove_variable(var)
            logging.debug(that)
            return that + term
        return self.copy()

    def isolate_variable(self, var_to_isolate: Var) -> PolyhedralTerm:
        """
        Isolate a variable in a term.

        Example:
            In the term $-2x + y \\le 6$ understood as equality, isolating the
            variable $x$ yields $x = 0.5 y - 3$, which in PolyhedralTerm
            notation we express as $0.5 y <= -3$.

        Args:
            var_to_isolate: The variable to be isolated.

        Returns:
            A new term which corresponds to the isolation of the indicated
                variable.

        Raises:
            ValueError: the indicated variable is not contained in the term.
        """
        if var_to_isolate not in self.vars:
            raise ValueError("Variable %s is not a term variable" % (var_to_isolate))
        return PolyhedralTerm(
            variables={
                k: -v / self.get_coefficient(var_to_isolate) for k, v in self.variables.items() if k != var_to_isolate
            },
            constant=self.constant / self.get_coefficient(var_to_isolate),
        )

    @staticmethod
    def to_symbolic(term: PolyhedralTerm) -> Any:
        """
        Translates the variable terms of a PolyhedralTerm into a sympy expression.

        Example:
            The code

            ```
                x = Var('x') y = Var('y') variables = {x:-2, y:3} constant  = 4
                term = PolyhedralTerm(variables, constant) expression =
                PolyhedralTerm.to_symbolic(term)
            ```

            yields the expression $-2x + 3y - 4$.

        Args:
            term:
                The term whose coefficients and variables are to be translated
                to sympy's data structure.

        Returns:
            Sympy expression corresponding to PolyhedralTerm.
        """
        ex = -term.constant
        for var in term.vars:  # noqa: VNE002
            sv = sympy.symbols(var.name)
            ex += sv * term.get_coefficient(var)
        return ex

    @staticmethod
    def to_term(expression: sympy.core.expr.Expr) -> PolyhedralTerm:
        """
        Translates a sympy expression into a PolyhedralTerm.

        Example:
            The expression $2x + 3y - 1$ is translated into
            `PolyhedralTerm(variables={x:2, y:3}, constant=1)`.

        Args:
            expression: The symbolic expression to be translated.

        Returns:
            PolyhedralTerm corresponding to sympy expression.
        """
        expression_coefficients: dict = expression.as_coefficients_dict()
        logging.debug(expression_coefficients)
        keys = list(expression_coefficients.keys())
        variable_dict = {}
        constant = 0
        for key in keys:
            logging.debug(type(key))
            if isinstance(key, (str, sympy.core.symbol.Symbol)):
                var = Var(str(key))  # noqa: VNE002
                variable_dict[var] = expression_coefficients[key]
            else:
                constant = constant - expression_coefficients[key] * key
        return PolyhedralTerm(variable_dict, constant)

    @staticmethod
    def term_to_polytope(term: PolyhedralTerm, variable_list: List[Var]) -> Tuple[List[numeric], numeric]:
        """
        Transform a term into a vector according to the given order.

        Example:
            The term $3x + 5y -2z \\le 7$ with `variable_list = [y,
            x, w, z]` yields the tuple `[5, 3, 0, -2], 7`.

        Args:
            term: The term to be transformed.
            variable_list:
                A list of variables indicating the order of appearance of
                variable coefficients.

        Returns:
            A tuple consisting of (i) the ordered list of coefficients and (ii)
                the term's constant.
        """
        coeffs = []
        for var in variable_list:  # noqa: VNE002
            coeffs.append(term.get_coefficient(var))
        return coeffs, term.constant

    @staticmethod
    def polytope_to_term(poly: List[numeric], const: numeric, variables: List[Var]) -> PolyhedralTerm:
        """
        Transform a list of coefficients and variables into a PolyhedralTerm.

        Args:
            poly: An ordered list of coefficients.
            const: The term's coefficient.
            variables: The variables corresponding to the list of coefficients.

        Returns:
            A PolyhedralTerm corresponding to the provided data.
        """
        assert len(poly) == len(variables)
        variable_dict = {}
        for i, var in enumerate(variables):  # noqa: VNE002
            variable_dict[var] = poly[i]
        return PolyhedralTerm(variable_dict, const)

    @staticmethod
    def solve_for_variables(context: PolyhedralTermList, vars_to_elim: List[Var]) -> dict:
        """
        Interpret termlist as equality and solve system of equations.

        Args:
            context:
                The list of terms to be solved. Each term will be interpreted as
                an equality.
            vars_to_elim:
                The list of variables whose solutions will be sought.

        Assumptions: the number of equations matches the number of vars_to_elim
        contained in the terms.

        Returns:
            A dictionary mapping variables to their solutions. The solutions are
                expressed as PolyhedralTerm instances.
        """
        logging.debug("GetVals: %s Vars: %s", context, vars_to_elim)
        vars_to_solve = list_intersection(context.vars, vars_to_elim)
        assert len(context.terms) == len(vars_to_solve)
        exprs = [PolyhedralTerm.to_symbolic(term) for term in context.terms]
        logging.debug("Solving %s", exprs)
        vars_to_solve_symb = [sympy.symbols(var.name) for var in vars_to_solve]
        sols = sympy.solve(exprs, *vars_to_solve_symb)
        logging.debug(sols)
        if len(sols) > 0:
            return {Var(str(key)): PolyhedralTerm.to_term(sols[key]) for key in sols.keys()}
        return {}


class PolyhedralTermList(TermList):  # noqa: WPS338
    """A TermList of PolyhedralTerm instances."""

    def __init__(self, terms: Optional[List[PolyhedralTerm]] = None):
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
        elif all(isinstance(t, PolyhedralTerm) for t in terms):
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
        str_list = []
        ts = self.terms.copy()
        while ts:
            s, rest = serializer.polyhedral_term_list_to_strings(ts)
            str_list.append(s)
            ts = rest
        return str_list

    def evaluate(self, var_values: Dict[Var, numeric]) -> PolyhedralTermList:  # noqa: WPS231
        """
        Replace variables in termlist with given values.

        Args:
            var_values:
                The values that variables will take.

        Returns:
            A new PolyhedralTermList in which the variables have been
                substituted with the values provided.

        Raises:
            ValueError: constraints are unsatisfiable under these valuation of variables.
        """
        new_list = []
        for term in self.terms:
            new_term = term.copy()
            for var, val in var_values.items():  # noqa: VNE002
                new_term = new_term.substitute_variable(
                    var=var, subst_with_term=PolyhedralTerm(variables={}, constant=-val)
                )
            # we may have eliminated all variables after substitution
            if not new_term.vars:
                if new_term.constant < 0:
                    raise ValueError("Term %s not satisfied" % (term))
                else:
                    continue  # noqa: WPS503
            new_list.append(new_term)
        return PolyhedralTermList(new_list)

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
        excess_vars = list_diff(self.vars, list(behavior.keys()))
        if excess_vars:
            raise ValueError("The variables %s were not assigned values" % (excess_vars))
        retval = True
        try:
            self.evaluate(behavior)
        except ValueError:
            retval = False
        return retval

    def elim_vars_by_refining(
        self,
        context: PolyhedralTermList,
        vars_to_elim: list,
        simplify: bool = True,
        tactics_order: Optional[List[int]] = None,
    ) -> Tuple[PolyhedralTermList, TacticStatistics]:
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
        logging.debug("Refining from terms: %s", self)
        logging.debug("Context: %s", context)
        logging.debug("Vars to elim: %s", vars_to_elim)
        if tactics_order is None:
            tactics_order = TACTICS_ORDER
        if simplify:
            try:
                termlist = self.simplify(context)
            except ValueError as e:
                raise ValueError(
                    "Provided constraints \n{}\n".format(self) + "are unsatisfiable in context \n{}".format(context)
                ) from e
        else:
            termlist = self
        try:
            return termlist._transform(
                context=context, vars_to_elim=vars_to_elim, refine=True, simplify=simplify, tactics_order=tactics_order
            )
        except ValueError as e:
            raise ValueError(
                "The elimination of variables \n{}\n".format([str(x) for x in vars_to_elim])
                + "by refining terms \n{}\n".format(self)
                + "in context \n{}\n".format(context)
                + "was not possible"
            ) from e

    def lacks_constraints(self) -> bool:
        """
        Tell whether TermList is empty.

        Returns:
            True if empty. False otherwise.
        """
        return len(self.terms) == 0

    def elim_vars_by_relaxing(
        self,
        context: PolyhedralTermList,
        vars_to_elim: list,
        simplify: bool = True,
        tactics_order: Optional[List[int]] = None,
    ) -> Tuple[PolyhedralTermList, TacticStatistics]:
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
        logging.debug("Relaxing with context")
        logging.debug("Relaxing from terms %s", self)
        logging.debug("Context: %s", context)
        logging.debug("Vars to elim: %s", vars_to_elim)

        if tactics_order is None:
            tactics_order = TACTICS_ORDER
        if simplify:
            try:
                termlist = self.simplify(context)
            except ValueError as e:
                raise ValueError(
                    "Provided constraints \n{}\n".format(self) + "are unsatisfiable in context \n{}".format(context)
                ) from e
        else:
            termlist = self.copy()
        try:
            (termlist, tactics_data) = termlist._transform(
                context=context, vars_to_elim=vars_to_elim, refine=False, simplify=simplify, tactics_order=tactics_order
            )
        except ValueError as e:
            raise ValueError(
                "The elimination of variables \n{}\n".format([str(x) for x in vars_to_elim])
                + "by relaxing terms \n{}\n".format(self)
                + "in context \n{}\n".format(context)
                + "was not possible"
            ) from e
        # eliminate terms containing the variables to be eliminated
        terms_to_elim = termlist.get_terms_with_vars(vars_to_elim)
        termlist.terms = list_diff(termlist.terms, terms_to_elim.terms)
        return termlist, tactics_data

    def simplify(self, context: Optional[PolyhedralTermList] = None) -> PolyhedralTermList:
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

        Raises:
            ValueError: The intersection of self and context is empty.
        """
        logging.debug("Starting simplification procedure")
        logging.debug("Simplifying terms: %s", self)
        logging.debug("Context: %s", context)
        if context:
            new_self = self - context
            result = PolyhedralTermList.termlist_to_polytope(new_self, context)
        else:
            result = PolyhedralTermList.termlist_to_polytope(self, PolyhedralTermList())

        variables = result[0]
        self_mat = result[1]
        self_cons = result[2]
        ctx_mat = result[3]
        ctx_cons = result[4]
        # logging.debug("Polytope is \n%s", self_mat)
        try:
            a_red, b_red = PolyhedralTermList.reduce_polytope(self_mat, self_cons, ctx_mat, ctx_cons)
        except ValueError as e:
            raise ValueError(
                "The constraints \n{}\n".format(self) + "are unsatisfiable in context \n{}".format(context)
            ) from e
        logging.debug("Reduction: \n%s", a_red)
        simplified = PolyhedralTermList.polytope_to_termlist(a_red, b_red, variables)
        logging.debug("Back to terms: \n%s", simplified)
        return simplified

    def refines(self, other: PolyhedralTermList) -> bool:
        """
        Tells whether the argument is a larger specification.

        Args:
            other:
                TermList against which we are comparing self.

        Returns:
            self <= other
        """
        logging.debug("Verifying refinement")
        logging.debug("LH term: %s", self)
        logging.debug("RH term: %s", other)
        if other.lacks_constraints():
            return True
        if self.lacks_constraints():
            return False
        variables, self_mat, self_cons, ctx_mat, ctx_cons = PolyhedralTermList.termlist_to_polytope(  # noqa: WPS236
            self, other
        )
        logging.debug("Polytope is \n%s", self_mat)
        return PolyhedralTermList.verify_polytope_containment(self_mat, self_cons, ctx_mat, ctx_cons)

    def is_empty(self) -> bool:
        """
        Tell whether the argument has no satisfying assignments.

        Returns:
            True if constraints cannot be satisfied.
        """
        _, self_mat, self_cons, _, _ = PolyhedralTermList.termlist_to_polytope(  # noqa: WPS236
            self, PolyhedralTermList([])
        )
        logging.debug("Polytope is \n%s", self_mat)
        return PolyhedralTermList.is_polytope_empty(self_mat, self_cons)

    # Returns:
    # - transformed term list
    # - a list of tuples of the tactic used, time spent, and invocation count
    def _transform(
        self,
        context: PolyhedralTermList,
        vars_to_elim: list,
        refine: bool,
        simplify: bool,
        tactics_order: Optional[List[int]] = None,
    ) -> Tuple[PolyhedralTermList, TacticStatistics]:
        logging.debug("Transforming: %s", self)
        logging.debug("Context terms: %s", context)
        logging.debug("Variables to eliminate: %s", vars_to_elim)
        if tactics_order is None:
            tactics_order = TACTICS_ORDER
        term_list = list(self.terms)
        new_terms = self.copy()

        # List to store the tuples of the tactic used, time spent, and invocation count
        tactics_used: TacticStatistics = []

        for i, term in enumerate(term_list):
            if list_intersection(term.vars, vars_to_elim):
                copy_new_terms = new_terms.copy()
                copy_new_terms.terms.remove(term)
                helpers = context | copy_new_terms
                try:
                    (new_term, tactic_num, tactic_time, tactic_count) = PolyhedralTermList._transform_term(
                        term, helpers, vars_to_elim, refine, tactics_order
                    )
                except ValueError:
                    new_term = term.copy()
                    tactic_num = 0
                    tactic_time = 0
                    tactic_count = 0
                tactics_used.append((tactic_num, tactic_time, tactic_count))

            else:
                new_term = term.copy()

            new_terms.terms[i] = new_term

        that = PolyhedralTermList(new_terms.terms)

        # the last step needs to be a simplification
        logging.debug("Ending transformation with simplification")
        if simplify:
            return that.simplify(context), tactics_used
        return that, tactics_used

    def optimize(self, objective: Dict[Var, numeric], maximize: bool = True) -> Optional[numeric]:
        """
        Optimizes a linear expression in the feasible region of the termlist.

        Args:
            objective:
                The objective to optimize.
            maximize:
                If true, the routine maximizes; it minimizes otherwise.

        Returns:
            The optimal value of the objective. If the objective is unbounded, None is returned.

        Raises:
            ValueError: Constraints are likely unfeasible.
        """
        obj = PolyhedralTermList([PolyhedralTerm(variables=objective, constant=0)])
        _, self_mat, self_cons, obj_mat, _ = PolyhedralTermList.termlist_to_polytope(self, obj)  # noqa: WPS236
        polarity = 1
        if maximize:
            polarity = -1
        res = linprog(c=polarity * obj_mat[0], A_ub=self_mat, b_ub=self_cons, bounds=(None, None))
        # Linprog's status values
        # 0 : Optimization proceeding nominally.
        # 1 : Iteration limit reached.
        # 2 : Problem appears to be infeasible.
        # 3 : Problem appears to be unbounded.
        # 4 : Numerical difficulties encountered.
        if res["status"] == 3:
            return None
        elif res["status"] == 0:
            fun_val: float = res["fun"]
            return polarity * fun_val
        raise ValueError("Constraints are unfeasible")

    @staticmethod
    def termlist_to_polytope(
        terms: PolyhedralTermList, context: PolyhedralTermList
    ) -> Tuple[List[Var], np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Converts a list of terms with its context into matrix-vector pairs.

        Example:
            Suppose the list of terms is $\\{x+y \\le 1, x - y \\le 4\\}$
            and the context is $\\{x + 4w \\le 5\\}$. The routine extracts
            all variables and generates an order for them, say, $[x, w,
            y]$. Then the routine returns matrix-vector pairs for both the terms
            TermList and the context. It returns $A = \\left(
            \\begin{smallmatrix} 1 & 0 & 1 \\\\ 1 &0 &-1
            \\end{smallmatrix}\\right)$ and $b = \\left(
            \\begin{smallmatrix} 1 \\\\ 4 \\end{smallmatrix}\\right)$ for the
            current TermList and $A_{c} = \\left( \\begin{smallmatrix} 1 &
            4 & 0 \\end{smallmatrix}\\right)$ and $b_c = \\left(
            \\begin{smallmatrix} 5 \\end{smallmatrix}\\right)$ for the context.

        Args:
            terms:
                list of terms to convert to matrix-vector form.
            context:
                Context terms to convert to matrix-vector form.

        Returns:
            A tuple `variables, A, b, a_h, b_h` consisting of the variable
                order and the matrix-vector pairs for the terms and the context.
        """
        variables = list(list_union(terms.vars, context.vars))
        a = []
        b = []
        for term in terms.terms:
            pol, coeff = PolyhedralTerm.term_to_polytope(term, variables)
            a.append(pol)
            b.append(coeff)

        a_h = []
        b_h = []
        for term in context.terms:
            pol, coeff = PolyhedralTerm.term_to_polytope(term, variables)
            a_h.append(pol)
            b_h.append(coeff)

        if len(context.terms) == 0:
            a_h_ret = np.array([[]])
        else:
            a_h_ret = np.array(a_h)
        # logging.debug("a is \n%s", a)
        return variables, np.array(a), np.array(b), a_h_ret, np.array(b_h)

    @staticmethod
    def polytope_to_termlist(matrix: np.ndarray, vector: np.ndarray, variables: List[Var]) -> PolyhedralTermList:
        """
        Transforms a matrix-vector pair into a PolyhedralTermList.

        Args:
            matrix:
                The matrix of the pair.
            vector:
                The vector of the pair.
            variables:
                A list indicating the variable which corresponds to each column
                of the matrix.

        Returns:
            The PolyhedralTermList corresponding to the given data.
        """
        term_list = []
        # logging.debug("Poly is " + str(polytope))
        # logging.debug("matrix is %s", matrix)
        if len(matrix.shape) > 1:
            n, m = matrix.shape
            assert m == len(variables)
        else:
            n = matrix.shape[0]
            m = 0
        for i in range(n):
            row = list(matrix[i])
            const = vector[i]
            term = PolyhedralTerm.polytope_to_term(row, const, variables)
            term_list.append(term)
        return PolyhedralTermList(list(term_list))

    @staticmethod
    def reduce_polytope(  # noqa: WPS231
        a: np.ndarray, b: np.ndarray, a_help: Optional[np.ndarray] = None, b_help: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Eliminate redundant constraints from a given polytope.

        Args:
            a:
                Matrix of H-representation of polytope to reduce.
            b:
                Vector of H-representation of polytope to reduce.
            a_help:
                Matrix of H-representation of context polytope.
            b_help:
                Vector of H-representation of context polytope.

        Raises:
            ValueError: The intersection of given polytope with its context is empty.

        Returns:
            a_temp: Matrix of H-representation of reduced polytope.
            b_temp: Vector of H-representation of reduced polytope.
        """
        if not isinstance(a_help, np.ndarray):
            a_help = np.array([[]])
        if not isinstance(b_help, np.ndarray):
            b_help = np.array([])
        if len(a.shape) > 1:
            n, m = a.shape
        else:
            n = a.shape[0]
            m = 0
        n_h, m_h = a_help.shape
        helper_present = n_h * m_h > 0
        assert n == len(b), "n is {} and b is {}".format(n, b)
        if helper_present:
            assert n_h == len(b_help)
        else:
            assert len(b_help) == 0
        if helper_present and m > 0:
            assert m_h == m
        if n == 0:
            return a, b
        if n == 1 and not helper_present:
            return a, b

        i = 0
        a_temp = np.copy(a)
        b_temp = np.copy(b)
        while i < n:
            objective = a_temp[i, :] * -1
            b_temp[i] += 1
            if helper_present:
                a_opt = np.concatenate((a_temp, a_help), axis=0)
                b_opt = np.concatenate((b_temp, b_help))
            else:
                a_opt = a_temp
                b_opt = b_temp
            # Linprog's status values
            # 0 : Optimization proceeding nominally.
            # 1 : Iteration limit reached.
            # 2 : Problem appears to be infeasible.
            # 3 : Problem appears to be unbounded.
            # 4 : Numerical difficulties encountered.
            res = linprog(c=objective, A_ub=a_opt, b_ub=b_opt, bounds=(None, None))  # ,options={'tol':0.000001})
            b_temp[i] -= 1
            if res["status"] == 3 or (res["status"] == 0 and -res["fun"] <= b_temp[i]):  # noqa: WPS309
                logging.debug("Can remove")
                a_temp = np.delete(a_temp, i, 0)
                b_temp = np.delete(b_temp, i)
                n -= 1
            else:
                i += 1
            if res["status"] == 2:
                raise ValueError("The constraints are unsatisfiable")

        return a_temp, b_temp

    @staticmethod
    def verify_polytope_containment(  # noqa: WPS231
        a_l: Optional[np.ndarray] = None,
        b_l: Optional[np.ndarray] = None,
        a_r: Optional[np.ndarray] = None,
        b_r: Optional[np.ndarray] = None,
    ) -> bool:
        """
        Tell whether a polytope is contained in another.

        Args:
            a_l:
                Matrix of H-representation of polytope on LHS of inequality.
            b_l:
                Vector of H-representation of polytope on LHS of inequality.
            a_r:
                Matrix of H-representation of polytope on RHS of inequality.
            b_r:
                Vector of H-representation of polytope on RHS of inequality.

        Returns:
            True if left polytope is contained in right polytope. False otherwise.
        """
        if not isinstance(a_l, np.ndarray):
            a_l = np.array([[]])
        if not isinstance(a_r, np.ndarray):
            a_r = np.array([[]])
        if not isinstance(b_l, np.ndarray):
            b_l = np.array([])
        if not isinstance(b_r, np.ndarray):
            b_r = np.array([])
        # If the LHS is empty, it is a refinement
        if PolyhedralTermList.is_polytope_empty(a_l, b_l):
            return True
        # If the RHS is empty, but not the LHS, not a refinement
        if PolyhedralTermList.is_polytope_empty(a_r, b_r):
            return False
        # If no side is empty, check whether the RHS terms are included in the
        # LHS
        n_l, m_l = a_l.shape
        n_r, m_r = a_r.shape
        assert m_l == m_r
        assert n_l == len(b_l)
        assert n_r == len(b_r)

        is_refinement = True
        for i in range(n_r):
            constraint = a_r[[i], :]
            objective = constraint * -1
            b_temp = b_r[i] + 1
            logging.debug("Optimization objective: \n%s", objective)
            logging.debug("a_l is \n%s", a_l)
            logging.debug("a_r is \n%s", a_r)
            logging.debug("b_l is \n%s", b_l)
            logging.debug("b_r is \n%s", b_r)

            a_opt = np.concatenate((a_l, constraint), axis=0)
            b_opt = np.concatenate((b_l, np.array([b_temp])))

            res = linprog(c=objective, A_ub=a_opt, b_ub=b_opt, bounds=(None, None))  # ,options={'tol':0.000001})
            b_temp -= 1
            if res["status"] == 2:
                is_refinement = False
                break
            else:
                if -res["fun"] <= b_temp:  # noqa: WPS309
                    logging.debug("Redundant constraint")
                else:
                    is_refinement = False
                    break
            logging.debug("Optimal value: %s", -res["fun"])
            logging.debug("Results: %s", res)
        return is_refinement

    @staticmethod
    def is_polytope_empty(a: np.ndarray, b: np.ndarray) -> bool:
        """
        Say whether a polytope is empty.

        Args:
            a:
                Matrix of H-representation of polytope to verify.
            b:
                Vector of H-representation of polytope to verify.

        Returns:
            True if empty. False otherwise.

        Raises:
            ValueError: Numerical difficulties encountered.
        """
        logging.debug("Verifying polytope emptiness: a is %s a.shape is %s, b is %s", a, a.shape, b)
        if len(a) == 0:
            return False
        n, m = a.shape
        if n * m == 0:
            return False
        assert n == len(b)
        objective = np.zeros((1, m))
        res = linprog(c=objective, A_ub=a, b_ub=b, bounds=(None, None))  # ,options={'tol':0.000001})
        # Linprog's status values
        # 0 : Optimization proceeding nominally.
        # 1 : Iteration limit reached.
        # 2 : Problem appears to be infeasible.
        # 3 : Problem appears to be unbounded.
        # 4 : Numerical difficulties encountered.
        if res["status"] == 2:
            return True
        elif res["status"] in {0, 3}:
            return False
        raise ValueError("Cannot decide emptiness")

    @staticmethod
    def _get_kaykobad_context(  # noqa: WPS231
        term: PolyhedralTerm, context: PolyhedralTermList, vars_to_elim: list, refine: bool
    ) -> Tuple[List[PolyhedralTerm], List[Var]]:
        forbidden_vars = list_intersection(vars_to_elim, term.vars)
        other_forbibben_vars = list_diff(vars_to_elim, term.vars)
        n = len(forbidden_vars)
        matrix_row_terms = []  # type: List[PolyhedralTerm]
        partial_sums = [float(0) for i in range(n)]
        transform_coeff = -1
        if refine:
            transform_coeff = 1
        matrix_contains_others = False
        # We add a row to the matrix in each iteration
        for i, i_var in enumerate(forbidden_vars):
            row_found = False
            logging.debug("Iterating for variable %s", i_var)
            for context_term in list_diff(context.terms, matrix_row_terms):
                logging.debug("Analyzing context term %s", context_term)
                if context_term == term:
                    continue
                term_is_invalid = False
                # make sure the term does not include other forbidden variables
                for var in other_forbibben_vars:  # noqa: VNE002
                    if context_term.get_coefficient(var) != 0:
                        term_is_invalid = True
                        logging.debug("Term contains other forbidden vars")
                        break
                if term_is_invalid:
                    continue
                # 1. Verify Kaykobad pair: sign of nonzero matrix terms
                for var in forbidden_vars:  # noqa: VNE002
                    if context_term.get_coefficient(var) != 0:
                        if transform_coeff * context_term.get_sign(var) != term.get_sign(var):
                            term_is_invalid = True
                            # logging.debug("Failed first matrix-vector verification")
                            break
                # 2. Verify Kaykobad pair: matrix diagonal terms
                if context_term.get_coefficient(i_var) == 0 or term_is_invalid:
                    # logging.debug("Failed second matrix-vector verification")
                    continue
                # 3. Verify Kaykobad pair: relation between matrix and vector
                residuals = [float(0) for i in range(n)]
                for j, j_var in enumerate(forbidden_vars):
                    # logging.debug("Verifying third condition on variable %s", j_var)
                    if j != i:
                        residuals[j] = (
                            term.get_sign(j_var)
                            * context_term.get_coefficient(j_var)
                            * term.get_coefficient(i_var)
                            / context_term.get_coefficient(i_var)
                        )
                    if np.abs(term.get_coefficient(j_var)) <= partial_sums[j] + residuals[j]:
                        # logging.debug("q coefficient: %s", term.get_coefficient(j_var))
                        # logging.debug("RHS: %s", partial_sums[j] + residuals[j])
                        term_is_invalid = True
                        # logging.debug("Failed third matrix-vector verification")
                        break
                if not term_is_invalid:
                    matrix_contains_others = (
                        matrix_contains_others or len(list_diff(context_term.vars, forbidden_vars)) > 0
                    )
                    row_found = True
                    for j in range(n):
                        partial_sums[j] += residuals[j]
                    matrix_row_terms.append(context_term)
                    break
            if not row_found:
                raise ValueError("Could not find the {}th row of matrix".format(i))
        if (not matrix_contains_others) and len(list_diff(term.vars, vars_to_elim)) == 0:
            raise ValueError("Found context will produce empty transformation")
        # logging.debug("Matrix row terms %s", matrix_row_terms)
        return matrix_row_terms, forbidden_vars

    @staticmethod
    def _context_reduction(
        term: PolyhedralTerm, context: PolyhedralTermList, vars_to_elim: list, refine: bool, strategy: int
    ) -> PolyhedralTerm:
        logging.debug("********** Context reduction")
        logging.debug("Vars_to_elim %s \nTerm %s \nContext %s " % (vars_to_elim, term, context))
        try:
            if strategy == 1:
                matrix_row_terms, forbidden_vars = PolyhedralTermList._get_kaykobad_context(
                    term, context, vars_to_elim, refine
                )
            elif strategy == 5:
                matrix_row_terms, forbidden_vars = PolyhedralTermList._get_tlp_context(
                    term, context, vars_to_elim, refine
                )
            else:
                raise ValueError("Unknown strategy")
        except ValueError:
            logging.debug("Could not transform %s using Context reduction", term)
            raise ValueError("Could not transform term {}".format(term))
        matrix_row_terms_tl = PolyhedralTermList(list(matrix_row_terms))
        sols = PolyhedralTerm.solve_for_variables(matrix_row_terms_tl, list(forbidden_vars))
        # logging.debug("Sols %s", sols)

        result = term.copy()
        # logging.debug("Result is %s", result)
        for var in sols.keys():  # noqa: VNE002
            result = result.substitute_variable(var, sols[var])
        logging.debug("Term %s transformed to %s", term, result)

        return result

    @staticmethod
    def _tactic_1(
        term: PolyhedralTerm, context: PolyhedralTermList, vars_to_elim: list, refine: bool
    ) -> Tuple[Optional[PolyhedralTerm], int]:
        logging.debug("********** Tactic 1")
        return PolyhedralTermList._context_reduction(term, context, vars_to_elim, refine, 1), 1

    @staticmethod
    def _tactic_2(  # noqa: WPS231
        term: PolyhedralTerm, context: PolyhedralTermList, vars_to_elim: list, refine: bool
    ) -> Tuple[Optional[PolyhedralTerm], int]:
        logging.debug("************ Tactic 2")
        logging.debug("Vars_to_elim %s \nTerm %s \nContext %s " % (vars_to_elim, term, context))
        conflict_vars = list_intersection(vars_to_elim, term.vars)
        new_context_list = []
        # Extract from context the terms that only contain forbidden vars
        for context_term in context.terms:
            if not list_diff(context_term.vars, vars_to_elim):
                if context_term != term:
                    new_context_list.append(context_term.copy())
        logging.debug("This is what we kept")
        for el in new_context_list:
            logging.debug(el)
        if not new_context_list:
            raise ValueError("No term contains only irrelevant variables")
        if list_diff(conflict_vars, PolyhedralTermList(new_context_list).vars):
            raise ValueError("Tactic 2 unsuccessful")
        # now optimize
        retval = PolyhedralTermList.termlist_to_polytope(PolyhedralTermList(new_context_list), PolyhedralTermList([]))
        variables = retval[0]
        new_context_mat = retval[1]
        new_context_cons = retval[2]
        polarity = 1
        if refine:
            polarity = -1
        objective = [polarity * term.get_coefficient(var) for var in variables]
        logging.debug(new_context_mat)
        logging.debug(new_context_cons)
        logging.debug(objective)
        res = linprog(c=objective, A_ub=new_context_mat, b_ub=new_context_cons, bounds=(None, None))
        if res["status"] in {2, 3}:
            # unbounded
            # return term.copy()
            raise ValueError("Tactic 2 did not succeed")
        replacement = polarity * res["fun"]
        # replace the irrelevant variables with new findings in term
        result = term.copy()
        for var in vars_to_elim:  # noqa: VNE002
            result = result.remove_variable(var)
        result.constant -= replacement
        # check vacuity
        if not result.vars:
            return term.copy(), 1
        return result, 1

    @staticmethod
    def _tactic_3(
        term: PolyhedralTerm, context: PolyhedralTermList, vars_to_elim: list, refine: bool
    ) -> Tuple[Optional[PolyhedralTerm], int]:
        logging.debug("************ Tactic 3")
        logging.debug("Vars_to_elim %s \nTerm %s \nContext %s " % (vars_to_elim, term, context))
        conflict_vars = list_intersection(vars_to_elim, term.vars)
        conflict_coeff = {var: term.get_coefficient(var) for var in conflict_vars}
        new_term = term.copy()
        for var in conflict_vars:  # noqa: VNE002 variable name 'var' should be clarified
            new_term = new_term.remove_variable(var)
        new_term.variables[Var("_")] = 1
        # modify the context
        subst_term_vars = {Var("_"): 1.0 / conflict_coeff[conflict_vars[0]]}
        for var in conflict_vars:  # noqa: VNE002 variable name 'var' should be clarified
            if var != conflict_vars[0]:
                subst_term_vars[var] = -conflict_coeff[var] / conflict_coeff[conflict_vars[0]]
        subst_term = PolyhedralTerm(variables=subst_term_vars, constant=0)
        new_context = PolyhedralTermList(
            [el.copy().substitute_variable(conflict_vars[0], subst_term) for el in context.terms]
        )
        # now we use tactic 1
        new_elims = list_diff(list_union(vars_to_elim, [Var("_")]), [conflict_vars[0]])
        try:
            result, count = PolyhedralTermList._tactic_1(new_term, new_context, new_elims, refine)
        except ValueError as e:  # noqa: WPS329 Found useless `except` case
            raise e
        logging.debug("************ Leaving Tactic 3")
        logging.debug("Vars_to_elim %s \nTerm %s \nContext %s " % (vars_to_elim, term, context))
        return result, count

    @staticmethod
    def _tactic_4(  # noqa: WPS231
        term: PolyhedralTerm, context: PolyhedralTermList, vars_to_elim: list, refine: bool, no_vars: List[Var]
    ) -> Tuple[Optional[PolyhedralTerm], int]:
        logging.debug("************ Tactic 4")
        logging.debug("Vars_to_elim %s \nTerm %s \nContext %s " % (vars_to_elim, term, context))
        if not refine:
            raise ValueError("Only refinement is supported")

        conflict_vars = list_intersection(vars_to_elim, term.vars)
        if len(conflict_vars) > 1:
            raise ValueError("Tactic 4 unsuccessful")

        var_to_elim = conflict_vars[0]
        goal_context: List[PolyhedralTerm] = []
        useful_context: List[PolyhedralTerm] = []
        polarity = -1

        if refine:
            polarity = 1

        for context_term in context.terms:
            if list_intersection(context_term.vars, no_vars):
                continue
            coeff = context_term.get_coefficient(var_to_elim)
            if coeff != 0 and polarity * coeff * term.get_coefficient(var_to_elim) > 0:
                temp_conflict_vars = list_intersection(context_term.vars, vars_to_elim)
                if len(temp_conflict_vars) == 1:
                    goal_context.append(context_term.copy())
                if len(temp_conflict_vars) == 2:
                    useful_context.append(context_term.copy())

        if not useful_context and not goal_context:
            raise ValueError("Tactic 4 unsuccessful")

        total_calls = 1

        if goal_context:
            return term.substitute_variable(var_to_elim, goal_context[0].isolate_variable(var_to_elim)), total_calls

        ############
        for useful_term in useful_context:
            new_context = context.copy()
            new_context.terms.remove(useful_term)
            new_term = useful_term.isolate_variable(var_to_elim)
            new_no_vars = no_vars.copy()
            new_no_vars.append(var_to_elim)
            try:  # noqa: WPS229
                return_term, recursive_count = PolyhedralTermList._tactic_4(
                    new_term, new_context, vars_to_elim, refine, new_no_vars
                )
                total_calls += recursive_count
                if return_term is None:
                    continue
                return term.substitute_variable(var_to_elim, return_term), total_calls
            except ValueError:
                total_calls += 1

        return None, total_calls

    @staticmethod
    def _get_tlp_context(  # noqa: WPS231
        term: PolyhedralTerm, context: PolyhedralTermList, vars_to_elim: list, refine: bool
    ) -> Tuple[List[PolyhedralTerm], List[Var]]:
        forbidden_vars = list_intersection(vars_to_elim, term.vars)
        matrix_row_terms = []

        var_list, B, b, _, _ = PolyhedralTermList.termlist_to_polytope(  # noqa: WPS236, N806
            terms=context, context=PolyhedralTermList([])
        )
        objective = np.array([term.get_coefficient(var) if var in forbidden_vars else 0 for var in var_list])
        if refine:
            objective *= -1

        res = linprog(c=objective, A_ub=B, b_ub=b, bounds=(None, None))
        # Linprog's status values
        # 0 : Optimization proceeding nominally.
        # 1 : Iteration limit reached.
        # 2 : Problem appears to be infeasible.
        # 3 : Problem appears to be unbounded.
        # 4 : Numerical difficulties encountered.
        if res["status"] == 3:
            raise ValueError("Unbounded")
        elif res["status"] != 0:
            raise ValueError("Constraints are unfeasible")

        num_vars_to_elim = len(forbidden_vars)
        slack = res["slack"]
        indices = np.where(np.isclose(slack, 0))[0]

        assert len(indices) >= num_vars_to_elim
        terms_added = 0
        for index in indices:
            context_term = context.terms[index]
            if list_intersection(context_term.vars, forbidden_vars):
                matrix_row_terms.append(context_term)
                terms_added += 1
                if terms_added == num_vars_to_elim:
                    break

        if terms_added < num_vars_to_elim:
            raise ValueError("Context has insufficient information")

        return matrix_row_terms, forbidden_vars

    @staticmethod
    def _tactic_5(  # noqa: WPS231
        term: PolyhedralTerm, context: PolyhedralTermList, vars_to_elim: list, refine: bool
    ) -> Tuple[Optional[PolyhedralTerm], int]:
        logging.debug("************ Tactic 5")
        return PolyhedralTermList._context_reduction(term, context, vars_to_elim, refine, 5), 1

    @staticmethod
    def _tactic_trivial(  # noqa: WPS231
        term: PolyhedralTerm, context: PolyhedralTermList, vars_to_elim: list, refine: bool
    ) -> Tuple[Optional[PolyhedralTerm], int]:
        return term.copy(), 1

    TACTICS = {  # noqa: WPS115
        1: _tactic_1.__func__,  # type: ignore
        2: _tactic_2.__func__,  # type: ignore
        3: _tactic_3.__func__,  # type: ignore
        4: lambda term, context, vars_to_elim, refine: PolyhedralTermList._tactic_4(
            term, context, vars_to_elim, refine, []
        ),
        5: _tactic_5.__func__,  # type: ignore
        6: _tactic_trivial.__func__,  # type: ignore
    }

    # Return:
    # - transformed term
    # - successful tactic number, if > 0; 0 if no applicable tactic, -1 if all tactics failed
    # - count of tactic invocations if successful
    @staticmethod
    def _transform_term(  # noqa: WPS231
        term: PolyhedralTerm,
        context: PolyhedralTermList,
        vars_to_elim: list,
        refine: bool,
        tactics_order: Optional[List[int]] = None,
    ) -> Tuple[PolyhedralTerm, int, float, int]:
        if tactics_order is None:
            tactics_order = TACTICS_ORDER

        if not list_intersection(term.vars, vars_to_elim):
            raise ValueError("Irrelevant transform term call!")

        logging.debug("Transforming term: %s", term)
        logging.debug("Context: %s", context)

        for tactic_num in tactics_order:  # noqa WPS327
            try:  # noqa: WPS229
                ta = time.time()
                result, count = PolyhedralTermList.TACTICS[tactic_num](term, context, vars_to_elim, refine)
                tb = time.time()
                if result is not None:
                    return result, tactic_num, tb - ta, count
            except ValueError:
                continue

        return term.copy(), -1, 0, 0
