"""
Amazon OpenSearch implementation of the vector store.

Uses opensearch-py client to connect to an OpenSearch cluster
(managed or serverless). Supports k-NN vector search with cosine
similarity for semantic code retrieval.

Required env vars for AWS:
    OPENSEARCH_HOST      (default: localhost)
    OPENSEARCH_PORT      (default: 9200)
    OPENSEARCH_INDEX     (default: synapse_vectors)
    OPENSEARCH_USER      (optional)
    OPENSEARCH_PASSWORD  (optional)
"""

import os
import json
from typing import Dict, List, Optional

from .base_store import BaseVectorStore

# Embedding dimension for all-MiniLM-L6-v2
EMBEDDING_DIM = 384


class OpenSearchVectorStore(BaseVectorStore):
    """Vector store backed by Amazon OpenSearch with k-NN plugin."""

    def __init__(self, index_name: Optional[str] = None):
        try:
            from opensearchpy import OpenSearch
        except ImportError:
            raise ImportError(
                "opensearch-py is required for OpenSearch backend. "
                "Install with: pip install opensearch-py"
            )

        self.index_name = index_name or os.getenv("OPENSEARCH_INDEX", "synapse_vectors")
        host = os.getenv("OPENSEARCH_HOST", "localhost")
        port = int(os.getenv("OPENSEARCH_PORT", "9200"))
        user = os.getenv("OPENSEARCH_USER")
        password = os.getenv("OPENSEARCH_PASSWORD")

        # Build connection config
        conn_kwargs = {
            "hosts": [{"host": host, "port": port}],
            "use_ssl": port == 443,
            "verify_certs": port == 443,
            "ssl_show_warn": False,
        }
        if user and password:
            conn_kwargs["http_auth"] = (user, password)

        self.client = OpenSearch(**conn_kwargs)
        self._ensure_index()
        print(f"[OpenSearch] Connected to {host}:{port}, index: {self.index_name}")

    def _ensure_index(self) -> None:
        """Create the k-NN index if it doesn't exist."""
        if self.client.indices.exists(index=self.index_name):
            return

        index_body = {
            "settings": {
                "index": {
                    "knn": True,
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                }
            },
            "mappings": {
                "properties": {
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": EMBEDDING_DIM,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib",
                        },
                    },
                    "document": {"type": "text"},
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "keyword"},
                            "type": {"type": "keyword"},
                            "name": {"type": "keyword"},
                            "unique_id": {"type": "keyword"},
                            "parent_class": {"type": "keyword"},
                            "signature": {"type": "text"},
                            "is_method": {"type": "boolean"},
                            "cyclomatic": {"type": "integer"},
                            "cognitive": {"type": "integer"},
                            "loc": {"type": "integer"},
                        },
                    },
                }
            },
        }

        self.client.indices.create(index=self.index_name, body=index_body)
        print(f"[OpenSearch] Created index: {self.index_name}")

    def add_nodes(self, nodes: List[Dict], embeddings: List[List[float]]) -> None:
        batch_size = 100
        total_nodes = len(nodes)

        for i in range(0, total_nodes, batch_size):
            batch_nodes = nodes[i : i + batch_size]
            batch_embeddings = embeddings[i : i + batch_size]

            # Build bulk request body
            bulk_body = []
            for node, embedding in zip(batch_nodes, batch_embeddings):
                unique_id = self.build_unique_id(node)
                if not unique_id:
                    continue

                # Index action
                bulk_body.append(
                    {"index": {"_index": self.index_name, "_id": unique_id}}
                )
                # Document body
                bulk_body.append({
                    "embedding": embedding,
                    "document": self.build_document(node),
                    "metadata": self.build_metadata(node, unique_id),
                })

            if not bulk_body:
                continue

            try:
                response = self.client.bulk(body=bulk_body, refresh=True)
                errors = response.get("errors", False)
                if errors:
                    failed = sum(
                        1 for item in response["items"]
                        if item.get("index", {}).get("error")
                    )
                    print(f"[OpenSearch] Batch {i}: {failed} errors out of {len(batch_nodes)}")
                else:
                    print(f"[OpenSearch] Indexed batch {i} to {i + len(batch_nodes)}")
            except Exception as e:
                print(f"[OpenSearch] Error indexing batch {i}: {e}")
                continue

    def search(self, query_embedding: List[float], n_results: int = 5) -> Dict:
        """
        k-NN vector search.
        
        Returns results in ChromaDB-compatible format so the RAG pipeline
        doesn't need to know which backend is being used.
        """
        search_body = {
            "size": n_results,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_embedding,
                        "k": n_results,
                    }
                }
            },
            "_source": ["document", "metadata"],
        }

        try:
            response = self.client.search(
                index=self.index_name, body=search_body
            )
        except Exception as e:
            print(f"[OpenSearch] Search error: {e}")
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        # Convert OpenSearch response to ChromaDB-compatible format
        documents = []
        metadatas = []
        distances = []

        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            documents.append(source.get("document", ""))
            metadatas.append(source.get("metadata", {}))
            # OpenSearch returns _score (higher = more similar)
            # ChromaDB uses distances (lower = more similar)
            # Convert: distance ≈ 1 - score
            distances.append(1.0 - hit.get("_score", 0.0))

        return {
            "documents": [documents],
            "metadatas": [metadatas],
            "distances": [distances],
        }

    def delete_collection(self) -> None:
        try:
            if self.client.indices.exists(index=self.index_name):
                self.client.indices.delete(index=self.index_name)
                print(f"[OpenSearch] Deleted index: {self.index_name}")
        except Exception as e:
            print(f"[OpenSearch] Error deleting index: {e}")
