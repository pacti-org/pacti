"""
IoContracts contains Gear's basic definitions: Var, Term, TemSet, and
IoContract. Var creates variables; Term is an abstract class representing
constraints; a TermSet (also an abstract class) is a collection of terms
semantically equivalent to the term which is the conjunction of all terms
contained in the TermSet; IoContract is an assume-guarantee specification
consisting of assumptions, guarantees, and input and output variables. The
assumptions and guarantees are given by TermSets. Assumptions make predicates
only on inputs, and guarantees on both input and outputs (and no other
variable).

This module implements all supported contract operations and relations. In order
to instantiate contracts and perform this operations, it is necessary to extend
Term and TermSet with specific constraint formalisms.
"""
from __future__ import annotations

import copy
import logging
from abc import ABC, abstractmethod
from typing import Set


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

    Term is an abstract class that must be extended in order to support specific
    constraint languages.
    """

    @property
    @abstractmethod
    def vars(self):
        """Variables contained in the syntax of the term."""

    @abstractmethod
    def contains_var(self, var: Var):
        """
        Tell whether term contains a given variable.

        Args:
            var: The variable that we are seeking in the current term.
        """

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


class TermSet(ABC):
    """
    A collection of terms, or constraints.

    A TermSet is semantically equivalent to a single term which is the
    conjunction of all terms contained in the TermSet. TermSet is an abstract
    class that must be extended to support a specific constraint formalism.
    """

    def __init__(self, termSet: set):
        self.terms = termSet.copy()

    @property
    def vars(self):
        """The set of variables contained in this set of terms."""
        varset = set()
        for t in self.terms:
            varset = varset | t.vars
        return varset

    def __str__(self) -> str:
        if len(self.terms) > 0:
            res = [str(el) for el in self.terms]
            return ", ".join(res)
        else:
            return "true"

    def __eq__(self, other):
        return self.terms == other.terms

    def get_terms_with_vars(self, variable_set: Set[Var]):
        """
        Returns the set of terms which contain any of the variables indicated.

        Args:
            varSet: a set of variables being sought in current TermSet.
        """
        terms = set()
        for t in self.terms:
            if len(t.vars & variable_set) > 0:
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
    def abduce_with_context(self, context: TermSet, vars_to_elim: Set[Var]) -> TermSet:
        """
        Abduce terms containing variables to be eliminated using a user-provided
        context.

        Given a context :math:`\\Gamma`, and the set of terms contained in self,
        :math:`s`, this routine identifies a TermSet :math:`x` lacking variables
        vars_to_elim such that :math:`\\frac{\\Gamma\\colon \\; x}{\\Gamma: \\;
        s}`.

        Args:
            context:
                Set of context terms that will be used to abduce the TermSet.
            vars_to_elim:
                Variables that cannot be present in TermSet after abduction.

        Returns:
            A set of terms not containing any variables in :code:`vars_to_elim`
            and which, in the context provided, imply the terms contained in the
            calling termset.
        """

    @abstractmethod
    def deduce_with_context(self, context: TermSet, vars_to_elim: Set[Var]) -> TermSet:
        """
        Deduce terms containing variables to be eliminated using a user-provided
        context.

        Given a context :math:`\\Gamma`, and the set of terms contained in self,
        :math:`s`, this routine identifies a formula :math:`x` lacking variables
        vars_to_elim such that :math:`\\frac{\\Gamma\\colon \\; s}{\\Gamma: \\;
        x}`.

        Args:
            context:
                Set of context terms that will be used to abstract the TermSet.
            vars_to_elim:
                Variables that cannot be present in TermSet after deduction.

        Returns:
            A set of terms not containing any variables in :code:`vars_to_elim`
            and which, in the context provided, are implied by the terms
            contained in the calling termset.
        """

    @abstractmethod
    def simplify(self, context=set()):
        """Remove redundant terms in TermSet.

        Let :math:`S` be this TermSet and suppose :math:`T \\subseteq S`. Let
        :math:`S_T = S \\setminus T`. Simplify will remove from :math:`S` a
        maximal subset :math:`T` such that :math:`\\frac{\\Gamma, S_T\\colon \\;
        \\top}{\\Gamma, S_T\\colon \\; \\wedge_{t \\in T} t}`.

        Args:
            context:
                Set of context terms that will be used to remove redundancies in
                the TermSet.
        """

    @abstractmethod
    def refines(self, other: TermSet) -> bool:
        """
        Tell whether the argument is a larger specification, i.e., compute self
        <= other.

        Args:
            other:
                TermSet against which we are comparing self.
        """


class IoContract:
    """
    Basic type for an IO contract, a structure consisting of assumptions,
    guarantees, and input and output vars.

    Attributes:
        inputvars:
            Variables which are inputs of the implementations of the contract.

        outputvars:
            Variables which are outputs of the implementations of the contract.

        a(TermSet): Contract assumptions.

        g(TermSet): Contract guarantees.
    """

    def __init__(self, assumptions: TermSet, guarantees: TermSet, inputVars: Set[Var], outputVars: Set[Var]) -> None:
        # make sure the input & output variables are disjoint
        assert len(inputVars & outputVars) == 0
        # make sure the assumptions only contain input variables
        assert len(assumptions.vars - inputVars) == 0, print(
            "A: " + str(assumptions.vars) + " Input vars: " + str(inputVars)
        )
        # make sure the guaranteees only contain input or output variables
        assert len(guarantees.vars - inputVars - outputVars) == 0, print(
            "G: "
            + str(guarantees)
            + " G Vars: "
            + str(guarantees.vars)
            + " Input: "
            + str(inputVars)
            + " Output: "
            + str(outputVars)
        )
        self.a = assumptions.copy()
        self.g = guarantees.copy()
        self.inputvars = inputVars.copy()
        self.outputvars = outputVars.copy()
        # simplify the guarantees with the assumptions
        self.g.simplify(self.a)

    @property
    def vars(self):
        """
        The set of variables contained in the assumptions and guarantees of the
        contract.
        """
        return self.a.vars | self.g.vars

    def __str__(self):
        return (
            "InVars: "
            + str(self.inputvars)
            + "\nOutVars:"
            + str(self.outputvars)
            + "\nA: "
            + str(self.a)
            + "\n"
            + "G: "
            + str(self.g)
        )

    def __le__(self, other):
        return self.refines(other)

    def can_compose_with(self, other: IoContract) -> bool:
        """
        Tell whether the contract can be composed with another contract.

        Args:
            other:
                Contract whose possibility to compose with self we are
                verifying.
        """
        # make sure sets of output variables don't intersect
        return len(self.outputvars & other.outputvars) == 0

    def can_quotient_by(self, other: IoContract) -> bool:
        """
        Tell whether the contract can quotiented by another contract.

        Args:
            other: potential quotient by which self would be quotiented.
        """
        # make sure the top level ouputs not contained in outputs of the
        # existing component do not intersect with the inputs of the existing
        # component
        return len((self.outputvars - other.outputvars) & other.inputvars) == 0

    def shares_io_with(self, other: IoContract) -> bool:
        """
        Tell whether two contracts have the same IO signature.

        Args:
            other: contract whose IO signature is compared with self.
        """
        return (self.inputvars == other.inputvars) & (self.outputvars == other.outputvars)

    def refines(self, other: IoContract) -> bool:
        """
        Tell whether the given contract is a refinement of another.

        Return self <= other.

        Args:
            other: contract being compared with self.
        """
        assert self.shares_io_with(other)
        return (other.a <= self.a) and ((self.g | other.a) <= (other.g | other.a))

    def compose(self, other: IoContract) -> IoContract:
        """Compose IO contracts.

        Compute the composition of the two given contracts and abstract the
        result in such a way that the result is a well-defined IO contract,
        i.e., that assumptions refer only to inputs, and guarantees to both
        inputs and outputs.

        Args:
            other:
                The second contract being composed.

        Returns:
            The abstracted composition of the two contracts.
        """
        logging.debug("Composing contracts \n%s and \n%s", self, other)
        intvars = (self.outputvars & other.inputvars) | (self.inputvars & other.outputvars)
        inputvars = (self.inputvars | other.inputvars) - intvars
        outputvars = (self.outputvars | other.outputvars) - intvars

        selfinputconst = self.a.vars
        otherinputconst = other.a.vars
        cycle_present = len(self.inputvars & other.outputvars) > 0 and len(other.inputvars & self.outputvars) > 0

        assumptions_forbidden_vars = intvars | outputvars
        assert self.can_compose_with(other)
        other_helps_self = len(other.outputvars & self.inputvars) > 0
        self_helps_other = len(other.inputvars & self.outputvars) > 0
        #
        other_drives_const_inputs = len(other.outputvars & selfinputconst) > 0
        self_drives_const_inputs = len(self.outputvars & otherinputconst) > 0
        # process assumptions
        if cycle_present and (other_drives_const_inputs or self_drives_const_inputs):
            assert False, "Cannot compose due to feedback"
        elif self_helps_other and not other_helps_self:
            logging.debug("Assumption computation: self provides context for other")
            new_a = other.a.abduce_with_context(self.a | self.g, assumptions_forbidden_vars)
            if len(new_a.vars & assumptions_forbidden_vars) > 0:
                raise ValueError(
                    "The guarantees \n{}\n".format(self.g)
                    + "were insufficient to abduce the assumptions \n{}\n".format(other.a)
                    + "by eliminating the variables \n{}".format(assumptions_forbidden_vars)
                )
            assumptions = new_a | self.a
        elif other_helps_self and not self_helps_other:
            logging.debug("Assumption computation: other provides context for self")
            new_a = self.a.abduce_with_context(other.a | other.g, assumptions_forbidden_vars)
            if len(new_a.vars & assumptions_forbidden_vars) > 0:
                raise ValueError(
                    "The guarantees \n{}\n".format(other.g)
                    + "were insufficient to abduce the assumptions \n{}\n".format(self.a)
                    + "by eliminating the variables \n{}".format(assumptions_forbidden_vars)
                )
            assumptions = new_a | other.a
        # contracts can't help each other
        else:
            logging.debug("Assumption computation: other provides context for self")
            assumptions = self.a | other.a
        logging.debug("Assumption computation: computed assumptions:\n%s", assumptions)
        assumptions.simplify()

        # process guarantees
        g1 = self.g.copy()
        g2 = other.g.copy()
        g1 = g1.deduce_with_context(g2, intvars)
        g2 = g2.deduce_with_context(g1, intvars)
        allguarantees = g1 | g2
        allguarantees = allguarantees.deduce_with_context(assumptions, intvars)

        # eliminate terms with forbidden vars
        terms_to_elim = allguarantees.get_terms_with_vars(intvars)
        allguarantees = allguarantees - terms_to_elim

        # build contract
        result = IoContract(assumptions, allguarantees, inputvars, outputvars)

        return result

    def quotient(self, other: IoContract) -> IoContract:
        """Compute the contract quotient.

        Compute the quotient self/other of the two given contracts and refine
        the result in such a way that the result is a well-defined IO contract,
        i.e., that assumptions refer only to inputs, and guarantees to both
        inputs and outputs.

        Args:
            other:
                The contract by which we take the quotient.

        Returns:
            The refined quotient self/other.
        """
        assert self.can_quotient_by(other)
        outputvars = (self.outputvars - other.outputvars) | (other.inputvars - self.inputvars)
        inputvars = (self.inputvars - other.inputvars) | (other.outputvars - self.outputvars)
        intvars = (self.outputvars & other.outputvars) | (self.inputvars & other.inputvars)

        # get assumptions
        logging.debug("Computing quotient assumptions")
        assumptions = copy.deepcopy(self.a)
        empty_context = type(assumptions)(set())
        if assumptions.refines(other.a):
            assumptions = assumptions | other.g
        assumptions = assumptions.deduce_with_context(empty_context, intvars | outputvars)
        logging.debug("Assumptions after processing: %s", assumptions)

        # get guarantees
        logging.debug("Computing quotient guarantees")
        guarantees = self.g
        logging.debug(
            """
        Using existing guarantees to aid system-level guarantees
        """
        )
        guarantees = guarantees.abduce_with_context(other.a | other.g, intvars)
        logging.debug(
            """
        Using system-level assumptions to aid quotient guarantees"""
        )
        guarantees = guarantees | other.a
        guarantees = guarantees.abduce_with_context(self.a, intvars)
        logging.debug("Guarantees after processing: %s", guarantees)

        return IoContract(assumptions, guarantees, inputvars, outputvars)

    def merge(self, other: IoContract) -> IoContract:
        """Compute the merging operation for two contracts.

        Compute the merging operation of the two given contracts. No
        abstraction/refinement is applied.

        Args:
            other:
                The contract with which we are merging self.

        Returns:
            The result of merging.
        """
        assert self.shares_io_with(other)
        assumptions = self.a | other.a
        guarantees = self.g | other.g
        return IoContract(assumptions, guarantees, self.inputvars, self.outputvars)
