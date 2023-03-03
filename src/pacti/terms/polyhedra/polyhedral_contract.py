"""Specializes IO contract into contracts with polyhedral assumptions and guarantees."""

from __future__ import annotations

from typing import Optional

from pacti.iocontract import IoContract, IoContractCompound, NestedTermList, Var
from pacti.terms.polyhedra import serializer
from pacti.terms.polyhedra.polyhedra import PolyhedralTerm, PolyhedralTermList


class PolyhedralContract(IoContract):
    def rename_variables(self, variable_mappings: list[tuple[str, str]]) -> PolyhedralContract:
        new_contract = self.copy()
        for mapping in variable_mappings:
            new_contract = new_contract.rename_variable(Var(mapping[0]), Var(mapping[1]))
        return new_contract

    def to_machine_dict(self):
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
        if vars_to_keep is None:
            vars_to_keep = []
        return super().compose(other, [Var(x) for x in vars_to_keep])

    def optimize(self, expr: str, maximize: bool = True):
        new_expr = expr + " <= 0"
        variables = serializer.internal_pt_from_string(new_expr)[0].variables
        constraints: PolyhedralTermList = self.a | self.g
        return constraints.optimize(objective=variables, maximize=maximize)

    def get_variable_bounds(self, var: str):  # noqa: VNE002 variable 'var' should be clarified
        maximum = self.optimize(var, maximize=True)
        minimum = self.optimize(var, maximize=False)
        return minimum, maximum


class NestedPolyhedra(NestedTermList):
    def __init__(self, nested_termlist: list[PolyhedralTermList]):  # noqa: WPS612 useless overwritten __init__
        super().__init__(nested_termlist)


class PolyhedralContractCompound(IoContractCompound):
    @staticmethod
    def from_string(
        assumptions: list[list[str]],
        guarantees: list[list[str]],
        input_vars: list[str],
        output_vars: list[str],
    ) -> PolyhedralContractCompound:
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
            assumptions=NestedPolyhedra(a),
            guarantees=NestedPolyhedra(g),
        )
