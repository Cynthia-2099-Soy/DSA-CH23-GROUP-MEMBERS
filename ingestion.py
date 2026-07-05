"""
ingestion.py
------------
Data structure used: QUEUE (collections.deque used as a FIFO buffer)

Rationale: live market data arrives as a continuous stream of ticks from
many symbols at once. Rather than writing directly into storage on every
single tick (which would force the ingestion source to wait on storage
locks), incoming ticks are pushed onto a queue and drained by a worker
in FIFO order. This decouples "receiving data" from "processing data" --
a classic producer/consumer buffering pattern -- and is also the natural
place to add backpressure or batching later without touching storage code.

Complexity
----------
enqueue_tick:  O(1)
drain (process n buffered ticks): O(n) total, O(1) per tick amortized
"""

from collections import deque
from dataclasses import dataclass
from datetime import date

from src.storage import StockDatabase


@dataclass
class RawTick:
    symbol: str
    trade_date: date
    price: float


class IngestionQueue:
    def __init__(self, database: StockDatabase):
        self._queue: deque[RawTick] = deque()
        self._database = database
        self._processed_count = 0

    def enqueue_tick(self, symbol: str, trade_date: date, price: float) -> None:
        """Producer side: O(1) append to the right end of the deque."""
        if price < 0:
            raise ValueError(f"Price cannot be negative: {price}")
        self._queue.append(RawTick(symbol, trade_date, price))

    def pending_count(self) -> int:
        return len(self._queue)

    def drain(self, max_items: int | None = None) -> int:
        """
        Consumer side: pop ticks off the front of the queue (FIFO) and
        write them into storage. Returns the number of ticks processed.
        """
        processed = 0
        while self._queue and (max_items is None or processed < max_items):
            tick = self._queue.popleft()   # O(1)
            self._database.insert_tick(tick.symbol, tick.trade_date, tick.price)
            processed += 1
            self._processed_count += 1
        return processed

    @property
    def total_processed(self) -> int:
        return self._processed_count
