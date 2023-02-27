from __future__ import annotations

from pacti.iocontract import IoContract
from pacti.terms.polyhedra import PolyhedralContract


class Tree:
    """
    Helper class to build the dependency tree of the contracts involved in the composition
    """
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
        prefix = "    " * level
        if not is_last_sibling:
            prefix += "|-- "
        else:
            prefix += "`-- "
        print(prefix + str(self.data))
        for i, child in enumerate(self.children):
            is_last_child = i == len(self.children) - 1
            child.print_tree(level + 1, is_last_child)


def build_dependency_tree(symbol_dict: dict[str, tuple[list[str], list[str]]]) -> Tree:
    """
    Build the dependency tree

    Args:
        symbol_dict: dictionary of dependencies.
                    Key: string; Value: tuple where each element is a list of strings.
                    The tuple represent input/output of the contract in the key.

    Returns:
        Dependency Tree
    """

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
    """
    Composition of multiple contracts

    Args:
        contracts: list of IoContract

    Returns:
        IoContract representing the composition of 'contracts'
    """
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
        main_contract.compose(contracts_dict[leaf.data])
        dependency_tree.remove_node(leaf)

    return main_contract


if __name__ == "__main__":
    c1 = PolyhedralContract.from_string(
        assumptions=["x <= 1"], guarantees=["y <= 0"], InputVars=["x"], OutputVars=["y"]
    )
    c2 = PolyhedralContract.from_string(
        assumptions=["y <= 0"], guarantees=["z <= 0"], InputVars=["y"], OutputVars=["z"]
    )
    c3 = PolyhedralContract.from_string(
        assumptions=["y <= 0"], guarantees=["q <= 0"], InputVars=["y"], OutputVars=["q"]
    )
    c4 = PolyhedralContract.from_string(
        assumptions=["q <= 0"], guarantees=["v <= 0"], InputVars=["q"], OutputVars=["v"]
    )
    c5 = PolyhedralContract.from_string(
        assumptions=["y <= 0"], guarantees=["v <= 0"], InputVars=["y"], OutputVars=["v"]
    )

    contract = composing_multiple_contracts([c1, c2, c3, c4, c5])
    print(contract)
