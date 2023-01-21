from __future__ import annotations

from dataclasses import dataclass, field

from pacti.iocontract import IoContract
from pacti.terms.polyhedra import writeContract


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

            print(c)
            print("<=")
            print(other)

            if not isinstance(c, IoContract):
                raise AttributeError
            if not isinstance(other, IoContract):
                raise AttributeError
            try:
                refine = c <= other
            except Exception as e :
                writeContract(c, f"C_exc_lhs")
                writeContract(other, f"C_exc_rhs")
                raise e
            # if c <= other:
            #     seed = random.choice(string.ascii_letters)
            #     writeContract(c, f"C{seed}_lhs")
            #     writeContract(other, f"C{seed}_rhs")
            #     return True
            if refine:
                return True
        return False

    def __hash__(self):
        all_hashes = []
        for c in self.contracts:
            all_hashes = c.__hash__()
        return hash(all_hashes)

