"""
Abstract base class for graph stores.

Defines the contract that all graph storage implementations (NetworkX,
Amazon Neptune, etc.) must follow. This provides a backend-agnostic
interface for all graph operations used by CodeGraph and consumers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple


class BaseGraphStore(ABC):
    """
    Abstract graph store interface.
    
    All implementations must support directed graph operations:
    nodes, edges, traversal, and graph analysis.
    """

    # ─────────────────────────────────────────────
    # Node Operations
    # ─────────────────────────────────────────────

    @abstractmethod
    def add_node(self, node_id: str, **attrs) -> None:
        """Add a node with optional attributes."""
        ...

    @abstractmethod
    def has_node(self, node_id: str) -> bool:
        """Check if a node exists in the graph."""
        ...

    @abstractmethod
    def get_node_data(self, node_id: str) -> Dict[str, Any]:
        """Get all attributes for a node. Returns {} if node not found."""
        ...

    @abstractmethod
    def get_all_nodes(self) -> List[str]:
        """Return list of all node IDs."""
        ...

    @abstractmethod
    def number_of_nodes(self) -> int:
        """Return total number of nodes."""
        ...

    # ─────────────────────────────────────────────
    # Edge Operations
    # ─────────────────────────────────────────────

    @abstractmethod
    def add_edge(self, source: str, target: str, **attrs) -> None:
        """Add a directed edge with optional attributes."""
        ...

    @abstractmethod
    def has_edge(self, source: str, target: str) -> bool:
        """Check if an edge exists."""
        ...

    @abstractmethod
    def get_edge_data(self, source: str, target: str) -> Optional[Dict[str, Any]]:
        """Get attributes for an edge. Returns None if edge not found."""
        ...

    @abstractmethod
    def number_of_edges(self) -> int:
        """Return total number of edges."""
        ...

    # ─────────────────────────────────────────────
    # Traversal
    # ─────────────────────────────────────────────

    @abstractmethod
    def predecessors(self, node_id: str) -> List[str]:
        """Get direct predecessors (nodes with edges INTO this node)."""
        ...

    @abstractmethod
    def successors(self, node_id: str) -> List[str]:
        """Get direct successors (nodes this node has edges TO)."""
        ...

    @abstractmethod
    def ancestors(self, node_id: str) -> Set[str]:
        """Get all upstream nodes (transitive predecessors)."""
        ...

    @abstractmethod
    def descendants(self, node_id: str) -> Set[str]:
        """Get all downstream nodes (transitive successors)."""
        ...

    @abstractmethod
    def in_degree(self, node_id: str) -> int:
        """Number of incoming edges."""
        ...

    @abstractmethod
    def out_degree(self, node_id: str) -> int:
        """Number of outgoing edges."""
        ...

    # ─────────────────────────────────────────────
    # Graph Analysis
    # ─────────────────────────────────────────────

    @abstractmethod
    def betweenness_centrality(self) -> Dict[str, float]:
        """Calculate betweenness centrality for all nodes."""
        ...

    @abstractmethod
    def find_cycles(self) -> List[List[str]]:
        """Find all simple cycles in the graph."""
        ...

    @abstractmethod
    def density(self) -> float:
        """Calculate graph density."""
        ...

    # ─────────────────────────────────────────────
    # Bulk Operations
    # ─────────────────────────────────────────────

    @abstractmethod
    def clear(self) -> None:
        """Remove all nodes and edges."""
        ...
