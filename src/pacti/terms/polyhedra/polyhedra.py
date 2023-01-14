"""
PolyhedralTerm provides support for linear inequalities as constraints, i.e.,
the constraints are of the form $\\sum_{i} a_i x_i \\le c$, where the
$x_i$ are variables and the $a_i$ and $c$ are constants.
"""
from __future__ import annotations

import logging

import numpy as np
import sympy
from scipy.optimize import linprog

from pacti.iocontract import Term, TermList, Var
from pacti.utils.lists import list_diff, list_intersection, list_union


class PolyhedralTerm(Term):
    """
    Polyhedral terms are linear inequalities over a list of variables.

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
    """

    # Constructor: get (i) a dictionary whose keys are variables and whose
    # values are the coefficients of those variables in the term, and (b) a
    # constant. The term is assumed to be in the form \Sigma_i a_i v_i +
    # constant <= 0
    def __init__(self, variables, constant):
        variable_dict = {}
        for key, val in variables.items():
            if val != 0:
                if isinstance(key, str):
                    variable_dict[Var(key)] = val
                else:
                    variable_dict[key] = val
        self.variables = variable_dict
        self.constant = constant

    def __eq__(self, other):
        match = self.variables.keys() == other.variables.keys()
        if match:
            for k, v in self.variables.items():
                match = match and (v == other.variables[k])
        return match and self.constant == other.constant

    def __str__(self) -> str:
        varlist = list(self.variables.items())
        varlist.sort(key=lambda x: str(x[0]))
        res = " + ".join([str(coeff) + "*" + var.name for var, coeff in varlist])
        res += " <= " + str(self.constant)
        return res

    def __hash__(self):
        return hash(str(self))

    def __repr__(self):
        return "<Term {0}>".format(self)

    def __add__(self, other):
        varlist = list_union(self.vars, other.vars)
        variables = {}
        for var in varlist:
            variables[var] = self.get_coefficient(var) + other.get_coefficient(var)
        return PolyhedralTerm(variables, self.constant + other.constant)

    def copy(self):
        return PolyhedralTerm(self.variables, self.constant)

    @property
    def vars(self):
        """
        Variables appearing in term with a nonzero coefficient.

        Example:
            For the term $ax + by \\le c$ with variables $x$ and
            $y$, this function returns the list $\\{x, y\\}$ if
            $a$ and $b$ are nonzero.
        """
        varlist = self.variables.keys()
        return list(varlist)

    def contains_var(self, var_to_seek):
        """
        Tell whether term contains a given variable.

        Args:
            var_to_seek: The variable that we are seeking in the current term.

        Returns:
            `True` if the syntax of the term refers to the given variable;
            `False` otherwise.
        """
        return var_to_seek in self.vars

    def get_coefficient(self, var):
        """
        Output the coefficient multiplying the given variable in the term.

        Args:
            var: The variable whose coefficient we are seeking.
        """
        if self.contains_var(var):
            return self.variables[var]
        else:
            return 0

    def get_polarity(self, var, polarity=True):
        """
        Tells whether the polarity of a given variable in the term matches the
        given polarity.

        The polarity of a variable in a term is defined as the polarity of the
        coefficient that multiplies it in a term, e.g., the variables $x$
        and $y$ in the term $-2x + y \\le 3$ have negative and
        positive polarities respectively.

        Args:
            var: The variable whose polarity in the term we are seeking.
            polarity: The polarity that we are comparing against the variable's
            polarity.

        Returns:
            `True` if the variable's polarity matches `polarity` and
            `False` otherwise. If the variable's coefficient in the term
            is zero, return `True`.
        """
        if polarity:
            return self.variables[var] >= 0
        else:
            return self.variables[var] <= 0

    def get_sign(self, var):
        """
        Tells whether the polarity of a given variable in the term matches the
        given polarity.

        The polarity of a variable in a term is defined as the polarity of the
        coefficient that multiplies it in a term, e.g., the variables $x$
        and $y$ in the term $-2x + y \\le 3$ have negative and
        positive polarities respectively.

        Args:
            var: The variable whose polarity in the term we are seeking.
            polarity: The polarity that we are comparing against the variable's
            polarity.

        Returns:
            `True` if the variable's polarity matches `polarity` and
            `False` otherwise. If the variable's coefficient in the term
            is zero, return `True`.
        """
        if self.get_polarity(var, True):
            return 1
        else:
            return -1

    def get_matching_vars(self, variable_polarity):
        """
        Returns the list of variables whose polarities match the polarities
        requested.

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
        variable_list = list()
        for var in variable_polarity.keys():
            if self.contains_var(var):
                if (self.get_polarity(var, True) == variable_polarity[var]) or (self.get_coefficient(var) == 0):
                    variable_list.add(var)
                else:
                    variable_list = list()
                    break
        return variable_list

    def remove_variable(self, var):
        """
        Eliminates a variable from a term. This is equivalent to setting its
        coefficient to zero.

        Args:
            var: variable to be eliminated.
        """
        if self.contains_var(var):
            self.variables.pop(var)

    def multiply(self, factor):
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

    def substitute_variable(self, var, subst_with_term):
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
            self.remove_variable(var)
            logging.debug(self)
            return self + term
        else:
            return self.copy()

    @staticmethod
    def to_symbolic(term):
        """
        Translates the variable terms of a PolyhedralTerm into a sympy
        expression.

        Example:
            The code

            ```
                x = Var('x') y = Var('y') variables = {x:-2, y:3} constant  = 4
                term = PolyhedralTerm(variables, constant) expression =
                PolyhedralTerm.to_symbolic(term)
            ```

            yields the expression $-2x + 3y$.

        Args:
            term(PolyhedralTerm):
                The term whose coefficients and variables are to be translated
                to sympy's data structure.
        """
        ex = -term.constant
        for var in term.vars:
            sv = sympy.symbols(var.name)
            ex += sv * term.get_coefficient(var)
        return ex

    @staticmethod
    def to_term(expression):
        """
        Translates a sympy expression into a PolyhedralTerm.

        Example:
            The expression $2x + 3y - 1$ is translated into
            `PolyhedralTerm(variables={x:2, y:3}, constant=1)`.

        Args:
            expression: The symbolic expression to be translated.
        """
        expression_coefficients = expression.as_coefficients_dict()
        logging.debug(expression_coefficients)
        keys = list(expression_coefficients.keys())
        variable_dict = {}
        constant = 0
        for key in keys:
            logging.debug(type(key))
            if isinstance(key, str) or isinstance(key, sympy.core.symbol.Symbol):
                var = Var(str(key))
                variable_dict[var] = expression_coefficients[key]
            else:
                constant = constant - expression_coefficients[key] * key
        return PolyhedralTerm(variable_dict, constant)

    @staticmethod
    def term_to_polytope(term, variable_list):
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
        for var in variable_list:
            coeffs.append(term.get_coefficient(var))
        return coeffs, term.constant

    @staticmethod
    def polytope_to_term(poly, const, variables):
        """
        Transform a list of coefficients and variables into a PolyhedralTerm.

        Args:
            poly: An ordered list of coefficients.

            const: The term's coefficient.

            variables:
                An ordered list of variables corresponding to the coefficients.
        """
        assert len(poly) == len(variables)
        variable_dict = {}
        for i, var in enumerate(variables):
            variable_dict[var] = poly[i]
        return PolyhedralTerm(variable_dict, const)

    @staticmethod
    def solve_for_variables(context, vars_to_elim):
        """
        Interpret a list of terms as equalities and solve the system of equations
        for the given variables.

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
        else:
            return {}


