from __future__ import annotations
from gear.iocontract import IoContract
from gear.terms.polyhedra import string_to_polyhedra_contract
from gear.utils.string_contract import StrContract


class Tree:
    def __init__(self, data=None):
        self.data = data
        self.children = set()

    def add_child(self, child: Tree):
        self.children.add(child)

    def get_leafs(self) -> set[Tree]:
        leafs = set()
        if not self.children:
            leafs.add(self)
        else:
            for child in self.children:
                leafs.update(child.get_leafs())
        return leafs

    def remove_node(self, leaf):
        if not self.children:
            return
        if leaf in self.children:
            self.children.remove(leaf)
            return
        for child in self.children:
            child.remove_node(leaf)

    def print_tree(self, level=0, is_last_sibling=True):
        prefix = '    ' * level
        if not is_last_sibling:
            prefix += '|-- '
        else:
            prefix += '`-- '
        print(prefix + str(self.data))
        for i, child in enumerate(self.children):
            is_last_child = i == len(self.children) - 1
            child.print_tree(level + 1, is_last_child)


def build_dependency_tree(symbol_dict):
    root = Tree()
    symbol_nodes = {}
    for symbol, value in symbol_dict.items():
        inputs, outputs = value
        if symbol not in symbol_nodes:
            symbol_nodes[symbol] = Tree(symbol)
            root.add_child(symbol_nodes[symbol])
        for output in outputs:
            for dependency, dep_values in symbol_dict.items():
                if output in dep_values[0]:
                    if dependency not in symbol_nodes:
                        symbol_nodes[dependency] = Tree(dependency)
                        # root.add_child(symbol_nodes[dependency])
                    symbol_nodes[symbol].add_child(symbol_nodes[dependency])
    return root


def composing_multiple_contracts(contracts: list[IoContract]) -> IoContract:
    symbol_dict: dict[str, tuple[list[str], list[str]]] = {}
    contracts_dict = {}
    for i, contract in enumerate(contracts):
        input_symbols = [v.name for v in contract.inputvars]
        output_symbols = [v.name for v in contract.outputvars]
        symbol_dict[f"c{i}"] = (input_symbols, output_symbols)
        contracts_dict[f"c{i}"] = contract

    dependency_tree: Tree = build_dependency_tree(symbol_dict)
    leaf = dependency_tree.get_leafs().pop()
    main_contract = contracts_dict[leaf.data]
    dependency_tree.print_tree()
    dependency_tree.remove_node(leaf)
    dependency_tree.print_tree()
    while dependency_tree is not None:
        leaf = dependency_tree.get_leafs().pop()
        print(main_contract)
        print("composing with")
        print(contracts_dict[leaf.data])
        main_contract.compose(contracts_dict[leaf.data])
        dependency_tree.remove_node(leaf)

    return main_contract


if __name__ == '__main__':
    c1 = StrContract(
        assumptions=["x <= 1"],
        guarantees=["y <= 0"],
        inputs=["x"],
        outputs=["y"]
    )
    c2 = StrContract(
        assumptions=["y <= 0"],
        guarantees=["z <= 0"],
        inputs=["y"],
        outputs=["z"]
    )
    c3 = StrContract(
        assumptions=["y <= 0"],
        guarantees=["q <= 0"],
        inputs=["y"],
        outputs=["q"]
    )
    c4 = StrContract(
        assumptions=["q <= 0"],
        guarantees=["v <= 0"],
        inputs=["q"],
        outputs=["v"]
    )
    c5 = StrContract(
        assumptions=["y <= 0"],
        guarantees=["v <= 0"],
        inputs=["y"],
        outputs=["v"]
    )
    """c1 relaxes the assumptions of both c2 and c3 => c2 and c3 must be composed first"""
    c1 = string_to_polyhedra_contract(c1)
    c2 = string_to_polyhedra_contract(c2)
    c3 = string_to_polyhedra_contract(c3)
    c4 = string_to_polyhedra_contract(c4)
    c5 = string_to_polyhedra_contract(c5)

    contract = composing_multiple_contracts([c1, c2, c3, c4, c5])
    print(contract)
