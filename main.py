"""
main.py
-------
Simple CLI demo of the Stock Query Server. Run with:

    python main.py

This seeds a handful of symbols with sample daily prices, then
demonstrates every required query type.
"""

from datetime import date, timedelta

from src.server import StockQueryServer


def seed_data(server: StockQueryServer) -> None:
    server.db.register_symbol("SCOM", sector="TELECOM")   # Safaricom
    server.db.register_symbol("EQTY", sector="BANKING")    # Equity Group
    server.db.register_symbol("KCB", sector="BANKING")     # KCB Group
    server.db.register_symbol("EABL", sector="CONSUMER")   # East Africa Breweries
    server.db.register_symbol("COOP", sector="BANKING")    # Co-operative Bank

    start = date(2026, 1, 1)
    sample_prices = {
        "SCOM": [17.0, 17.2, 17.1, 17.5, 17.8, 18.0, 18.2],
        "EQTY": [45.0, 44.5, 44.8, 46.0, 46.5, 47.0, 46.8],
        "KCB": [38.0, 38.2, 37.9, 38.5, 39.0, 39.2, 39.5],
        "EABL": [150.0, 152.0, 151.5, 153.0, 154.0, 153.5, 155.0],
        "COOP": [12.0, 12.1, 12.05, 12.2, 12.3, 12.25, 12.4],
    }

    for symbol, prices in sample_prices.items():
        for i, price in enumerate(prices):
            server.submit_tick(symbol, start + timedelta(days=i), price)

    server.process_pending_ticks()


def main():
    server = StockQueryServer(rolling_window_size=3)
    seed_data(server)

    print("=== 1. Price on a specific date (binary search) ===")
    print("SCOM on 2026-01-04:", server.get_price_on_date("SCOM", date(2026, 1, 4)))

    print("\n=== 2. Price range query ===")
    for point in server.get_price_range("EQTY", date(2026, 1, 2), date(2026, 1, 5)):
        print(" ", point)

    print("\n=== 3. Rolling metrics (deque, window=3) ===")
    print("EABL rolling metrics:", server.get_rolling_metrics("EABL"))

    print("\n=== 4. Top gainers / losers (heap, heapq.nlargest/nsmallest) ===")
    print("Top 3 gainers:", server.top_gainers(3))
    print("Top 3 losers:", server.top_losers(3))

    print("\n=== 5. Merge sort a symbol's history by price ===")
    print([p.price for p in server.sorted_history_by_price("KCB")])

    print("\n=== 6. Related stocks via BFS (graph, same sector) ===")
    print("Related to EQTY (depth 1):", server.related_stocks_bfs("EQTY", max_depth=1))

    print("\n=== 7. Related stocks via DFS ===")
    print("DFS from KCB:", server.related_stocks_dfs("KCB"))

    print("\n=== 8. Audit stack / undo ===")
    print("Undoing last action:", server.undo_last_action())
    print("SCOM history length after undo:", len(server.db.get_history("SCOM")))


if __name__ == "__main__":
    main()
