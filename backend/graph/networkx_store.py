"""
NetworkX implementation of the graph store.

Wraps a NetworkX DiGraph behind the BaseGraphStore interface.
This is the default backend for local development.
"""

from typing import Any, Dict, List, Optional, Set

import networkx as nx

from .base_graph_store import BaseGraphStore


class NetworkXStore(BaseGraphStore):
    """Graph store backed by NetworkX (in-memory directed graph)."""

    def __init__(self):
        self._graph = nx.DiGraph()

    # ─── Node Operations ──────────────────────────

    def add_node(self, node_id: str, **attrs) -> None:
        self._graph.add_node(node_id, **attrs)

    def has_node(self, node_id: str) -> bool:
        return node_id in self._graph

    def get_node_data(self, node_id: str) -> Dict[str, Any]:
        if node_id in self._graph:
            return dict(self._graph.nodes[node_id])
        return {}

    def get_all_nodes(self) -> List[str]:
        return list(self._graph.nodes)

    def number_of_nodes(self) -> int:
        return self._graph.number_of_nodes()

    # ─── Edge Operations ──────────────────────────

    def add_edge(self, source: str, target: str, **attrs) -> None:
        self._graph.add_edge(source, target, **attrs)

    def has_edge(self, source: str, target: str) -> bool:
        return self._graph.has_edge(source, target)

    def get_edge_data(self, source: str, target: str) -> Optional[Dict[str, Any]]:
        data = self._graph.get_edge_data(source, target)
        return dict(data) if data else None

    def number_of_edges(self) -> int:
        return self._graph.number_of_edges()

    # ─── Traversal ────────────────────────────────

    def predecessors(self, node_id: str) -> List[str]:
        return list(self._graph.predecessors(node_id))

    def successors(self, node_id: str) -> List[str]:
        return list(self._graph.successors(node_id))

    def ancestors(self, node_id: str) -> Set[str]:
        return nx.ancestors(self._graph, node_id)

    def descendants(self, node_id: str) -> Set[str]:
        return nx.descendants(self._graph, node_id)

    def in_degree(self, node_id: str) -> int:
        return self._graph.in_degree(node_id)

    def out_degree(self, node_id: str) -> int:
        return self._graph.out_degree(node_id)

    # ─── Analysis ─────────────────────────────────

    def betweenness_centrality(self) -> Dict[str, float]:
        return nx.betweenness_centrality(self._graph)

    def find_cycles(self) -> List[List[str]]:
        return list(nx.simple_cycles(self._graph))

    def density(self) -> float:
        if self._graph.number_of_nodes() == 0:
            return 0.0
        return nx.density(self._graph)

    # ─── Bulk Operations ──────────────────────────

    def clear(self) -> None:
        self._graph.clear()
