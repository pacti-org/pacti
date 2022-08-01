"""
IoContracts contains Gear's basic definitions: Var, Term, TemList, and
IoContract. Var creates variables; Term is an abstract class representing
constraints; a TermList (also an abstract class) is a collection of terms
semantically equivalent to the term which is the conjunction of all terms
contained in the TermList; IoContract is an assume-guarantee specification
consisting of assumptions, guarantees, and input and output variables. The
assumptions and guarantees are given by TermLists. Assumptions make predicates
only on inputs, and guarantees on both input and outputs (and no other
variable).

This module implements all supported contract operations and relations. In order
to instantiate contracts and perform this operations, it is necessary to extend
Term and TermList with specific constraint formalisms.
"""
import logging
import copy
from abc import ABC, abstractmethod


class Var:
    """
    Variables used in system modeling.

    Variables allow us to name an entity for which we want to write constraints.
    """
    def __init__(self, val):
        self._name = str(val)

    @property
    def name(self) -> str:
        """The name of the variable."""
        return self._name

    def __eq__(self, other):
        return self.name == other.name

    def __str__(self) -> str:
        return self.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __repr__(self):
        return "<Var {0}>".format(self.name)


class Term(ABC):
    """
    Terms, or constraints, to be imposed on the system or components.

    Terms is an abstract class that must be extended in order to support specific constraint languages. 
    """

    @property
    @abstractmethod
    def vars(self):
        """Variables contained in the syntax of the term."""
        pass

    @abstractmethod
    def containsVar(self, var:Var):
        """
        Tell whether term contains a given variable.
        
        Args:
            var: The variable that we are seeking in the current term.
        """
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
    """
    A collection of terms, or constraints.
    
    A TermList is semantically equivalent to a single term which is the
    conjunction of all terms contained in the TermList. TermList is an abstract
    class that must be extended by specific constraint languages.
    """
    def __init__(self, termSet:set):
        self.terms = termSet.copy()

    @property
    def vars(self):
        """The set of variables contained in this list of terms."""
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
        """
        Returns a set of terms which contain any of the variables indicated.
        
        Args:
            varSet: a set of variables being sought in TermList. 
        """
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

    def __le__(self, other):
        return self.refines(other)

    def copy(self):
        return type(self)(copy.copy(self.terms))


    @abstractmethod
    def abduceWithContext(self, helperTerms:set, varsToElim:set):
        """
        Abduce terms containing variables to be eliminated using
        a user-provided context.

        Args:
            helperTerms:
                Set of context terms that will be used to abduce the TermList.
            varsToElim:
                Variables that cannot be present in TermList after abduction. 
        """
        pass

    @abstractmethod
    def deduceWithContext(self, helperTerms:set, varsToElim:set):
        """
        Deduce terms containing variables to be eliminated using
        a user-provided context.

        Args:
            helperTerms:
                Set of context terms that will be used to abstract the TermList.
            varsToElim:
                Variables that cannot be present in TermList after deduction. 
        """
        pass

    @abstractmethod
    def simplify(self, helpers=set()):
        """Remove redundant terms in TermList.
        
        Args:
            helpers:
                Set of context terms that will be used to remove redundancies in the TermList.
        """
        pass

    @abstractmethod
    def refines(self, other) -> bool:
        """Tell whether the argument is a larger specification, i.e., compute self <= other.
        
        Args:
            other:
                TermList against which we are comparing self.
        """
        pass





