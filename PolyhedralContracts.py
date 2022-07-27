
import networkx as nx
import sympy
import polytope as pc
import numpy as np
import scipy

class Number:
    def __init__(self, val):
        self.value = val

    @property
    def val(self):
        return self.value

    def __str__(self):
        return self.value

class Var:
    def __init__(self, val):
        self.value = str(val)

    @property
    def val(self):
        return self.value

    def __eq__(self, other):
        return self.val == other.val

    def __str__(self) -> str:
        return self.val

    def __hash__(self) -> int:
        return hash(self.val)

    def __repr__(self):
        return "<Var {0}>".format(self.val)


class Term:
    # Constructor: get (i) a dictionary whose keys are variabes and whose values
    # are the coefficients of those variables in the term, and (b) a constant.
    # The term is assumed to be in the form \Sigma_i a_i v_i + constant <= 0
    def __init__(self, variables, constant):
        vars = {key:val for key, val in variables.items() if val != 0}
        self.variables = vars
        self.constant = constant

    @property
    def vars(self):
        varset = self.variables.keys()
        return set(varset)

    def containsVar(self, var):
        return var in self.vars

    def getVarCoeff(self, var):
        if self.containsVar(var):
            return self.variables[var]
        else:
            return 0

    def getMatchingVars(self, varPol):
        varSet = set()
        for var in varPol.keys():
            if self.containsVar(var):
                if self.getVarPolarity(var) == varPol[var]:
                    varSet.add(var)
                else:
                    varSet = set()
                    break
        return varSet
        

    def varsMatchPolarity(self, varPol):
        return len(self.getMatchingVars(varPol)) > 0


    def getVarPolarity(self, var):
        return self.variables[var] > 0



    def __add__(self, other):
        vars = list(self.vars | other.vars)
        variables = {}
        for var in vars:
            variables[var] = self.getVarCoeff(var) + other.getVarCoeff(var)
        return Term(variables, self.constant + other.constant)

    def removeVar(self, var):
        if self.containsVar(var):
            self.variables.pop(var)

    def multiply(self, factor):
        return Term({key:factor*val for key,val in self.variables.items()}, factor*self.constant)

    # This routine accepts a variable to be substituted by a term and plugs in a subst term in place
    def substVar(self, var, substTerm):
        if self.containsVar(var):
            term = substTerm.multiply(self.getVarCoeff(var))
            print("Term is " + str(term))
            self.removeVar(var)
            print(self)
            return self + term
        else:
            return self.copy()
        

    def __eq__(self, other):
        return (self.variables == other.variables and self.constant == other.constant)


    def __str__(self) -> str:
        res = " + ".join([str(self.variables[var])+"*"+var.val for var in self.variables.keys()])
        res += "<= " + str(self.constant)
        return res
    
    def __hash__(self):
        return hash(str(self))

    def __repr__(self):
        return "<Term {0}>".format(self)

    def copy(self):
        return Term(self.variables, self.constant)

    class Interfaces:
        def termToSymb(term):
            ex = 0
            for var in term.vars:
                sv = sympy.symbols(var.val)
                ex += sv * term.getVarCoeff(var)
            return ex
        

        def symbToTerm(expression):
            exAry = expression.as_coefficients_dict()
            keys = list(exAry.keys())
            vars = {}
            constant = 0
            for key in keys:
                if key == 1:
                    constant = exAry[key]
                else:
                    var = Var(str(key))
                    vars[var] = exAry[key]
            return Term(vars, constant)


        def termToPolytope(term, vars):
            coeffs = []
            for var in vars:
                coeffs.append(term.getVarCoeff(var))
            return coeffs, term.constant

        def polytopeToTerm(poly, const, vars):
            variables = {}
            for i, var in enumerate(vars):
                variables[var] = poly[i]
            return Term(variables, const)
    

    # This routine accepts a set of terms and a set of variables that should be optimized.
    # ----------------------
    # Inputs: the terms and the variables that will be optimized
    # Assumptions: the number of equations matches the number of varsToElim contained in the terms
    def getValuesOfVarsToElim(termsToUse, varsToElim):
        print("GetVals: " + str(termsToUse) + " Vars: " + str(varsToElim))
        varsToOpt = termsToUse.vars & varsToElim
        assert len(termsToUse.terms) == len(varsToOpt)
        exprs = [Term.Interfaces.termToSymb(term) for term in termsToUse.terms]
        varsToSolve = [sympy.symbols(var.val) for var in varsToOpt]
        sols = sympy.solve(exprs, *varsToSolve)
        print(sols)
        if len(sols) >0:
            return {Var(str(key)):Term.Interfaces.symbToTerm(sols[key]) for key in sols.keys()}
        else:
            return {}





