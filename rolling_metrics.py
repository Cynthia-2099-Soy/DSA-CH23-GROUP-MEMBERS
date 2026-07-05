"""
rolling_metrics.py
-------------------
Data structure used: DEQUE (monotonic deque), acting as the project's
heap/priority-queue-equivalent requirement.

Design note (documented for the report's "Bottlenecks" section):
A naive way to get rolling max/min over the last N prices is to keep
a max-heap and a min-heap of the window and lazily evict stale entries.
That works, but each insertion/eviction costs O(log n) and the heap
carries entries far outside the current window until they bubble out.

A MONOTONIC DEQUE gives the same rolling max/min in O(1) amortized per
tick, because it only ever keeps candidates that could still become the
max/min later -- anything a new tick outclasses is popped immediately.
We therefore implement rolling max/min with two deques, and keep the
rolling average with a running sum, and explicitly discuss both
approaches (heap vs deque) in the design report as the tradeoff
justifying this data-structure choice.

Complexity
----------
add_price:            O(1) amortized (each element pushed & popped once)
current_max/min/avg:  O(1)
"""

from collections import deque
from typing import Optional


class RollingWindowMetrics:
    def __init__(self, window_size: int):
        if window_size <= 0:
            raise ValueError("window_size must be a positive integer")
        self.window_size = window_size

        self._values: deque[float] = deque()        # raw window values, FIFO
        self._max_deque: deque[float] = deque()      # monotonically decreasing
        self._min_deque: deque[float] = deque()      # monotonically increasing
        self._running_sum: float = 0.0

    def add_price(self, price: float) -> None:
        # 1. Evict the oldest value if the window is already full
        if len(self._values) == self.window_size:
            oldest = self._values.popleft()
            self._running_sum -= oldest
            if self._max_deque and self._max_deque[0] == oldest:
                self._max_deque.popleft()
            if self._min_deque and self._min_deque[0] == oldest:
                self._min_deque.popleft()

        # 2. Add the new value
        self._values.append(price)
        self._running_sum += price

        # 3. Maintain the monotonic max deque (pop smaller trailing values)
        while self._max_deque and self._max_deque[-1] < price:
            self._max_deque.pop()
        self._max_deque.append(price)

        # 4. Maintain the monotonic min deque (pop larger trailing values)
        while self._min_deque and self._min_deque[-1] > price:
            self._min_deque.pop()
        self._min_deque.append(price)

    def current_max(self) -> Optional[float]:
        return self._max_deque[0] if self._max_deque else None

    def current_min(self) -> Optional[float]:
        return self._min_deque[0] if self._min_deque else None

    def current_avg(self) -> Optional[float]:
        if not self._values:
            return None
        return self._running_sum / len(self._values)

    def __len__(self) -> int:
        return len(self._values)
