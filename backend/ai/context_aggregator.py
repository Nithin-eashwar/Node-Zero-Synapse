"""
Multi-Source Context Aggregator for Synapse RAG Pipeline.

Collects live data from multiple backend features and injects it
into the LLM prompt alongside vector search results. Based on the
detected query intent, it fetches relevant data from:
- Blast radius calculations (graph analysis)
- Governance violations (architecture validator)
- Expertise scores (git blame analysis)
- Complexity metrics (parsing data)
"""

from typing import Dict, List, Optional, Any
from .prompts import QueryIntent


class ContextAggregator:
    """
    Aggregates context from multiple backend sources for the RAG pipeline.
    
    Instead of relying solely on vector search, this fetches live 
    feature-specific data and formats it for LLM consumption.
    """

    def __init__(self, graph_store, raw_data: List[Dict]):
        self.graph = graph_store
        self.raw_data = raw_data
        
        # Build lookup indices
        self._node_by_name: Dict[str, Dict] = {}
        self._nodes_by_file: Dict[str, List[Dict]] = {}
        for node in self.raw_data:
            self._node_by_name[node.get("name", "")] = node
            file_path = node.get("file", "")
            if file_path not in self._nodes_by_file:
                self._nodes_by_file[file_path] = []
            self._nodes_by_file[file_path].append(node)

        # Lazy-loaded services (avoid import-time failures)
        self._validator = None
        self._drift_detector = None

    async def gather(self, intent: QueryIntent, entity_names: List[str], repo_path: str = None) -> str:
        """
        Gather feature-specific context based on query intent.
        
        Returns a formatted string ready to inject into the LLM prompt.
        """
        sections = []

        if intent == QueryIntent.BLAST_RADIUS:
            sections.append(self._gather_blast_radius(entity_names))
            sections.append(self._gather_complexity(entity_names))

        elif intent == QueryIntent.GOVERNANCE:
            sections.append(self._gather_governance(repo_path))

        elif intent == QueryIntent.EXPERTISE:
            sections.append(await self._gather_file_ownership(entity_names, repo_path))

        elif intent == QueryIntent.COMPLEXITY:
            sections.append(self._gather_complexity(entity_names))
            sections.append(self._gather_complexity_hotspots())

        else:  # GENERAL - light context from all sources
            sections.append(self._gather_graph_stats())

        # Filter out empty sections
        result = "\n\n".join(s for s in sections if s)
        return result if result else "No additional feature data available."

    # ─────────────────────────────────────────────
    # Blast Radius Data
    # ─────────────────────────────────────────────

    def _gather_blast_radius(self, entity_names: List[str]) -> str:
        """Compute live blast radius for matched entities."""
        lines = ["=== LIVE BLAST RADIUS ANALYSIS ==="]
        
        for name in entity_names[:3]:
            if not self.graph.has_node(name):
                continue
            
            try:
                anc = list(self.graph.ancestors(name))
                desc = list(self.graph.descendants(name))
            except Exception:
                continue
            
            lines.append(f"\n📍 Target: {name}")
            lines.append(f"  Upstream impact (breaks if this changes): {len(anc)} entities")
            if anc:
                lines.append(f"  Affected: {', '.join(anc[:10])}")
            
            lines.append(f"  Downstream deps (this depends on): {len(desc)} entities")
            if desc:
                lines.append(f"  Dependencies: {', '.join(desc[:10])}")
            
            # Risk level
            total = len(anc)
            if total > 10:
                lines.append(f"  ⚠️ RISK: HIGH — changes affect {total} entities")
            elif total > 5:
                lines.append(f"  ⚡ RISK: MODERATE — test carefully")
            else:
                lines.append(f"  ✅ RISK: LOW — relatively safe to change")
            
            # Identify if it's a hub node
            if self.graph.number_of_nodes() > 0:
                in_deg = self.graph.in_degree(name)
                out_deg = self.graph.out_degree(name)
                lines.append(f"  Connectivity: {in_deg} callers, {out_deg} callees")
        
        return "\n".join(lines) if len(lines) > 1 else ""

    # ─────────────────────────────────────────────
    # Governance Data
    # ─────────────────────────────────────────────

    def _gather_governance(self, repo_path: str = None) -> str:
        """Fetch live governance data (violations, drift)."""
        lines = ["=== LIVE ARCHITECTURE ANALYSIS ==="]
        
        try:
            from backend.governance import ArchitectureValidator
            validator = ArchitectureValidator()
            path = repo_path or self._find_repo_path()
            
            if not path:
                return "Governance: No repository path configured"
            
            result = validator.validate_repository(path)
            
            lines.append(f"\nFiles analyzed: {result.total_files}")
            lines.append(f"Total violations: {result.total_violations}")
            lines.append(f"Total warnings: {result.total_warnings}")
            
            # Show violations
            if result.all_violations:
                lines.append(f"\n🚨 Violations ({len(result.all_violations)}):")
                for v in result.all_violations[:8]:
                    v_dict = v.to_dict()
                    lines.append(f"  - [{v_dict.get('severity', 'ERROR')}] {v_dict.get('message', 'Unknown')}")
                    if v_dict.get('file'):
                        lines.append(f"    File: {v_dict['file']}")
                if len(result.all_violations) > 8:
                    lines.append(f"  ... and {len(result.all_violations) - 8} more")
            else:
                lines.append("\n✅ No architectural violations found!")
            
            # Show warnings
            if result.all_warnings:
                lines.append(f"\n⚡ Warnings ({len(result.all_warnings)}):")
                for w in result.all_warnings[:5]:
                    w_dict = w.to_dict()
                    lines.append(f"  - {w_dict.get('message', 'Unknown')}")
            
        except ImportError:
            lines.append("Governance module not available")
        except Exception as e:
            lines.append(f"Governance analysis error: {str(e)}")
        
        return "\n".join(lines)

    # ─────────────────────────────────────────────
    # Expertise / Ownership Data
    # ─────────────────────────────────────────────

    async def _gather_file_ownership(self, entity_names: List[str], repo_path: str = None) -> str:
        """Gather file ownership info for matched entities."""
        lines = ["=== CODE OWNERSHIP ANALYSIS ==="]
        
        # Get unique files for the matched entities
        files_seen = set()
        for name in entity_names:
            node = self._node_by_name.get(name)
            if node:
                files_seen.add(node.get("file", ""))
        
        if not files_seen:
            return ""
        
        for file_path in list(files_seen)[:3]:
            if not file_path:
                continue
            
            lines.append(f"\n📁 File: {file_path}")
            
            # Entities in this file
            file_nodes = self._nodes_by_file.get(file_path, [])
            funcs = [n for n in file_nodes if n.get("type") == "function"]
            classes = [n for n in file_nodes if n.get("type") == "class"]
            
            if classes:
                lines.append(f"  Classes: {', '.join(c['name'] for c in classes)}")
            if funcs:
                lines.append(f"  Functions: {len(funcs)} total")
            
            # Complexity distribution
            if funcs:
                complexities = [n.get("complexity", {}).get("cyclomatic", 0) for n in funcs]
                avg = sum(complexities) / len(complexities)
                max_c = max(complexities)
                max_func = next(n["name"] for n in funcs 
                              if n.get("complexity", {}).get("cyclomatic", 0) == max_c)
                lines.append(f"  Avg complexity: {avg:.1f}, Hotspot: {max_func} (cyc={max_c})")
            
            # Try to get git blame data
            try:
                from backend.git.smart_git import get_git_blame
                blame_data = await get_git_blame(file_path, repo_path=repo_path)
                if blame_data and blame_data.get("primary_expert"):
                    expert = blame_data["primary_expert"]
                    score = blame_data.get("score") or {}
                    confidence = score.get("confidence", 0)
                    lines.append(
                        f"  Recommended expert: {expert.get('name', 'Unknown')} "
                        f"(confidence: {confidence:.0%})"
                    )
                    recommendation = blame_data.get("recommendation")
                    if recommendation:
                        lines.append(f"  Recommendation: {recommendation}")
                    reasoning = score.get("reasoning")
                    if reasoning:
                        lines.append(f"  Reasoning: {reasoning}")
            except Exception:
                # Git blame may not work without a real repo
                lines.append(f"  (Git blame data not available)")
        
        return "\n".join(lines) if len(lines) > 1 else ""

    # ─────────────────────────────────────────────
    # Complexity Data
    # ─────────────────────────────────────────────

    def _gather_complexity(self, entity_names: List[str]) -> str:
        """Gather detailed complexity metrics for matched entities."""
        lines = ["=== COMPLEXITY METRICS ==="]
        
        for name in entity_names[:5]:
            node = self._node_by_name.get(name)
            if not node:
                continue
            
            complexity = node.get("complexity", {})
            if not complexity:
                continue
            
            cyc = complexity.get("cyclomatic", 0)
            cog = complexity.get("cognitive", 0)
            loc = complexity.get("lines_of_code", 0)
            
            risk = "🔴 HIGH" if cyc > 10 else ("🟡 MODERATE" if cyc > 5 else "🟢 LOW")
            
            lines.append(f"\n{node.get('type', 'entity').title()}: {name}")
            lines.append(f"  Cyclomatic complexity: {cyc} ({risk})")
            lines.append(f"  Cognitive complexity: {cog}")
            lines.append(f"  Lines of code: {loc}")
            
            if node.get("signature"):
                lines.append(f"  Signature: {node['signature']}")
            
            # Recommendations based on metrics
            if cyc > 10:
                lines.append(f"  ⚠️ Consider breaking this function into smaller pieces")
            if cog > 15:
                lines.append(f"  ⚠️ High cognitive load — simplify nested logic")
            if loc > 50:
                lines.append(f"  ⚠️ Long function — extract helper functions")
        
        return "\n".join(lines) if len(lines) > 1 else ""

    def _gather_complexity_hotspots(self) -> str:
        """Find the most complex entities across the entire codebase."""
        lines = ["=== CODEBASE COMPLEXITY HOTSPOTS ==="]
        
        # Collect all functions with complexity data
        scored = []
        for node in self.raw_data:
            if node.get("type") == "function":
                cyc = node.get("complexity", {}).get("cyclomatic", 0)
                if cyc > 0:
                    scored.append((node["name"], node.get("file", ""), cyc))
        
        if not scored:
            return ""
        
        # Top 5 by cyclomatic complexity
        scored.sort(key=lambda x: x[2], reverse=True)
        
        lines.append(f"\nTop complex functions (out of {len(scored)}):")
        for name, file_path, cyc in scored[:5]:
            risk = "🔴" if cyc > 10 else ("🟡" if cyc > 5 else "🟢")
            lines.append(f"  {risk} {name} (cyc={cyc}) — {file_path}")
        
        # Overall stats
        all_cyc = [s[2] for s in scored]
        avg = sum(all_cyc) / len(all_cyc)
        lines.append(f"\n  Average complexity: {avg:.1f}")
        lines.append(f"  Functions above threshold (>5): {sum(1 for c in all_cyc if c > 5)}")
        
        return "\n".join(lines)

    # ─────────────────────────────────────────────
    # Graph-level Stats
    # ─────────────────────────────────────────────

    def _gather_graph_stats(self) -> str:
        """Light-weight graph stats for general queries."""
        lines = ["=== GRAPH STATISTICS ==="]
        lines.append(f"Total nodes: {self.graph.number_of_nodes()}")
        lines.append(f"Total edges: {self.graph.number_of_edges()}")
        
        if self.graph.number_of_nodes() > 0:
            graph_density = self.graph.density()
            lines.append(f"Density: {graph_density:.4f}")
            
            # Most connected
            all_nodes = self.graph.get_all_nodes()
            in_degs = [(n, self.graph.in_degree(n)) for n in all_nodes]
            in_degs.sort(key=lambda x: x[1], reverse=True)
            if in_degs and in_degs[0][1] > 0:
                lines.append(f"Most depended-on: {in_degs[0][0]} ({in_degs[0][1]} callers)")
        
        return "\n".join(lines)

    def _find_repo_path(self) -> Optional[str]:
        """Try to infer the repo path from loaded data."""
        import os
        base = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(base, "..", "..", "dummy_repo")
        if os.path.exists(candidate):
            return os.path.abspath(candidate)
        return None
