"""
Amazon Neptune implementation of the graph store.

Uses Gremlin traversal language via gremlin_python to connect to
an Amazon Neptune cluster. Supports all graph operations needed
by CodeGraph for blast radius, dependency analysis, etc.

Required env vars:
    NEPTUNE_ENDPOINT    Neptune cluster endpoint (e.g., your-cluster.neptune.amazonaws.com)
    NEPTUNE_PORT        WebSocket port (default: 8182)
"""

import os
from collections import deque
from typing import Any, Dict, List, Optional, Set

from .base_graph_store import BaseGraphStore


class NeptuneStore(BaseGraphStore):
    """Graph store backed by Amazon Neptune via Gremlin."""

    def __init__(self):
        try:
            from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
            from gremlin_python.process.anonymous_traversal import traversal
        except ImportError:
            raise ImportError(
                "gremlinpython is required for Neptune backend. "
                "Install with: pip install gremlinpython"
            )

        endpoint = os.getenv("NEPTUNE_ENDPOINT")
        port = int(os.getenv("NEPTUNE_PORT", "8182"))

        if not endpoint:
            raise ValueError("NEPTUNE_ENDPOINT env var is required for Neptune backend.")

        url = f"wss://{endpoint}:{port}/gremlin"
        print(f"[Neptune] Connecting to {url}...")

        self._connection = DriverRemoteConnection(url, "g")
        self._g = traversal().withRemote(self._connection)
        print("[Neptune] Connected successfully")

    def __del__(self):
        """Close the connection on cleanup."""
        if hasattr(self, "_connection") and self._connection:
            try:
                self._connection.close()
            except Exception:
                pass

    # ─── Node Operations ──────────────────────────

    def add_node(self, node_id: str, **attrs) -> None:
        from gremlin_python.process.graph_traversal import __

        t = self._g.V().has("code", "id", node_id).fold().coalesce(
            __.unfold(),
            __.addV("code").property("id", node_id)
        )
        # Add attributes as properties
        for key, value in attrs.items():
            if value is not None and isinstance(value, (str, int, float, bool)):
                t = t.property(key, value)
        t.next()

    def has_node(self, node_id: str) -> bool:
        count = self._g.V().has("code", "id", node_id).count().next()
        return count > 0

    def get_node_data(self, node_id: str) -> Dict[str, Any]:
        try:
            props = self._g.V().has("code", "id", node_id).valueMap(True).next()
            # Flatten single-value lists that Gremlin returns
            result = {}
            for k, v in props.items():
                if isinstance(v, list) and len(v) == 1:
                    result[str(k)] = v[0]
                elif isinstance(v, list):
                    result[str(k)] = v
                else:
                    result[str(k)] = v
            return result
        except Exception:
            return {}

    def get_all_nodes(self) -> List[str]:
        return self._g.V().hasLabel("code").values("id").toList()

    def number_of_nodes(self) -> int:
        return self._g.V().hasLabel("code").count().next()

    # ─── Edge Operations ──────────────────────────

    def add_edge(self, source: str, target: str, **attrs) -> None:
        from gremlin_python.process.graph_traversal import __

        # Ensure both nodes exist
        self.add_node(source)
        self.add_node(target)

        # Add edge
        t = (
            self._g.V().has("code", "id", source)
            .addE("depends_on")
            .to(__.V().has("code", "id", target))
        )
        for key, value in attrs.items():
            if value is not None and isinstance(value, (str, int, float, bool)):
                t = t.property(key, value)
        t.next()

    def has_edge(self, source: str, target: str) -> bool:
        from gremlin_python.process.graph_traversal import __

        count = (
            self._g.V().has("code", "id", source)
            .outE("depends_on")
            .where(__.inV().has("code", "id", target))
            .count()
            .next()
        )
        return count > 0

    def get_edge_data(self, source: str, target: str) -> Optional[Dict[str, Any]]:
        from gremlin_python.process.graph_traversal import __

        try:
            props = (
                self._g.V().has("code", "id", source)
                .outE("depends_on")
                .where(__.inV().has("code", "id", target))
                .valueMap(True)
                .next()
            )
            result = {}
            for k, v in props.items():
                if isinstance(v, list) and len(v) == 1:
                    result[str(k)] = v[0]
                else:
                    result[str(k)] = v
            return result
        except Exception:
            return None

    def number_of_edges(self) -> int:
        return self._g.E().hasLabel("depends_on").count().next()

    # ─── Traversal ────────────────────────────────

    def predecessors(self, node_id: str) -> List[str]:
        """Direct predecessors = nodes that have an edge TO this node."""
        return (
            self._g.V().has("code", "id", node_id)
            .in_("depends_on")
            .values("id")
            .toList()
        )

    def successors(self, node_id: str) -> List[str]:
        """Direct successors = nodes this node has edges TO."""
        return (
            self._g.V().has("code", "id", node_id)
            .out("depends_on")
            .values("id")
            .toList()
        )

    def ancestors(self, node_id: str) -> Set[str]:
        """All upstream nodes (transitive predecessors)."""
        result = (
            self._g.V().has("code", "id", node_id)
            .repeat(__.in_("depends_on")).emit()
            .dedup()
            .values("id")
            .toList()
        )
        return set(result)

    def descendants(self, node_id: str) -> Set[str]:
        """All downstream nodes (transitive successors)."""
        from gremlin_python.process.graph_traversal import __

        result = (
            self._g.V().has("code", "id", node_id)
            .repeat(__.out("depends_on")).emit()
            .dedup()
            .values("id")
            .toList()
        )
        return set(result)

    def in_degree(self, node_id: str) -> int:
        return (
            self._g.V().has("code", "id", node_id)
            .inE("depends_on")
            .count()
            .next()
        )

    def out_degree(self, node_id: str) -> int:
        return (
            self._g.V().has("code", "id", node_id)
            .outE("depends_on")
            .count()
            .next()
        )

    # ─── Analysis ─────────────────────────────────

    def betweenness_centrality(self) -> Dict[str, float]:
        """
        Approximate betweenness centrality.
        
        Neptune doesn't have a built-in centrality algorithm,
        so we compute it locally by pulling the graph structure.
        For large graphs, consider using Neptune Analytics.
        """
        # Pull graph structure and compute locally
        import networkx as nx

        G = nx.DiGraph()
        nodes = self.get_all_nodes()
        for node in nodes:
            G.add_node(node)
        for node in nodes:
            for succ in self.successors(node):
                G.add_edge(node, succ)
        return nx.betweenness_centrality(G)

    def find_cycles(self) -> List[List[str]]:
        """
        Find cycles by pulling graph structure locally.
        Neptune doesn't have built-in cycle detection.
        """
        import networkx as nx

        G = nx.DiGraph()
        nodes = self.get_all_nodes()
        for node in nodes:
            G.add_node(node)
        for node in nodes:
            for succ in self.successors(node):
                G.add_edge(node, succ)
        return list(nx.simple_cycles(G))

    def density(self) -> float:
        n = self.number_of_nodes()
        if n == 0:
            return 0.0
        e = self.number_of_edges()
        # Directed graph density = E / (N * (N - 1))
        return e / (n * (n - 1)) if n > 1 else 0.0

    # ─── Bulk Operations ──────────────────────────

    def clear(self) -> None:
        """Remove all code vertices and their edges."""
        self._g.V().hasLabel("code").drop().iterate()
        print("[Neptune] Cleared all code vertices")
