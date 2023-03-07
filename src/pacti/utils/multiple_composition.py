"""Support for multiple composition."""
from __future__ import annotations

from typing import Any, Dict

from pacti.iocontract import IoContract


class _Tree:
    def __init__(self, data: Any = None):
        self.data = data
        self.children: set[Any] = set()

    def add_child(self, child: _Tree) -> None:
        self.children.add(child)

    def get_leafs(self) -> set[_Tree]:
        leafs = set()
        if self.children:
            for child in self.children:
                leafs.update(child.get_leafs())
        else:
            leafs.add(self)
        return leafs

    def remove_node(self, leaf: Any) -> None:
        if not self.children:
            return
        if leaf in self.children:
            self.children.remove(leaf)
            return
        for child in self.children:
            child.remove_node(leaf)

    def print_tree(self, level: int = 0, is_last_sibling: bool = True) -> None:
        prefix = "    " * level
        if is_last_sibling:
            prefix += "`-- "
        else:
            prefix += "|-- "
        print(prefix + str(self.data))
        for i, child in enumerate(self.children):
            is_last_child = i == len(self.children) - 1
            child.print_tree(level + 1, is_last_child)


def _build_dependency_tree(symbol_dict: Dict) -> _Tree:  # noqa: WPS231 too much cognitive complexity
    root = _Tree()
    symbol_nodes = {}
    for symbol, value in symbol_dict.items():
        inputs, outputs = value
        if symbol not in symbol_nodes:
            symbol_nodes[symbol] = _Tree(symbol)
            root.add_child(symbol_nodes[symbol])
        for output in outputs:
            for dependency, dep_values in symbol_dict.items():
                if output in dep_values[0]:
                    if dependency not in symbol_nodes:
                        symbol_nodes[dependency] = _Tree(dependency)
                        # root.add_child(symbol_nodes[dependency])
                    symbol_nodes[symbol].add_child(symbol_nodes[dependency])
    return root


def compose_multiple_contracts(contracts: list[IoContract]) -> IoContract:
    """
    Compose several contracts, finding the right order to compose them.

    Args:
        contracts: list of contracts to be composed.

    Returns:
        A contract corresponding to the ordered composition of the given contracts.
    """
    symbol_dict: dict[str, tuple[list[str], list[str]]] = {}  # noqa: WPS234 complex annotation
    contracts_dict = {}
    for i, contract in enumerate(contracts):
        input_symbols = [v.name for v in contract.inputvars]
        output_symbols = [v.name for v in contract.outputvars]
        symbol_dict[f"c{i}"] = (input_symbols, output_symbols)
        contracts_dict[f"c{i}"] = contract

    dependency_tree: _Tree = _build_dependency_tree(symbol_dict)
    leaf = dependency_tree.get_leafs().pop()
    main_contract = contracts_dict[leaf.data]
    dependency_tree.remove_node(leaf)
    while dependency_tree is not None:
        leaf = dependency_tree.get_leafs().pop()
        if leaf.data is None:
            break
        main_contract.compose(contracts_dict[leaf.data])
        dependency_tree.remove_node(leaf)

    return main_contract
