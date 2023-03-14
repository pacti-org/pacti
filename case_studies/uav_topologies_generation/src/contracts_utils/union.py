from __future__ import annotations

from dataclasses import dataclass, field

from case_studies.uav_topologies_generation.src.contracts_utils.misc import get_equalized_alphabets
from pacti.iocontract import IoContract, Var
from pacti.utils.lists import list_intersection, list_union


def check_variables_containment(contract_1: IoContract, contract_2: IoContract):
    """Returns True if all variables in contract_1 are also in contract_2"""
    for v in contract_1.vars:
        if v not in contract_2.vars:
            return False
    return True


@dataclass
class ContractsUnions:
    """Store a set of IoContracts"""

    contracts: set[IoContract] = field(default_factory=set)
    name: str = ""

    def get_inverted(self) -> ContractsUnions:
        inverted_contracts = ContractsUnions(name=self.name)

        for contract in self.contracts:
            from pacti.terms.polyhedra import PolyhedralTermList

            new_contract = IoContract(
                assumptions=contract.g, guarantees=PolyhedralTermList(), output_vars=[], input_vars=contract.outputvars
            )
            inverted_contracts.contracts.add(new_contract)

        return inverted_contracts

    def __le__(self, other: IoContract | ContractsUnions) -> bool:
        """
        A ContractsUnions Cu refines a IoContract C' if any of the IoContracts in Cu refine C'
        A ContractsUnions Cu refines a ContractsUnions Cu' if any of the IoContracts in Cu refine any of the IoContracts in Cu'
        """

        for contract in self.contracts:
            if isinstance(other, IoContract):
                contract_eq, other_eq = get_equalized_alphabets(contract, other)
                if not contract_eq <= other_eq:
                    print("REFINEMENT NOT VERIFIED [1]")
                    print(self)
                    print("<=")
                    print(other)
                    return False
            else:
                """Each contract must refine at least one contract in other.contracts"""
                found = False
                for other_c in other.contracts:
                    contract_eq, other_c_eq = get_equalized_alphabets(contract, other_c)
                    print(contract_eq)
                    print(other_c_eq)
                    if contract_eq <= other_c_eq:
                        found = True
                        break
                if not found:
                    print("REFINEMENT NOT VERIFIED [2]")
                    print(self)
                    print("<=")
                    print(other)
                    return False
        print("REFINEMENT VERIFIED")
        print(self)
        print("<=")
        print(other)
        return True

    def __str__(self):
        assumptions = [str(c.a).replace("in", "").replace("1*", "") for c in self.contracts]
        guarantees = [str(c.g).replace("in", "").replace("1*", "") for c in self.contracts]
        a = "\t | \t".join(assumptions)
        g = "\t | \t".join(guarantees)
        return f"A: {a}\nG: {g}"

    def add(self, other: IoContract):
        self.contracts.add(other)

    # def _refines_at_least_one_io_contract(self, other: IoContract):
    #     for c in self.contracts:
    #         """Equalizing inputs/outputs symbols"""
    #
    #         vars_not_preset = False
    #         for v in c.vars:
    #             if v not in other.vars:
    #                 vars_not_preset = True
    #                 break
    #         if vars_not_preset:
    #             continue
    #
    #         # c_mod, other_mod = get_equalized_abstracted_contracts(c, other)
    #         c_mod, other_mod = get_equalized_alphabets(c, other)
    #
    #         if not isinstance(c, IoContract):
    #             raise AttributeError
    #         if not isinstance(other, IoContract):
    #             raise AttributeError
    #         try:
    #             refine = c_mod <= other_mod
    #         except Exception as e:
    #             writeContract(c, f"C_exc_lhs")
    #             writeContract(other, f"C_exc_rhs")
    #             raise e
    #         if not refine:
    #             return False
    #         # else:
    #         #     print("\t" + str(c_mod.g))
    #         #     print("\t" + str(other_mod.g) + "\n")
    #     print("All refine")
    #     return True

    def can_be_composed_with_old(self, other: ContractsUnions):
        """Returns true if any element of self can be composed with all the elements of other"""
        for c_self in self.contracts:
            next = False
            for c_other in other.contracts:
                try:
                    c = c_self.compose(c_other)
                    print("\n")
                    print(str(c_self.a).replace("in", "").replace("1*", ""))
                    print(str(c_other.g).replace("in", "").replace("1*", ""))
                    print("TRUE")
                except Exception as e:
                    print("\n")
                    print(str(c_self.a).replace("in", "").replace("1*", ""))
                    print(str(c_other.g).replace("in", "").replace("1*", ""))
                    print("FALSE")
                    next = True
                    break
            if next:
                continue
            else:
                return True
        return False

    def can_be_composed_with(self, other: ContractsUnions):
        """Returns true if every element of other can be composed with at least one the elements of self"""
        for c_other in other.contracts:
            next = False
            for c_self in self.contracts:
                try:
                    c_other.compose(c_self)
                    # print("\n")
                    # print(str(c_self.a).replace('in', '').replace('1*', ''))
                    # print(str(c_other.g).replace('in', '').replace('1*', ''))
                    # print("TRUE")
                    next = True
                    break
                except Exception as e:
                    pass
                    # print("\n")
                    # print(str(c_self.a).replace('in', '').replace('1*', ''))
                    # print(str(c_other.g).replace('in', '').replace('1*', ''))
                    # print("FALSE")
            if next:
                continue
            else:
                return False
        return True

    def get_relaxed(self, other: ContractsUnions) -> ContractsUnions:
        """Returns a new ContractsUnions that only contains variables also in 'other'"""
        new_contracts = ContractsUnions(name=self.name)

        allowed_ins = other.inputs
        allowed_out = other.outputs
        allowed_vars = list_union(other.inputs, other.outputs)

        for contract in self.contracts:
            new_ins = list_intersection(contract.inputvars, allowed_vars)
            new_out = list_intersection(contract.outputvars, allowed_vars)

            new_a = contract.a.get_terms_with_vars(new_ins)
            new_g = contract.g.get_terms_with_vars(new_out)

            new_io_contract = IoContract(assumptions=new_a, guarantees=new_g, input_vars=new_ins, output_vars=new_out)
            new_contracts.add(new_io_contract)

        return new_contracts

    @property
    def vars(self) -> list[Var]:
        c_vars = []
        for c in self.contracts:
            c_vars.extend(c.vars)
        return list(set(c_vars))

    @property
    def inputs(self) -> list[Var]:
        c_vars = []
        for c in self.contracts:
            c_vars.extend(c.inputvars)
        return c_vars

    @property
    def outputs(self) -> list[Var]:
        c_vars = []
        for c in self.contracts:
            c_vars.extend(c.outputvars)
        return c_vars

    def __hash__(self):
        all_hashes = []
        for c in self.contracts:
            all_hashes = c.__hash__()
        return hash(all_hashes)
