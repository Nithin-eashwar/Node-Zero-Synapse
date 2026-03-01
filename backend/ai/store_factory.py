"""
Vector store factory.

Returns the appropriate vector store backend based on configuration.
Default is ChromaDB for backward compatibility and local development.

Set VECTOR_STORE_BACKEND env var to switch:
    - "chroma"     → ChromaDB (local, default)
    - "opensearch" → Amazon OpenSearch (AWS production)
"""

import os
from .base_store import BaseVectorStore


def create_vector_store(backend: str = None) -> BaseVectorStore:
    """
    Create and return a vector store instance.
    
    Args:
        backend: "chroma" or "opensearch". If None, reads from
                 VECTOR_STORE_BACKEND env var (default: "chroma").
    
    Returns:
        A BaseVectorStore implementation.
    """
    backend = backend or os.getenv("VECTOR_STORE_BACKEND", "chroma").lower()

    if backend == "opensearch":
        from .opensearch_store import OpenSearchVectorStore
        print("[Factory] Using OpenSearch vector store")
        return OpenSearchVectorStore()

    elif backend == "chroma":
        from .store import ChromaVectorStore
        print("[Factory] Using ChromaDB vector store")
        return ChromaVectorStore()

    else:
        raise ValueError(
            f"Unknown vector store backend: '{backend}'. "
            f"Supported: 'chroma', 'opensearch'"
        )
