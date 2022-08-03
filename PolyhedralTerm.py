"""
PolyhedralTerm provides support for linear inequalities as constraints, i.e.,
the constraints are of the form :math:`\\sum_{i} a_i x_i \\le c`, where the
:math:`x_i` are variables and the :math:`a_i` and :math:`c` are constants.
"""

import logging
import sympy
import numpy as np
from scipy.optimize import linprog
import IoContract



class PolyhedralTerm(IoContract.Term):
    """
    Polyhedral terms are linear inequalities over a set of variables.

    Usage:
        Polyhedral terms are initialized as follows

        .. highlight:: python
        .. code-block:: python

            variables = {Var(x):2, Var(y):3}
            constant = 3
            term = PolyhedralTerm(variables, constant)

        Asi es
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
            For the term a*x + b*y <= c with variables x and y, this function
            returns the set {x, y} if a and b are nonzero.
        """
        varlist = self.variables.keys()
        return set(varlist)

    def contains_var(self, var):
        """
        Tell whether term contains a given variable.

        Args:
            var: The variable that we are seeking in the current term.
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
        """Definition"""
        if polarity:
            return self.variables[var] >= 0
        else:
            return self.variables[var] <= 0


    def get_matching_vars(self, variable_polarity):
        """
        Return the set of variables
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


    def variables_math_polarity(self, variable_polarity):
        """Definition"""
        return len(self.get_matching_vars(variable_polarity)) > 0


    def remove_variable(self, var):
        """Definition"""
        if self.contains_var(var):
            self.variables.pop(var)

    def multiply(self, factor):
        """Definition"""
        variables = {key:factor*val for key, val in self.variables.items()}
        return PolyhedralTerm(variables, factor*self.constant)

    # This routine accepts a variable to be substituted by a term and plugs in a
    # subst term in place
    def substitute_variable(self, var, subst_with_term):
        """Definition"""
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
        """Definition"""
        ex = 0
        for var in term.vars:
            sv = sympy.symbols(var.name)
            ex += sv * term.get_coefficient(var)
        return ex

    @staticmethod
    def to_term(expression):
        """Definition"""
        expression_coefficients = expression.as_coefficients_dict()
        keys = list(expression_coefficients.keys())
        variable_dict = {}
        constant = 0
        for key in keys:
            if key == 1:
                constant = expression_coefficients[key]
            else:
                var = IoContract.Var(str(key))
                variable_dict[var] = expression_coefficients[key]
        return PolyhedralTerm(variable_dict, constant)

    @staticmethod
    def term_to_polytope(term, variables):
        """Definition"""
        coeffs = []
        for var in variables:
            coeffs.append(term.get_coefficient(var))
        return coeffs, term.constant

    @staticmethod
    def polytope_to_term(poly, const, variables):
        """Definition"""
        variable_dict = {}
        for i, var in enumerate(variables):
            variable_dict[var] = poly[i]
        return PolyhedralTerm(variable_dict, const)


    @staticmethod
    def solve_for_variables(context, vars_to_elim):
        """
        Accepts a set of terms and a set of variables that should be optimized.

        Inputs: the terms and the variables that will be optimized

        Assumptions: the number of equations matches the number of vars_to_elim
        contained in the terms
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
    """Class description"""


    # This routine accepts a term that will be adbuced with the help of other
    # terms The abduction aims to eliminate from the term appearances of the
    # variables contained in vars_to_elim
    def _transform(self, context: set,
                   vars_to_elim: set, polarity: True):
        """Definition"""
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

        # the last step needs to be a simplication
        self.simplify()


    def abduceWithContext(self, context: set, vars_to_elim: set):
        """Definition"""
        logging.debug("Abducing from terms: %s", self)
        logging.debug("Context: %s", context)
        logging.debug("Vars to elim: %s", vars_to_elim)
        self.simplify(context)
        self._transform(context, vars_to_elim, True)

    def deduceWithContext(self, context: set, vars_to_elim: set):
        """Definition"""
        logging.debug("Deducing from term %s", self)
        logging.debug("Context: %s", context)
        logging.debug("Vars to elim: %s", vars_to_elim)
        self.simplify(context)
        self._transform(context, vars_to_elim, False)
        # eliminate terms containing the variables to be eliminated
        terms_to_elim = self.getTermsWithVars(vars_to_elim)
        self.terms = self.terms - terms_to_elim.terms


    def simplify(self, context=set()):
        """Definition"""
        logging.debug("Simplifying terms: %s", self)
        logging.debug("Context: %s", context)
        if isinstance(context, set):
            variables, A, b, A_h, b_h = \
                PolyhedralTermSet.\
                    termset_to_polytope(self, PolyhedralTermSet(context))
        else:
            variables, A, b, A_h, b_h = \
                PolyhedralTermSet.termset_to_polytope(self, context)
        logging.debug("Polytope is %s", A)
        A_red, b_red = PolyhedralTermSet.reduce_polytope(A, b, A_h, b_h)
        logging.debug("Reduction: %s", A_red)
        self.terms = PolyhedralTermSet.polytope_to_termset(A_red, b_red,
                                                           variables).terms
        logging.debug("Back to terms: %s", self)


    def refines(self, other) -> bool:
        """
        Tell whether the argument is a larger specification, i.e., compute self
        <= other.

        Args:
            other:
                TermSet against which we are comparing self.
        """
        raise NotImplementedError



    @staticmethod
    def termset_to_polytope(terms, helpers=set()):
        """Definition"""
        variables = list(terms.vars | helpers.vars)
        A = []
        b = []
        for term in terms.terms:
            pol, coeff = PolyhedralTerm.term_to_polytope(term, variables)
            A.append(pol)
            b.append(coeff)

        A_h = []
        b_h = []
        for term in helpers.terms:
            pol, coeff = PolyhedralTerm.term_to_polytope(term, variables)
            A_h.append(pol)
            b_h.append(coeff)

        A = np.array(A)
        b = np.array(b)
        if len(helpers.terms) == 0:
            A_h = np.array([[]])
        else:
            A_h = np.array(A_h)
        b_h = np.array(b_h)
        logging.debug("A is %s", A)
        return variables, A, b, A_h, b_h

    @staticmethod
    def polytope_to_termset(A, b, variables):
        """Definition"""
        term_list = []
        logging.debug("&&&&&&&&&&")
        #logging.debug("Poly is " + str(polytope))
        logging.debug("A is %s", A)
        n, m = A.shape
        for i in range(n):
            vect = list(A[i])
            const = b[i]
            term = PolyhedralTerm.polytope_to_term(vect, const, variables)
            term_list.append(term)
        return PolyhedralTermSet(set(term_list))


    @staticmethod
    def reduce_polytope(A: np.array, b: np.array,
                        A_help: np.array = np.array([[]]),
                        b_help: np.array = np.array([])):
        """Definition"""
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

