"""
PolyhedralTerm provides support for linear inequalities as constraints, i.e.,
the constraints are of the form :math:`\\sum_{i} a_i x_i \\le c`, where the
:math:`x_i` are variables and the :math:`a_i` and :math:`c` are constants.
"""
from __future__ import annotations
import logging
import sympy
import numpy as np
from scipy.optimize import linprog
import IoContract



class PolyhedralTerm(IoContract.Term):
    """
    Polyhedral terms are linear inequalities over a set of variables.

    Usage:
        Polyhedral terms are initialized as follows:

        .. highlight:: python
        .. code-block:: python

            variables = {Var('x'):2, Var('y'):3}
            constant = 3
            term = PolyhedralTerm(variables, constant)

        :code:`variables` is a dictionary whose keys are :code:`Var` instances,
        and :code:`constant` is a number. Thus, our example represents the
        expression :math:`2x + 3y \\le 3`.
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
                    variable_dict[IoContract.Var(key)] = val
                else:
                    variable_dict[key] = val
        self.variables = variable_dict
        self.constant = constant

    def __eq__(self, other):
        return self.variables == other.variables and \
            self.constant == other.constant

    def __str__(self) -> str:
        res = " + ".join([str(coeff)+"*"+var.name
                          for var, coeff in self.variables.items()])
        res += " <= " + str(self.constant)
        return res

    def __hash__(self):
        return hash(str(self))

    def __repr__(self):
        return "<Term {0}>".format(self)

    def __add__(self, other):
        varlist = list(self.vars | other.vars)
        variables = {}
        for var in varlist:
            variables[var] = self.get_coefficient(var) + \
                other.get_coefficient(var)
        return PolyhedralTerm(variables, self.constant + other.constant)

    def copy(self):
        return PolyhedralTerm(self.variables, self.constant)

    @property
    def vars(self):
        """
        Variables appearing in term with a nonzero coefficient.

        Example:
            For the term :math:`ax + by \\le c` with variables :math:`x` and
            :math:`y`, this function returns the set :math:`\\{x, y\\}` if
            :math:`a` and :math:`b` are nonzero.
        """
        varlist = self.variables.keys()
        return set(varlist)

    def contains_var(self, var):
        """
        Tell whether term contains a given variable.

        Args:
            var: The variable that we are seeking in the current term.

        Returns:
            :code:`True` if the syntax of the term refers to the given variable;
            :code:`False` otherwise.
        """
        return var in self.vars

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
        coefficient that multiplies it in a term, e.g., the variables :math:`x`
        and :math:`y` in the term :math:`-2x + y \\le 3` have negative and
        positive polarities respectively.

        Args:
            var: The variable whose polarity in the term we are seeking.
            polarity: The polarity that we are comparing against the variable's
            polarity.

        Returns:
            :code:`True` if the variable's polarity matches :code:`polarity` and
            :code:`False` otherwise. If the variable's coefficient in the term
            is zero, return :code:`True`.
        """
        if polarity:
            return self.variables[var] >= 0
        else:
            return self.variables[var] <= 0


    def get_matching_vars(self, variable_polarity):
        """
        Returns the set of variables whose polarities match the polarities
        requested.

        Example:

        .. code-block:: python

            x = Var('x')
            y = Var('y')
            z = Var('z')
            variables = {x:-2, y:3}
            constant  = 4
            term = PolyhedralTerm(variables, constant)
            polarities = {y:True}
            term.get_matching_vars(polarities)        
        
        The last call returns :code:`{y, z}` because the variable y matches the
        requested polarity in the term, and the variable z has a zero
        coefficient. 


        Args:
            variable_polarity: A dictionary mapping Var instances to Boolean
            values indicating the polarity of the given variable.

        Returns:
            If all variables in the term match the polarities specified in the
            argument, the routine returns the matching variables.  Otherwise,
            it returns an empty set.
        """
        variable_set = set()
        for var in variable_polarity.keys():
            if self.contains_var(var):
                if (self.get_polarity(var, True) == variable_polarity[var]) or \
                    (self.get_coefficient(var) == 0):
                    variable_set.add(var)
                else:
                    variable_set = set()
                    break
        return variable_set


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
        
        For example, multiplying the term :math:`2x + 3y \\le 4` by the factor 2
        yields :math:`4x + 6y \\le 8`.

        Args:
            factor: element by which the term is multiplied.

        Returns:
            A new term which is the result of the given term multiplied by
            :code:`factor`.
        """
        variables = {key:factor*val for key, val in self.variables.items()}
        return PolyhedralTerm(variables, factor*self.constant)

    
    def substitute_variable(self, var, subst_with_term):
        """
        Substitutes a specified variable in a term with a given term.

        Example:
            In the term :math:`2x - y \\le 6`, substituting y by the term
            :math:`x + z \\le 5` yields :math:`x - z \\le 1`. Observe that the
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

            .. code-block:: python

                x = Var('x') y = Var('y') variables = {x:-2, y:3} constant  = 4
                term = PolyhedralTerm(variables, constant) expression =
                PolyhedralTerm.to_symbolic(term)

            yields the expression :math:`-2x + 3y`.

        Args:
            term(PolyhedralTerm):
                The term whose coefficients and variables are to be translated
                to sympy's data structure.
        """
        ex = 0
        for var in term.vars:
            sv = sympy.symbols(var.name)
            ex += sv * term.get_coefficient(var)
        return ex


    @staticmethod
    def to_term(expression):
        """
        Translates a sympy expression into a PolyhedralTerm.

        Example:
            The expression :math:`2x + 3y - 1` is translated into
            :code:`PolyhedralTerm(variables={x:2, y:3}, constant=1)`.

        Args:
            expression: The symbolic expression to be translated.
        """
        expression_coefficients = expression.as_coefficients_dict()
        keys = list(expression_coefficients.keys())
        variable_dict = {}
        constant = 0
        for key in keys:
            if key == 1:
                constant = -expression_coefficients[key]
            else:
                var = IoContract.Var(str(key))
                variable_dict[var] = expression_coefficients[key]
        return PolyhedralTerm(variable_dict, constant)

    @staticmethod
    def term_to_polytope(term, variable_list):
        """
        Transform a term into a vector according to the given order.

        Example:
            The term :math:`3x + 5y -2z \\le 7` with :code:`variable_list = [y,
            x, w, z]` yields the tuple :code:`[5, 3, 0, -2], 7`.

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
        Interpret a set of terms as equalities and solve the system of equations
        for the given variables.

        Args:
            context:
                The set of terms to be solved. Each term will be interpreted as
                an equality.
            
            vars_to_elim:
                The set of variables whose solutions will be sought.

        Assumptions: the number of equations matches the number of vars_to_elim
        contained in the terms.

        Returns:
            A dictionary mapping variables to their solutions. The solutions are
            expressed as PolyhedralTerm instances.
        """
        logging.debug("GetVals: %s Vars: %s", context, vars_to_elim)
        vars_to_solve = context.vars & vars_to_elim
        assert len(context.terms) == len(vars_to_solve)
        exprs = [PolyhedralTerm.to_symbolic(term) for term in context.terms]
        vars_to_solve_symb = [sympy.symbols(var.name) for var in vars_to_solve]
        sols = sympy.solve(exprs, *vars_to_solve_symb)
        logging.debug(sols)
        if len(sols) > 0:
            return {IoContract.Var(str(key)):
                    PolyhedralTerm.to_term(sols[key]) for
                    key in sols.keys()}
        else:
            return {}



class PolyhedralTermSet(IoContract.TermSet):
    """
    A TermSet of PolyhedralTerm instances.
    """


    # This routine accepts a term that will be adbuced with the help of other
    # terms The abduction aims to eliminate from the term appearances of the
    # variables contained in vars_to_elim
    def _transform(self, context: set,
                   vars_to_elim: set, polarity: True):
        logging.debug("Context terms: %s", context)
        logging.debug("Variables to eliminate: %s", vars_to_elim)
        helpers = context.copy()
        term_list = list(self.terms)
        for i, term in enumerate(term_list):
            logging.debug("Transforming %s", term)
            vars_elim = {}
            for var in term.vars & vars_to_elim:
                vars_elim[var] = term.get_polarity(var, polarity)
            logging.debug("Vars to elim: %s", vars_elim)
            vars_to_cover = set(vars_elim.keys())
            terms_to_use = PolyhedralTermSet(set())

            # now we have to choose from the helpers any terms that we can use
            # to eliminate these variables
            for helper in helpers.terms:
                matching_vars = helper.get_matching_vars(vars_elim)
                if len(matching_vars & vars_to_cover) > 0:
                    vars_to_cover = vars_to_cover - matching_vars
                    terms_to_use.terms.add(helper)
                    helpers.terms.remove(helper)
                    if len(vars_to_cover) == 0:
                        break

            logging.debug("TermsToUse: %s", terms_to_use)

            # as long as we have more "to_elim" variables than terms, we seek
            # additional terms. For now, we throw an error if we don't have
            # enough terms
            assert len(terms_to_use.terms) == \
                len(terms_to_use.vars & vars_to_elim)

            sols = PolyhedralTerm.solve_for_variables(terms_to_use,
                                                      vars_to_elim)
            logging.debug(sols)
            for var in sols.keys():
                term = term.substitute_variable(var, sols[var])
            term_list[i] = term

            logging.debug("After subst: %s", term)

        self.terms = set(term_list)

        # the last step needs to be a simplification
        self.simplify()


    def abduce_with_context(self, context: set, vars_to_elim: set) -> None:
        """
        Obtain a set of PolyhedralTerm instances lacking the indicated variables
        and implying the given TermSet in the given context.

        Example:
            Suppose the current set of terms is :math:`\\{x + y \\le 6\\}`, the
            context is :math:`\\{y \\le 5\\}`, and the abduced terms should not
            contain variable :math:`y`. Then the current TermSet could be
            abduced to :math:`\\{x \\le 1\\}` because :math:`x \\le 1
            \\;\\land\\; y \\le 5 \\Rightarrow x + y \\le 6`.

        Args:
            context:
                The TermSet providing the context for the abduction.

            vars_to_elim:
                Variables that should not appear in the abduced term.
        """
        logging.debug("Abducing from terms: %s", self)
        logging.debug("Context: %s", context)
        logging.debug("Vars to elim: %s", vars_to_elim)
        self.simplify(context)
        self._transform(context, vars_to_elim, True)

    def deduce_with_context(self, context: set, vars_to_elim: set) -> None:
        """
        Obtain a set of PolyhedralTerm instances lacking the indicated variables
        and implied by the given TermSet in the given context.

        Example:
            Suppose the current set of terms is :math:`\\{x - y \\le 6\\}`, the
            context is :math:`\\{y \\le 5\\}`, and the deduced terms should not
            contain variable :math:`y`. Then the current TermSet could be
            deduced to :math:`\\{x \\le 11\\}` because :math:`x - y \\le 6
            \\;\\land\\; y \\le 5 \\Rightarrow x + y \\le 6`.

        Args:
            context:
                The TermSet providing the context for the deduction.

            vars_to_elim:
                Variables that should not appear in the deduced term.
        """
        logging.debug("Deducing from term %s", self)
        logging.debug("Context: %s", context)
        logging.debug("Vars to elim: %s", vars_to_elim)
        self.simplify(context)
        self._transform(context, vars_to_elim, False)
        # eliminate terms containing the variables to be eliminated
        terms_to_elim = self.get_terms_with_vars(vars_to_elim)
        self.terms = self.terms - terms_to_elim.terms


    def simplify(self, context=set()) -> None:
        """
        Remove redundant terms in the PolyhedralTermSet using the provided
        context.

        Example:
            Suppose the TermSet is :math:`\\{x - 2y \\le 5, x - y \\le 0\\}` and
            the context is :math:`\\{x + y \\le 0\\}`. Then the TermSet could be
            simplified to :math:`\\{x - y \\le 0\\}`.

        Args:
            context:
                The TermSet providing the context for the simplification.
        """
        logging.debug("Simplifying terms: %s", self)
        logging.debug("Context: %s", context)
        if isinstance(context, set):
            variables, self_mat, self_cons, ctx_mat, ctx_cons = \
                PolyhedralTermSet.\
                    termset_to_polytope(self, PolyhedralTermSet(context))
        else:
            variables, self_mat, self_cons, ctx_mat, ctx_cons = \
                PolyhedralTermSet.termset_to_polytope(self, context)
        logging.debug("Polytope is %s", self_mat)
        A_red, b_red = PolyhedralTermSet.reduce_polytope(self_mat, self_cons,
                                                         ctx_mat, ctx_cons)
        logging.debug("Reduction: %s", A_red)
        self.terms = PolyhedralTermSet.polytope_to_termset(A_red, b_red,
                                                           variables).terms
        logging.debug("Back to terms: %s", self)


    def refines(self, other) -> bool:
        """
        Tells whether the argument is a larger specification, i.e., compute self
        <= other.

        Args:
            other:
                TermSet against which we are comparing self.
        """
        raise NotImplementedError



    @staticmethod
    def termset_to_polytope(terms:PolyhedralTermSet, context:PolyhedralTermSet):
        """
        Converts a set of terms with its context into matrix-vector pairs.

        Example:
            Suppose the set of terms is :math:`\\{x+y \\le 1, x - y \\le 4\\}`
            and the context is :math:`\\{x + 4w \le 5\\}`. The routine extracts
            all variables and generates an order for them, say, :math:`[x, w,
            y]`. Then the routine returns matrix-vector pairs for both the terms
            TermSet and the context. It returns :math:`A = \left(
            \\begin{smallmatrix} 1 & 0 & 1 \\\\ 1 &0 &-1
            \\end{smallmatrix}\\right)` and :math:`b = \\left(
            \\begin{smallmatrix} 1 \\\\ 4 \\end{smallmatrix}\\right)` for the
            current TermSet and :math:`A_{c} = \\left( \\begin{smallmatrix} 1 &
            4 & 0 \\end{smallmatrix}\\right)` and :math:`b_c = \\left(
            \\begin{smallmatrix} 5 \\end{smallmatrix}\\right)` for the context.

        Args:
            terms:
                Set of terms to convert to matrix-vector form.
            context:
                Context terms to convert to matrix-vector form.

        Returns:
            A tuple :code:`variables, A, b, A_h, b_h` consisting of the variable
            order and the matrix-vector pairs for the terms and the context.
        """
        variables = list(terms.vars | context.vars)
        A = []
        b = []
        for term in terms.terms:
            pol, coeff = PolyhedralTerm.term_to_polytope(term, variables)
            A.append(pol)
            b.append(coeff)

        A_h = []
        b_h = []
        for term in context.terms:
            pol, coeff = PolyhedralTerm.term_to_polytope(term, variables)
            A_h.append(pol)
            b_h.append(coeff)

        A = np.array(A)
        b = np.array(b)
        if len(context.terms) == 0:
            A_h = np.array([[]])
        else:
            A_h = np.array(A_h)
        b_h = np.array(b_h)
        logging.debug("A is %s", A)
        return variables, A, b, A_h, b_h

    @staticmethod
    def polytope_to_termset(matrix, vector,
                            variables:list[IoContract.Var]) -> PolyhedralTermSet:
        """
        Transforms a matrix-vector pair into a PolyhedralTermSet, assuming that
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
            The PolyhedralTermSet corresponding to the given data.
        """
        term_list = []
        logging.debug("&&&&&&&&&&")
        #logging.debug("Poly is " + str(polytope))
        logging.debug("matrix is %s", matrix)
        n, m = matrix.shape
        assert m == len(variables)
        for i in range(n):
            row = list(matrix[i])
            const = vector[i]
            term = PolyhedralTerm.polytope_to_term(row, const, variables)
            term_list.append(term)
        return PolyhedralTermSet(set(term_list))


    @staticmethod
    def reduce_polytope(A: np.array, b: np.array,
                        A_help: np.array = np.array([[]]),
                        b_help: np.array = np.array([])):
        """
        Eliminate redundant constraints from the H-representation of a given
        polytope using as context a given polytope.

        Args:
            A:
                Matrix of H-representation of polytope to reduce.
            b:
                Vector of H-representation of polytope to reduce.
            A_help:
                Matrix of H-representation of context polytope.
            b_help:
                Vector of H-representation of context polytope.
        """
        n, m = A.shape
        n_h, m_h = A_help.shape
        helper_present = n_h*m_h > 0
        assert n == len(b)
        if helper_present:
            assert n_h == len(b_help)
        else:
            assert len(b_help) == 0
        if helper_present:
            assert m_h == m
        if n == 0:
            return A, b
        if n == 1 and not helper_present:
            return A, b

        i = 0
        A_temp = np.copy(A)
        b_temp = np.copy(b)
        while i < n:
            objective = A_temp[i, :] * -1
            b_temp[i] += 1
            logging.debug("Obj is \n%s", objective)
            logging.debug("A_temp is \n%s", A_temp)
            logging.debug("A_help is \n%s", A_help)
            logging.debug("b_temp is \n%s", b_temp)
            logging.debug("b_help is \n%s", b_help)
            if helper_present:
                res = linprog(c=objective,
                              A_ub=np.concatenate((A_temp, A_help), axis=0),
                              b_ub=np.concatenate((b_temp, b_help)),
                              bounds=(None, None))
            else:
                res = linprog(c=objective,
                              A_ub=A_temp,
                              b_ub=b_temp,
                              bounds=(None, None))
            b_temp[i] -= 1
            logging.debug("Optimal value: %s", -res["fun"])
            logging.debug("Results: %s", res)
            if -res["fun"] <= b_temp[i]:
                logging.debug("Can remove")
                A_temp = np.delete(A_temp, i, 0)
                b_temp = np.delete(b_temp, i)
                n -= 1
            else:
                i += 1
        return A_temp, b_temp

