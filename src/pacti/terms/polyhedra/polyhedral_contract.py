from __future__ import annotations
from typing import List
from functools import reduce
from dataclasses import field
from pacti.iocontract import IoContract, Var
from pacti.terms.polyhedra.polyhedra import PolyhedralTerm, PolyhedralTermList

import pacti.terms.polyhedra.serializer as serializer

class PolyhedralContract(IoContract):

    def __init__(
        self, assumptions: PolyhedralTermList, guarantees: PolyhedralTermList, input_vars: List[Var], output_vars: List[Var]
    ) -> None:
        super().__init__(assumptions, guarantees, input_vars, output_vars)
        
    @staticmethod
    def from_string(
        assumptions: list[str] = field(default_factory=list),
        guarantees: list[str] = field(default_factory=list),
        InputVars: list[str] = field(default_factory=list),
        OutputVars: list[str] = field(default_factory=list)) -> PolyhedralContract:
        
        if assumptions:
            a: list[PolyhedralTerm] = reduce(list.__add__, list(map(lambda x: serializer.internal_pt_from_string(x), assumptions)))
        else:
            a: list[PolyhedralTerm] = []

        if guarantees:
            g: list[PolyhedralTerm] = reduce(list.__add__, list(map(lambda x: serializer.internal_pt_from_string(x), guarantees)))
        else:
            g: list[PolyhedralTerm] = []

        return PolyhedralContract(
            input_vars=[Var(x) for x in InputVars],
            output_vars=[Var(x) for x in OutputVars],
            assumptions=PolyhedralTermList(a),
            guarantees=PolyhedralTermList(g))
        
    @staticmethod
    def from_dict(
        contract: dict) -> PolyhedralContract:
        if not isinstance(contract, dict):
            raise ValueError("A dict type contract is expected.")
        
        if all(isinstance(x, dict) for x in contract["assumptions"]):
            a = PolyhedralTermList(list(PolyhedralTerm(x["coefficients"], float(x["constant"])) for x in contract["assumptions"]))
        else:
            raise ValueError(f"Assumptions must be a list of dicts.")
        
        if all(isinstance(x, dict) for x in contract["guarantees"]):
            g = PolyhedralTermList(list(PolyhedralTerm(x["coefficients"], float(x["constant"])) for x in contract["guarantees"]))
        else:
            raise ValueError(f"Guarantees must be a list of dicts.")
        
        return PolyhedralContract(
            input_vars=[Var(x) for x in contract["InputVars"]],
            output_vars=[Var(x) for x in contract["OutputVars"]],
            assumptions=a,
            guarantees=g)
