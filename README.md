# DSA stock Query Server

A mini stock market data system built for the Data Structures & Algorithms group
project, following the 5-step system design process from **Chapter 23: System
Design** (Hemant Jain). Theme C (Stock Query Server), **Variant C2: Rolling
metrics (max/min/avg over a window) using heaps/deques**.

## Problem statement

Design and implement a server that ingests daily stock price ticks and answers
queries such as: what was the price on a given date, what happened over a date
range, what are the rolling max/min/average over the last N trading days, which
stocks are the top gainers/losers, and which stocks are related to a given one.
The system must be read-heavy-optimized while still supporting fast, buffered
writes, and must be able to explain how it would scale as the number of
symbols and ticks grows.

## Features

- Ingest price ticks through a buffered queue (decouples receiving data from
  writing it to storage)
- O(log n) exact-date and date-range price lookups via binary search over a
  hash-map-indexed, per-symbol sorted history
- O(1)-amortized rolling max/min/average over a configurable sliding window,
  using a monotonic deque
- O(n log k) top-k gainers/losers using a heap (`heapq.nlargest`/`nsmallest`)
- Related-stock discovery via a sector-relationship graph, traversed with
  BFS (nearest relationships first) or DFS (full connected component)
- O(n log n) merge sort for price-based ordering
- Undo/audit trail of every mutating action via a stack
- 21 automated tests covering normal operation and edge cases
- Benchmark script comparing performance at 10,000 vs 100,000 ticks

##  The Architecture diagram




Price ticks are buffered on a FIFO **queue** before being written into
**hash-map storage** (symbol -> sorted price history). Storage is read by four
independent query modules -- **rolling stats** (deque), **top movers** (heap),
the **stock relationship graph** (BFS/DFS), and **sort & search** (merge sort +
binary search) -- while an **audit stack** alongside storage logs every
mutation so it can be undone.

## Chapter 23 five-step design process

### 1. Use cases generation
- Query the price of a symbol on a specific date
- Query price history over a date range
- Get rolling max/min/average over the last N trading days for a symbol
- Get the top-K gaining and losing symbols
- Find stocks related to a given symbol (same sector / known relationship)
- Ingest new price ticks (bulk or streaming)
- Undo the most recent ingestion mistake

### 2. Constraints and analysis
- **Read-heavy**: queries vastly outnumber writes outside of market hours;
  writes arrive in bursts during trading sessions
- **Volume**: modelled at 50 symbols x up to 100,000 ticks in the benchmark
  (a real exchange would be thousands of symbols x years of daily data)
- **Latency**: exact-date and rolling-metric queries should stay sub-millisecond
  even as history grows, since they're on the interactive query path
- **Consistency**: ticks must be process-ordered so rolling metrics stay correct;
  late/out-of-order ticks are still supported but are the more expensive path

### 3. Basic design
See the architecture diagram above. Ingestion queue -> hash-map storage ->
four read-side modules (rolling stats, top movers, relationship graph,
sort & search), with an audit stack for undo.

### 4. Bottlenecks
- A **single ingestion queue** becomes a hot spot once tick volume grows past
  what one consumer can drain in real time
- Recomputing rolling max/min from scratch on every query would be O(n) per
  query; a naive heap-based sliding window would cost O(log n) per tick and
  still carry stale entries until they age out
- A hash map alone cannot answer "give me everything between date A and B"
  efficiently -- it needs the sorted-list-plus-binary-search structure this
  design already uses
- Computing top-k gainers by fully sorting all symbols is O(n log n) when only
  the top few are needed

### 5. Scalability
- **Shard storage by symbol hash** across multiple storage nodes so no single
  hash map holds the entire market
- **Precompute rolling metrics incrementally** (as this design already does
  with the monotonic deque) rather than recomputing per query
- **Cache** frequently-queried "hot" symbols in front of storage
- **Parallelize ingestion** with multiple queue consumers, partitioned by
  symbol so per-symbol ordering is preserved
- **Replicate read-only storage nodes** since the workload is read-heavy

## Data structures & algorithms used

