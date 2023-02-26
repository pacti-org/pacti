from __future__ import annotations

from functools import reduce
from typing import Optional

import pacti.terms.polyhedra.serializer as serializer
from pacti.iocontract import IoContract, IoContractCompound, NestedTermList, Var
from pacti.terms.polyhedra.polyhedra import PolyhedralTerm, PolyhedralTermList


class PolyhedralContract(IoContract):
    def rename_variables(self, variable_mappings: list[tuple[str, str]]) -> IoContract:
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

    def compose(self, other: PolyhedralContract, vars_to_keep: Optional[list[str]] = None):
        if vars_to_keep is None:
            vars_to_keep = []
        return super().compose(other, [Var(x) for x in vars_to_keep])


class NestedPolyhedra(NestedTermList):
    def __init__(self, nested_termlist: list[PolyhedralTermList]):  # noqa: WPS612 useless overwritten __init__
        super().__init__(nested_termlist)


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
            assumptions=NestedPolyhedra(a),
            guarantees=NestedPolyhedra(g),
        )
