def list_intersection(list1, list2):
    return [el for el in list1 if el in list2]


def list_diff(list1, list2):
    return [el for el in list1 if not (el in list2)]


def list_union(list1, list2):
    return list1 + [el for el in list2 if not (el in list1)]


def lists_equal(list1, list2):
    return (len(list_diff(list1, list2)) == 0) & (len(list_diff(list2, list1)) == 0)
