"""
test_server.py
---------------
Test plan for the Stock Query Server.

Covers normal operation plus the edge cases required by the assignment:
empty history, single data point, duplicate/out-of-order timestamps,
non-existent symbol, boundary conditions on binary search, rolling
window smaller/larger than available data, unreachable graph nodes,
empty-stack undo, empty-queue drain, sort stability/ties, and negative
input validation.

Run with:  pytest tests/test_server.py -v
"""

import pytest
from datetime import date, timedelta

from src.server import StockQueryServer
from src.storage import SymbolNotFoundError
from src.rolling_metrics import RollingWindowMetrics
from src.stock_graph import StockGraph
from src.audit_stack import AuditStack
from src.sorting import merge_sort


@pytest.fixture
def server():
    s = StockQueryServer(rolling_window_size=3)
    s.db.register_symbol("AAA", sector="TECH")
    s.db.register_symbol("BBB", sector="TECH")
    s.db.register_symbol("CCC", sector="BANKING")
    return s


# ---------- 1-3: basic ingestion + lookup ----------

def test_insert_and_lookup_by_exact_date(server):
    server.submit_tick("AAA", date(2026, 1, 1), 10.0)
    server.process_pending_ticks()
    assert server.get_price_on_date("AAA", date(2026, 1, 1)) == 10.0


def test_lookup_date_with_no_data_returns_none(server):
    server.submit_tick("AAA", date(2026, 1, 1), 10.0)
    server.process_pending_ticks()
    assert server.get_price_on_date("AAA", date(2026, 1, 2)) is None


def test_price_range_query_returns_correct_window(server):
    for i, price in enumerate([10, 11, 12, 13, 14]):
        server.submit_tick("AAA", date(2026, 1, 1) + timedelta(days=i), price)
    server.process_pending_ticks()
    result = server.get_price_range("AAA", date(2026, 1, 2), date(2026, 1, 4))
    assert [p.price for p in result] == [11, 12, 13]


# ---------- 4-6: edge cases on storage ----------

def test_empty_history_raises_no_error_but_returns_empty_range(server):
    result = server.get_price_range("BBB", date(2026, 1, 1), date(2026, 1, 5))
    assert result == []


def test_single_data_point_history(server):
    server.submit_tick("CCC", date(2026, 1, 1), 5.0)
    server.process_pending_ticks()
    history = server.db.get_history("CCC")
    assert len(history) == 1
    assert server.get_price_on_date("CCC", date(2026, 1, 1)) == 5.0


def test_nonexistent_symbol_raises_symbol_not_found(server):
    with pytest.raises(SymbolNotFoundError):
        server.db.get_history("ZZZ")


def test_out_of_order_tick_is_inserted_in_sorted_position(server):
    server.submit_tick("AAA", date(2026, 1, 1), 10.0)
    server.submit_tick("AAA", date(2026, 1, 3), 12.0)
    server.submit_tick("AAA", date(2026, 1, 2), 11.0)  # arrives late, out of order
    server.process_pending_ticks()
    dates = [p.trade_date for p in server.db.get_history("AAA")]
    assert dates == sorted(dates)


def test_negative_price_is_rejected(server):
    with pytest.raises(ValueError):
        server.submit_tick("AAA", date(2026, 1, 1), -5.0)


# ---------- 7-9: rolling metrics (deque) ----------

def test_rolling_window_smaller_than_available_data():
    tracker = RollingWindowMetrics(window_size=3)
    for price in [1, 2, 3, 4, 5]:
        tracker.add_price(price)
    # only the last 3 values (3, 4, 5) should count
    assert tracker.current_max() == 5
    assert tracker.current_min() == 3
    assert tracker.current_avg() == 4


def test_rolling_window_larger_than_available_data():
    tracker = RollingWindowMetrics(window_size=10)
    for price in [1, 2, 3]:
        tracker.add_price(price)
    assert tracker.current_max() == 3
    assert tracker.current_min() == 1
    assert len(tracker) == 3


def test_rolling_window_size_one_behaves_like_latest_value():
    tracker = RollingWindowMetrics(window_size=1)
    tracker.add_price(10)
    tracker.add_price(20)
    assert tracker.current_max() == 20
    assert tracker.current_min() == 20
    assert tracker.current_avg() == 20


def test_rolling_window_rejects_non_positive_size():
    with pytest.raises(ValueError):
        RollingWindowMetrics(window_size=0)


# ---------- 10-11: graph BFS/DFS ----------

def test_bfs_finds_same_sector_neighbors(server):
    server.build_relationship_graph()
    related = server.related_stocks_bfs("AAA", max_depth=1)
    assert "BBB" in related
    assert "CCC" not in related  # different sector


def test_bfs_on_unreachable_node_returns_empty():
    graph = StockGraph()
    graph.add_symbol("ISOLATED")
    assert graph.bfs_related("ISOLATED", max_depth=2) == []


def test_dfs_on_unknown_symbol_returns_empty():
    graph = StockGraph()
    assert graph.dfs_related("NOPE") == []


# ---------- 12-13: audit stack ----------

def test_undo_on_empty_stack_returns_none():
    stack = AuditStack()
    assert stack.undo_last() is None


def test_undo_reverses_last_insert(server):
    server.submit_tick("AAA", date(2026, 1, 1), 10.0)
    server.process_pending_ticks()
    assert len(server.db.get_history("AAA")) == 1
    server.undo_last_action()
    assert len(server.db.get_history("AAA")) == 0


# ---------- 14-15: sorting + queue ----------

def test_merge_sort_handles_ties_stably():
    data = [{"v": 3, "tag": "a"}, {"v": 1, "tag": "b"}, {"v": 3, "tag": "c"}, {"v": 1, "tag": "d"}]
    result = merge_sort(data, key=lambda x: x["v"])
    assert [d["v"] for d in result] == [1, 1, 3, 3]
    # stability: original relative order preserved among equal keys
    assert [d["tag"] for d in result] == ["b", "d", "a", "c"]


def test_draining_empty_queue_returns_zero(server):
    assert server.queue.drain() == 0


def test_merge_sort_empty_and_single_element_lists():
    assert merge_sort([]) == []
    assert merge_sort([42]) == [42]


# ---------- 16: top movers heap ----------

def test_top_k_gainers_and_losers(server):
    server.submit_tick("AAA", date(2026, 1, 1), 10.0)
    server.submit_tick("AAA", date(2026, 1, 2), 12.0)   # +20%
    server.submit_tick("BBB", date(2026, 1, 1), 10.0)
    server.submit_tick("BBB", date(2026, 1, 2), 8.0)    # -20%
    server.process_pending_ticks()

    gainers = server.top_gainers(1)
    losers = server.top_losers(1)
    assert gainers[0].symbol == "AAA"
    assert losers[0].symbol == "BBB"
