"""
top_movers.py
--------------
Data structure used: HEAP / PRIORITY QUEUE (heapq), satisfying the
"heap / priority queue OR balanced tree" requirement explicitly (kept
separate from the rolling-metrics deque, which solves a different
problem: sliding-window max/min rather than whole-market top-k).

Use case: "show me the top K gainers and top K losers today across
the whole market" -- given the % change of every symbol, we want the
K largest and K smallest values without sorting the entire list.

heapq.nlargest / nsmallest internally maintain a heap of size K, giving:

Complexity
----------
top_k_gainers / top_k_losers:  O(n log k)   where n = number of symbols,
                                             k = requested top-k count
(compare to O(n log n) for a full sort when k << n)
"""

import heapq
from dataclasses import dataclass
from typing import List

from src.storage import StockDatabase


@dataclass
class Mover:
    symbol: str
    percent_change: float

    def __repr__(self):
        sign = "+" if self.percent_change >= 0 else ""
        return f"{self.symbol}: {sign}{self.percent_change:.2f}%"


def _percent_changes(db: StockDatabase) -> List[Mover]:
    movers = []
    for symbol in db.all_symbols():
        history = db.get_history(symbol)
        if len(history) < 2:
            continue  # need at least 2 points to compute a change
        start_price = history[0].price
        end_price = history[-1].price
        if start_price == 0:
            continue
        pct = ((end_price - start_price) / start_price) * 100
        movers.append(Mover(symbol, pct))
    return movers


def top_k_gainers(db: StockDatabase, k: int) -> List[Mover]:
    """O(n log k) via a size-k heap instead of sorting all n symbols."""
    movers = _percent_changes(db)
    return heapq.nlargest(k, movers, key=lambda m: m.percent_change)


def top_k_losers(db: StockDatabase, k: int) -> List[Mover]:
    movers = _percent_changes(db)
    return heapq.nsmallest(k, movers, key=lambda m: m.percent_change)
