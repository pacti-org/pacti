"""Functionality for IO contracts with assumptions and guarantees expressed as disconnected convex sets."""

from __future__ import annotations

import logging
from typing import List, TypeVar, Union

from pacti.iocontract.iocontract import TermList_t, Var
from pacti.utils.lists import list_diff, list_intersection, list_union

NTL_t = TypeVar("NTL_t", bound="NestedTermList")
numeric = Union[int, float]


class NestedTermList:
    """A collection of termlists interpreted as their disjunction."""

    def __init__(  # noqa: WPS231 too much cognitive complexity
        self, nested_termlist: list[TermList_t], force_empty_intersection: bool
    ):
        """
        Class constructor.

        Args:
            nested_termlist: A list of terms contained by TermList.
            force_empty_intersection: Raise error if the termlists are not disjoint.

        Raises:
            ValueError: argument has separate termlists with nonempty intersection.
        """
        # make sure the elements of the argument don't intersect
        if force_empty_intersection:
            for i, tli in enumerate(nested_termlist):
                for j, tlj in enumerate(nested_termlist):
                    if j > i:
                        intersection = tli | tlj
                        if not intersection.is_empty():
                            raise ValueError("Terms %s and %s have nonempty intersection" % (tli, tlj))
        self.nested_termlist: list[TermList_t] = []
        for tl in nested_termlist:
            self.nested_termlist.append(tl.copy())

    def __str__(self) -> str:
        if self.nested_termlist:
            res = [str(tl) for tl in self.nested_termlist]
            return "\nor \n".join(res)
        return "true"

    def simplify(self: NTL_t, context: NTL_t, force_empty_intersection: bool) -> None:
        """
        Remove redundant terms in nested termlist.

        Args:
            context: Nested termlist serving as context for simplification.
            force_empty_intersection: Make sure the resulting termlists have empty intersection.
        """
        new_nested_tl = []
        for self_tl in self.nested_termlist:
            for context_tl in context.nested_termlist:
                new_tl = self_tl.copy()
                try:
                    new_tl.simplify(context_tl)
                except ValueError:
                    continue
                new_nested_tl.append(new_tl)
        self.nested_termlist = type(self)(new_nested_tl, force_empty_intersection).nested_termlist

    def intersect(self: NTL_t, other: NTL_t, force_empty_intersection: bool) -> NTL_t:
        """
        Semantically intersect two nested termlists.

        Args:
            other: second argument to intersection.
            force_empty_intersection: Raise error if termlists are not disjoint.

        Returns:
            The nested termlist for the intersection.
        """
        new_nested_tl = []
        for self_tl in self.nested_termlist:
            for other_tl in other.nested_termlist:
                new_tl = self_tl | other_tl
                if not new_tl.is_empty():
                    new_nested_tl.append(new_tl)
        return type(self)(new_nested_tl, force_empty_intersection)

    @property
    def vars(self) -> list[Var]:  # noqa: A003
        """The list of variables contained in this nested termlist.

        Returns:
            List of variables referenced in nested termlist.
        """
        varlist: list[Var] = []
        for tl in self.nested_termlist:
            varlist = list_union(varlist, tl.vars)
        return varlist

    def copy(self: NTL_t, force_empty_intersection: bool) -> NTL_t:
        """
        Makes copy of nested termlist.

        Args:
            force_empty_intersection: Raise error if the termlists are not disjoint.

        Returns:
            Copy of nested termlist.
        """
        return type(self)([tl.copy() for tl in self.nested_termlist], force_empty_intersection)

    def contains_behavior(self, behavior: dict[Var, numeric]) -> bool:
        """
        Tell whether constraints contain the given behavior.

        Args:
            behavior:
                The behavior in question.

        Returns:
            True if the behavior satisfies the constraints; false otherwise.

        Raises:
            ValueError: Not all variables in the constraints were assigned values.
        """
        for tl in self.nested_termlist:
            try:
                if tl.contains_behavior(behavior):
                    return True
            except ValueError as e:
                raise ValueError from e
        return False


class IoContractCompound:
    """
    Basic type for a compound IO contract.

    Attributes:
        inputvars:
            Variables which are inputs of the implementations of the contract.

        outputvars:
            Variables which are outputs of the implementations of the contract.

        a: Contract assumptions.

        g: Contract guarantees.
    """

    def __init__(self, assumptions: NTL_t, guarantees: NTL_t, input_vars: List[Var], output_vars: List[Var]):
        """
        Class constructor.

        Args:
            assumptions: The assumptions of the contract.
            guarantees: The guarantees of the contract.
            input_vars: The input variables of the contract.
            output_vars: The output variables of the contract.

        Raises:
            ValueError: Arguments provided does not produce a valid IO contract.
        """
        logging.debug("Constructor assumptions")
        logging.debug(assumptions)
        logging.debug("Constructor guarantees")
        logging.debug(guarantees)
        # make sure the input and output variables have no repeated entries
        if len(input_vars) != len(set(input_vars)):
            raise ValueError(
                "The following input variables appear multiple times in argument %s"
                % (set(list_diff(input_vars, list(set(input_vars)))))
            )
        if len(output_vars) != len(set(output_vars)):
            raise ValueError(
                "The following output variables appear multiple times in argument %s"
                % (set(list_diff(output_vars, list(set(output_vars)))))
            )
        # make sure the input & output variables are disjoint
        if list_intersection(input_vars, output_vars):
            raise ValueError(
                "The following variables appear in inputs and outputs: %s"
                % (list_intersection(input_vars, output_vars))
            )
        # make sure the assumptions only contain input variables
        if list_diff(assumptions.vars, input_vars):
            raise ValueError(
                "The following variables appear in the assumptions but are not inputs: %s"
                % (list_diff(assumptions.vars, input_vars))
            )
        # make sure the guarantees only contain input or output variables
        if list_diff(guarantees.vars, list_union(input_vars, output_vars)):
            raise ValueError(
                "The guarantees contain the following variables which are neither"
                "inputs nor outputs: %s. Inputs: %s. Outputs: %s. Guarantees: %s"
                % (list_diff(guarantees.vars, list_union(input_vars, output_vars)), input_vars, output_vars, guarantees)
            )

        self.a: NTL_t = assumptions.copy(True)
        self.g: NTL_t = guarantees.copy(False)
        self.inputvars = input_vars.copy()
        self.outputvars = output_vars.copy()
        # simplify the guarantees with the assumptions
        # self.g.simplify(self.a)

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

    def merge(self, other: IoContractCompound) -> IoContractCompound:
        """
        Compute the merging operation for two contracts.

        Compute the merging operation of the two given contracts. No
        abstraction/refinement is applied.

        Args:
            other: The contract with which we are merging self.

        Returns:
            The result of merging.
        """
        input_vars = list_union(self.inputvars, other.inputvars)
        output_vars = list_union(self.outputvars, other.outputvars)
        assumptions = self.a.intersect(other.a, force_empty_intersection=True)
        guarantees = self.g.intersect(other.g, force_empty_intersection=False)
        return IoContractCompound(assumptions, guarantees, input_vars, output_vars)