| Requirement | Module | Structure | Key complexity |
|---|---|---|---|
| Hash table / map | `src/storage.py` | `dict[symbol -> history]` | O(1) avg lookup |
| Stack | `src/audit_stack.py` | list used LIFO | O(1) push/pop (undo) |
| Queue | `src/ingestion.py` | `collections.deque` FIFO | O(1) enqueue/dequeue |
| Heap / priority queue | `src/top_movers.py` | `heapq.nlargest`/`nsmallest` | O(n log k) |
| Graph (BFS/DFS) | `src/stock_graph.py` | adjacency list (dict of sets) | O(V + E) |
| Sort (O(n log n)) | `src/sorting.py` | merge sort | O(n log n) |
| Search | `src/storage.py` | binary search (`bisect`) | O(log n) |
| Deque (sliding window) | `src/rolling_metrics.py` | monotonic deque | O(1) amortized |

## How to run

```bash
# from the project root
pip install pytest matplotlib --break-system-packages   # or use a venv

# run the demo
python main.py

# run the test suite
pytest tests/test_server.py -v

# run the benchmark (prints a table + saves benchmark/benchmark_results.png)
python benchmark/benchmark.py
```

## Sample input/output

```
=== 1. Price on a specific date (binary search) ===
SCOM on 2026-01-04: 17.5

=== 3. Rolling metrics (deque, window=3) ===
EABL rolling metrics: {'max': 155.0, 'min': 153.5, 'avg': 154.16666666666666}

=== 4. Top gainers / losers (heap, heapq.nlargest/nsmallest) ===
Top 3 gainers: [SCOM: +7.06%, EQTY: +4.00%, KCB: +3.95%]
Top 3 losers: [EABL: +3.33%, COOP: +3.33%, KCB: +3.95%]

=== 6. Related stocks via BFS (graph, same sector) ===
Related to EQTY (depth 1): ['KCB', 'COOP']
```


## Test plan

21 automated tests in `tests/test_server.py` (run with `pytest -v`), covering:

- Normal ingestion, exact-date lookup, and range queries
- Edge cases: empty history, a single data point, a non-existent symbol
- Out-of-order tick insertion and negative-price rejection
- Rolling window smaller than, larger than, and equal in size to the data,
  plus a rejected zero/negative window size
- Graph BFS/DFS on unreachable and unknown nodes
- Undo on an empty stack and undo reversing a real insert
- Merge sort stability, and empty/single-element inputs
- Draining an empty ingestion queue
- Top-k gainers/losers correctness

## Benchmark notes

`benchmark/benchmark.py` measures ingestion, exact-date lookup, range query,
and top-k time at **10,000** and **100,000** ticks across 50 symbols. On the
reference machine used for this project:

| Ticks | Ingest total | Ingest / tick | 1,000 lookups | 100 range queries | Top-k |
|---|---|---|---|---|---|
| 10,000 | ~0.06 s | ~5.7 us | ~0.0009 s | ~0.0007 s | ~0.0002 s |
| 100,000 | ~0.97 s | ~9.7 us | ~0.048 s | ~0.005 s | ~0.0001 s |

Observation we made : The  time per query grows roughly with the log of history size
(consistent with the O(log n) binary search), while top-k stays flat regardless
of data volume because it only depends on k, not n. See
`benchmark/benchmark_results.png` for the chart.



## Repository structure

```
stock_query_server/
|-- src/
|   |-- storage.py          # hash map + binary search
|   |-- ingestion.py        # queue
|   |-- rolling_metrics.py  # monotonic deque
|   |-- top_movers.py       # heap
|   |-- stock_graph.py      # graph + BFS/DFS
|   |-- audit_stack.py      # stack (undo)
|   |-- sorting.py          # merge sort
|   `-- server.py           # top-level facade
|-- tests/
|   `-- test_server.py      # 21 tests
|-- benchmark/
|   `-- benchmark.py        # performance benchmark + chart
|-- docs/
|   |-- architecture.svg
|   `-- architecture.png
|-- main.py                 # CLI demo
`-- README.md
```
