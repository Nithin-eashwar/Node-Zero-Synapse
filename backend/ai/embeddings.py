from sentence_transformers import SentenceTransformer
from typing import List, Dict
import os


# Model comparison:
#   all-MiniLM-L6-v2:   384-dim, 22M params, fast but lower accuracy
#   all-mpnet-base-v2:  768-dim, 109M params, ~10% better retrieval accuracy
#   all-MiniLM-L12-v2:  384-dim, 33M params, balanced speed/quality
EMBEDDING_MODEL_DEFAULT = "all-mpnet-base-v2"


class CodeEmbedder:
    def __init__(self, model_name=None):
        model_name = model_name or os.getenv("EMBEDDING_MODEL", EMBEDDING_MODEL_DEFAULT)
        print(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self._model_name = model_name
        self._dim = self.model.get_sentence_embedding_dimension()
        print(f"Embedding model loaded. (dim={self._dim})")

    @property
    def embedding_dim(self) -> int:
        """Return the dimension of the embedding vectors."""
        return self._dim

    def embed_text(self, text):
        return self.model.encode(text).tolist()

    def embed_nodes(self, nodes: List[Dict]):
        """
        Embeds a list of nodes (functions/classes) for search.
        
        Constructs a rich text representation for each node that
        captures its full semantic meaning:
        - Identity (type, name, signature)
        - Purpose (docstring)
        - Structure (parameters, return type, parent class)
        - Relationships (calls, inheritance)
        - Complexity (metrics)
        """
        embeddings = []
        for node in nodes:
            text_rep = self._build_rich_representation(node)
            embeddings.append(self.embed_text(text_rep))
        return embeddings

    def _build_rich_representation(self, node: Dict) -> str:
        """
        Build a semantically rich text representation of a code entity.
        
        This is the text that gets embedded into the vector space.
        Better representations = better search results.
        """
        node_type = node.get("type", "unknown")
        name = node.get("name", "unknown")
        
        if node_type == "class":
            return self._build_class_text(node)
        else:
            return self._build_function_text(node)

    def _build_function_text(self, node: Dict) -> str:
        """Build rich text for a function/method node."""
        parts = []
        
        # Type and identity
        if node.get("is_method"):
            parent = node.get("parent_class", "")
            parts.append(f"Method {parent}.{node['name']}")
        else:
            parts.append(f"Function {node['name']}")
        
        # Full signature (most important for matching)
        if node.get("signature"):
            parts.append(f"Signature: {node['signature']}")
        
        # File location
        parts.append(f"File: {node.get('file', 'unknown')}")
        
        # Purpose/description
        if node.get("docstring"):
            parts.append(f"Purpose: {node['docstring']}")
        
        # Parameters (helps match queries about inputs)
        params = node.get("parameters", [])
        if params:
            param_strs = []
            for p in params:
                p_str = p.get("name", "?")
                if p.get("type_hint"):
                    p_str += f": {p['type_hint']}"
                if p.get("default_value"):
                    p_str += f" = {p['default_value']}"
                param_strs.append(p_str)
            parts.append(f"Parameters: {', '.join(param_strs)}")
        
        # Return type
        if node.get("return_type"):
            parts.append(f"Returns: {node['return_type']}")
        
        # Parent class context
        if node.get("parent_class"):
            parts.append(f"Class: {node['parent_class']}")
        
        # What it calls (dependencies)
        calls = node.get("calls", [])
        if calls:
            # Filter noise (builtins, self.attribute access)
            meaningful = [c for c in calls 
                         if c not in ("print", "len", "str", "range", "int", "float", "list", "dict", "set", "tuple")
                         and not c.endswith(".append")
                         and not c.endswith(".get")]
            if meaningful:
                parts.append(f"Calls: {', '.join(meaningful[:10])}")
        
        # Complexity (helps match "complex", "risky" queries)
        complexity = node.get("complexity", {})
        if complexity:
            cyc = complexity.get("cyclomatic", 0)
            cog = complexity.get("cognitive", 0)
            loc = complexity.get("lines_of_code", 0)
            if cyc > 5:
                parts.append(f"Complexity: cyclomatic={cyc} cognitive={cog} (high)")
            elif cyc > 1:
                parts.append(f"Complexity: cyclomatic={cyc} cognitive={cog}")
        
        # Special flags
        flags = []
        if node.get("is_async"):
            flags.append("async")
        if node.get("is_generator"):
            flags.append("generator")
        if node.get("is_static"):
            flags.append("static")
        if node.get("is_property"):
            flags.append("property")
        if flags:
            parts.append(f"Flags: {', '.join(flags)}")
        
        return "\n".join(parts)

    def _build_class_text(self, node: Dict) -> str:
        """Build rich text for a class node."""
        parts = []
        
        # Identity
        parts.append(f"Class {node['name']}")
        
        # File
        parts.append(f"File: {node.get('file', 'unknown')}")
        
        # Docstring
        if node.get("docstring"):
            parts.append(f"Purpose: {node['docstring']}")
        
        # Inheritance
        bases = node.get("bases", [])
        if bases:
            parts.append(f"Inherits from: {', '.join(bases)}")
        
        # Methods (critical for matching)
        methods = node.get("methods", [])
        if methods:
            parts.append(f"Methods: {', '.join(methods)}")
        
        # Variables
        class_vars = node.get("class_variables", [])
        if class_vars:
            parts.append(f"Fields: {', '.join(class_vars)}")
        
        inst_vars = node.get("instance_variables", [])
        if inst_vars:
            parts.append(f"Instance variables: {', '.join(inst_vars)}")
        
        # Type flags
        flags = []
        if node.get("is_dataclass"):
            flags.append("dataclass")
        if node.get("is_abstract"):
            flags.append("abstract")
        if node.get("is_protocol"):
            flags.append("protocol")
        if node.get("decorators"):
            flags.extend(node["decorators"])
        if flags:
            parts.append(f"Type: {', '.join(flags)}")
        
        return "\n".join(parts)
