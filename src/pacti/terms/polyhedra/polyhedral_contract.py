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
    def readFromString(
        assumptions: list[str] = field(default_factory=list),
        guarantees: list[str] = field(default_factory=list),
        InputVars: list[str] = field(default_factory=list),
        OutputVars: list[str] = field(default_factory=list)) -> PolyhedralContract:
        
        if assumptions:
            a: list[PolyhedralTerm] = reduce(list.__add__, list(map(lambda x: serializer.pt_from_string(x), assumptions)))
        else:
            a: list[PolyhedralTerm] = []

        if guarantees:
            g: list[PolyhedralTerm] = reduce(list.__add__, list(map(lambda x: serializer.pt_from_string(x), guarantees)))
        else:
            g: list[PolyhedralTerm] = []

        return PolyhedralContract(
            input_vars=[Var(x) for x in InputVars],
            output_vars=[Var(x) for x in OutputVars],
            assumptions=PolyhedralTermList(a),
            guarantees=PolyhedralTermList(g))
        
    @staticmethod
    def readFromDict(
        contract: dict) -> PolyhedralContract:
        if not isinstance(contract, dict):
            raise ValueError("A dict type contract is expected.")
        
        return PolyhedralContract(
            input_vars=[Var(x) for x in contract["InputVars"]],
            output_vars=[Var(x) for x in contract["OutputVars"]],
            assumptions=PolyhedralContract.read_polyhedralTermList("Assumptions", contract["assumptions"]),
            guarantees=PolyhedralContract.read_polyhedralTermList("Guarantees", contract["guarantees"]),
        )
    
    @staticmethod
    def read_polyhedralTermList(kind: str, l: list[dict]) -> PolyhedralTermList:
        if all(isinstance(x, dict) for x in l):
            return PolyhedralTermList(list(PolyhedralTerm(x["coefficients"], float(x["constant"])) for x in l))
        else:
            raise ValueError(f"{kind} must be either a list of dicts or strings.")
   