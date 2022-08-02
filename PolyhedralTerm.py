

import logging
import sympy
import numpy as np
import scipy.optimize
import copy
import IoContract



class PolyhedralTerm(IoContract.Term):
    """Class description"""

    # Constructor: get (i) a dictionary whose keys are variables and whose values
    # are the coefficients of those variables in the term, and (b) a constant.
    # The term is assumed to be in the form \Sigma_i a_i v_i + constant <= 0
    def __init__(self, variables, constant):
        vars = {}
        for key, val in variables.items():
            if val != 0:
                if isinstance(key, str):
                    vars[IoContract.Var(key)] = val
                else:
                    vars[key] = val
        self.variables = vars
        self.constant = constant

    @property
    def vars(self):
        """Definition"""
        varset = self.variables.keys()
        return set(varset)

    def containsVar(self, var):
        """Definition"""
        return var in self.vars

    def getVarCoeff(self, var):
        """Definition"""
        if self.containsVar(var):
            return self.variables[var]
        else:
            return 0

    def getMatchingVars(self, varPol, polarity=True):
        """Definition"""
        varSet = set()
        for var in varPol.keys():
            if self.containsVar(var):
                if (self.getVarPolarity(var, True) == varPol[var]) or (self.getVarCoeff(var) == 0):
                    varSet.add(var)
                else:
                    varSet = set()
                    break
        return varSet
        

    def varsMatchPolarity(self, varPol):
        """Definition"""
        return len(self.getMatchingVars(varPol)) > 0


    def getVarPolarity(self, var, polarity=True):
        """Definition"""
        if polarity:
            return self.variables[var] >= 0
        else:
            return self.variables[var] <= 0



    def __add__(self, other):
        vars = list(self.vars | other.vars)
        variables = {}
        for var in vars:
            variables[var] = self.getVarCoeff(var) + other.getVarCoeff(var)
        return PolyhedralTerm(variables, self.constant + other.constant)

    def removeVar(self, var):
        """Definition"""
        if self.containsVar(var):
            self.variables.pop(var)

    def multiply(self, factor):
        """Definition"""
        return PolyhedralTerm({key:factor*val for key,val in self.variables.items()}, factor*self.constant)

    # This routine accepts a variable to be substituted by a term and plugs in a subst term in place
    def substVar(self, var, substTerm):
        """Definition"""
        if self.containsVar(var):
            term = substTerm.multiply(self.getVarCoeff(var))
            logging.debug("Term is " + str(term))
            self.removeVar(var)
            logging.debug(self)
            return self + term
        else:
            return self.copy()
        

    def __eq__(self, other):
        return (self.variables == other.variables and self.constant == other.constant)


    def __str__(self) -> str:
        res = " + ".join([str(self.variables[var])+"*"+var.name for var in self.variables.keys()])
        res += " <= " + str(self.constant)
        return res
    
    def __hash__(self):
        return hash(str(self))

    def __repr__(self):
        return "<Term {0}>".format(self)

    def copy(self):
        return PolyhedralTerm(self.variables, self.constant)


    @staticmethod
    def termToSymb(term):
        """Definition"""
        ex = 0
        for var in term.vars:
            sv = sympy.symbols(var.name)
            ex += sv * term.getVarCoeff(var)
        return ex
    
    @staticmethod
    def symbToTerm(expression):
        """Definition"""
        exAry = expression.as_coefficients_dict()
        keys = list(exAry.keys())
        vars = {}
        constant = 0
        for key in keys:
            if key == 1:
                constant = exAry[key]
            else:
                var = IoContract.Var(str(key))
                vars[var] = exAry[key]
        return PolyhedralTerm(vars, constant)

    @staticmethod
    def termToPolytope(term, vars):
        """Definition"""
        coeffs = []
        for var in vars:
            coeffs.append(term.getVarCoeff(var))
        return coeffs, term.constant

    @staticmethod
    def polytopeToTerm(poly, const, vars):
        """Definition"""
        variables = {}
        for i, var in enumerate(vars):
            variables[var] = poly[i]
        return PolyhedralTerm(variables, const)
    

    @staticmethod
    def getValuesOfVarsToElim(termsToUse, varsToElim):
        """
        Accepts a set of terms and a set of variables that should be optimized.
        
        Inputs: the terms and the variables that will be optimized
        Assumptions: the number of equations matches the number of varsToElim contained in the terms
        """
        logging.debug("GetVals: " + str(termsToUse) + " Vars: " + str(varsToElim))
        varsToOpt = termsToUse.vars & varsToElim
        assert len(termsToUse.terms) == len(varsToOpt)
        exprs = [PolyhedralTerm.termToSymb(term) for term in termsToUse.terms]
        varsToSolve = [sympy.symbols(var.name) for var in varsToOpt]
        sols = sympy.solve(exprs, *varsToSolve)
        logging.debug(sols)
        if len(sols) >0:
            return {IoContract.Var(str(key)):PolyhedralTerm.symbToTerm(sols[key]) for key in sols.keys()}
        else:
            return {}



