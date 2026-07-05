"""
sorting.py
----------
Data structure/algorithm used: MERGE SORT (O(n log n) sort), one of the
two mandatory sorting/searching requirements (binary search, the other
requirement, lives in storage.py).

Used to sort a full day's closing prices across the market -- e.g. to
produce a "sorted by performance" leaderboard, or to sort a symbol's
own price history by value (rather than by date) for statistical
analysis.

Complexity
----------
merge_sort:  O(n log n) time, O(n) auxiliary space
"""

from typing import List, TypeVar

T = TypeVar("T")


def merge_sort(items: List[T], key=lambda x: x) -> List[T]:
    """Standard top-down merge sort. Stable, O(n log n)."""
    if len(items) <= 1:
        return list(items)

    mid = len(items) // 2
    left = merge_sort(items[:mid], key)
    right = merge_sort(items[mid:], key)
    return _merge(left, right, key)


def _merge(left: List[T], right: List[T], key) -> List[T]:
    merged: List[T] = []
    i = j = 0
    while i < len(left) and j < len(right):
        if key(left[i]) <= key(right[j]):
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1
    merged.extend(left[i:])
    merged.extend(right[j:])
    return merged
