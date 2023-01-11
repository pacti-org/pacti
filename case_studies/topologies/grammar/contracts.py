from __future__ import annotations
import itertools
from dataclasses import dataclass, field

from gear.iocontract import IoContract


@dataclass
class ContractsAlternatives:
    contracts: set[IoContract] = field(default_factory=set)

    def __le__(self, other: IoContract | ContractsAlternatives) -> bool:
        """Checking refinement with an IoContract"""
        if isinstance(other, IoContract):
            return self.refines_io_contract(other)
        else:
            for contract in other.contracts:
                if self.refines_io_contract(contract):
                    return True
        return False

    def refines_io_contract(self, other: IoContract):
        for c in self.contracts:
            """Equalizing inputs/outputs symbols"""
            ins_eq = list(set(c.inputvars) | set(other.inputvars))
            outs_eq = list(set(c.outputvars) | set(other.outputvars))
            c.inputvars = ins_eq
            c.outputvars = outs_eq
            other.inputvars = ins_eq
            other.outputvars = outs_eq
            if c <= other:
                return True
        return False

    def __hash__(self):
        all_hashes = []
        for c in self.contracts:
            all_hashes = c.__hash__()
        return hash(all_hashes)

