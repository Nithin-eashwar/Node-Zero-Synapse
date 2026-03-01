"""
AI-Powered Blast Radius Explainer.

Takes the structured ImpactAssessment data from CodeGraph and uses
the LLM to generate natural language explanations with deeper 
reasoning about risk, impact chains, and actionable recommendations.
"""

import os
import dotenv
from typing import Dict, List, Optional
from langchain_core.prompts import ChatPromptTemplate
from .llm_factory import create_llm

dotenv.load_dotenv()


BLAST_RADIUS_EXPLAIN_PROMPT = ChatPromptTemplate.from_template("""You are Synapse, an AI-powered codebase intelligence assistant.
You are explaining the blast radius analysis for a code change.

=== TARGET ENTITY ===
{entity_info}

=== IMPACT ASSESSMENT DATA ===
{impact_data}

=== RISK FACTOR BREAKDOWN ===
{risk_breakdown}

=== DEPENDENCY CHAINS ===
{dependency_chains}

=== CODEBASE CONTEXT ===
{codebase_context}

Generate a clear, actionable blast radius explanation covering:

1. **Summary**: One-paragraph overview of the risk level and why
2. **Impact Chain**: Explain HOW changes propagate (A calls B, B is used by C, etc.)
3. **Key Risk Factors**: For each high-risk factor, explain WHY it's risky in plain language
4. **Testing Strategy**: Which tests are affected and what additional testing is needed
5. **Safe Change Checklist**: Concrete steps a developer should follow before making this change
6. **Recommendation**: Overall verdict — is this change safe, needs caution, or requires senior review?

Be specific — reference actual function names, files, and numbers from the data.
Keep it concise but thorough. Use bullet points for readability.

Explanation:""")


