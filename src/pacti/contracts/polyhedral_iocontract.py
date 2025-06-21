"""Specializes IO contract into contracts with polyhedral assumptions and guarantees."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, TypedDict, Union

from pacti.iocontract import IoContract, IoContractCompound, NestedTermList, TacticStatistics, Var
from pacti.terms.polyhedra import serializer
from pacti.terms.polyhedra.polyhedra import PolyhedralTerm, PolyhedralTermList

numeric = Union[int, float]
ser_pt = Dict[str, Union[float, Dict[str, float]]]
ser_contract = TypedDict(
    "ser_contract",
    {"input_vars": List[str], "output_vars": List[str], "assumptions": List[ser_pt], "guarantees": List[ser_pt]},
)

TACTICS_ORDER = [1, 2, 3, 4, 5]  # noqa: WPS407


class PolyhedralIoContract(IoContract):
    """IO Contracts with assumptions and guarantees expressed as polyhedral constraints."""

    def rename_variables(self, variable_mappings: List[Tuple[str, str]]) -> PolyhedralIoContract:
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
        input_vars = [str(x) for x in self.inputvars]
        output_vars = [str(x) for x in self.outputvars]
        assumptions: List[ser_pt] = [
            {
                "constant": float(term.constant),
                "coefficients": {str(k): float(v) for k, v in term.variables.items()},
            }
            for term in self.a.terms
        ]
        guarantees: List[ser_pt] = [
            {
                "constant": float(term.constant),
                "coefficients": {str(k): float(v) for k, v in term.variables.items()},
            }
            for term in self.g.terms
        ]

        return {
            "input_vars": input_vars,
            "output_vars": output_vars,
            "assumptions": assumptions,
            "guarantees": guarantees,
        }

    def to_dict(self) -> dict:
        """
        Map contract into a user-readable dictionary.

        Returns:
            A dictionary containing the contract's information.
        """
        c_temp = {}
        c_temp["input_vars"] = [str(x) for x in self.inputvars]
        c_temp["output_vars"] = [str(x) for x in self.outputvars]
        c_temp["assumptions"] = self.a.to_str_list()
        c_temp["guarantees"] = self.g.to_str_list()
        return c_temp

    @staticmethod
    def from_strings(
        assumptions: List[str],
        guarantees: List[str],
        input_vars: List[str],
        output_vars: List[str],
        simplify: bool = True,
    ) -> PolyhedralIoContract:
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
        a: List[PolyhedralTerm] = []
        if assumptions:
            a = [item for x in assumptions for item in serializer.polyhedral_termlist_from_string(x)]

        g: List[PolyhedralTerm] = []
        if guarantees:
            g = [item for x in guarantees for item in serializer.polyhedral_termlist_from_string(x)]

        return PolyhedralIoContract(
            input_vars=[Var(x) for x in input_vars],
            output_vars=[Var(x) for x in output_vars],
            assumptions=PolyhedralTermList(a),
            guarantees=PolyhedralTermList(g),
            simplify=simplify,
        )

    @staticmethod
    def from_dict(contract: dict, simplify: bool = True) -> PolyhedralIoContract:
        """
        Create contract from a dictionary.

        Args:
            contract: a dictionary containing the contract's data.
            simplify: whether to simplify the guarantees with respect to the assumptions.

        Returns:
            A polyhedral contract built from the arguments provided.

        Raises:
            ValueError: dictionary provided was not well-formed.
        """
        if not isinstance(contract, dict):
            raise ValueError("A dict type contract is expected.")
        for kw in ("assumptions", "guarantees", "input_vars", "output_vars"):
            if kw not in contract:
                raise ValueError(f"Passed dictionary does not have key {kw}.")

        if all(isinstance(x, dict) for x in contract["assumptions"]):
            a = PolyhedralTermList(
                [
                    PolyhedralTerm({Var(k): v for k, v in x["coefficients"].items()}, float(x["constant"]))
                    for x in contract["assumptions"]
                ]
            )
        else:
            raise ValueError("Assumptions must be a list of dicts.")

        if all(isinstance(x, dict) for x in contract["guarantees"]):
            g = PolyhedralTermList(
                [
                    PolyhedralTerm({Var(k): v for k, v in x["coefficients"].items()}, float(x["constant"]))
                    for x in contract["guarantees"]
                ]
            )
        else:
            raise ValueError("Guarantees must be a list of dicts.")

        return PolyhedralIoContract(
            input_vars=[Var(x) for x in contract["input_vars"]],
            output_vars=[Var(x) for x in contract["output_vars"]],
            assumptions=a,
            guarantees=g,
            simplify=simplify,
        )

    def compose(
        self,
        other: PolyhedralIoContract,
        vars_to_keep: Optional[List[str]] = None,
        simplify: bool = True,
    ) -> PolyhedralIoContract:
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
        other: PolyhedralIoContract,
        vars_to_keep: Optional[List[str]] = None,
        simplify: bool = True,
        tactics_order: Optional[List[int]] = None,
    ) -> Tuple[PolyhedralIoContract, List[TacticStatistics]]:
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
        return super().compose_tactics(other, [Var(x) for x in vars_to_keep], simplify, tactics_order)

    def quotient(  # noqa: WPS612
        self: PolyhedralIoContract,
        other: PolyhedralIoContract,
        additional_inputs: Optional[List[Var]] = None,
        simplify: bool = True,
    ) -> PolyhedralIoContract:
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
        self: PolyhedralIoContract,
        other: PolyhedralIoContract,
        additional_inputs: Optional[List[Var]] = None,
        simplify: bool = True,
        tactics_order: Optional[List[int]] = None,
    ) -> Tuple[PolyhedralIoContract, List[TacticStatistics]]:
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

    def optimize(self, expr: str, maximize: bool = True) -> Optional[numeric]:
        """Optimize linear objective over the contract.

        Compute the optima of a linear objective over the assumptions and
        guarantees of the contract.

        Args:
            expr:
                linear objective being optimized.
            maximize:
                Maximize if True; minimize if False.

        Returns:
            The optimal value of the objective in the context of the contract.
        """
        new_expr = expr + " <= 0"
        variables = serializer.polyhedral_termlist_from_string(new_expr)[0].variables
        constraints: PolyhedralTermList = self.a | self.g
        return constraints.optimize(objective=variables, maximize=maximize)

    def get_variable_bounds(
        self, var: str
    ) -> Tuple[Optional[numeric], Optional[numeric]]:  # noqa: VNE002 variable 'var' should be clarified
        """Obtain bounds for a variable in the context of a contract.

        Args:
            var:
                variable whose bounds are sought.

        Returns:
            The minimum and maximum values for the variable in the context of the contract.
        """
        maximum = self.optimize(var, maximize=True)
        minimum = self.optimize(var, maximize=False)
        return minimum, maximum


class NestedPolyhedra(NestedTermList):
    """A collection of polyhedral termlists interpreted as their disjunction."""

    def __init__(  # noqa: WPS612 useless overwritten __init__
        self, nested_termlist: List[PolyhedralTermList], force_empty_intersection: bool
    ):
        """
        Class constructor.

        Args:
            nested_termlist: A list of terms contained by TermList.
            force_empty_intersection: Raise error if the termlists are not disjoint.
        """
        super().__init__(nested_termlist, force_empty_intersection)


class PolyhedralIoContractCompound(IoContractCompound):
    """
    Compound IO contract with polyhedral assumptions and guarantees.

    Attributes:
        inputvars:
            Variables which are inputs of the implementations of the contract.

        outputvars:
            Variables which are outputs of the implementations of the contract.

        a: Contract assumptions.

        g: Contract guarantees.
    """

    @staticmethod
    def from_strings(
        assumptions: List[list[str]],
        guarantees: List[list[str]],
        input_vars: List[str],
        output_vars: List[str],
    ) -> PolyhedralIoContractCompound:
        """
        Create contract from several lists of strings.

        Args:
            assumptions: contract's assumptions.
            guarantees: contract's guarantees.
            input_vars: input variables of contract.
            output_vars: output variables of contract.

        Returns:
            A polyhedral contract built from the arguments provided.
        """
        a: List[PolyhedralTermList] = []
        if assumptions:
            for termlist_str in assumptions:
                a_termlist = [item for x in termlist_str for item in serializer.polyhedral_termlist_from_string(x)]
                a.append(PolyhedralTermList(a_termlist))

        g: List[PolyhedralTermList] = []
        if guarantees:
            for termlist_str in guarantees:
                g_termlist = [item for x in termlist_str for item in serializer.polyhedral_termlist_from_string(x)]
                g.append(PolyhedralTermList(g_termlist))

        return PolyhedralIoContractCompound(
            input_vars=[Var(x) for x in input_vars],
            output_vars=[Var(x) for x in output_vars],
            assumptions=NestedPolyhedra(a, force_empty_intersection=True),
            guarantees=NestedPolyhedra(g, force_empty_intersection=False),
        )

    def to_dict(self) -> dict:
        """
        Map contract into a user-readable dictionary.

        Returns:
            A dictionary containing the contract's information.
        """
        c_temp = {}
        c_temp["input_vars"] = [str(x) for x in self.inputvars]
        c_temp["output_vars"] = [str(x) for x in self.outputvars]
        c_temp["assumptions"] = [x.to_str_list() for x in self.a.nested_termlist]
        c_temp["guarantees"] = [x.to_str_list() for x in self.g.nested_termlist]
        return c_temp
