"""
Abstract base class for vector stores.

Defines the contract that all vector store implementations (ChromaDB,
OpenSearch, etc.) must follow. Also contains shared helper methods for
building document text and metadata from code nodes.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseVectorStore(ABC):
    """
    Abstract vector store interface.
    
    All implementations must support:
    - add_nodes: Upsert code entity nodes with their embeddings
    - search: Find nearest neighbors by embedding vector
    - delete_collection: Clear the index for re-indexing
    """

    @abstractmethod
    def add_nodes(self, nodes: List[Dict], embeddings: List[List[float]]) -> None:
        """Upsert nodes into the vector store in batches."""
        ...

    @abstractmethod
    def search(self, query_embedding: List[float], n_results: int = 5) -> Dict:
        """
        Search for nearest neighbors.
        
        Must return a dict compatible with ChromaDB's format:
        {
            "documents": [[str, ...]],
            "metadatas": [[dict, ...]],
            "distances": [[float, ...]]
        }
        """
        ...

    @abstractmethod
    def delete_collection(self) -> None:
        """Delete the entire collection/index for a fresh re-index."""
        ...

    # ─────────────────────────────────────────────
    # Shared helpers (used by all backends)
    # ─────────────────────────────────────────────

    def build_unique_id(self, node: Dict) -> str:
        """Build a stable unique ID for an entity. Format: file:name:start_line"""
        file_path = node.get("file")
        name = node.get("name")
        if not file_path or not name:
            return ""
        start_line = 0
        if "range" in node and isinstance(node["range"], list) and node["range"]:
            start_line = node["range"][0]
        elif "line" in node and isinstance(node["line"], int):
            start_line = node["line"]
        return f"{file_path}:{name}:{start_line}"

    def build_document(self, node: Dict) -> str:
        """
        Build rich document text for retrieval context.
        
        This is what gets returned to the LLM during search.
        Shared across all backends so context quality is consistent.
        """
        node_type = node.get("type", "unknown")
        name = node.get("name", "unknown")
        parts = []

        # Header
        if node_type == "class":
            bases = node.get("bases", [])
            base_str = f" (extends {', '.join(bases)})" if bases else ""
            parts.append(f"[CLASS] {name}{base_str}")
        elif node.get("is_method"):
            parts.append(f"[METHOD] {node.get('parent_class', '')}.{name}")
        else:
            parts.append(f"[FUNCTION] {name}")

        # Signature
        if node.get("signature"):
            parts.append(f"Signature: {node['signature']}")

        # File and location
        file_path = node.get("file", "unknown")
        line_range = node.get("range", [])
        if len(line_range) >= 2:
            parts.append(f"Location: {file_path} (lines {line_range[0]}-{line_range[1]})")
        else:
            parts.append(f"File: {file_path}")

        # Docstring
        if node.get("docstring"):
            parts.append(f"Description: {node['docstring']}")

        # Parameters
        params = node.get("parameters", [])
        if params:
            param_parts = []
            for p in params:
                p_str = p.get("name", "?")
                if p.get("type_hint"):
                    p_str += f": {p['type_hint']}"
                if p.get("default_value"):
                    p_str += f" = {p['default_value']}"
                param_parts.append(p_str)
            parts.append(f"Parameters: ({', '.join(param_parts)})")

        # Return type
        if node.get("return_type"):
            parts.append(f"Returns: {node['return_type']}")

        # Class-specific fields
        if node_type == "class":
            methods = node.get("methods", [])
            if methods:
                parts.append(f"Methods: {', '.join(methods)}")
            class_vars = node.get("class_variables", [])
            inst_vars = node.get("instance_variables", [])
            all_vars = class_vars + inst_vars
            if all_vars:
                parts.append(f"Fields: {', '.join(all_vars)}")

        # Dependencies
        calls = node.get("calls", [])
        if calls:
            meaningful = [c for c in calls
                         if c not in ("print", "len", "str", "range", "int", "float")
                         and not c.endswith(".append")
                         and not c.endswith(".get")]
            if meaningful:
                parts.append(f"Calls: {', '.join(meaningful[:10])}")

        # Complexity
        complexity = node.get("complexity", {})
        if complexity:
            cyc = complexity.get("cyclomatic", 0)
            cog = complexity.get("cognitive", 0)
            loc = complexity.get("lines_of_code", 0)
            risk = "HIGH" if cyc > 10 else ("moderate" if cyc > 5 else "low")
            parts.append(f"Complexity: cyclomatic={cyc} cognitive={cog} LOC={loc} ({risk} risk)")

        return "\n".join(parts)

    def build_metadata(self, node: Dict, unique_id: str) -> Dict:
        """
        Build metadata dict for filtering and display.
        Values must be str, int, float, or bool (compatible with both ChromaDB and OpenSearch).
        """
        meta = {
            "file": node.get("file", ""),
            "type": node.get("type", ""),
            "name": node.get("name", ""),
            "unique_id": unique_id,
        }

        if node.get("parent_class"):
            meta["parent_class"] = node["parent_class"]
        if node.get("signature"):
            meta["signature"] = node["signature"]
        if node.get("is_method") is not None:
            meta["is_method"] = bool(node.get("is_method", False))

        complexity = node.get("complexity", {})
        if complexity:
            meta["cyclomatic"] = complexity.get("cyclomatic", 0)
            meta["cognitive"] = complexity.get("cognitive", 0)
            meta["loc"] = complexity.get("lines_of_code", 0)

        return meta