class PolyhedralTermList(TermList):
    """
    A TermList of PolyhedralTerm instances.
    """

    def _transform(self, context: PolyhedralTermList, vars_to_elim: list, abduce: bool):
        logging.debug("Transforming: %s", self)
        logging.debug("Context terms: %s", context)
        logging.debug("Variables to eliminate: %s", vars_to_elim)
        term_list = list(self.terms)
        new_terms = list()
        for term in term_list:
            helpers = (context | self) - PolyhedralTermList([term])
            try:
                new_term = PolyhedralTermList.transform_term(term, helpers, vars_to_elim, abduce)
            except ValueError as e:
                new_term = term
            new_terms.append(new_term)

        self.terms = list(new_terms)

        # the last step needs to be a simplification
        logging.debug("Ending transformation with simplification")
        self.simplify(context)

    def abduce_with_context(self, context: TermList, vars_to_elim: list) -> TermList:
        """
        Obtain a list of PolyhedralTerm instances lacking the indicated variables
        and implying the given TermList in the given context.

        Example:
            Suppose the current list of terms is $\\{x + y \\le 6\\}$, the
            context is $\\{y \\le 5\\}$, and the abduced terms should not
            contain variable $y$. Then the current TermList could be
            abduced to $\\{x \\le 1\\}$ because $x \\le 1
            \\;\\land\\; y \\le 5 \\Rightarrow x + y \\le 6$.

        Args:
            context:
                The TermList providing the context for the abduction.

            vars_to_elim:
                Variables that should not appear in the abduced term.

        Returns:
            A list of terms not containing any variables in `vars_to_elim`
            and which, in the context provided, imply the terms contained in the
            calling termlist.
        """
        termlist = self.copy()
        logging.debug("Abducing from terms: %s", self)
        logging.debug("Context: %s", context)
        logging.debug("Vars to elim: %s", vars_to_elim)
        try:
            termlist.simplify(context)
        except ValueError as e:
            raise ValueError(
                "Provided constraints \n{}\n".format(self) + "are unsatisfiable in context \n{}".format(context)
            ) from e
        try:
            termlist._transform(context, vars_to_elim, True)
        except ValueError as e:
            raise ValueError(
                "The elimination of variables \n{}\n".format(vars_to_elim)
                + "by abducing terms \n{}\n".format(self)
                + "in context \n{}\n".format(context)
                + "was not possible"
            ) from e
        return termlist

    def lacks_constraints(self):
        """
        Tell whether TermList is empty.
        """
        return len(self.terms) == 0

    def deduce_with_context(self, context: TermList, vars_to_elim: list) -> TermList:
        """
        Obtain a list of PolyhedralTerm instances lacking the indicated variables
        and implied by the given TermList in the given context.

        Example:
            Suppose the current list of terms is $\\{x - y \\le 6\\}$, the
            context is $\\{y \\le 5\\}$, and the deduced terms should not
            contain variable $y$. Then the current TermList could be
            deduced to $\\{x \\le 11\\}$ because $x - y \\le 6
            \\;\\land\\; y \\le 5 \\Rightarrow x \\le 11$.

        Args:
            context:
                The TermList providing the context for the deduction.

            vars_to_elim:
                Variables that should not appear in the deduced term.

        Returns:
            A list of terms not containing any variables in `vars_to_elim`
            and which, in the context provided, are implied by the terms
            contained in the calling termlist.
        """
        termlist = self.copy()
        logging.debug("Deduce with context")
        logging.debug("Deducing from terms %s", self)
        logging.debug("Context: %s", context)
        logging.debug("Vars to elim: %s", vars_to_elim)
        try:
            termlist.simplify(context)
        except ValueError as e:
            raise ValueError(
                "Provided constraints \n{}\n".format(self) + "are unsatisfiable in context \n{}".format(context)
            ) from e
        try:
            termlist._transform(context, vars_to_elim, False)
        except ValueError as e:
            raise ValueError(
                "The elimination of variables \n{}\n".format(vars_to_elim)
                + "by deducing terms \n{}\n".format(self)
                + "in context \n{}\n".format(context)
                + "was not possible"
            ) from e
        # eliminate terms containing the variables to be eliminated
        terms_to_elim = termlist.get_terms_with_vars(vars_to_elim)
        termlist.terms = list_diff(termlist.terms, terms_to_elim.terms)
        return termlist

    def simplify(self, context: PolyhedralTermList | None = None) -> None:  # type: ignore[override]
        """
        Remove redundant terms in the PolyhedralTermList using the provided
        context.

        Example:
            Suppose the TermList is $\\{x - 2y \\le 5, x - y \\le 0\\}$ and
            the context is $\\{x + y \\le 0\\}$. Then the TermList could be
            simplified to $\\{x - y \\le 0\\}$.

        Args:
            context:
                The TermList providing the context for the simplification.
        """
        logging.debug("Starting simplification procedure")
        logging.debug("Simplifying terms: %s", self)
        logging.debug("Context: %s", context)
        if not context:
            variables, self_mat, self_cons, ctx_mat, ctx_cons = PolyhedralTermList.termlist_to_polytope(
                self, PolyhedralTermList()
            )
        else:
            variables, self_mat, self_cons, ctx_mat, ctx_cons = PolyhedralTermList.termlist_to_polytope(self, context)
        logging.debug("Polytope is \n%s", self_mat)
        try:
            a_red, b_red = PolyhedralTermList.reduce_polytope(self_mat, self_cons, ctx_mat, ctx_cons)
        except ValueError as e:
            raise ValueError(
                "The constraints \n{}\n".format(self) + "are unsatisfiable in context \n{}".format(context)
            ) from e
        logging.debug("Reduction: \n%s", a_red)
        self.terms = PolyhedralTermList.polytope_to_termlist(a_red, b_red, variables).terms
        logging.debug("Back to terms: \n%s", self)

    def refines(self, other: PolyhedralTermList) -> bool:  # type: ignore[override]
        """
        Tells whether the argument is a larger specification, i.e., compute self
        <= other.

        Args:
            other:
                TermList against which we are comparing self.
        """
        logging.debug("Verifying refinement")
        logging.debug("LH term: %s", self)
        logging.debug("RH term: %s", other)
        if other.lacks_constraints():
            return True
        variables, self_mat, self_cons, ctx_mat, ctx_cons = PolyhedralTermList.termlist_to_polytope(self, other)
        logging.debug("Polytope is \n%s", self_mat)
        result = PolyhedralTermList.verify_polytope_containment(self_mat, self_cons, ctx_mat, ctx_cons)
        return result

    @staticmethod
    def termlist_to_polytope(terms: PolyhedralTermList, context: PolyhedralTermList):
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
        logging.debug("a is \n%s", a)
        return variables, np.array(a), np.array(b), a_h_ret, np.array(b_h)

    @staticmethod
    def polytope_to_termlist(matrix, vector, variables: list[Var]) -> PolyhedralTermList:
        """
        Transforms a matrix-vector pair into a PolyhedralTermList, assuming that
        the variable coefficients in the matrix are ordered as specified.

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
        logging.debug("&&&&&&&&&&")
        # logging.debug("Poly is " + str(polytope))
        logging.debug("matrix is %s", matrix)
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
    def reduce_polytope(
        a: np.ndarray, b: np.ndarray, a_help: np.ndarray = np.array([[]]), b_help: np.ndarray = np.array([])
    ):
        """
        Eliminate redundant constraints from the H-representation of a given
        polytope using as context a given polytope.

        Args:
            a:
                Matrix of H-representation of polytope to reduce.
            b:
                Vector of H-representation of polytope to reduce.
            a_help:
                Matrix of H-representation of context polytope.
            b_help:
                Vector of H-representation of context polytope.
        """
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
            logging.debug("Optimization objective: \n%s", objective)
            logging.debug("a_temp is \n%s", a_temp)
            logging.debug("a_help is \n%s", a_help)
            logging.debug("b_temp is \n%s", b_temp)
            logging.debug("b_help is \n%s", b_help)
            if helper_present:
                a_opt = np.concatenate((a_temp, a_help), axis=0)
                b_opt = np.concatenate((b_temp, b_help))
            else:
                a_opt = a_temp
                b_opt = b_temp
            res = linprog(c=objective, A_ub=a_opt, b_ub=b_opt, bounds=(None, None))  # ,options={'tol':0.000001})
            b_temp[i] -= 1
            if res["fun"]:
                logging.debug("Optimal value: %s", -res["fun"])
            logging.debug("Results: %s", res)
            # if res["success"] and -res["fun"] <= b_temp[i]:
            if res["status"] != 2 and -res["fun"] <= b_temp[i]:
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
    def verify_polytope_containment(
        a_l: np.ndarray = np.array([[]]),
        b_l: np.ndarray = np.array([]),
        a_r: np.ndarray = np.array([[]]),
        b_r: np.ndarray = np.array([]),
    ) -> bool:
        """
        Say whether a polytope is contained in another. Both are given in their
        H-representation.

        Args:
            a_l:
                Matrix of H-representation of polytope on LHS of inequality.
            b_l:
                Vector of H-representation of polytope on LHS of inequality.
            a_r:
                Matrix of H-representation of polytope on RHS of inequality.
            b_r:
                Vector of H-representation of polytope on RHS of inequality.
        """
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
            logging.debug("Optimal value: %s", -res["fun"])
            logging.debug("Results: %s", res)
            # if res["success"] and -res["fun"] <= b_temp[i]:
            if res["status"] != 2 and -res["fun"] <= b_temp:
                logging.debug("Redundant constraint")
            else:
                is_refinement = False
                break
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
        """
        logging.debug("Verifying polytope emptyness: a is %s ashape is %s, b is %s", a, a.shape, b)
        if len(a) == 0:
            return False
        n, m = a.shape
        if n * m == 0:
            return False
        assert n == len(b)
        objective = np.zeros((1, m))
        res = linprog(c=objective, A_ub=a, b_ub=b, bounds=(None, None))  # ,options={'tol':0.000001})
        if res["status"] != 2:
            return False
        else:
            return True

    @staticmethod
    def get_kaykobad_context(term: PolyhedralTerm, context: PolyhedralTermList, vars_to_elim: list, abduce: bool):
        forbidden_vars = list_intersection(vars_to_elim, term.vars)
        other_forbibben_vars = list_diff(vars_to_elim, term.vars)
        n = len(forbidden_vars)
        matrix_row_terms = []  # type: list[PolyhedralTerm]
        partial_sums = [0.0] * n
        transform_coeff = -1
        if abduce:
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
                for var in other_forbibben_vars:
                    if context_term.get_coefficient(var) != 0:
                        term_is_invalid = True
                        logging.debug("Term contains other forbidden vars")
                        break
                if term_is_invalid:
                    continue
                # 1. Verify Kaykobad pair: sign of nonzero matrix terms
                for var in forbidden_vars:
                    if context_term.get_coefficient(var) != 0 and transform_coeff * context_term.get_sign(
                        var
                    ) != term.get_sign(var):
                        term_is_invalid = True
                        logging.debug("Failed first matrix-vector verification")
                        break
                # 2. Verify Kaykobad pair: matrix diagonal terms
                if context_term.get_coefficient(i_var) == 0 or term_is_invalid:
                    logging.debug("Failed second matrix-vector verification")
                    continue
                # 3. Verify Kaykobad pair: relation between matrix and vector
                residuals = [0.0] * n
                for j, j_var in enumerate(forbidden_vars):
                    logging.debug("Verifying third condition on variable %s", j_var)
                    if j != i:
                        residuals[j] = (
                            term.get_sign(j_var)
                            * context_term.get_coefficient(j_var)
                            * term.get_coefficient(i_var)
                            / context_term.get_coefficient(i_var)
                        )
                    if np.abs(term.get_coefficient(j_var)) <= partial_sums[j] + residuals[j]:
                        logging.debug("q coefficient: %s", term.get_coefficient(j_var))
                        logging.debug("RHS: %s", partial_sums[j] + residuals[j])
                        term_is_invalid = True
                        logging.debug("Failed third matrix-vector verification")
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
            logging.debug("Hola2")
            raise ValueError("Found context will produce empty transformation")
        logging.debug("Matrix row terms %s", matrix_row_terms)
        return matrix_row_terms, forbidden_vars

    @staticmethod
    def transform_term(term: PolyhedralTerm, context: PolyhedralTermList, vars_to_elim: list, abduce: bool):
        logging.debug("Transforming term: %s", term)
        logging.debug("Context: %s", context)
        try:
            matrix_row_terms, forbidden_vars = PolyhedralTermList.get_kaykobad_context(
                term, context, vars_to_elim, abduce
            )
        except ValueError as e:
            logging.debug("Could not transform %s", term)
            raise ValueError("Could not transform term {}".format(term)) from e
        matrix_row_terms = PolyhedralTermList(list(matrix_row_terms))
        sols = PolyhedralTerm.solve_for_variables(matrix_row_terms, list(forbidden_vars))
        logging.debug("Sols %s", sols)

        result = term.copy()
        logging.debug("Result is %s", result)
        for var in sols.keys():
            result = result.substitute_variable(var, sols[var])
        logging.debug("Term %s transformed to %s", term, result)

        return result
