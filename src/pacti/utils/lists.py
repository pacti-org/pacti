def list_intersection(list1: list, list2: list) -> list:
    return [el for el in list1 if el in list2]


def list_diff(list1: list, list2: list) -> list:
    return [el for el in list1 if (el not in list2)]


def list_union(list1: list, list2: list) -> list:
    return list1 + [el for el in list2 if (el not in list1)]


def lists_equal(list1: list, list2: list) -> bool:
    return (len(list_diff(list1, list2)) == 0) and (len(list_diff(list2, list1)) == 0)
