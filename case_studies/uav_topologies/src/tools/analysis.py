def get_clusters_consecutive_integers(list_int: list[int]) -> list[tuple[int, int]]:
    """
    Given a list of integers "list_int" as input produces a list of intervals
    where each integer in the interval is contained in "list_int"
    """

    list_int.sort()
    intervals = []
    start = list_int[0]
    end = list_int[0]
    for i in range(1, len(list_int)):
        if list_int[i] == end + 1:
            end = list_int[i]
        else:
            intervals.append((start, end))
            start = list_int[i]
            end = list_int[i]
    intervals.append((start, end))

    return intervals
