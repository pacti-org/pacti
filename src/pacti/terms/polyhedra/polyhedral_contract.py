from __future__ import annotations

from functools import reduce
from typing import Optional

import pacti.terms.polyhedra.serializer as serializer
from pacti.iocontract import IoContract, IoContractCompound, NestedTermList, Var
from pacti.terms.polyhedra.polyhedra import PolyhedralTerm, PolyhedralTermList


class PolyhedralContract(IoContract):
    def rename_variables(self, variable_mappings: list[tuple[str, str]]) -> PolyhedralContract:
        new_contract = self.copy()
        for mapping in variable_mappings:
            new_contract = new_contract.rename_variable(Var(mapping[0]), Var(mapping[1]))
        return new_contract

    @staticmethod
    def from_string(
        assumptions: list[str],
        guarantees: list[str],
        InputVars: list[str],
        OutputVars: list[str],
    ) -> PolyhedralContract:
        a: list[PolyhedralTerm] = []
        if assumptions:
            a = reduce(list.__add__, [serializer.internal_pt_from_string(x) for x in assumptions])

        g: list[PolyhedralTerm] = []
        if guarantees:
            g = reduce(list.__add__, [serializer.internal_pt_from_string(x) for x in guarantees])

        return PolyhedralContract(
            input_vars=[Var(x) for x in InputVars],
            output_vars=[Var(x) for x in OutputVars],
            assumptions=PolyhedralTermList(a),
            guarantees=PolyhedralTermList(g),
        )

    @staticmethod
    def from_dict(contract: dict) -> PolyhedralContract:
        if not isinstance(contract, dict):
            raise ValueError("A dict type contract is expected.")

        if all(isinstance(x, dict) for x in contract["assumptions"]):
            a = PolyhedralTermList(
                list(PolyhedralTerm(x["coefficients"], float(x["constant"])) for x in contract["assumptions"])
            )
        else:
            raise ValueError(f"Assumptions must be a list of dicts.")

        if all(isinstance(x, dict) for x in contract["guarantees"]):
            g = PolyhedralTermList(
                list(PolyhedralTerm(x["coefficients"], float(x["constant"])) for x in contract["guarantees"])
            )
        else:
            raise ValueError(f"Guarantees must be a list of dicts.")

        return PolyhedralContract(
            input_vars=[Var(x) for x in contract["InputVars"]],
            output_vars=[Var(x) for x in contract["OutputVars"]],
            assumptions=a,
            guarantees=g,
        )

    @staticmethod
    def from_file(file_name: str) -> list[PolyhedralContract]:
        return [PolyhedralContract.from_dict(cont) for cont in serializer.read_contract_dict_from_file(file_name)]

    def compose(self, other: PolyhedralContract, vars_to_keep: Optional[list[str]] = None):
        if vars_to_keep is None:
            vars_to_keep = []
        return super().compose(other, [Var(x) for x in vars_to_keep])

    def optimize(self, expr: str, maximize: bool = True):
        new_expr = expr + " <= 0"
        variables = serializer.internal_pt_from_string(new_expr)[0].variables
        constraints: PolyhedralTermList = self.a | self.g
        return constraints.optimize(objective=variables, maximize=maximize)

    def get_variable_bounds(self, var: str):
        max = self.optimize(var, True)
        min = self.optimize(var, False)
        return min, max


class NestedPolyhedra(NestedTermList):
    def __init__(self, nested_termlist: list[PolyhedralTermList], force_empty_intersection : bool):  # noqa: WPS612 useless overwritten __init__
        super().__init__(nested_termlist, force_empty_intersection)


class PolyhedralContractCompound(IoContractCompound):
    @staticmethod
    def from_string(
        assumptions: list[list[str]],
        guarantees: list[list[str]],
        InputVars: list[str],
        OutputVars: list[str],
    ) -> PolyhedralContractCompound:
        a: list[PolyhedralTermList] = []
        if assumptions:
            for termlist_str in assumptions:
                a_termlist = reduce(list.__add__, [serializer.internal_pt_from_string(x) for x in termlist_str])
                a.append(PolyhedralTermList(a_termlist))

        g: list[PolyhedralTermList] = []
        if guarantees:
            for termlist_str in guarantees:
                g_termlist = reduce(list.__add__, [serializer.internal_pt_from_string(x) for x in termlist_str])
                g.append(PolyhedralTermList(g_termlist))

        return PolyhedralContractCompound(
            input_vars=[Var(x) for x in InputVars],
            output_vars=[Var(x) for x in OutputVars],
            assumptions=NestedPolyhedra(a, force_empty_intersection=True),
            guarantees=NestedPolyhedra(g, force_empty_intersection=False)
        )
