from __future__ import annotations

from dataclasses import field
from functools import reduce
from typing import List

import pacti.terms.polyhedra.serializer as serializer
from pacti.iocontract import IoContract, Var, IoContractCompound, NestedTermList
from pacti.terms.polyhedra.polyhedra import PolyhedralTerm, PolyhedralTermList


class PolyhedralContract(IoContract):
    def __init__(
        self,
        assumptions: PolyhedralTermList,
        guarantees: PolyhedralTermList,
        input_vars: List[Var],
        output_vars: List[Var],
    ) -> None:
        super().__init__(assumptions, guarantees, input_vars, output_vars)

    def rename_variables(self, variable_mappings: list[tuple[str, str]]) -> IoContract:
        new_contract = self.copy()
        for mapping in variable_mappings:
            new_contract = new_contract.rename_variable(Var(mapping[0]), Var(mapping[1]))
        return new_contract

    @staticmethod
    def from_string(
        assumptions: list[str] = field(default_factory=list),
        guarantees: list[str] = field(default_factory=list),
        InputVars: list[str] = field(default_factory=list),
        OutputVars: list[str] = field(default_factory=list),
    ) -> PolyhedralContract:
        a: list[PolyhedralTerm] = []
        if assumptions:
            a = reduce(list.__add__, list(map(lambda x: serializer.internal_pt_from_string(x), assumptions)))

        g: list[PolyhedralTerm] = []
        if guarantees:
            g = reduce(list.__add__, list(map(lambda x: serializer.internal_pt_from_string(x), guarantees)))

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



class NestedPolyhedra(NestedTermList):
    def __init__(self, nested_termlist: list[PolyhedralTermList]):
        super().__init__(nested_termlist)

class PolyhedralContractCompound(IoContractCompound):
    def __init__(self, assumptions: NestedPolyhedra, guarantees: NestedPolyhedra, input_vars: List[Var], output_vars: List[Var]):
        super().__init__(assumptions, guarantees, input_vars, output_vars)

    @staticmethod
    def from_string(
        assumptions: list[list[str]] = field(default_factory=list),
        guarantees: list[list[str]] = field(default_factory=list),
        InputVars: list[str] = field(default_factory=list),
        OutputVars: list[str] = field(default_factory=list),
    ) -> PolyhedralContractCompound:
        a: list[PolyhedralTermList] = []
        if assumptions:
            for termlist_str in assumptions:
                a_termlist = reduce(list.__add__, list(map(lambda x: serializer.internal_pt_from_string(x), termlist_str)))
                a.append(PolyhedralTermList(a_termlist))

        g: list[PolyhedralTermList] = []
        if guarantees:
            for termlist_str in guarantees:
                g_termlist = reduce(list.__add__, list(map(lambda x: serializer.internal_pt_from_string(x), termlist_str)))
                g.append(PolyhedralTermList(g_termlist))

        return PolyhedralContractCompound(
            input_vars=[Var(x) for x in InputVars],
            output_vars=[Var(x) for x in OutputVars],
            assumptions=NestedPolyhedra(a),
            guarantees=NestedPolyhedra(g),
        )

    