class IoContract:
    """
    Basic type for an IO contract, a structure consisting of assumptions, guarantees, and input and output vars.

    Attributes:
        inputvars: Variables which are inputs of the implementations of the contract.
        outputvars: Variables which are outputs of the implementations of the contract.
        a(TermList): Contract assumptions.
        g(TermList): Contract guarantees.
    """
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
        """Init"""
        return self.a.vars | self.g.vars

    def __str__(self):
        """Init"""
        return "InVars: " + str(self.inputvars) + "\nOutVars:" + str(self.outputvars) + "\nA: " + str(self.a) + "\n" + "G: " + str(self.g)

    def __le__(self, other):
        return self.refines(other)

    def canComposeWith(self, other) -> bool:
        """Init"""
        # make sure sets of output variables don't intersect
        return len(self.outputvars & other.outputvars) == 0

    def canQuotientBy(self, other) -> bool:
        """Init"""
        # make sure the top level ouputs not contained in outputs of the existing component do not intersect with the inputs of the existing component
        return len((self.outputvars - other.outputvars) & other.inputvars) == 0

    def sharesIoWith(self, other) -> bool:
        assert (self.inputvars == other.inputvars) & (self.outputvars == other.outputvars)


    def refines(self, other) -> bool:
        """Init"""
        assert self.sharesIoWith(other)
        return (other.a <= self.a) and ((self.g | other.a) <= (other.g | other.a))


    def compose(self, other):
        """Compose IO contracts.

        Retrieves rows pertaining to the given keys from the Table instance
        represented by table_handle.  String keys will be UTF-8 encoded.

        Args:
            table_handle:
                An open smalltable.Table instance.
            keys:
                A sequence of strings representing the key of each table row to
                fetch.  String keys will be UTF-8 encoded.
            require_all_keys:
                If True only rows with values set for all keys will be returned.

        Returns:
        A dict mapping keys to the corresponding table row data
        fetched. Each row is represented as a tuple of strings. For
        example:

        {b'Serak': ('Rigel VII', 'Preparer'),
        b'Zim': ('Irk', 'Invader'),
        b'Lrrr': ('Omicron Persei 8', 'Emperor')}

        Returned keys are always bytes.  If a key from the keys argument is
        missing from the dictionary, then that row was not found in the
        table (and require_all_keys must have been False).

        Raises:
        IOError: An error occurred accessing the smalltable.
        """
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
            other.a.abduceWithContext(self.g, intvars | outputvars)
            assumptions = other.a | self.a
        elif otherHelpsSelf:
            self.a.abduceWithContext(other.g, intvars | outputvars)
            assumptions = self.a | other.a
        assumptions.simplify()

        # process guarantees
        g1 = self.g.copy()
        g2 = other.g.copy()
        g1.deduceWithContext(g2,intvars)
        g2.deduceWithContext(g1,intvars)
        allguarantees = g1 | g2
        allguarantees.deduceWithContext(assumptions, intvars)

        # eliminate terms with forbidden vars
        termsToElim = allguarantees.getTermsWithVars(intvars)
        allguarantees = allguarantees - termsToElim
        
        # build contract
        result = IoContract(assumptions, allguarantees, inputvars, outputvars)
        
        return result
    
    def quotient(self, other):
        """Init"""
        assert self.canQuotientBy(other)
        outputvars = (self.outputvars - other.outputvars) | (other.inputvars - self.inputvars)
        inputvars  = (self.inputvars - other.inputvars) | (other.outputvars - self.outputvars)
        intvars = (self.outputvars & other.outputvars) | (self.inputvars & other.inputvars)
        
        # get assumptions
        logging.debug("Computing quotient assumptions")
        assumptions = copy.deepcopy(self.a)
        assumptions.deduceWithContext(other.g, intvars | outputvars)
        logging.debug("Assumptions after processing: " + str(assumptions))

        # get guarantees
        logging.debug("Computing quotient guarantees")
        guarantees = self.g
        logging.debug("Using existing guarantees to aid system-level guarantees")
        guarantees.abduceWithContext(other.g, intvars)
        logging.debug("Using system-level assumptions to aid quotient guarantees")
        guarantees = guarantees | other.a
        guarantees.abduceWithContext(self.a, intvars)
        logging.debug("Guarantees after processing: " + str(guarantees))
        

        return IoContract(assumptions, guarantees, inputvars, outputvars)


if __name__ == '__main__':
    exit()