class PolyhedralTermSet(IoContract.TermSet):
    """Class description"""


    # This routine accepts a term that will be adbuced with the help of other
    # terms The abduction aims to eliminate from the term appearances of the
    # variables contained in varsToElim
    def transformWithContext(self, context:set, varsToElim:set, polarity:True):
        """Definition"""
        logging.debug("Context terms" + str(context))
        logging.debug("Variables to eliminate: " + str(varsToElim))
        helpers = context.copy()
        termList = list(self.terms)
        for i, term in enumerate(termList):
            logging.debug("Transforming " + str(term))
            vars_elim = {}
            for var in term.vars & varsToElim:
                vars_elim[var] = term.getVarPolarity(var, polarity)
            logging.debug("Vars to elim: " + str(vars_elim))
            varsToCover = set(vars_elim.keys())
            termsToUse = PolyhedralTermSet(set())
            
            # now we have to choose from the helpers any terms that we can use to eliminate these variables
            for helper in helpers.terms:
                varsMatch = helper.getMatchingVars(vars_elim, polarity)
                if len(varsMatch & varsToCover) > 0:
                    varsToCover = varsToCover - varsMatch
                    termsToUse.terms.add(helper)
                    helpers.terms.remove(helper)
                    if len(varsToCover) == 0:
                        break

            logging.debug("TermsToUse: " + str(termsToUse))

            # as long as we have more "to_elim" variables than terms, we seek additional terms. For now, we throw an error if we don't have enough terms
            assert len(termsToUse.terms) == len(termsToUse.vars & varsToElim)
            
            sols = PolyhedralTerm.getValuesOfVarsToElim(termsToUse, varsToElim)
            logging.debug(sols)
            for var in sols.keys():
                term = term.substVar(var, sols[var])
            termList[i] = term
            
            logging.debug("After subst: " + str(term))

        self.terms = set(termList)

        # the last step needs to be a simplication
        self.simplify()

    
    def abduceWithContext(self, context:set, varsToElim:set):
        """Definition"""
        logging.debug("Abducing from terms: " + str(self))
        logging.debug("Context: " + str(context))
        logging.debug("Vars to elim: " + str(varsToElim))
        self.simplify(context)
        self.transformWithContext(context, varsToElim, True)

    def deduceWithContext(self, context:set, varsToElim:set):
        """Definition"""
        logging.debug("Deducing from term" + str(self))
        logging.debug("Context: " + str(context))
        logging.debug("Vars to elim: " + str(varsToElim))
        self.simplify(context)
        self.transformWithContext(context, varsToElim, False)
        # eliminate terms containing the variables to be eliminated
        termsToElim = self.getTermsWithVars(varsToElim)
        self = self - termsToElim


    def simplify(self, context=set()):
        """Definition"""
        logging.debug("Simplifying terms: " + str(self))
        logging.debug("Context: " + str(context))
        if isinstance(context, set):
            vars, A, b, A_h, b_h = PolyhedralTermSet.termsToPolytope(self, PolyhedralTermSet(context))
        else:
            vars, A, b, A_h, b_h = PolyhedralTermSet.termsToPolytope(self, context)
        logging.debug("Polytope is " + str(A))
        A_red, b_red = PolyhedralTermSet.ReducePolytope(A, b, A_h, b_h)
        logging.debug("Reduction: " + str(A_red))
        self.terms = PolyhedralTermSet.polytopeToTerms(A_red, b_red, vars).terms
        logging.debug("Back to terms: " + str(self))


    def refines(self, other) -> bool:
        """Tell whether the argument is a larger specification, i.e., compute self <= other.
        
        Args:
            other:
                TermSet against which we are comparing self.
        """
        raise NotImplemented



    @staticmethod
    def termsToPolytope(terms, helpers=set()):
        """Definition"""
        vars = list(terms.vars | helpers.vars)
        A = []
        b = []
        for term in terms.terms:
            pol, coeff = PolyhedralTerm.termToPolytope(term, vars)
            A.append(pol)
            b.append(coeff)

        A_h = []
        b_h = []
        for term in helpers.terms:
            pol, coeff = PolyhedralTerm.termToPolytope(term, vars)
            A_h.append(pol)
            b_h.append(coeff)
        
        A = np.array(A)
        b = np.array(b)
        if len(helpers.terms) == 0:
            A_h = np.array([[]])
        else:
            A_h = np.array(A_h)
        b_h = np.array(b_h)
        logging.debug("A is " + str(A))
        return vars, A, b, A_h, b_h

    @staticmethod
    def polytopeToTerms(A, b, vars):
        """Definition"""
        termList = []
        logging.debug("&&&&&&&&&&")
        #logging.debug("Poly is " + str(polytope))
        logging.debug("A is " + str(A))
        n,m = A.shape
        for i in range(n):
            vect = list(A[i])
            const = b[i]
            term = PolyhedralTerm.polytopeToTerm(vect, const, vars)
            termList.append(term)
        return PolyhedralTermSet(set(termList))


    @staticmethod
    def ReducePolytope(A:np.array, b:np.array, A_help:np.array=np.array([[]]), b_help:np.array=np.array([])):
        """Definition"""
        n,m = A.shape
        n_h, m_h = A_help.shape
        helperPresent = n_h*m_h > 0
        assert n == len(b)
        if helperPresent:
            assert n_h == len(b_help)
        else:
            assert len(b_help) == 0
        if helperPresent:
            assert m_h == m
        if n == 0:
            return A, b
        if n == 1 and not helperPresent:
            return A, b
        
        i = 0
        A_temp = np.copy(A)
        b_temp = np.copy(b)
        while i < n:
            objective = A_temp[i,:] * -1
            b_temp[i] += 1
            logging.debug("Obj is \n" + str(objective))
            logging.debug("A_temp is \n" + str(A_temp))
            logging.debug("A_help is \n" + str(A_help))
            logging.debug("b_temp is \n" + str(b_temp))
            logging.debug("b_help is \n" + str(b_help))
            if helperPresent:
                res = scipy.optimize.linprog(c=objective, A_ub=np.concatenate((A_temp, A_help),axis=0), b_ub=np.concatenate((b_temp, b_help)), bounds=(None,None))
            else:
                res = scipy.optimize.linprog(c=objective, A_ub=A_temp, b_ub=b_temp, bounds=(None,None))
            b_temp[i] -= 1
            logging.debug("Optimal value: " + str(-res['fun']))
            logging.debug("Results: " + str(res))
            if -res['fun'] <= b_temp[i]:
                logging.debug("Can remove")
                A_temp = np.delete(A_temp, i, 0)
                b_temp = np.delete(b_temp, i)
                n -= 1
            else:
                i += 1
        return A_temp, b_temp

