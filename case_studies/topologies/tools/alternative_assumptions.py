import itertools

from case_studies.topologies.grammar import symbols_short_in, constraint_str_between_integers
from case_studies.topologies.grammar.symbols import all_symbols_types
from case_studies.topologies.tools.analysis import get_clusters_consecutive_integers


def get_alternative_assumptions(assignment: dict, get_all_symbol_types_and_directions: dict) \
        -> tuple[list[list[str]], set]:
    assumptions: list[list[list[[str]]]] = []
    input_symbols = set()

    for symbol, all_directions in get_all_symbol_types_and_directions.items():
        a_symbol = []
        all_directions_ints = list(map(lambda x: assignment[x], all_directions))
        clusters = get_clusters_consecutive_integers(all_directions_ints)
        input_symbol = f"{symbols_short_in(symbol)}"
        input_symbols.add(input_symbol)
        for cluster in clusters:
            a_symbol.append(constraint_str_between_integers(input_symbol, cluster))
        assumptions.append(a_symbol)

    or_assumptions = list(itertools.product(*assumptions))
    new_assumptions_or: list[list[str]] = []

    all_short_symbols = {f"{symbols_short_in(symbol)}" for symbol in all_symbols_types}
    # missing_symbols = all_short_symbols - input_symbols
    # saturation_constraints = []
    # for s in missing_symbols:
    #     saturation_constraints.append(constraint_str_between_integers(s, (0, 0))[0])
    for a in or_assumptions:
        new_assumptions = []
        for elem_list in a:
            new_assumptions.extend(elem_list)
        # new_assumptions.extend(saturation_constraints)
        new_assumptions_or.append(new_assumptions)

    return new_assumptions_or, input_symbols