class BlastRadiusExplainer:
    """
    Generates AI-powered explanations for blast radius analysis.
    
    Takes structured ImpactAssessment data and produces human-readable
    explanations with reasoning about risk and impact.
    """

    def __init__(self):
        # Initialize LLM via factory (provider selected by LLM_PROVIDER env var)
        self.llm = create_llm(temperature=0.3)

    def explain(
        self,
        impact_dict: Dict,
        entity_node: Optional[Dict] = None,
        graph_nodes: Optional[List[Dict]] = None,
        nx_graph=None,
    ) -> Dict:
        """
        Generate an AI explanation for blast radius results.
        
        Args:
            impact_dict: Output from ImpactAssessment.to_dict()
            entity_node: Raw node data for the target entity
            graph_nodes: All raw nodes (for building context)
            nx_graph: NetworkX graph (for dependency chain analysis)
            
        Returns:
            Dict with explanation, risk_summary, and safe_to_change flag
        """
        if not self.llm:
            return {
                "explanation": "AI explanation unavailable (GOOGLE_API_KEY not set).",
                "risk_summary": impact_dict.get("risk_level", "UNKNOWN"),
                "safe_to_change": impact_dict.get("risk_score", 1.0) < 0.3
            }

        # Build context sections
        entity_info = self._build_entity_info(impact_dict, entity_node)
        impact_data = self._build_impact_data(impact_dict)
        risk_breakdown = self._build_risk_breakdown(impact_dict)
        dependency_chains = self._build_dependency_chains(impact_dict, nx_graph)
        codebase_context = self._build_codebase_context(impact_dict, graph_nodes)

        try:
            chain = BLAST_RADIUS_EXPLAIN_PROMPT | self.llm
            response = chain.invoke({
                "entity_info": entity_info,
                "impact_data": impact_data,
                "risk_breakdown": risk_breakdown,
                "dependency_chains": dependency_chains,
                "codebase_context": codebase_context,
            })

            risk_score = impact_dict.get("risk_score", 0)
            return {
                "explanation": response.content,
                "risk_summary": {
                    "level": impact_dict.get("risk_level", "UNKNOWN"),
                    "score": risk_score,
                    "top_risks": impact_dict.get("top_risks", []),
                },
                "safe_to_change": risk_score < 0.3,
                "blast_radius": impact_dict.get("blast_radius", 0),
                "affected_count": {
                    "direct": len(impact_dict.get("direct_callers", [])),
                    "indirect": len(impact_dict.get("indirect_callers", [])),
                    "tests": len(impact_dict.get("affected_tests", [])),
                }
            }
        except Exception as e:
            return {
                "explanation": f"AI explanation failed: {str(e)}",
                "risk_summary": impact_dict.get("risk_level", "UNKNOWN"),
                "safe_to_change": False
            }

    def _build_entity_info(self, impact: Dict, node: Optional[Dict]) -> str:
        """Build entity description section."""
        target = impact.get("target", "unknown")
        lines = [f"Entity: {target}"]
        
        if node:
            if node.get("signature"):
                lines.append(f"Signature: {node['signature']}")
            if node.get("file"):
                lines.append(f"File: {node['file']}")
            if node.get("docstring"):
                lines.append(f"Purpose: {node['docstring']}")
            if node.get("parent_class"):
                lines.append(f"Class: {node['parent_class']}")
            
            complexity = node.get("complexity", {})
            if complexity:
                lines.append(f"Cyclomatic: {complexity.get('cyclomatic', 0)}, "
                           f"Cognitive: {complexity.get('cognitive', 0)}, "
                           f"LOC: {complexity.get('lines_of_code', 0)}")
        
        return "\n".join(lines)

    def _build_impact_data(self, impact: Dict) -> str:
        """Build impact assessment section."""
        lines = [
            f"Blast Radius: {impact.get('blast_radius', 0)} entities affected",
            f"Risk Score: {impact.get('risk_score', 0):.1%}",
            f"Risk Level: {impact.get('risk_level', 'UNKNOWN')}",
        ]
        
        direct = impact.get("direct_callers", [])
        if direct:
            lines.append(f"\nDirect callers ({len(direct)}): {', '.join(direct[:10])}")
        
        indirect = impact.get("indirect_callers", [])
        if indirect:
            lines.append(f"Indirect callers ({len(indirect)}): {', '.join(indirect[:10])}")
        
        tests = impact.get("affected_tests", [])
        if tests:
            lines.append(f"Affected tests ({len(tests)}): {', '.join(tests)}")
        else:
            lines.append("Affected tests: NONE — no test coverage detected!")
        
        # By relationship type
        by_type = impact.get("affected_by_type", {})
        if by_type:
            lines.append(f"\nBreakdown by relationship type:")
            for rel_type, entities in by_type.items():
                lines.append(f"  {rel_type}: {len(entities)} ({', '.join(entities[:5])})")
        
        return "\n".join(lines)

    def _build_risk_breakdown(self, impact: Dict) -> str:
        """Build risk factor breakdown section."""
        risk_factors = impact.get("risk_factors", {})
        if not risk_factors:
            return "No detailed risk factors available."
        
        lines = ["Risk Factor Breakdown (0% = safe, 100% = critical):"]
        
        factor_labels = {
            "complexity_risk": ("Code Complexity", "Function has high cyclomatic/cognitive complexity"),
            "centrality_risk": ("Graph Centrality", "Entity is a hub node with many connections"),
            "test_coverage_risk": ("Test Coverage Gap", "Insufficient test coverage for this entity"),
            "dependency_risk": ("Dependency Count", "Many other entities depend on this one"),
            "change_frequency_risk": ("Change Frequency", "Entity has been changed frequently (unstable)"),
            "bus_factor_risk": ("Bus Factor", "Knowledge concentrated in few contributors"),
        }
        
        for key, (label, desc) in factor_labels.items():
            value = risk_factors.get(key, 0)
            bar = "█" * int(value * 10) + "░" * (10 - int(value * 10))
            status = "🔴" if value >= 0.7 else ("🟡" if value >= 0.4 else "🟢")
            lines.append(f"  {status} {label}: {value:.0%} {bar}")
            if value >= 0.5:
                lines.append(f"     → {desc}")
        
        top_risks = impact.get("top_risks", [])
        if top_risks:
            lines.append(f"\nTop risk alerts: {'; '.join(top_risks)}")
        
        recommendations = impact.get("recommendations", [])
        if recommendations:
            lines.append(f"\nRule-based recommendations:")
            for rec in recommendations:
                lines.append(f"  • {rec}")
        
        return "\n".join(lines)

    def _build_dependency_chains(self, impact: Dict, nx_graph=None) -> str:
        """Build dependency chain analysis."""
        target = impact.get("target", "")
        lines = []
        
        if nx_graph and target in nx_graph:
            # Show actual call chains
            direct = impact.get("direct_callers", [])
            
            if direct:
                lines.append("Call chains leading to this entity:")
                for caller in direct[:5]:
                    # Trace one level up from each direct caller
                    chain = [caller, "→", target]
                    if caller in nx_graph:
                        grandparents = list(nx_graph.predecessors(caller))
                        if grandparents:
                            chain = [grandparents[0], "→"] + chain
                    lines.append(f"  {'  '.join(chain)}")
            
            # Show outgoing dependencies
            successors = list(nx_graph.successors(target))
            if successors:
                lines.append(f"\nThis entity depends on: {', '.join(successors[:8])}")
                lines.append(f"(Changes to these could also break {target})")
        
        if not lines:
            lines.append("No dependency chain data available.")
        
        return "\n".join(lines)

    def _build_codebase_context(self, impact: Dict, graph_nodes: Optional[List[Dict]]) -> str:
        """Build codebase-level context."""
        if not graph_nodes:
            return "No codebase context available."
        
        total_functions = sum(1 for n in graph_nodes if n.get("type") == "function")
        total_classes = sum(1 for n in graph_nodes if n.get("type") == "class")
        blast = impact.get("blast_radius", 0)
        
        pct = (blast / max(total_functions, 1)) * 100
        
        lines = [
            f"Codebase: {total_functions} functions, {total_classes} classes",
            f"This change affects {blast} out of {total_functions} functions ({pct:.1f}% of codebase)",
        ]
        
        if pct > 30:
            lines.append("⚠️ This is a WIDE-REACHING change — affects over 30% of the codebase!")
        elif pct > 10:
            lines.append("⚡ Significant reach — affects more than 10% of entities")
        
        return "\n".join(lines)
