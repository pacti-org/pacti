
import networkx as nx

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
    def __init__(self, l, c, r):
        self.l = l
        self.c = c
        self.r = r

    @property
    def vars(self):
        varset = []
        if type(self.l) == Var:
            varset.append(self.l)
        if type(self.r) == Var:
            varset.append(self.r)
        #print(varset)
        return set(varset)

    def swap(self):
        if self.c == "eq":
            self.l, self.r = self.r, self.l
        else:
            raise ValueError
        return self

    def __eq__(self, other):
        if (self.c != other.c):
            return False
        elif self.c == "lt":
            return (self.l == other.l) and (self.r == other.r)
        else:
            return ((self.l == other.l) and (self.r == other.r)) or (
                (self.l == other.r) and (self.r == other.l)
            )

    def __str__(self) -> str:
        translation = {"eq": "=", "lt": "<"}
        return f'({str(self.l)} {translation[self.c]} {str(self.r)})'
    
    def __hash__(self):
        return hash(str(self)) if self.c != "eq" else hash(self.l) + hash(self.r)

    def __repr__(self):
        return "<Term {0}>".format(self)

    def copy(self):
        return Term(self.l, self.c, self.r)

    @classmethod
    def EQ(cls, l, r):
        return Term(l, "eq", r)

    @classmethod
    def LT(cls, l, r):
        return Term(l, "lt", r)
        
    
class rule:
    def __init__(self, check, apply):
        self.check = check
        self.apply = apply

    def ruleCheck(self, lterm, rterm):
        return self.apply(lterm, rterm)

    def ruleApply(self, lterm, rterm):
        return self.apply(lterm, rterm)


