"""Specializes IO contract into contracts with polyhedral assumptions and guarantees."""

from __future__ import annotations

from typing import Optional, Tuple, Union

from pacti.iocontract import IoContract, IoContractCompound, NestedTermList, Var
from pacti.terms.polyhedra import serializer
from pacti.terms.polyhedra.polyhedra import PolyhedralTerm, PolyhedralTermList

numeric = Union[int, float]


class PolyhedralContract(IoContract):
    """IO Contracts with assumptions and guarantees expressed as polyhedral constraints."""

    def rename_variables(self, variable_mappings: list[tuple[str, str]]) -> PolyhedralContract:
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

    def to_machine_dict(self):
        """
        Map contract into a machine-optimized dictionary.

        Returns:
            A dictionary containing the contract's information.
        """
        c_temp = {}
        c_temp["input_vars"] = [str(x) for x in self.inputvars]
        c_temp["output_vars"] = [str(x) for x in self.outputvars]

        c_temp["assumptions"] = [
            {
                "constant": float(term.constant),
                "coefficients": {str(k): float(v) for k, v in term.variables.items()},
            }
            for term in self.a.terms
        ]

        c_temp["guarantees"] = [
            {
                "constant": float(term.constant),
                "coefficients": {str(k): float(v) for k, v in term.variables.items()},
            }
            for term in self.g.terms
        ]
        return c_temp

    def to_dict(self):
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
    def from_string(
        assumptions: list[str],
        guarantees: list[str],
        input_vars: list[str],
        output_vars: list[str],
    ) -> PolyhedralContract:
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
        a: list[PolyhedralTerm] = []
        if assumptions:
            a = [item for x in assumptions for item in serializer.internal_pt_from_string(x)]

        g: list[PolyhedralTerm] = []
        if guarantees:
            g = [item for x in guarantees for item in serializer.internal_pt_from_string(x)]

        return PolyhedralContract(
            input_vars=[Var(x) for x in input_vars],
            output_vars=[Var(x) for x in output_vars],
            assumptions=PolyhedralTermList(a),
            guarantees=PolyhedralTermList(g),
        )

    @staticmethod
    def from_dict(contract: dict) -> PolyhedralContract:
        """
        Create contract from a dictionary.

        Args:
            contract: a dictionary containing the contract's data.

        Returns:
            A polyhedral contract built from the arguments provided.

        Raises:
            ValueError: dictionary provided was not well-formed.
        """
        if not isinstance(contract, dict):
            raise ValueError("A dict type contract is expected.")

        if all(isinstance(x, dict) for x in contract["assumptions"]):
            a = PolyhedralTermList(
                [PolyhedralTerm(x["coefficients"], float(x["constant"])) for x in contract["assumptions"]]
            )
        else:
            raise ValueError("Assumptions must be a list of dicts.")

        if all(isinstance(x, dict) for x in contract["guarantees"]):
            g = PolyhedralTermList(
                [PolyhedralTerm(x["coefficients"], float(x["constant"])) for x in contract["guarantees"]]
            )
        else:
            raise ValueError("Guarantees must be a list of dicts.")

        return PolyhedralContract(
            input_vars=[Var(x) for x in contract["input_vars"]],
            output_vars=[Var(x) for x in contract["output_vars"]],
            assumptions=a,
            guarantees=g,
        )

    def compose(self, other: PolyhedralContract, vars_to_keep: Optional[list[str]] = None):
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

        Returns:
            The abstracted composition of the two contracts.
        """
        if vars_to_keep is None:
            vars_to_keep = []
        return super().compose(other, [Var(x) for x in vars_to_keep])

    def optimize(self, expr: str, maximize: bool = True):
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
        variables = serializer.internal_pt_from_string(new_expr)[0].variables
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
        self, nested_termlist: list[PolyhedralTermList], force_empty_intersection: bool
    ):
        """
        Class constructor.

        Args:
            nested_termlist: A list of terms contained by TermList.
            force_empty_intersection: Raise error if the termlists are not disjoint.
        """
        super().__init__(nested_termlist, force_empty_intersection)


class PolyhedralContractCompound(IoContractCompound):
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
    def from_string(
        assumptions: list[list[str]],
        guarantees: list[list[str]],
        input_vars: list[str],
        output_vars: list[str],
    ) -> PolyhedralContractCompound:
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
        a: list[PolyhedralTermList] = []
        if assumptions:
            for termlist_str in assumptions:
                a_termlist = [item for x in termlist_str for item in serializer.internal_pt_from_string(x)]
                a.append(PolyhedralTermList(a_termlist))

        g: list[PolyhedralTermList] = []
        if guarantees:
            for termlist_str in guarantees:
                g_termlist = [item for x in termlist_str for item in serializer.internal_pt_from_string(x)]
                g.append(PolyhedralTermList(g_termlist))

        return PolyhedralContractCompound(
            input_vars=[Var(x) for x in input_vars],
            output_vars=[Var(x) for x in output_vars],
            assumptions=NestedPolyhedra(a, force_empty_intersection=True),
            guarantees=NestedPolyhedra(g, force_empty_intersection=False),
        )
