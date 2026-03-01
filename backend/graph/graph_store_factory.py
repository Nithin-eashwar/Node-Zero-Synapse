"""
Graph store factory.

Returns the appropriate graph store backend based on configuration.
Default is NetworkX for backward compatibility and local development.

Set GRAPH_STORE_BACKEND env var to switch:
    - "networkx" → NetworkX in-memory (local, default)
    - "neptune"  → Amazon Neptune (AWS production)
"""

import os
from .base_graph_store import BaseGraphStore


def create_graph_store(backend: str = None) -> BaseGraphStore:
    """
    Create and return a graph store instance.
    
    Args:
        backend: "networkx" or "neptune". If None, reads from
                 GRAPH_STORE_BACKEND env var (default: "networkx").
    
    Returns:
        A BaseGraphStore implementation.
    """
    backend = backend or os.getenv("GRAPH_STORE_BACKEND", "networkx").lower()

    if backend == "neptune":
        from .neptune_store import NeptuneStore
        print("[Factory] Using Neptune graph store")
        return NeptuneStore()

    elif backend == "networkx":
        from .networkx_store import NetworkXStore
        print("[Factory] Using NetworkX graph store")
        return NetworkXStore()

    else:
        raise ValueError(
            f"Unknown graph store backend: '{backend}'. "
            f"Supported: 'networkx', 'neptune'"
        )
