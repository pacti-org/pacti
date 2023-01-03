from collections import Counter

from case_studies.topologies.grammar import Grammar


def get_clusters_consecutive_integers(list_of_integers: list[int]) -> list[tuple[int]]:
    low_bound = sorted(list_of_integers)[0]
    high_bound = sorted(list_of_integers)[-1]

    clusters = []
    previous_element = low_bound
    current_cluster = [low_bound, high_bound]
    for current_element in sorted(list_of_integers)[1:]:
        if not current_element == previous_element + 1:
            current_cluster[1] = previous_element
            clusters.append(tuple(current_cluster))
            current_cluster[0] = current_element
            current_cluster[1] = high_bound
        previous_element = current_element

    clusters.append(tuple(current_cluster))
    return clusters


def get_best_direction_assignment(grammar: Grammar) -> dict[str, int]:
    direction_set_stats = Counter()
    direction_single_stats = Counter()
    for rule in grammar.rules:
        for symbol in rule.conditions.get_all_symbol_types():
            all_directions = rule.conditions.get_all_directions_where_is_symbol(symbol)
            direction_key = "-".join(sorted(list(all_directions)))
            if direction_key not in direction_set_stats.keys():
                direction_set_stats[direction_key] = 0
            direction_set_stats[direction_key] += 1
            for direction in all_directions:
                if direction not in direction_single_stats.keys():
                    direction_single_stats[direction] = 0
                direction_single_stats[direction] += 1

    direction_single_stats_ordered = direction_single_stats.most_common()

    best_assignment = {}

    for i, (key, occurrences) in enumerate(direction_single_stats_ordered):
        best_assignment[key] = i
        # print(f"{key}\t{occurrences}")

    return best_assignment


if __name__ == '__main__':
    get_clusters_consecutive_integers([0, 1, 2, 3, 4, 5])
    get_clusters_consecutive_integers([0, 1, 2, 4, 5])
    get_clusters_consecutive_integers([1, 2, 4, 5])
    get_clusters_consecutive_integers([5])
