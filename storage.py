"""
storage.py
----------
Core storage layer for the Stock Query Server.

Data structure used: HASH MAP (Python dict)
  - Maps symbol (str) -> a chronologically sorted list of PricePoint records.
  - Gives O(1) average-case lookup of "does this symbol exist" and
    O(1) access to a symbol's full price history reference.

Within each symbol's history, records are kept SORTED BY DATE so that
range queries can use BINARY SEARCH instead of a linear scan.

Complexity summary
-------------------
insert_tick (in-order append):      O(1) amortized
insert_tick (out-of-order insert):  O(log n) search + O(n) shift  (list insert)
get_price_on_date:                  O(log n)  (binary search)
get_price_range:                    O(log n + k)  where k = number of results
symbol_exists:                      O(1) average
"""

from bisect import bisect_left, insort
from dataclasses import dataclass
from datetime import date
from typing import List, Optional


@dataclass(order=True)
class PricePoint:
    trade_date: date
    price: float

    def __repr__(self):
        return f"PricePoint({self.trade_date.isoformat()}, {self.price})"


class SymbolNotFoundError(KeyError):
    """Raised when a query references a stock symbol that isn't in storage."""


class StockDatabase:
    """
    Hash map of symbol -> sorted list of PricePoint.

    This is the single source of truth the rest of the system (ingestion,
    rolling metrics, sorting/searching, graph) reads from and writes to.
    """

    def __init__(self):
        # symbol -> List[PricePoint] sorted by trade_date
        self._data: dict[str, List[PricePoint]] = {}
        # symbol -> sector, used later by the relationship graph
        self._sectors: dict[str, str] = {}

    def register_symbol(self, symbol: str, sector: str = "UNSPECIFIED") -> None:
        """Register a symbol so it exists in storage even with zero ticks."""
        symbol = symbol.upper()
        if symbol not in self._data:
            self._data[symbol] = []
        self._sectors[symbol] = sector

    def symbol_exists(self, symbol: str) -> bool:
        return symbol.upper() in self._data

    def insert_tick(self, symbol: str, trade_date: date, price: float) -> None:
        """
        Insert a price point for a symbol, maintaining sort order by date.

        Uses bisect.insort -> O(log n) to find position + O(n) worst case
        to shift elements. In real-market conditions ticks mostly arrive
        in order, so this is O(1) amortized (append) far more often than not.
        """
        symbol = symbol.upper()
        if symbol not in self._data:
            self.register_symbol(symbol)

        history = self._data[symbol]
        point = PricePoint(trade_date, price)

        if not history or history[-1].trade_date < trade_date:
            history.append(point)          # common case: in-order tick
        else:
            insort(history, point)         # rare case: late/out-of-order tick

    def get_history(self, symbol: str) -> List[PricePoint]:
        symbol = symbol.upper()
        if symbol not in self._data:
            raise SymbolNotFoundError(symbol)
        return self._data[symbol]

    def get_price_on_date(self, symbol: str, trade_date: date) -> Optional[float]:
        """Binary search for an exact date. O(log n)."""
        history = self.get_history(symbol)
        dates = [p.trade_date for p in history]
        i = bisect_left(dates, trade_date)
        if i < len(dates) and dates[i] == trade_date:
            return history[i].price
        return None

    def get_price_range(self, symbol: str, start: date, end: date) -> List[PricePoint]:
        """
        Return all points with start <= trade_date <= end.
        Two binary searches locate the window boundaries -> O(log n + k).
        """
        history = self.get_history(symbol)
        dates = [p.trade_date for p in history]
        lo = bisect_left(dates, start)
        hi = bisect_left(dates, end, lo)
        # include any point exactly equal to `end`
        while hi < len(dates) and dates[hi] == end:
            hi += 1
        return history[lo:hi]

    def all_symbols(self) -> List[str]:
        return list(self._data.keys())

    def get_sector(self, symbol: str) -> str:
        return self._sectors.get(symbol.upper(), "UNSPECIFIED")

    def latest_close(self, symbol: str) -> Optional[float]:
        history = self.get_history(symbol)
        return history[-1].price if history else None
