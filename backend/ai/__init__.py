# Backend AI Module
# Use lazy imports to avoid loading heavy ML dependencies
# when only lightweight modules (like graph_context) are needed.

from .graph_context import GraphContextBuilder


def get_embedder():
    """Lazy import for CodeEmbedder (requires sentence-transformers)."""
    from .embeddings import CodeEmbedder
    return CodeEmbedder


def get_vector_store():
    """Lazy import for vector store (backend-agnostic via factory)."""
    from .store_factory import create_vector_store
    return create_vector_store


def get_rag_pipeline():
    """Lazy import for RAGPipeline (requires all AI deps)."""
    from .rag import RAGPipeline
    return RAGPipeline


# For backward compatibility - these will only fail if actually used
# without the ML dependencies installed
def __getattr__(name):
    """Lazy module-level attribute access for heavy imports."""
    if name == "CodeEmbedder":
        from .embeddings import CodeEmbedder
        return CodeEmbedder
    elif name == "VectorStore":
        from .store import ChromaVectorStore
        return ChromaVectorStore
    elif name == "RAGPipeline":
        from .rag import RAGPipeline
        return RAGPipeline
    raise AttributeError(f"module 'backend.ai' has no attribute {name}")

