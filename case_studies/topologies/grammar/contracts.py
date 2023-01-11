from dataclasses import dataclass, field

from gear.iocontract import IoContract


@dataclass
class ContractsAlternatives:
    contracts: set[IoContract] = field(default_factory=set)

    def __le__(self, other: IoContract) -> bool:
        """Checking refinement with an IoContract"""
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
