"""
IoContracts definitions.

IoContracts contains Pacti's basic definitions: Var, Term, TemList, and
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
from __future__ import annotations

import copy
import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, List, Optional, TypeVar

from pacti.utils.errors import IncompatibleArgsError
from pacti.utils.lists import list_diff, list_intersection, list_union, lists_equal

Var_t = TypeVar("Var_t", bound="Var")
Term_t = TypeVar("Term_t", bound="Term")
TermList_t = TypeVar("TermList_t", bound="TermList")
IoContract_t = TypeVar("IoContract_t", bound="IoContract")


class Var:
    """
    Variables used in system modeling.

    Variables allow us to name an entity for which we want to write constraints.
    """

    def __init__(self, varname: str):
        """
        Constructor for Var.

        Args:
            varname: The name of the variable.
        """
        self._name = str(varname)

    @property
    def name(self) -> str:
        """The name of the variable.

        Returns:
            The name of the variable.
        """
        return self._name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            raise ValueError()
        return self.name == other.name

    def __str__(self) -> str:
        return self.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __repr__(self) -> str:
        return "<Var {0}>".format(self.name)


class Term(ABC):
    """
    Terms, or constraints, to be imposed on the system or components.

    Term is an abstract class that must be extended in order to support specific
    constraint languages.
    """

    @property
    @abstractmethod
    def vars(self) -> List[Var]:  # noqa: A003
        """Variables contained in the syntax of the term."""

    @abstractmethod
    def contains_var(self, var_to_seek: Var) -> bool:
        """
        Tell whether term contains a given variable.

        Args:
            var_to_seek: The variable that we are seeking in the current term.
        """

    @abstractmethod
    def __eq__(self, other: object) -> bool:
        """
        Equality.

        Args:
            other: the object against which we are comparing self.
        """

    @abstractmethod
    def __str__(self) -> str:
        """Printing support."""

    @abstractmethod
    def __hash__(self) -> int:
        """Hashing."""

    @abstractmethod
    def __repr__(self) -> str:
        """Printable representation."""

    @abstractmethod
    def copy(self: Term_t) -> Term_t:
        """Returns a copy of term."""

    @abstractmethod
    def rename_variable(self: Term_t, source_var: Var, target_var: Var) -> Term_t:
        """
        Rename a variable in a term.

        Args:
            source_var: The variable to be replaced.
            target_var: The new variable.

        Returns:
            A term with `source_var` replaced by `target_var`.
        """


class TermList(ABC):
    """
    A collection of terms, or constraints.

    A TermList is semantically equivalent to a single term which is the
    conjunction of all terms contained in the TermList. TermList is an abstract
    class that must be extended to support a specific constraint formalism.
    """

    def __init__(self, term_list: Optional[List] = None):
        """
        Class constructor.

        Args:
            term_list: A list of terms contained by TermList.
        """
        if term_list:
            self.terms = term_list.copy()
        else:
            self.terms = []

    @property
    def vars(self) -> List[Var]:  # noqa: A003
        """The list of variables contained in this list of terms.

        Returns:
            List of variables referenced in the term.
        """
        varlist: List[Var] = []
        for t in self.terms:
            varlist = list_union(varlist, t.vars)
        return varlist

    def __str__(self) -> str:
        if self.terms:
            res = [str(el) for el in self.terms]
            return ", ".join(res)
        return "true"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            raise ValueError()
        return self.terms == other.terms

    def get_terms_with_vars(self: TermList_t, variable_list: List[Var]) -> TermList_t:
        """
        Returns the list of terms which contain any of the variables indicated.

        Args:
            variable_list: a list of variables being sought in current TermList.

        Returns:
            The list of terms which contain any of the variables indicated.
        """
        terms = []
        for t in self.terms:
            if list_intersection(t.vars, variable_list):
                terms.append(t)
        return type(self)(terms)

    def __and__(self: TermList_t, other: TermList_t) -> TermList_t:
        return type(self)(list_intersection(self.copy().terms, other.copy().terms))

    def __or__(self: TermList_t, other: TermList_t) -> TermList_t:
        return type(self)(list_union(self.copy().terms, other.copy().terms))

    def __sub__(self: TermList_t, other: TermList_t) -> TermList_t:
        return type(self)(list_diff(self.copy().terms, other.copy().terms))

    def __le__(self: TermList_t, other: TermList_t) -> bool:
        return self.refines(other)

    @abstractmethod
    def __hash__(self) -> int:
        ...

    def copy(self: TermList_t) -> TermList_t:
        """
        Makes copy of termlist.

        Returns:
            Copy of termlist.
        """
        return type(self)([term.copy() for term in self.terms])

    def rename_variable(self: TermList_t, source_var: Var, target_var: Var) -> TermList_t:
        """
        Rename a variable in a termlist.

        Args:
            source_var: The variable to be replaced.
            target_var: The new variable.

        Returns:
            A termlist with `source_var` replaced by `target_var`.
        """
        return type(self)([term.rename_variable(source_var, target_var) for term in self.terms])

    @abstractmethod
    def contains_behavior(self, behavior: Any) -> bool:
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

    @abstractmethod
    def elim_vars_by_refining(self: TermList_t, context: TermList_t, vars_to_elim: List[Var]) -> TermList_t:
        """
        Eliminate variables from termlist by refining it in a context.

        Given a context $\\Gamma$, and the list of terms contained in self,
        $s$, this routine identifies a TermList $x$ lacking variables
        vars_to_elim such that $\\frac{\\Gamma\\colon \\; x}{\\Gamma: \\;
        s}$.

        Args:
            context:
                List of context terms that will be used to refine the TermList.
            vars_to_elim:
                Variables to be eliminated.

        Returns:
            A list of terms not containing any variables in `vars_to_elim`
                and which, in the context provided, imply the terms contained in the
                calling termlist.
        """

    @abstractmethod
    def elim_vars_by_relaxing(self: TermList_t, context: TermList_t, vars_to_elim: List[Var]) -> TermList_t:
        """
        Eliminate variables from termlist by relaxing it in a context

        Given a context $\\Gamma$, and the list of terms contained in self,
        $s$, this routine identifies a formula $x$ lacking variables
        vars_to_elim such that $\\frac{\\Gamma\\colon \\; s}{\\Gamma: \\;
        x}$.

        Args:
            context:
                List of context terms that will be used to abstract the TermList.
            vars_to_elim:
                Variables that cannot be present in TermList after relaxation.

        Returns:
            A list of terms not containing any variables in `vars_to_elim`
                and which, in the context provided, are implied by the terms
                contained in the calling termlist.
        """

    @abstractmethod
    def simplify(self: TermList_t, context: Optional[TermList_t] = None) -> TermList_t:
        """Remove redundant terms in TermList.

        Args:
            context:
                List of context terms that will be used to remove redundancies in
                the TermList.

        Returns:
            Let $S$ be this TermList. Simplify will return
                $S_T = S \\setminus T$, where $T \\subseteq S$ is a maximal subset such that
                $\\frac{\\Gamma, S_T\\colon \\; \\top}{\\Gamma, S_T\\colon \\; \\wedge_{t \\in T} t}$.
        """

    @abstractmethod
    def refines(self: TermList_t, other: TermList_t) -> bool:
        """
        Tell whether the argument is a larger specification.

        Args:
            other:
                TermList against which we are comparing self.

        Returns:
            self <= other.
        """

    @abstractmethod
    def is_empty(self) -> bool:
        """
        Tell whether the termlist has no satisfying assignments.

        Returns:
            True if termlist constraints cannot be satisfied.
        """


class IoContract(Generic[TermList_t]):
    """
    Basic type for an IO contract.

    Attributes:
        inputvars:
            Variables which are inputs of the implementations of the contract.

        outputvars:
            Variables which are outputs of the implementations of the contract.

        a(TermList): Contract assumptions.

        g(TermList): Contract guarantees.
    """

    def __init__(
        self, assumptions: TermList_t, guarantees: TermList_t, input_vars: List[Var], output_vars: List[Var]
    ) -> None:
        """
        Class constructor.

        Args:
            assumptions: The assumptions of the contract.
            guarantees: The guarantees of the contract.
            input_vars: The input variables of the contract.
            output_vars: The output variables of the contract.

        Raises:
            IncompatibleArgsError: Arguments provided does not produce a valid IO contract.
        """
        # make sure the input and output variables have no repeated entries
        if len(input_vars) != len(set(input_vars)):
            raise IncompatibleArgsError(
                "The following input variables appear multiple times in argument %s"
                % (set(list_diff(input_vars, list(set(input_vars)))))
            )
        if len(output_vars) != len(set(output_vars)):
            raise IncompatibleArgsError(
                "The following output variables appear multiple times in argument %s"
                % (set(list_diff(output_vars, list(set(output_vars)))))
            )
        # make sure the input & output variables are disjoint
        if list_intersection(input_vars, output_vars):
            raise IncompatibleArgsError(
                "The following variables appear in inputs and outputs: %s"
                % (list_intersection(input_vars, output_vars))
            )
        # make sure the assumptions only contain input variables
        if list_diff(assumptions.vars, input_vars):
            raise IncompatibleArgsError(
                "The following variables appear in the assumptions but are not inputs: %s"
                % (list_diff(assumptions.vars, input_vars))
            )
        # make sure the guarantees only contain input or output variables
        if list_diff(guarantees.vars, list_union(input_vars, output_vars)):
            raise IncompatibleArgsError(
                "The guarantees contain the following variables which are neither"
                "inputs nor outputs: %s. Inputs: %s. Outputs: %s. Guarantees: %s"
                % (list_diff(guarantees.vars, list_union(input_vars, output_vars)), input_vars, output_vars, guarantees)
            )

        self.a: TermList_t = assumptions.copy()
        self.inputvars = input_vars.copy()
        self.outputvars = output_vars.copy()
        # simplify the guarantees with the assumptions
        self.g = guarantees.simplify(self.a)

    @property
    def vars(self) -> List[Var]:  # noqa: A003
        """
        The list of variables in the interface of the contract.

        Returns:
            Input and output variables of the contract.
        """
        return list_union(self.inputvars, self.outputvars)

    def __str__(self) -> str:
        return (
            "InVars: "
            + "["
            + ", ".join([v.name for v in self.inputvars])
            + "]"
            + "\nOutVars:"
            + "["
            + ", ".join([v.name for v in self.outputvars])
            + "]"
            + "\nA: "
            + str(self.a)
            + "\n"
            + "G: "
            + str(self.g)
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            raise ValueError
        return (
            self.inputvars == other.inputvars
            and self.outputvars == self.outputvars
            and self.a == other.a
            and self.g == other.g
        )

    def __hash__(self) -> int:
        return hash((tuple(self.inputvars), tuple(self.outputvars), self.a, self.g))

    def rename_variable(  # noqa: WPS231 too much cognitive complexity
        self: IoContract_t, source_var: Var, target_var: Var
    ) -> IoContract_t:
        """
        Rename a variable in a contract.

        Args:
            source_var: The variable to be replaced.
            target_var: The new variable.

        Returns:
            A contract with `source_var` replaced by `target_var`.

        Raises:
            IncompatibleArgsError: The new variable is both an input and output of the resulting contract.
        """
        inputvars = self.inputvars.copy()
        outputvars = self.outputvars.copy()
        assumptions = self.a.copy()
        guarantees = self.g.copy()
        if source_var != target_var:
            if source_var in inputvars:
                if target_var in outputvars:
                    raise IncompatibleArgsError("Making variable %s both an input and output" % (target_var))
                elif target_var not in inputvars:
                    inputvars[inputvars.index(source_var)] = target_var
                else:
                    inputvars.remove(source_var)
                assumptions = assumptions.rename_variable(source_var, target_var)
                guarantees = guarantees.rename_variable(source_var, target_var)
            elif source_var in outputvars:
                if target_var in inputvars:
                    raise IncompatibleArgsError("Making variable %s both an input and output" % (target_var))
                elif target_var not in outputvars:
                    outputvars[outputvars.index(source_var)] = target_var
                else:
                    outputvars.remove(source_var)
                assumptions = assumptions.rename_variable(source_var, target_var)
                guarantees = guarantees.rename_variable(source_var, target_var)
        return type(self)(assumptions, guarantees, inputvars, outputvars)

    def copy(self: IoContract_t) -> IoContract_t:
        """
        Makes copy of contract.

        Returns:
            Copy of contract.
        """
        inputvars = self.inputvars.copy()
        outputvars = self.outputvars.copy()
        assumptions = self.a.copy()
        guarantees = self.g.copy()
        return type(self)(assumptions, guarantees, inputvars, outputvars)

    def __le__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            raise ValueError()
        return self.refines(other)

    def __repr__(self) -> str:
        return "<Var {0}>".format(self)

    def can_compose_with(self: IoContract_t, other: IoContract_t) -> bool:
        """
        Tell whether the contract can be composed with another contract.

        Args:
            other:
                Contract whose possibility to compose with self we are
                verifying.

        Returns:
            True if the contracts can be composed. False otherwise.
        """
        # make sure lists of output variables don't intersect
        return len(list_intersection(self.outputvars, other.outputvars)) == 0

    def can_quotient_by(self: IoContract_t, other: IoContract_t) -> bool:
        """
        Tell whether the contract can quotiented by another contract.

        Args:
            other: potential quotient by which self would be quotiented.

        Returns:
            True if the IO profiles of the contracts allow the quotient to
                exist. False otherwise.
        """
        # make sure the top level outputs not contained in outputs of the
        # existing component do not intersect with the inputs of the existing
        # component
        return len(list_intersection(list_diff(self.outputvars, other.outputvars), other.inputvars)) == 0

    def shares_io_with(self: IoContract_t, other: IoContract_t) -> bool:
        """
        Tell whether two contracts have the same IO signature.

        Args:
            other: contract whose IO signature is compared with self.

        Returns:
            True if the contracts have the same IO profile.
        """
        return lists_equal(self.inputvars, other.inputvars) & lists_equal(self.outputvars, other.outputvars)

    def refines(self: IoContract_t, other: IoContract_t) -> bool:
        """
        Tell whether the given contract is a refinement of another.

        Return self <= other.

        Args:
            other: contract being compared with self.

        Returns:
            True if the calling contract refines the argument.

        Raises:
            IncompatibleArgsError: Refinement cannot be computed.
        """
        if not self.shares_io_with(other):
            raise IncompatibleArgsError("Contracts do not share IO")
        assumptions_check: bool = other.a <= self.a
        guarantees_check: bool = (self.g | other.a) <= (other.g | other.a)
        return assumptions_check and guarantees_check

    def compose(self: IoContract_t, other: IoContract_t, vars_to_keep: Any = None) -> IoContract_t:  # noqa: WPS231
        """Compose IO contracts.

        Compute the composition of the two given contracts and abstract the
        result in such a way that the result is a well-defined IO contract,
        i.e., that assumptions refer only to inputs, and guarantees to both
        inputs and outputs.

        Args:
            other:
                The second contract being composed.
            vars_to_keep:
                A list of variables that should be kept as top-level outputs.

        Returns:
            The abstracted composition of the two contracts.

        Raises:
            IncompatibleArgsError: An error occurred during composition.
        """
        if vars_to_keep is None:
            vars_to_keep = []
        conflict_vars = list_diff(vars_to_keep, list_union(self.outputvars, other.outputvars))
        if conflict_vars:
            raise IncompatibleArgsError("Asked to keep variables %s, which are not outputs" % (conflict_vars))

        logging.debug("Composing contracts \n%s and \n%s", self, other)
        intvars = list_union(
            list_intersection(self.outputvars, other.inputvars), list_intersection(self.inputvars, other.outputvars)
        )
        inputvars = list_diff(list_union(self.inputvars, other.inputvars), intvars)
        outputvars = list_diff(list_union(self.outputvars, other.outputvars), intvars)
        # remove requested variables
        intvars = list_diff(intvars, vars_to_keep)
        outputvars = list_union(outputvars, vars_to_keep)

        selfinputconst = self.a.vars
        otherinputconst = other.a.vars
        cycle_present = (
            len(list_intersection(self.inputvars, other.outputvars)) > 0
            and len(list_intersection(other.inputvars, self.outputvars)) > 0
        )

        assumptions_forbidden_vars = list_union(intvars, outputvars)
        if not self.can_compose_with(other):
            raise IncompatibleArgsError(
                "Cannot compose the following contracts due to incompatible IO profiles:\n %s \n %s" % (self, other)
            )
        other_helps_self = len(list_intersection(other.outputvars, self.inputvars)) > 0
        self_helps_other = len(list_intersection(other.inputvars, self.outputvars)) > 0
        other_drives_const_inputs = len(list_intersection(other.outputvars, selfinputconst)) > 0
        self_drives_const_inputs = len(list_intersection(self.outputvars, otherinputconst)) > 0
        # process assumptions
        if cycle_present and (other_drives_const_inputs or self_drives_const_inputs):
            raise IncompatibleArgsError("Cannot compose contracts due to feedback")
        elif self_helps_other and not other_helps_self:
            logging.debug("Assumption computation: self provides context for other")
            new_a: TermList_t = other.a.elim_vars_by_refining(self.a | self.g, assumptions_forbidden_vars)
            conflict_variables = list_intersection(new_a.vars, assumptions_forbidden_vars)
            if conflict_variables:
                raise IncompatibleArgsError(
                    "Could not eliminate variables {}\n".format([str(x) for x in assumptions_forbidden_vars])
                    + "by refining the assumptions \n{}\n".format(new_a.get_terms_with_vars(assumptions_forbidden_vars))
                    + "using guarantees \n{}\n".format(self.a | self.g)
                )
            assumptions = new_a | self.a
        elif other_helps_self and not self_helps_other:
            logging.debug("****** Assumption computation: other provides context for self")
            new_a = self.a.elim_vars_by_refining(other.a | other.g, assumptions_forbidden_vars)
            conflict_variables = list_intersection(new_a.vars, assumptions_forbidden_vars)
            if conflict_variables:
                raise IncompatibleArgsError(
                    "Could not eliminate variables {}".format([str(x) for x in assumptions_forbidden_vars])
                    + " by refining the assumptions \n{}\n".format(
                        new_a.get_terms_with_vars(assumptions_forbidden_vars)
                    )
                    + "using guarantees \n{}\n".format(other.a | other.g)
                )
            assumptions = new_a | other.a
        # contracts can't help each other
        else:
            logging.debug("****** Assumption computation: other provides context for self")
            assumptions = self.a | other.a
        logging.debug("Assumption computation: computed assumptions:\n%s", assumptions)
        assumptions = assumptions.simplify()

        # process guarantees
        logging.debug("****** Computing guarantees")
        g1_t = self.g.copy()
        g2_t = other.g.copy()
        g1 = g1_t.elim_vars_by_relaxing(g2_t, intvars)
        g2 = g2_t.elim_vars_by_relaxing(g1_t, intvars)
        allguarantees = g1 | g2
        allguarantees = allguarantees.elim_vars_by_relaxing(assumptions, intvars)

        # eliminate terms with forbidden vars
        terms_to_elim = allguarantees.get_terms_with_vars(intvars)
        allguarantees -= terms_to_elim

        return type(self)(assumptions, allguarantees, inputvars, outputvars)

    def quotient(
        self: IoContract_t, other: IoContract_t, additional_inputs: Optional[List[Var]] = None
    ) -> IoContract_t:
        """Compute the contract quotient.

        Compute the quotient self/other of the two given contracts and refine
        the result in such a way that the result is a well-defined IO contract,
        i.e., that assumptions refer only to inputs, and guarantees to both
        inputs and outputs.

        Args:
            other:
                The contract by which we take the quotient.
            additional_inputs:
                Additional variables that the quotient is allowed to consider as
                inputs. These variables can be either top level-inputs or
                outputs of the other argument.

        Returns:
            The refined quotient self/other.

        Raises:
            IncompatibleArgsError: Arguments provided are incompatible with computation of the quotient.
        """
        if not additional_inputs:
            additional_inputs = []
        if not self.can_quotient_by(other):
            raise IncompatibleArgsError("Contracts cannot be quotiented due to incompatible IO")
        if list_diff(additional_inputs, list_union(other.outputvars, self.inputvars)):
            raise IncompatibleArgsError(
                "The additional inputs %s are neither top level inputs nor existing component outputs"
                % (list_diff(additional_inputs, list_union(other.outputvars, self.inputvars)))
            )
        outputvars = list_union(
            list_diff(self.outputvars, other.outputvars), list_diff(other.inputvars, self.inputvars)
        )
        inputvars = list_union(list_diff(self.inputvars, other.inputvars), list_diff(other.outputvars, self.outputvars))
        inputvars = list_union(inputvars, additional_inputs)
        intvars = list_union(
            list_intersection(self.outputvars, other.outputvars), list_intersection(self.inputvars, other.inputvars)
        )
        intvars = list_diff(intvars, additional_inputs)

        # get assumptions
        logging.debug("Computing quotient assumptions")
        assumptions = copy.deepcopy(self.a)
        empty_context = type(assumptions)([])
        if assumptions.refines(other.a):
            logging.debug("Extending top-level assumptions with divisor's guarantees")
            assumptions = assumptions | other.g
        assumptions = assumptions.elim_vars_by_relaxing(empty_context, list_union(intvars, outputvars))
        logging.debug("Assumptions after processing: %s", assumptions)

        # get guarantees
        logging.debug("Computing quotient guarantees")
        guarantees: TermList_t = self.g
        logging.debug("Using existing guarantees to aid system-level guarantees")
        try:
            guarantees = guarantees.elim_vars_by_refining(other.g | other.a, intvars)
        except ValueError:
            guarantees = self.g
        logging.debug("Guarantees are %s" % (guarantees))
        logging.debug("Using system-level assumptions to aid quotient guarantees")
        guarantees = guarantees | other.a
        try:
            guarantees = guarantees.elim_vars_by_refining(self.a, intvars)
        except ValueError:
            ...
        logging.debug("Guarantees after processing: %s", guarantees)
        conflict_variables = list_intersection(guarantees.vars, intvars)
        if conflict_variables:
            raise IncompatibleArgsError(
                "Could not eliminate variables \n{}".format([str(x) for x in conflict_variables])
                + "by refining the guarantees \n{}\n".format(guarantees.get_terms_with_vars(intvars))
            )

        return type(self)(assumptions, guarantees, inputvars, outputvars)

    def merge(self: IoContract_t, other: IoContract_t) -> IoContract_t:
        """
        Compute the merging operation for two contracts.

        Compute the merging operation of the two given contracts. No
        abstraction/refinement is applied.

        Args:
            other: The contract with which we are merging self.

        Returns:
            The result of merging.

        Raises:
            IncompatibleArgsError: trying to merge different contract types.
        """
        if not isinstance(self, type(other)):
            raise IncompatibleArgsError("Asked to merge incompatible contracts")
        input_vars = list_union(self.inputvars, other.inputvars)
        output_vars = list_union(self.outputvars, other.outputvars)
        assumptions = self.a | other.a
        guarantees = self.g | other.g
        return type(self)(assumptions, guarantees, input_vars, output_vars)

    def contains_environment(self, component: TermList) -> bool:
        """
        Tell whether a component is a valid environment for the contract.

        Args:
            component: The component in question.

        Returns:
            True if the component is a valid environment; false otherwise.
        """
        return component <= self.a

    def contains_implementation(self, component: TermList) -> bool:
        """
        Tell whether a component is a valid implementation for the contract.

        Args:
            component:
                The component in question.

        Returns:
            True if the component is a valid implementation; false otherwise.
        """
        return (component | self.a) <= (self.g | self.a)