class TermSet:
    def __init__(self, termSet:set):
        self.rules = TermSet.getRules()
        self.terms = termSet.copy()
        self.foreignOrigin = {t:False for t in self.terms}

    @property
    def vars(self):
        varset = set()
        for t in self.terms:
            if not self.foreignOrigin[t]:
                varset = varset | t.vars
        return varset

    def getRules():
        rules = dict()
        # ineq rule
        check = lambda lt, rt: (lt.c == rt.c == "lt") and (lt.l == rt.l)
        apply = lambda lt, rt: {lt if lt.r < rt.r else rt}
        rules['ineq'] = rule(check, apply)

        # eqtrans rule
        check = lambda lt, rt: (lt.c == rt.c == "eq") and (lt.l == rt.r)
        apply = lambda lt, rt: {Term(rt.l,"eq",lt.r)}
        rules['eqtrans'] = rule(check, apply)

        # subst rule
        check = lambda lt, rt: (lt.c == "lt" and rt.c == "eq") and (lt.l == rt.l)
        apply = lambda lt, rt: {Term(rt.r,"lt",lt.r)}
        rules['subst'] = rule(check, apply)

        # and
        check = lambda lt, rt: (lt == rt)
        apply = lambda lt, rt: {lt}
        rules['and'] = rule(check, apply)

        return rules

    def __str__(self) -> str:
        res = [str(el) for el in self.terms]
        return " ".join(res)

    def addForeignTerms(self, foreignTerms) -> None:
        self.terms = self.terms | foreignTerms.terms
        for t in foreignTerms.terms:
            self.foreignOrigin[t] = True

    def removeForeignTerms(self) -> None:
        toRemove = set()
        for t in self.terms:
            if self.foreignOrigin[t]:
                toRemove.add(t)
        self.terms -= toRemove

    def getTermsWithVars(self, varSet):
        terms = set()
        for t in self.terms:
            if len(t.vars & varSet) > 0:
                terms.add(t)
        return terms

    def checkRule(self, rulename, lterm, rterm):
        #print("Checking rule {0}".format(rulename))
        #print("Args: {0} --- {1}".format(lterm, rterm))
        return self.rules[rulename].check(lterm, rterm)

    def applyRule(self, rulename, lterm, rterm):
        #print("Applying rule {0}".format(rulename))
        #print("Args: {0} --- {1}".format(lterm, rterm))
        retVal = self.rules[rulename].apply(lterm, rterm)
        return retVal

    def getEqualityGraph(self):
        terms = self.terms
        G = nx.Graph()
        for t in terms:
            if t.c == "eq":
                G.add_edge(*t.vars)
        return G

    def checkAndApply(self, rulename, lterm, rterm):
        terms = set()
        if self.checkRule(rulename, lterm, rterm):
            terms = self.applyRule(rulename, lterm, rterm)
        return terms

    def reduceVariable(self, elimVars):
        # we can eliminate variables using the
        termList = list(self.terms)
        G = self.getEqualityGraph()
        components = list(nx.connected_components(G))
        print("Comps: " + str(components))
        print("Elim vars: " + str(elimVars))

        for component in components:
            varsToElim = component & elimVars
            try:
                repVar = (component - elimVars).pop()
            except KeyError:
                break
            print("Replacing {0} with {1}".format(varsToElim,repVar))

            for repterm in termList:
                if len(repterm.vars & varsToElim) != 1:
                    continue
                print("Rep term: " + str(repterm))
                
                newterm = repterm.copy()
                if newterm.l in varsToElim:
                    newterm.l = repVar
                elif newterm.r in varsToElim:
                    newterm.r = repVar
                else:
                    raise ValueError

                if newterm == repterm:
                    continue

                self.terms -= {repterm}
                self.terms = self.terms | {newterm}
                print("Adding term " + str(newterm))
                self.foreignOrigin[newterm] = self.foreignOrigin[repterm]
        return False
                        

    def reduceTerms(self):
        # we can eliminate variables using the
        termList = list(self.terms)
        n = len(termList)
        for i, rterm in enumerate(termList):
            for j,lterm in enumerate(termList):
                if (j != i):
                    newTerms = set()
                    if self.checkRule("and", lterm, rterm):
                        newTerms = self.applyRule("and", lterm, rterm)
                    elif self.checkRule("ineq", lterm, rterm):
                        newTerms = self.applyRule("ineq", lterm, rterm)
                    else:
                        continue
                    self.terms -= {lterm, rterm}
                    self.terms = self.terms.union(newTerms)
                    return True
        for term in termList:
            if (term.c == "eq") and (term.l == term.r):
                self.terms.discard(term)
        return False


    def __and__(self, other):
        return TermSet(self.terms & other.terms)

    def __or__(self, other):
        return TermSet(self.terms | other.terms)

    def __sub__(self, other):
        return TermSet(self.terms - other.terms)


    def reduceMultipleVariables(self, additionalTerms, elimVars:set):
        newTermList = self.copy()
        print("New terms: " + str(self))
        print("Support terms: " + str(additionalTerms))
        
        newTermList.addForeignTerms(additionalTerms)
        newTermList.reduceVariable(elimVars)
        newTermList.removeForeignTerms()
        done = False
        while (not done):
            done = not newTermList.reduceTerms()
        

        #newTermList.terms -= {t for t in newTermList.terms if self.foreignOrigin[t]}
        print("New terms mod: " + str(newTermList))
        return newTermList


    def eliminateTerms(self, elimVars) -> None:
        elimTerms = set()
        for term in self.terms:
            if len(term.vars & elimVars) > 0:
                elimTerms.add(term)
        self.terms -= elimTerms

    def copy(self):
        return TermSet(self.terms)



class IoContract:
    def __init__(self, assumptions:TermSet, guarantees:TermSet, inputVars:set, outputVars:set) -> None:
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
    requirements = {Term.LT(Var("a"), 5), Term.LT(Var("a"), 6)}
    requirements = TermSet(requirements)
    print(requirements)
    requirements.reduceTerms()
    print(requirements)
    
    requirements = {Term.LT(Var("a"), 5), Term.EQ(Var("b"), Var("a"))}
    requirements = TermSet(requirements)
    print(requirements)
    requirements.reduceVariable({Var("a")})
    print(requirements)


    # now we operate with contracts
    iVar = Var("i")
    oVar = Var("o")
    assumptions = TermSet({Term.LT(iVar, 2)})
    guarantees = TermSet({Term.EQ(oVar, iVar)})
    cont = IoContract(assumptions, guarantees, {iVar}, {oVar})

    opVar = Var("o'")
    assumptions = TermSet({Term.LT(oVar, 1)})
    guarantees = TermSet({Term.EQ(opVar, oVar)})
    contp = IoContract(assumptions, guarantees, {oVar}, {opVar})

    oppVar = Var("o''")
    assumptions = TermSet({Term.LT(opVar, 0)})
    guarantees = TermSet({Term.EQ(oppVar, opVar)})
    contpp = IoContract(assumptions, guarantees, {opVar}, {oppVar})

    print("Contract is")
    print(cont)
    print("Contract' is")
    print(contp)
    print("Their composition is")
    print(contp.compose(cont.compose(contpp)))