class TermList:
    def __init__(self, termSet:set):
        self.terms = termSet.copy()

    @property
    def vars(self):
        varset = set()
        for t in self.terms:
            varset = varset | t.vars
        return varset



    def __str__(self) -> str:
        res = [str(el) for el in self.terms]
        return ", ".join(res)

    def __eq__(self, other):
        return (self.terms == other.terms)



    def getTermsWithVars(self, varSet):
        terms = set()
        for t in self.terms:
            if len(t.vars & varSet) > 0:
                terms.add(t)
        return terms



    def __and__(self, other):
        return TermList(self.terms & other.terms)

    def __or__(self, other):
        return TermList(self.terms | other.terms)

    def __sub__(self, other):
        return TermList(self.terms - other.terms)

    def copy(self):
        return TermList(self.terms)



    # This routine accepts a term that will be adbuced with the help of other
    # terms The abduction aims to eliminate from the term appearances of the
    # variables contained in varsToElim
    def abduceWithHelpers(self, helperTerms:set, varsToElim:set):
        print("Helper terms" + str(helperTerms))
        print("Variables to eliminate: " + str(varsToElim))
        helpers = helperTerms.copy()
        for i, term in enumerate(self.terms):
            print("Abducing " + str(term))
            vars_elim = {}
            for var in term.vars & varsToElim:
                vars_elim[var] = term.getVarPolarity(var)
            print("Vars to elim: " + str(vars_elim))
            varsToCover = set(vars_elim.keys())
            termsToUse = TermList(set())
            
            # now we have to choose from the helpers any terms that we can use to eliminate these variables
            for helper in helpers.terms:
                varsMatch = helper.getMatchingVars(vars_elim)
                if len(varsMatch & varsToCover) > 0:
                    varsToCover = varsToCover - varsMatch
                    termsToUse.terms.add(helper)
                    helpers.terms.remove(helper)
                    if len(varsToCover) == 0:
                        break

            print("TermsToUse: " + str(termsToUse))

            # as long as we have more "to_elim" variables than terms, we seek additional terms. For now, we throw an error if we don't have enough terms
            assert len(termsToUse.terms) == len(termsToUse.vars & varsToElim)
            
            sols = Term.getValuesOfVarsToElim(termsToUse, varsToElim)
            print(sols)
            for var in sols.keys():
                term = term.substVar(var, sols[var])
            self.terms[i] = term
            
            print("After subst: " + str(term))

        # the last step needs to be a simplication
        self.simplify()


    def simplify(self):
        vars, polytope = TermList.Interfaces.termsToPolytope(self)
        print("Polytope is " + str(polytope))
        pol = pc.reduce(polytope)
        print("Reduction: " + str(pol))
        self = TermList.Interfaces.polytopeToTerms(pol, vars)
        print("Back to terms: " + str(self))

    class Interfaces:
        
        def termsToPolytope(terms):
            vars = list(terms.vars)
            A = []
            b = []
            for term in terms.terms:
                pol, coeff = Term.Interfaces.termToPolytope(term, vars)
                A.append(pol)
                b.append(coeff)
            A = np.array(A)
            b = np.array(b)
            print("A is " + str(A))
            return vars, pc.Polytope(A, b)

        def polytopeToTerms(polytope:pc.Polytope, vars):
            A = polytope.A
            b = polytope.b
            termList = []
            print("&&&&&&&&&&")
            print("Poly is " + str(polytope))
            print("A is " + str(A))
            n,m = A.shape
            for i in range(n):
                vect = list(A[i])
                const = b[i]
                term = Term.Interfaces.polytopeToTerm(vect, const, vars)
                termList.append(term)
            return TermList(termList)





class IoContract:
    def __init__(self, assumptions:TermList, guarantees:TermList, inputVars:set, outputVars:set) -> None:
        assert len(assumptions.vars - inputVars) == 0, print("A: " + str(assumptions.vars) + " Input vars: " + str(inputVars))
        assert len(guarantees.vars - inputVars - outputVars) == 0, print("G: " + str(guarantees.vars) + " Input: " + str(inputVars) + " Output: " + str(outputVars))
        self.a = assumptions.copy()
        self.g = guarantees.copy()
        self.inputvars = inputVars.copy()
        self.outputvars = outputVars.copy()

    @property
    def vars(self):
        return self.a.vars | self.g.vars

    def __str__(self):
        return "A: " + str(self.a) + "\n" + "G: " + str(self.g)

    def composable(self, other) -> bool:
        # make sure sets of output variables don't intersect
        return len(self.outputvars & other.outputvars) == 0


    def compose(self, other):
        intvars = (self.outputvars & other.inputvars) | (self.inputvars & other.outputvars)
        inputvars = (self.inputvars | other.inputvars) - intvars
        outputvars = (self.outputvars | other.outputvars) - intvars
        assert self.composable(other)
        allassumptions = self.a | other.a
        allguarantees = self.g | other.g
        print("****************")
        print("****************")
        print("MSG> Computing assumptions")
        assumptions = allassumptions.reduceMultipleVariables(allguarantees, intvars | outputvars)
        print("****************")
        print("MSG> Computing guarantees")
        guarantees  = allguarantees.reduceMultipleVariables(allassumptions, intvars)
        guarantees.eliminateTerms(intvars)
        print("Comp A: " + str(assumptions))
        print("Comp G: " + str(guarantees))
        return IoContract(assumptions, guarantees, inputvars, outputvars)


if __name__ == '__main__':



    exit()
    requirements = {Term.LT(Var("a"), 5), Term.LT(Var("a"), 6)}
    requirements = TermList(requirements)
    print(requirements)
    requirements.reduceTerms()
    print(requirements)
    
    requirements = {Term.LT(Var("a"), 5), Term.EQ(Var("b"), Var("a"))}
    requirements = TermList(requirements)
    print(requirements)
    requirements.reduceVariable({Var("a")})
    print(requirements)


    # now we operate with contracts
    iVar = Var("i")
    oVar = Var("o")
    assumptions = TermList({Term.LT(iVar, 2)})
    guarantees = TermList({Term.EQ(oVar, iVar)})
    cont = IoContract(assumptions, guarantees, {iVar}, {oVar})

    opVar = Var("o'")
    assumptions = TermList({Term.LT(oVar, 1)})
    guarantees = TermList({Term.EQ(opVar, oVar)})
    contp = IoContract(assumptions, guarantees, {oVar}, {opVar})

    oppVar = Var("o''")
    assumptions = TermList({Term.LT(opVar, 0)})
    guarantees = TermList({Term.EQ(oppVar, opVar)})
    contpp = IoContract(assumptions, guarantees, {opVar}, {oppVar})

    print("Contract is")
    print(cont)
    print("Contract' is")
    print(contp)
    print("Their composition is")
    print(contp.compose(cont.compose(contpp)))
