"""
ChromaDB implementation of the vector store.

Uses ChromaDB's PersistentClient for local/dev usage.
This is the default backend when VECTOR_STORE_BACKEND is not set.
"""

import os
import shutil
import tempfile
import time
from typing import Dict, List

import chromadb

from .base_store import BaseVectorStore


class ChromaVectorStore(BaseVectorStore):
    """Vector store backed by ChromaDB (local persistent storage)."""

    def __init__(self, collection_name: str = "codebase_vectors"):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        db_path = os.getenv("CHROMA_DB_PATH", os.path.join(base_dir, "chroma_db"))
        self.client = self._create_client_with_recovery(db_path)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def _create_client_with_recovery(self, db_path: str):
        """
        Create a Chroma client with defensive recovery.

        Chroma's rust bindings can panic on some persisted states/schema mismatches.
        If that happens, quarantine the broken directory and recreate an empty DB.
        """
        try:
            return chromadb.PersistentClient(path=db_path)
        except BaseException as first_error:
            print(f"[ChromaDB] Persistent client init failed at '{db_path}': {first_error}")

        quarantine_path = f"{db_path}_corrupt_{int(time.time())}"
        try:
            if os.path.exists(db_path):
                shutil.move(db_path, quarantine_path)
                print(f"[ChromaDB] Moved corrupted DB to: {quarantine_path}")
            os.makedirs(db_path, exist_ok=True)
            return chromadb.PersistentClient(path=db_path)
        except BaseException as second_error:
            print(f"[ChromaDB] Recovery with fresh persistent DB failed: {second_error}")

        # Last-resort fallback to an isolated temp directory.
        fallback_dir = os.path.join(tempfile.gettempdir(), "node_zero_synapse_chroma")
        os.makedirs(fallback_dir, exist_ok=True)
        print(f"[ChromaDB] Falling back to temp DB path: {fallback_dir}")
        return chromadb.PersistentClient(path=fallback_dir)

    def add_nodes(self, nodes: List[Dict], embeddings: List[List[float]]) -> None:
        batch_size = 100
        total_nodes = len(nodes)

        for i in range(0, total_nodes, batch_size):
            batch_nodes = nodes[i : i + batch_size]
            batch_embeddings = embeddings[i : i + batch_size]

            ids = []
            documents = []
            metadatas = []
            embeddings_to_upsert = []

            for node, embedding in zip(batch_nodes, batch_embeddings):
                unique_id = self.build_unique_id(node)
                if not unique_id:
                    continue
                ids.append(unique_id)
                documents.append(self.build_document(node))
                metadatas.append(self.build_metadata(node, unique_id))
                embeddings_to_upsert.append(embedding)

            try:
                if ids:
                    self.collection.upsert(
                        ids=ids,
                        documents=documents,
                        embeddings=embeddings_to_upsert,
                        metadatas=metadatas,
                    )
                    print(f"[ChromaDB] Indexed batch {i} to {i + len(batch_nodes)}")
            except Exception as e:
                print(f"[ChromaDB] Error indexing batch {i}: {e}")
                continue

    def search(self, query_embedding: List[float], n_results: int = 5) -> Dict:
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas"],
        )

    def delete_collection(self) -> None:
        try:
            self.client.delete_collection(self.collection.name)
            print("[ChromaDB] Collection deleted.")
        except Exception as e:
            print(f"[ChromaDB] Error deleting collection: {e}")


# Backward-compatible alias
VectorStore = ChromaVectorStore
