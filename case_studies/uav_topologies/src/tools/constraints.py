import itertools

from ..shared import Direction, DirectionsAssignment, SymbolType, symbols_short_in
from ..tools.analysis import get_clusters_consecutive_integers


def constraint_str_between_integers(symbol: str, cluster: tuple[int, int]) -> list[str]:
    if cluster[1] < cluster[0]:
        raise AttributeError("Not valid interval")
    constraints = []
    if cluster[0] > 0:
        constraints.append(constraint_str_greater_eq_than(symbol, cluster[0]))
    constraints.append(constraint_str_less_eq_than(symbol, cluster[1]))

    return constraints


def constraint_str_greater_eq_than(symbol: str, n: int) -> str:
    return f"-1 * {symbol} <= -{n}"


def constraint_str_less_eq_than(symbol: str, n: int) -> str:
    return f"{symbol} <= {n}"


def from_symbol_directions_to_constraints(
    symbol_dirs: dict[SymbolType, set[Direction]]
) -> tuple[list[list[str]], set[str]]:
    """
    Convert a dictionary of symbol_types -> directions into linear constraints

        Args:
            symbol_dirs:
                dictionary mapping SymbolType to list od Direction

        Returns:
            Tuple where the first elements is a list of list of constraints (str),
            and the second element is the set of symbols used (str)

    """

    symbols: set[str] = set()

    assignment = DirectionsAssignment().data
    # print(assignment)

    dir_constraints: list[list[str]] = []
    for symbol, all_directions in symbol_dirs.items():
        sym_constraints: list[list[str]] = []
        all_directions_ints = list(map(lambda x: assignment[x], all_directions))
        clusters = get_clusters_consecutive_integers(all_directions_ints)
        symbol = f"{symbols_short_in(symbol)}"
        symbols.add(symbol)
        for cluster in clusters:
            sym_constraints.append(constraint_str_between_integers(symbol, cluster))
        dir_constraints.append(sym_constraints)

    or_constraints = list(itertools.product(*dir_constraints))

    constraints: list[list[[str]]] = []

    for or_constraint in or_constraints:
        constraints.append([item for sublist in or_constraint for item in sublist])

    return constraints, symbols

    # or_assumptions = list(itertools.product(*assumptions))
    # new_assumptions_or: list[list[str]] = []
    #
    # all_short_symbols = {f"{symbols_short_in(symbol)}" for symbol in all_symbols_types}
    # # missing_symbols = all_short_symbols - input_symbols
    # # saturation_constraints = []
    # # for s in missing_symbols:
    # #     saturation_constraints.append(constraint_str_between_integers(s, (0, 0))[0])
    # for a in or_assumptions:
    #     new_assumptions = []
    #     for elem_list in a:
    #         new_assumptions.extend(elem_list)
    #     # new_assumptions.extend(saturation_constraints)
    #     new_assumptions_or.append(new_assumptions)
