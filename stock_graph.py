"""
stock_graph.py
--------------
Data structure used: GRAPH (adjacency list, dict[str, set[str]])

Stocks are modeled as nodes. An edge connects two stocks if they share
a sector (e.g. all technology stocks are mutually connected) or have
been explicitly linked (e.g. known supplier/competitor relationship).
This lets the server answer "find stocks related to X" using BFS
(shortest relationship distance / nearest neighbours first) or DFS
(explore one relationship branch deeply, e.g. for a full connected
sector dump).

Complexity
----------
add_edge:            O(1)
bfs_related (radius r): O(V + E) bounded to the visited frontier
dfs_related:          O(V + E) worst case
"""

from collections import deque
from typing import Dict, List, Set

from src.storage import StockDatabase


class StockGraph:
    def __init__(self):
        self._adjacency: Dict[str, Set[str]] = {}

    def add_symbol(self, symbol: str) -> None:
        symbol = symbol.upper()
        self._adjacency.setdefault(symbol, set())

    def add_edge(self, symbol_a: str, symbol_b: str) -> None:
        symbol_a, symbol_b = symbol_a.upper(), symbol_b.upper()
        self.add_symbol(symbol_a)
        self.add_symbol(symbol_b)
        if symbol_a != symbol_b:
            self._adjacency[symbol_a].add(symbol_b)
            self._adjacency[symbol_b].add(symbol_a)

    def neighbors(self, symbol: str) -> Set[str]:
        return self._adjacency.get(symbol.upper(), set())

    @classmethod
    def build_from_sectors(cls, db: StockDatabase) -> "StockGraph":
        """Convenience builder: connect every pair of symbols in the same sector."""
        graph = cls()
        sector_groups: Dict[str, List[str]] = {}
        for symbol in db.all_symbols():
            sector = db.get_sector(symbol)
            sector_groups.setdefault(sector, []).append(symbol)

        for symbols in sector_groups.values():
            for i in range(len(symbols)):
                graph.add_symbol(symbols[i])
                for j in range(i + 1, len(symbols)):
                    graph.add_edge(symbols[i], symbols[j])
        return graph

    def bfs_related(self, start_symbol: str, max_depth: int = 1) -> List[str]:
        """
        Breadth-first search: return symbols reachable within max_depth
        hops, ordered by increasing distance (nearest relationships first).
        """
        start_symbol = start_symbol.upper()
        if start_symbol not in self._adjacency:
            return []

        visited = {start_symbol}
        queue = deque([(start_symbol, 0)])
        result = []

        while queue:
            node, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for neighbor in self._adjacency[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    result.append(neighbor)
                    queue.append((neighbor, depth + 1))
        return result

    def dfs_related(self, start_symbol: str) -> List[str]:
        """Depth-first search: fully explore the connected component."""
        start_symbol = start_symbol.upper()
        if start_symbol not in self._adjacency:
            return []

        visited = set()
        result = []

        def _dfs(node: str):
            visited.add(node)
            for neighbor in self._adjacency[node]:
                if neighbor not in visited:
                    result.append(neighbor)
                    _dfs(neighbor)

        _dfs(start_symbol)
        return result
