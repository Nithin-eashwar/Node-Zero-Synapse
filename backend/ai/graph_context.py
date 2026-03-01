"""
Graph-Aware Context Builder for RAG Pipeline.

Extracts rich structural context from the code knowledge graph
to augment LLM prompts with relationship, complexity, and 
architectural data that vector search alone cannot provide.
"""

from typing import Dict, List, Optional, Any


class GraphContextBuilder:
    """
    Builds graph-aware context strings for LLM consumption.
    
    Takes the graph store and raw node data, and for
    any entity or query, produces a rich context string that includes:
    - Function/class relationships (callers, callees, dependencies)
    - Complexity metrics (cyclomatic, cognitive, LOC)
    - Class hierarchy (inheritance, methods)
    - Blast radius summary
    - File-level overview
    """

    def __init__(self, graph_store, raw_data: List[Dict]):
        self.graph = graph_store
        self.raw_data = raw_data
        # Build lookup indices for fast access
        self._node_by_name: Dict[str, Dict] = {}
        self._nodes_by_file: Dict[str, List[Dict]] = {}
        self._classes: Dict[str, Dict] = {}
        self._build_indices()

    def _build_indices(self):
        """Build fast-lookup indices from raw node data."""
        for node in self.raw_data:
            name = node.get("name", "")
            self._node_by_name[name] = node
            
            # Also index by unique_id if available
            uid = node.get("unique_id", "") or self._compute_unique_id(node)
            if uid:
                self._node_by_name[uid] = node
            
            # File index
            file_path = node.get("file", "")
            if file_path not in self._nodes_by_file:
                self._nodes_by_file[file_path] = []
            self._nodes_by_file[file_path].append(node)
            
            # Class index
            if node.get("type") == "class":
                self._classes[name] = node

    def get_entity_context(self, entity_name: str) -> str:
        """
        Build rich context for a specific entity (function or class).
        
        Returns a structured string the LLM can reason over.
        """
        node = self._find_node(entity_name)
        if not node:
            return f"Entity '{entity_name}' not found in the knowledge graph."

        sections = []

        # 1. Identity & Signature
        sections.append(self._build_identity_section(node))

        # 2. Complexity Metrics
        if node.get("type") == "function":
            sections.append(self._build_complexity_section(node))

        # 3. Graph Relationships
        sections.append(self._build_relationship_section(entity_name, node))

        # 4. Class Context (if method or class)
        class_ctx = self._build_class_context(node)
        if class_ctx:
            sections.append(class_ctx)

        # 5. Blast Radius Summary
        sections.append(self._build_blast_radius_section(entity_name))

        # 6. File Context
        sections.append(self._build_file_context(node))

        return "\n\n".join(sections)

    def get_file_context(self, file_path: str) -> str:
        """Build context for an entire file."""
        nodes = self._nodes_by_file.get(file_path, [])
        if not nodes:
            return f"No entities found in file '{file_path}'."

        sections = [f"=== File: {file_path} ==="]

        # Separate classes and functions
        classes = [n for n in nodes if n.get("type") == "class"]
        functions = [n for n in nodes if n.get("type") == "function" and not n.get("is_method")]
        methods = [n for n in nodes if n.get("type") == "function" and n.get("is_method")]

        if classes:
            sections.append(f"Classes ({len(classes)}):")
            for cls in classes:
                bases = cls.get("bases", [])
                base_str = f" (extends {', '.join(bases)})" if bases else ""
                sections.append(f"  - {cls['name']}{base_str}: {cls.get('docstring', 'No description')}")
                if cls.get("methods"):
                    sections.append(f"    Methods: {', '.join(cls['methods'])}")

        if functions:
            sections.append(f"\nStandalone Functions ({len(functions)}):")
            for fn in functions:
                sig = fn.get("signature", fn["name"])
                sections.append(f"  - {sig}")
                if fn.get("docstring"):
                    # Take just first line of docstring
                    first_line = fn["docstring"].split("\n")[0].strip()
                    sections.append(f"    {first_line}")

        # File-level complexity summary
        all_funcs = [n for n in nodes if n.get("type") == "function"]
        if all_funcs:
            complexities = [n.get("complexity", {}).get("cyclomatic", 0) for n in all_funcs]
            avg_complexity = sum(complexities) / len(complexities)
            max_complexity = max(complexities)
            max_func = next(n["name"] for n in all_funcs 
                          if n.get("complexity", {}).get("cyclomatic", 0) == max_complexity)
            sections.append(f"\nComplexity Summary:")
            sections.append(f"  Average cyclomatic: {avg_complexity:.1f}")
            sections.append(f"  Most complex: {max_func} (cyclomatic={max_complexity})")

        return "\n".join(sections)

    def get_query_context(self, matched_names: List[str]) -> str:
        """
        Build context for a RAG query given matched entity names.
        
        This is the main entry point called from the RAG pipeline.
        For each entity matched by vector search, we enrich it with
        graph-aware context.
        """
        contexts = []
        seen_files = set()

        for name in matched_names[:5]:  # Limit to top 5 to avoid context bloat
            node = self._find_node(name)
            if not node:
                continue
            
            # Entity-level context
            contexts.append(self.get_entity_context(name))
            
            # Add file context once per unique file
            file_path = node.get("file", "")
            if file_path and file_path not in seen_files:
                seen_files.add(file_path)
                contexts.append(self.get_file_context(file_path))

        if not contexts:
            return ""

        return "\n\n---\n\n".join(contexts)

    def get_graph_summary(self) -> str:
        """Build a high-level summary of the entire graph."""
        total_nodes = self.graph.number_of_nodes()
        total_edges = self.graph.number_of_edges()
        
        num_classes = len(self._classes)
        num_functions = sum(1 for n in self.raw_data if n.get("type") == "function")
        num_files = len(self._nodes_by_file)

        # Find highly connected nodes (potential hotspots)
        hotspots = []
        if total_nodes > 0:
            all_nodes = self.graph.get_all_nodes()
            in_degs = [(n, self.graph.in_degree(n)) for n in all_nodes]
            in_degs.sort(key=lambda x: x[1], reverse=True)
            hotspots = [(name, deg) for name, deg in in_degs[:5] if deg > 0]

        summary = [
            f"=== Codebase Graph Summary ===",
            f"Files: {num_files} | Classes: {num_classes} | Functions: {num_functions}",
            f"Graph: {total_nodes} nodes, {total_edges} edges",
        ]

        if hotspots:
            summary.append(f"\nMost depended-upon entities:")
            for name, deg in hotspots:
                summary.append(f"  - {name} ({deg} dependents)")

        return "\n".join(summary)

    # ---- Private helper methods ----

    def _find_node(self, name: str) -> Optional[Dict]:
        """Find a node by name or unique_id."""
        # Direct match
        if name in self._node_by_name:
            return self._node_by_name[name]
        # Partial match (e.g., "process" matching "DataProcessor.process")
        for key, node in self._node_by_name.items():
            if key.endswith(f".{name}") or key.endswith(f":{name}"):
                return node
        return None

    def _compute_unique_id(self, node: Dict) -> str:
        """Compute a stable unique id for nodes that lack one."""
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

    def _build_identity_section(self, node: Dict) -> str:
        """Build the identity/signature section."""
        node_type = node.get("type", "unknown")
        name = node.get("name", "unknown")
        
        lines = [f"=== {node_type.title()}: {name} ==="]
        
        if node.get("signature"):
            lines.append(f"Signature: {node['signature']}")
        if node.get("file"):
            line_range = node.get("range", [])
            loc = f" (lines {line_range[0]}-{line_range[1]})" if len(line_range) >= 2 else ""
            lines.append(f"File: {node['file']}{loc}")
        if node.get("docstring"):
            lines.append(f"Description: {node['docstring']}")
        if node.get("decorators"):
            lines.append(f"Decorators: {', '.join(node['decorators'])}")
        
        # Function-specific flags
        flags = []
        if node.get("is_async"):
            flags.append("async")
        if node.get("is_generator"):
            flags.append("generator")
        if node.get("is_static"):
            flags.append("static")
        if node.get("is_classmethod"):
            flags.append("classmethod")
        if node.get("is_property"):
            flags.append("property")
        if node.get("is_abstract"):
            flags.append("abstract")
        if flags:
            lines.append(f"Flags: {', '.join(flags)}")

        return "\n".join(lines)

    def _build_complexity_section(self, node: Dict) -> str:
        """Build complexity metrics section."""
        complexity = node.get("complexity", {})
        if not complexity:
            return "Complexity: No data available"

        cyclomatic = complexity.get("cyclomatic", 0)
        cognitive = complexity.get("cognitive", 0)
        loc = complexity.get("lines_of_code", 0)

        # Interpret the metrics
        risk = "low"
        if cyclomatic > 10:
            risk = "HIGH"
        elif cyclomatic > 5:
            risk = "moderate"

        lines = [
            f"Complexity Metrics:",
            f"  Cyclomatic: {cyclomatic} ({risk} risk)",
            f"  Cognitive: {cognitive}",
            f"  Lines of Code: {loc}",
        ]

        return "\n".join(lines)

    def _build_relationship_section(self, entity_name: str, node: Dict) -> str:
        """Build graph relationship section."""
        lines = ["Graph Relationships:"]

        # Direct calls this entity makes
        calls = node.get("calls", [])
        if calls:
            # Filter out builtins and common patterns
            meaningful_calls = [c for c in calls if not c.startswith(("print", "len", "str", "range", "enumerate"))]
            if meaningful_calls:
                lines.append(f"  Calls: {', '.join(meaningful_calls[:10])}")

        # Who calls this entity (from graph)
        if self.graph.has_node(entity_name):
            preds = self.graph.predecessors(entity_name)
            if preds:
                lines.append(f"  Called by: {', '.join(preds[:10])}")
            
            succs = self.graph.successors(entity_name)
            if succs:
                lines.append(f"  Depends on: {', '.join(succs[:10])}")

        # Globals
        reads = node.get("reads_globals", [])
        writes = node.get("writes_globals", [])
        if reads:
            lines.append(f"  Reads globals: {', '.join(reads)}")
        if writes:
            lines.append(f"  Writes globals: {', '.join(writes)}")

        if len(lines) == 1:
            lines.append("  No relationships found in graph")

        return "\n".join(lines)

    def _build_class_context(self, node: Dict) -> Optional[str]:
        """Build class hierarchy context."""
        if node.get("type") == "class":
            lines = [f"Class Details:"]
            bases = node.get("bases", [])
            if bases:
                lines.append(f"  Inherits: {', '.join(bases)}")
            lines.append(f"  Inheritance depth: {node.get('inheritance_depth', 0)}")
            methods = node.get("methods", [])
            if methods:
                lines.append(f"  Methods: {', '.join(methods)}")
            class_vars = node.get("class_variables", [])
            if class_vars:
                lines.append(f"  Class variables: {', '.join(class_vars)}")
            inst_vars = node.get("instance_variables", [])
            if inst_vars:
                lines.append(f"  Instance variables: {', '.join(inst_vars)}")
            if node.get("is_dataclass"):
                lines.append(f"  Type: dataclass")
            if node.get("is_abstract"):
                lines.append(f"  Type: abstract")
            return "\n".join(lines)
        
        # If it's a method, show its parent class context
        parent_class = node.get("parent_class")
        if parent_class and parent_class in self._classes:
            cls = self._classes[parent_class]
            lines = [f"Parent Class: {parent_class}"]
            bases = cls.get("bases", [])
            if bases:
                lines.append(f"  Inherits: {', '.join(bases)}")
            methods = cls.get("methods", [])
            if methods:
                lines.append(f"  Sibling methods: {', '.join(m for m in methods if m != node.get('name'))}")
            return "\n".join(lines)

        return None

    def _build_blast_radius_section(self, entity_name: str) -> str:
        """Build blast radius summary from graph."""
        if not self.graph.has_node(entity_name):
            return "Blast Radius: Entity not in dependency graph"

        try:
            ancestors = list(self.graph.ancestors(entity_name))
            descendants = list(self.graph.descendants(entity_name))
        except Exception:
            return "Blast Radius: Unable to calculate"

        lines = [
            f"Impact Analysis:",
            f"  Upstream (affected if this changes): {len(ancestors)} entities",
            f"  Downstream (this depends on): {len(descendants)} entities",
        ]
        
        if ancestors:
            lines.append(f"  Affected: {', '.join(ancestors[:8])}")
            if len(ancestors) > 8:
                lines.append(f"  ... and {len(ancestors) - 8} more")

        # Risk level based on blast radius
        total_impact = len(ancestors)
        if total_impact > 10:
            lines.append(f"  ⚠️ HIGH blast radius - changes here are risky")
        elif total_impact > 5:
            lines.append(f"  ⚡ MODERATE blast radius - test carefully")
        else:
            lines.append(f"  ✅ LOW blast radius - changes are relatively safe")

        return "\n".join(lines)

    def _build_file_context(self, node: Dict) -> str:
        """Brief file context for the entity."""
        file_path = node.get("file", "")
        nodes_in_file = self._nodes_by_file.get(file_path, [])
        
        other_entities = [n["name"] for n in nodes_in_file if n["name"] != node.get("name")]
        
        if not other_entities:
            return f"File Context: Only entity in {file_path}"
        
        return f"File Context: {file_path} also contains: {', '.join(other_entities[:8])}"
