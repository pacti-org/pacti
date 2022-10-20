def list_intersection(list1, list2):
    return [el for el in list1 if el in list2]


def list_diff(list1, list2):
    return [el for el in list1 if not (el in list2)]


def list_union(list1, list2):
    return list1 + [el for el in list2 if not (el in list1)]
