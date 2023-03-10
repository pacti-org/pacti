"""Some list operations."""

from typing import Any


def list_intersection(list1: list[Any], list2: list[Any]) -> list[Any]:
    """
    Intersect two lists.

    Args:
        list1: First argument.
        list2: Second argument.

    Returns:
        A list containing the intersection of both lists.
    """
    return [el for el in list1 if el in list2]


def list_diff(list1: list[Any], list2: list[Any]) -> list[Any]:
    """
    Compute difference between lists.

    Args:
        list1: First argument.
        list2: Second argument.

    Returns:
        A list containing the elements of the first argument which do not belong to the second.
    """
    return [el for el in list1 if (el not in list2)]


def list_union(list1: list[Any], list2: list[Any]) -> list[Any]:
    """
    Compute the union of two lists.

    Args:
        list1: First argument.
        list2: Second argument.

    Returns:
        A list containing the elements that at least one list contains.
    """
    return list1 + [el for el in list2 if (el not in list1)]


def lists_equal(list1: list[Any], list2: list[Any]) -> bool:
    """
    Tells whether two lists have the same elements.

    Args:
        list1: First argument.
        list2: Second argument.

    Returns:
        True if the lists are equal element-wise.
    """
    return (len(list_diff(list1, list2)) == 0) and (len(list_diff(list2, list1)) == 0)
