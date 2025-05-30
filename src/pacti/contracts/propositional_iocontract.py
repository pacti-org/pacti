"""Specializes IO contract into contracts with polyhedral assumptions and guarantees."""

from __future__ import annotations

from typing import List, Optional, Tuple, TypedDict, Union

from pacti.iocontract import IoContract, TacticStatistics, Var
from pacti.terms.propositions.propositions import PropositionalTerm, PropositionalTermList
import re

numeric = Union[int, float]
ser_contract = TypedDict(
    "ser_contract",
    {"input_vars": List[str], "output_vars": List[str], "assumptions": List[str], "guarantees": List[str]},
)

TACTICS_ORDER = [1, 2, 3, 4, 5]  # noqa: WPS407


class PropositionalIoContract(IoContract):
    """IO Contracts with assumptions and guarantees expressed as polyhedral constraints."""

    def rename_variables(self, variable_mappings: List[Tuple[str, str]]) -> PropositionalIoContract:
        """
        Rename variables in a contract.

        Args:
            variable_mappings: Variables to be replaced.

        Returns:
            A contract with `source_var` replaced by `target_var`.
        """
        new_contract = self.copy()
        for mapping in variable_mappings:
            new_contract = new_contract.rename_variable(Var(mapping[0]), Var(mapping[1]))
        return new_contract

    def to_machine_dict(self) -> ser_contract:
        """
        Map contract into a machine-optimized dictionary.

        Returns:
            A dictionary containing the contract's information.
        """
        return self.to_dict()

    def to_dict(self) -> ser_contract:
        """
        Map contract into a user-readable dictionary.

        Returns:
            A dictionary containing the contract's information.
        """
        c_temp: ser_contract = {
            "input_vars": [str(x) for x in self.inputvars],
            "output_vars": [str(x) for x in self.outputvars],
            "assumptions": self.a.to_str_list(),
            "guarantees": self.g.to_str_list(),
        }
        return c_temp  # noqa: WPS331 c_temp only used for `return`
    
    @staticmethod
    def remove_globally(constraint : str) -> str:
        m = re.search(r'\s*G\(\s*(.*)', constraint)
        assert(m)
        newconstraint = m.group(1)
        m = re.search(r'(.*)\)', newconstraint)
        assert(m)
        newconstraint = m.group(1)
        return newconstraint

    @staticmethod
    def from_strings(
        assumptions: List[str],
        guarantees: List[str],
        input_vars: List[str],
        output_vars: List[str],
        simplify: bool = True,
    ) -> PropositionalIoContract:
        """
        Create contract from several lists of strings.

        Args:
            assumptions: contract's assumptions.
            guarantees: contract's guarantees.
            input_vars: input variables of contract.
            output_vars: output variables of contract.
            simplify: whether to simplify the guarantees with respect to the assumptions.

        Returns:
            A polyhedral contract built from the arguments provided.
        """
        a: List[PropositionalTerm] = []
        if assumptions:
            #a = [PropositionalTerm(PropositionalIoContract.remove_globally(x)) for x in assumptions]
            a = [PropositionalTerm(x) for x in assumptions]

        g: List[PropositionalTerm] = []
        if guarantees:
            #g = [PropositionalTerm(PropositionalIoContract.remove_globally(x)) for x in guarantees]
            g = [PropositionalTerm(x) for x in guarantees]

        return PropositionalIoContract(
            input_vars=[Var(x) for x in input_vars],
            output_vars=[Var(x) for x in output_vars],
            assumptions=PropositionalTermList(a),
            guarantees=PropositionalTermList(g),
            simplify=simplify,
        )

    def compose(
        self,
        other: PropositionalIoContract,
        vars_to_keep: Optional[List[str]] = None,
        simplify: bool = True,
    ) -> PropositionalIoContract:
        """Compose polyhedral contracts.

        Compute the composition of the two given contracts and abstract the
        result in such a way that the result is a well-defined IO contract,
        i.e., that assumptions refer only to inputs, and guarantees to both
        inputs and outputs.

        Args:
            other:
                The second contract being composed.
            vars_to_keep:
                A list of variables that should be kept as top-level outputs.
            simplify:
                Whether to simplify the result of variable elimination by refining or relaxing.

        Returns:
            The abstracted composition of the two contracts.
        """
        if vars_to_keep is None:
            vars_to_keep = []
        return super().compose(other, [Var(x) for x in vars_to_keep], simplify)
    

    def compose_tactics(
        self,
        other: PropositionalIoContract,
        vars_to_keep: Optional[List[str]] = None,
        simplify: bool = True,
        tactics_order: Optional[List[int]] = None,
        diagnose: bool = False,
    ) -> Tuple[PropositionalIoContract, List[TacticStatistics]]:
        """Compose polyhedral contracts.

        Compute the composition of the two given contracts and abstract the
        result in such a way that the result is a well-defined IO contract,
        i.e., that assumptions refer only to inputs, and guarantees to both
        inputs and outputs.

        Args:
            other:
                The second contract being composed.
            vars_to_keep:
                A list of variables that should be kept as top-level outputs.
            simplify:
                Whether to simplify the result of variable elimination by refining or relaxing.
            tactics_order:
                The order of tactics to try for variable term elimination.

        Returns:
            The tuple of the abstracted composition of the two contracts and of the list of tactics used.
        """
        if tactics_order is None:
            tactics_order = TACTICS_ORDER

        if vars_to_keep is None:
            vars_to_keep = []
        return super().compose_tactics(other, [Var(x) for x in vars_to_keep], simplify, tactics_order, diagnose)

    def quotient(  # noqa: WPS612
        self: PropositionalIoContract,
        other: PropositionalIoContract,
        additional_inputs: Optional[List[Var]] = None,
        simplify: bool = True,
    ) -> PropositionalIoContract:
        """Quotient polyhedral contracts.

        Compute the quotient of the two given contracts and abstract the
        result in such a way that the result is a well-defined IO contract,
        i.e., that assumptions refer only to inputs, and guarantees to both
        inputs and outputs.

        Args:
            other:
                The contract by which we take the quotient.
            additional_inputs:
                Additional variables that the quotient is allowed to consider as
                inputs. These variables can be either top level-inputs or
                outputs of the other argument.
            simplify:
                Whether to simplify the result of variable elimination by refining or relaxing.

        Returns:
            The abstracted quotient of the two contracts.
        """
        return super().quotient(other, additional_inputs, simplify)

    def quotient_tactics(
        self: PropositionalIoContract,
        other: PropositionalIoContract,
        additional_inputs: Optional[List[Var]] = None,
        simplify: bool = True,
        tactics_order: Optional[List[int]] = None,
    ) -> Tuple[PropositionalIoContract, List[TacticStatistics]]:
        """Quotient polyhedral contracts with support for specifying the order of tactics and measuring their use.

        Compute the quotient of the two given contracts and abstract the
        result in such a way that the result is a well-defined IO contract,
        i.e., that assumptions refer only to inputs, and guarantees to both
        inputs and outputs.

        Args:
            other:
                The contract by which we take the quotient.
            additional_inputs:
                Additional variables that the quotient is allowed to consider as
                inputs. These variables can be either top level-inputs or
                outputs of the other argument.
            simplify:
                Whether to simplify the result of variable elimination by refining or relaxing.
            tactics_order:
                The order of tactics to try for variable term elimination.

        Returns:
            The tuple of the abstracted quotient of the two contracts and of the list of tactics used.
        """
        if tactics_order is None:
            tactics_order = TACTICS_ORDER

        return super().quotient_tactics(other, additional_inputs, simplify, tactics_order)
