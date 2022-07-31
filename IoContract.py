

import logging
import copy
from abc import ABC, abstractmethod


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


class Term(ABC):

    @property
    @abstractmethod
    def vars(self):
        pass

    @abstractmethod
    def containsVar(self, var):
        pass

    @abstractmethod
    def __eq__(self, other):
        pass

    @abstractmethod
    def __str__(self) -> str:
        pass
    
    @abstractmethod
    def __hash__(self):
        pass

    @abstractmethod
    def __repr__(self):
        pass

    @abstractmethod
    def copy(self):
        pass




class TermList(ABC):
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
        return type(self)(terms)


    def __and__(self, other):
        return type(self)(self.terms & other.terms)

    def __or__(self, other):
        return type(self)(self.terms | other.terms)

    def __sub__(self, other):
        return type(self)(self.terms - other.terms)

    def copy(self):
        return type(self)(copy.copy(self.terms))

    @abstractmethod
    def abduceWithHelpers(self, helperTerms:set, varsToElim:set):
        pass

    @abstractmethod
    def deduceWithHelpers(self, helperTerms:set, varsToElim:set):
        pass

    @abstractmethod
    def simplify(self, helpers=set()):
        pass



class IoContract:
    def __init__(self, assumptions:TermList, guarantees:TermList, inputVars:set, outputVars:set) -> None:
        # make sure the input & output variables are disjoint
        assert len(inputVars & outputVars) == 0
        # make sure the assumptions only contain input variables
        assert len(assumptions.vars - inputVars) == 0, print("A: " + str(assumptions.vars) + " Input vars: " + str(inputVars))
        # make sure the guaranteees only contain input or output variables
        assert len(guarantees.vars - inputVars - outputVars) == 0, print("G: " + str(guarantees) + " G Vars: "+ str(guarantees.vars) + " Input: " + str(inputVars) + " Output: " + str(outputVars))
        self.a = assumptions.copy()
        self.g = guarantees.copy()
        self.inputvars = inputVars.copy()
        self.outputvars = outputVars.copy()
        # simplify the guarantees with the assumptions
        self.g.simplify(self.a)

    @property
    def vars(self):
        return self.a.vars | self.g.vars

    def __str__(self):
        return "InVars: " + str(self.inputvars) + "\nOutVars:" + str(self.outputvars) + "\nA: " + str(self.a) + "\n" + "G: " + str(self.g)

    def canComposeWith(self, other) -> bool:
        # make sure sets of output variables don't intersect
        return len(self.outputvars & other.outputvars) == 0

    def canQuotientBy(self, other) -> bool:
        # make sure the top level ouputs not contained in outputs of the existing component do not intersect with the inputs of the existing component
        return len((self.outputvars - other.outputvars) & other.inputvars) == 0


    def compose(self, other):
        intvars = (self.outputvars & other.inputvars) | (self.inputvars & other.outputvars)
        inputvars = (self.inputvars | other.inputvars) - intvars
        outputvars = (self.outputvars | other.outputvars) - intvars
        assert self.canComposeWith(other)
        otherHelpsSelf = len(other.outputvars & self.inputvars) > 0
        selfHelpsOther = len(other.inputvars & self.outputvars) > 0
        # process assumptions
        if otherHelpsSelf and selfHelpsOther:
            assert False
        elif selfHelpsOther:
            other.a.abduceWithHelpers(self.g, intvars | outputvars)
            assumptions = other.a | self.a
        elif otherHelpsSelf:
            self.a.abduceWithHelpers(other.g, intvars | outputvars)
            assumptions = self.a | other.a
        assumptions.simplify()

        # process guarantees
        g1 = self.g.copy()
        g2 = other.g.copy()
        g1.deduceWithHelpers(g2,intvars)
        g2.deduceWithHelpers(g1,intvars)
        allguarantees = g1 | g2
        allguarantees.deduceWithHelpers(assumptions, intvars)

        # eliminate terms with forbidden vars
        termsToElim = allguarantees.getTermsWithVars(intvars)
        allguarantees = allguarantees - termsToElim
        
        # build contract
        result = IoContract(assumptions, allguarantees, inputvars, outputvars)
        
        return result
    
    def quotient(self, other):
        assert self.canQuotientBy(other)
        outputvars = (self.outputvars - other.outputvars) | (other.inputvars - self.inputvars)
        inputvars  = (self.inputvars - other.inputvars) | (other.outputvars - self.outputvars)
        intvars = (self.outputvars & other.outputvars) | (self.inputvars & other.inputvars)
        
        # get assumptions
        logging.debug("Computing quotient assumptions")
        assumptions = copy.deepcopy(self.a)
        assumptions.deduceWithHelpers(other.g, intvars | outputvars)
        logging.debug("Assumptions after processing: " + str(assumptions))

        # get guarantees
        logging.debug("Computing quotient guarantees")
        guarantees = self.g
        logging.debug("Using existing guarantees to aid system-level guarantees")
        guarantees.abduceWithHelpers(other.g, intvars)
        logging.debug("Using system-level assumptions to aid quotient guarantees")
        guarantees = guarantees | other.a
        guarantees.abduceWithHelpers(self.a, intvars)
        logging.debug("Guarantees after processing: " + str(guarantees))
        

        return IoContract(assumptions, guarantees, inputvars, outputvars)


if __name__ == '__main__':
    exit()
