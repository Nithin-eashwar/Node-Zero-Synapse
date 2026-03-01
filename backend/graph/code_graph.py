"""
Knowledge graph construction and analysis for code dependencies.

This module builds a NetworkX graph from extracted relationships
and provides advanced analysis capabilities including:
- Blast radius calculation
- Dependency analysis
- Change impact assessment
"""

import json
from .graph_store_factory import create_graph_store
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass

from .relationships import Relationship, RelationType, RelationshipGraph
from backend.parsing.entities import ParsedFile


# --- CONFIGURATION ---
INPUT_FILE = "repo_graph.json"

# Risk scoring weights
RISK_WEIGHTS = {
    'complexity': 0.25,      # Code complexity impact
    'centrality': 0.20,      # Graph centrality (how connected)
    'test_coverage': 0.20,   # Whether tests cover this
    'dependency_count': 0.15, # Number of dependencies
    'change_frequency': 0.10, # How often code changes
    'bus_factor': 0.10,      # Author concentration
}


@dataclass
class RiskFactors:
    """
    Detailed breakdown of risk factors for a code change.
    
    Each factor is normalized to 0.0 - 1.0 where higher = more risky.
    """
    complexity_risk: float = 0.0      # Based on cyclomatic/cognitive complexity
    centrality_risk: float = 0.0      # Based on graph centrality (hub = risky)
    test_coverage_risk: float = 0.5   # 0.0 = well tested, 1.0 = no tests
    dependency_risk: float = 0.0      # Based on # of things depending on this
    change_frequency_risk: float = 0.0  # Recently changed = unstable
    bus_factor_risk: float = 0.5      # Single expert = risky
    
    @property
    def weighted_total(self) -> float:
        """Calculate weighted total risk score."""
        total = (
            self.complexity_risk * RISK_WEIGHTS['complexity'] +
            self.centrality_risk * RISK_WEIGHTS['centrality'] +
            self.test_coverage_risk * RISK_WEIGHTS['test_coverage'] +
            self.dependency_risk * RISK_WEIGHTS['dependency_count'] +
            self.change_frequency_risk * RISK_WEIGHTS['change_frequency'] +
            self.bus_factor_risk * RISK_WEIGHTS['bus_factor']
        )
        return min(total, 1.0)
    
    def to_dict(self) -> Dict:
        return {
            "complexity_risk": round(self.complexity_risk, 3),
            "centrality_risk": round(self.centrality_risk, 3),
            "test_coverage_risk": round(self.test_coverage_risk, 3),
            "dependency_risk": round(self.dependency_risk, 3),
            "change_frequency_risk": round(self.change_frequency_risk, 3),
            "bus_factor_risk": round(self.bus_factor_risk, 3),
            "weighted_total": round(self.weighted_total, 3)
        }
    
    def get_top_risks(self, threshold: float = 0.5) -> List[str]:
        """Get list of risk factors above threshold."""
        risks = []
        if self.complexity_risk >= threshold:
            risks.append(f"High complexity ({self.complexity_risk:.0%})")
        if self.centrality_risk >= threshold:
            risks.append(f"High centrality - hub node ({self.centrality_risk:.0%})")
        if self.test_coverage_risk >= threshold:
            risks.append(f"Low test coverage ({self.test_coverage_risk:.0%})")
        if self.dependency_risk >= threshold:
            risks.append(f"Many dependencies ({self.dependency_risk:.0%})")
        if self.change_frequency_risk >= threshold:
            risks.append(f"Frequently changed ({self.change_frequency_risk:.0%})")
        if self.bus_factor_risk >= threshold:
            risks.append(f"Low bus factor ({self.bus_factor_risk:.0%})")
        return risks


@dataclass
class ImpactAssessment:
    """
    Assessment of the impact of changing a code entity.
    
    Attributes:
        target: The entity being analyzed
        direct_callers: Functions that directly call this entity
        indirect_callers: Functions that indirectly depend on this entity
        affected_tests: Test functions that would be affected
        risk_score: Overall risk score (0.0 - 1.0)
        risk_factors: Detailed breakdown of risk factors
        affected_by_type: Breakdown of affected entities by relationship type
        recommendations: List of recommendations based on analysis
    """
    target: str
    direct_callers: List[str]
    indirect_callers: List[str]
    affected_tests: List[str]
    risk_score: float
    affected_by_type: Dict[str, List[str]]
    blast_radius: int  # Total count of affected entities
    risk_factors: RiskFactors = None
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.risk_factors is None:
            self.risk_factors = RiskFactors()
        if self.recommendations is None:
            self.recommendations = []
    
    def to_dict(self) -> Dict:
        return {
            "target": self.target,
            "blast_radius": self.blast_radius,
            "risk_score": round(self.risk_score, 3),
            "risk_level": self._get_risk_level(),
            "risk_factors": self.risk_factors.to_dict() if self.risk_factors else {},
            "direct_callers": self.direct_callers,
            "indirect_callers": self.indirect_callers,
            "affected_tests": self.affected_tests,
            "affected_by_type": self.affected_by_type,
            "recommendations": self.recommendations,
            "top_risks": self.risk_factors.get_top_risks() if self.risk_factors else []
        }
    
    def _get_risk_level(self) -> str:
        """Get human-readable risk level."""
        if self.risk_score < 0.2:
            return "LOW"
        elif self.risk_score < 0.5:
            return "MEDIUM"
        elif self.risk_score < 0.8:
            return "HIGH"
        else:
            return "CRITICAL"


class CodeGraph:
    """
    Knowledge graph for code analysis.
    
    Uses a pluggable graph store backend (NetworkX local or Neptune AWS).
    """
    
    def __init__(self):
        self.store = create_graph_store()
        self.entity_metadata: Dict[str, Dict] = {}
        self.relationships: List[Relationship] = []
    
    def add_entity(self, entity_id: str, metadata: Optional[Dict] = None):
        """Add a code entity node to the graph."""
        self.store.add_node(entity_id)
        if metadata:
            self.entity_metadata[entity_id] = metadata
    
    def add_relationship(self, rel: Relationship):
        """Add a relationship edge to the graph."""
        self.relationships.append(rel)
        
        # Add edge with relationship metadata
        self.store.add_edge(
            rel.source,
            rel.target,
            type=rel.rel_type.value,
            weight=rel.weight,
            line=rel.line,
            context=rel.context
        )
    
    def add_relationships(self, rels: List[Relationship]):
        """Add multiple relationships."""
        for rel in rels:
            self.add_relationship(rel)
    
    def get_callers(self, entity_id: str) -> List[str]:
        """Get all entities that call this entity (predecessors with CALLS edge)."""
        callers = []
        for pred in self.store.predecessors(entity_id):
            edge_data = self.store.get_edge_data(pred, entity_id)
            if edge_data and edge_data.get("type") == RelationType.CALLS.value:
                callers.append(pred)
        return callers
    
    def get_callees(self, entity_id: str) -> List[str]:
        """Get all entities that this entity calls."""
        callees = []
        for succ in self.store.successors(entity_id):
            edge_data = self.store.get_edge_data(entity_id, succ)
            if edge_data and edge_data.get("type") == RelationType.CALLS.value:
                callees.append(succ)
        return callees
    
    def get_dependencies(self, entity_id: str, rel_types: Optional[Set[RelationType]] = None) -> List[str]:
        """Get all entities this entity depends on."""
        if rel_types is None:
            rel_types = {RelationType.CALLS, RelationType.IMPORTS, 
                        RelationType.INHERITS, RelationType.USES_TYPE}
        
        deps = []
        for succ in self.store.successors(entity_id):
            edge_data = self.store.get_edge_data(entity_id, succ)
            if edge_data and edge_data.get("type") in {rt.value for rt in rel_types}:
                deps.append(succ)
        return deps
    
    def get_dependents(self, entity_id: str, rel_types: Optional[Set[RelationType]] = None) -> List[str]:
        """Get all entities that depend on this entity."""
        if rel_types is None:
            rel_types = {RelationType.CALLS, RelationType.IMPORTS, 
                        RelationType.INHERITS, RelationType.USES_TYPE}
        
        deps = []
        for pred in self.store.predecessors(entity_id):
            edge_data = self.store.get_edge_data(pred, entity_id)
            if edge_data and edge_data.get("type") in {rt.value for rt in rel_types}:
                deps.append(pred)
        return deps
    
    def calculate_blast_radius(self, target: str, complexity_data: Optional[Dict] = None) -> ImpactAssessment:
        """
        Calculate the full blast radius of changing an entity.
        
        Args:
            target: Entity ID to analyze
            complexity_data: Optional dict mapping entity_id -> complexity metrics
            
        Returns:
            ImpactAssessment with full impact analysis including enhanced risk factors
        """
        if not self.store.has_node(target):
            return ImpactAssessment(
                target=target,
                direct_callers=[],
                indirect_callers=[],
                affected_tests=[],
                risk_score=0.0,
                affected_by_type={},
                blast_radius=0
            )
        
        # Get direct callers
        direct_callers = self.get_callers(target)
        
        # Get all transitive dependencies (who would be affected)
        all_affected = set()
        self._collect_upstream(target, all_affected)
        all_affected.discard(target)  # Remove self
        
        # Separate indirect callers
        indirect_callers = [a for a in all_affected if a not in direct_callers]
        
        # Identify affected tests
        affected_tests = [a for a in all_affected 
                        if 'test' in a.lower() or a.startswith('test_')]
        
        # Categorize by relationship type
        affected_by_type = self._categorize_affected(target, all_affected)
        
        # Calculate enhanced risk factors
        risk_factors = self._calculate_enhanced_risk_factors(
            target=target,
            direct_callers=direct_callers,
            indirect_callers=indirect_callers,
            affected_tests=affected_tests,
            complexity_data=complexity_data
        )
        
        # Use weighted total as risk score
        risk_score = risk_factors.weighted_total
        
        # Generate recommendations
        recommendations = self._generate_recommendations(risk_factors, affected_tests)
        
        return ImpactAssessment(
            target=target,
            direct_callers=direct_callers,
            indirect_callers=indirect_callers,
            affected_tests=affected_tests,
            risk_score=risk_score,
            affected_by_type=affected_by_type,
            blast_radius=len(all_affected),
            risk_factors=risk_factors,
            recommendations=recommendations
        )
    
    def _calculate_enhanced_risk_factors(
        self,
        target: str,
        direct_callers: List[str],
        indirect_callers: List[str],
        affected_tests: List[str],
        complexity_data: Optional[Dict] = None
    ) -> RiskFactors:
        """
        Calculate comprehensive risk factors for an entity.
        
        Uses graph analysis, complexity metrics, and coverage data
        to produce a detailed risk breakdown.
        """
        # 1. Complexity Risk
        complexity_risk = 0.0
        if complexity_data and target in complexity_data:
            metrics = complexity_data[target]
            cyclomatic = metrics.get('cyclomatic', 0)
            cognitive = metrics.get('cognitive', 0)
            # Normalize: 10+ cyclomatic = high risk
            complexity_risk = min((cyclomatic + cognitive / 2) / 15, 1.0)
        else:
            # Default: check entity metadata for stored complexity
            metadata = self.entity_metadata.get(target, {})
            if 'complexity' in metadata:
                complexity_risk = min(metadata['complexity'] / 15, 1.0)
        
        # 2. Centrality Risk (how connected is this node)
        centrality_risk = self._calculate_centrality_risk(target)
        
        # 3. Test Coverage Risk
        test_coverage_risk = 1.0  # Assume no coverage
        if affected_tests:
            # More tests = less risk
            test_coverage_risk = max(0.0, 1.0 - len(affected_tests) * 0.3)
        
        # 4. Dependency Risk (many dependents = high risk)
        total_dependents = len(direct_callers) + len(indirect_callers)
        dependency_risk = min(total_dependents / 10, 1.0)
        
        # 5. Change Frequency Risk (placeholder - would need git integration)
        # For now, use graph degree as proxy (highly connected = often changed)
        in_deg = self.store.in_degree(target) if self.store.has_node(target) else 0
        out_deg = self.store.out_degree(target) if self.store.has_node(target) else 0
        change_frequency_risk = min((in_deg + out_deg) / 20, 1.0)
        
        # 6. Bus Factor Risk (placeholder - would need git integration)
        # For now, default to medium risk
        bus_factor_risk = 0.5
        
        return RiskFactors(
            complexity_risk=complexity_risk,
            centrality_risk=centrality_risk,
            test_coverage_risk=test_coverage_risk,
            dependency_risk=dependency_risk,
            change_frequency_risk=change_frequency_risk,
            bus_factor_risk=bus_factor_risk
        )
    
    def _calculate_centrality_risk(self, target: str) -> float:
        """
        Calculate centrality-based risk using graph algorithms.
        
        Uses betweenness centrality to identify critical path nodes.
        """
        try:
            if self.store.number_of_nodes() < 3:
                return 0.0
            
            # Calculate betweenness centrality for the target
            centrality = self.store.betweenness_centrality()
            target_centrality = centrality.get(target, 0.0)
            
            # Normalize against max centrality in graph
            max_centrality = max(centrality.values()) if centrality else 1.0
            if max_centrality > 0:
                normalized = target_centrality / max_centrality
            else:
                normalized = 0.0
            
            return min(normalized, 1.0)
        except Exception:
            # Fallback to simple degree-based calculation
            if self.store.has_node(target):
                degree = self.store.in_degree(target) + self.store.out_degree(target)
                return min(degree / 20, 1.0)
            return 0.0
    
    def _generate_recommendations(
        self,
        risk_factors: RiskFactors,
        affected_tests: List[str]
    ) -> List[str]:
        """Generate actionable recommendations based on risk factors."""
        recommendations = []
        
        if risk_factors.complexity_risk >= 0.7:
            recommendations.append("Consider refactoring to reduce complexity before changes")
        
        if risk_factors.test_coverage_risk >= 0.7:
            if not affected_tests:
                recommendations.append("Add unit tests before modifying this code")
            else:
                recommendations.append("Consider adding more test coverage")
        
        if risk_factors.centrality_risk >= 0.6:
            recommendations.append("This is a critical path node - changes will have wide impact")
        
        if risk_factors.dependency_risk >= 0.6:
            recommendations.append("Many modules depend on this - coordinate with affected teams")
        
        if risk_factors.bus_factor_risk >= 0.7:
            recommendations.append("Consider pair programming or code review with another developer")
        
        if not recommendations:
            recommendations.append("Risk level acceptable for standard development workflow")
        
        return recommendations
    
    def _collect_upstream(self, entity_id: str, collected: Set[str]):
        """Recursively collect all upstream dependencies."""
        for pred in self.store.predecessors(entity_id):
            if pred not in collected:
                collected.add(pred)
                self._collect_upstream(pred, collected)
    
    def _categorize_affected(self, target: str, affected: Set[str]) -> Dict[str, List[str]]:
        """Categorize affected entities by how they're related."""
        categories: Dict[str, List[str]] = {
            "callers": [],
            "inheritors": [],
            "type_users": []
        }
        
        for entity in affected:
            for succ in self.store.successors(entity):
                if succ == target or succ in affected:
                    edge_data = self.store.get_edge_data(entity, succ)
                    if edge_data:
                        edge_type = edge_data.get("type")
                        if edge_type == RelationType.CALLS.value:
                            if entity not in categories["callers"]:
                                categories["callers"].append(entity)
                        elif edge_type == RelationType.INHERITS.value:
                            if entity not in categories["inheritors"]:
                                categories["inheritors"].append(entity)
                        elif edge_type == RelationType.USES_TYPE.value:
                            if entity not in categories["type_users"]:
                                categories["type_users"].append(entity)
        
        return categories
    
    def get_inheritance_tree(self, class_id: str) -> Dict:
        """Get the inheritance tree for a class."""
        tree = {"class": class_id, "bases": [], "subclasses": []}
        
        # Get bases
        for succ in self.store.successors(class_id):
            edge_data = self.store.get_edge_data(class_id, succ)
            if edge_data and edge_data.get("type") == RelationType.INHERITS.value:
                tree["bases"].append(succ)
        
        # Get subclasses
        for pred in self.store.predecessors(class_id):
            edge_data = self.store.get_edge_data(pred, class_id)
            if edge_data and edge_data.get("type") == RelationType.INHERITS.value:
                tree["subclasses"].append(pred)
        
        return tree
    
    def find_cycles(self) -> List[List[str]]:
        """Find all cycles in the dependency graph."""
        try:
            return self.store.find_cycles()
        except:
            return []
    
    def get_statistics(self) -> Dict:
        """Get graph statistics."""
        stats = {
            "nodes": self.store.number_of_nodes(),
            "edges": self.store.number_of_edges(),
            "density": self.store.density(),
        }
        
        # Count edge types from tracked relationships
        edge_types = {}
        for rel in self.relationships:
            rel_type = rel.rel_type.value
            edge_types[rel_type] = edge_types.get(rel_type, 0) + 1
        stats["edge_types"] = edge_types
        
        return stats


def build_dependency_graph(data: List[Dict]) -> CodeGraph:
    """
    Build a CodeGraph from parsed entity data.
    
    Args:
        data: List of entity dictionaries (from repo_graph.json)
        
    Returns:
        Populated CodeGraph
    """
    graph = CodeGraph()
    
    # Add all entities as nodes
    for entity in data:
        entity_id = entity.get("unique_id") or entity.get("name")
        graph.add_entity(entity_id, metadata={
            "type": entity.get("type"),
            "file": entity.get("file"),
            "name": entity.get("name"),
            "range": entity.get("range")
        })
    
    # Build a lookup for entities
    entities_by_name = {}
    for entity in data:
        name = entity.get("name")
        if name:
            if name not in entities_by_name:
                entities_by_name[name] = []
            entities_by_name[name].append(entity)
    
    print("[*] Building Links...")
    
    # Add call relationships
    for entity in data:
        if entity.get("type") != "function":
            continue
            
        caller_id = entity.get("unique_id") or entity.get("name")
        calls = entity.get("calls", [])
        
        for call_str in calls:
            # Try to resolve the call
            target_id = _resolve_call(call_str, entities_by_name)
            
            if target_id:
                rel = Relationship(
                    source=caller_id,
                    target=target_id,
                    rel_type=RelationType.CALLS,
                    context=call_str
                )
                graph.add_relationship(rel)
                print(f"  [LINK] {caller_id} -> {target_id}")
    
    # Add inheritance relationships for classes
    for entity in data:
        if entity.get("type") != "class":
            continue
            
        class_id = entity.get("unique_id") or entity.get("name")
        bases = entity.get("bases", [])
        
        for base in bases:
            # Try to find base class
            base_entities = entities_by_name.get(base, [])
            if base_entities:
                base_id = base_entities[0].get("unique_id") or base
            else:
                base_id = base
            
            rel = Relationship(
                source=class_id,
                target=base_id,
                rel_type=RelationType.INHERITS
            )
            graph.add_relationship(rel)
            print(f"  [INHERITS] {class_id} -> {base_id}")
    
    return graph


def _resolve_call(call_str: str, entities_by_name: Dict[str, List]) -> Optional[str]:
    """Simple call resolution for backward compatibility."""
    # Extract function name from call
    parts = call_str.split(".")
    func_name = parts[-1].split("(")[0]
    
    # Direct match
    candidates = entities_by_name.get(func_name, [])
    if candidates:
        return candidates[0].get("unique_id") or func_name
    
    # Check if full call matches any entity
    for name, entities in entities_by_name.items():
        if call_str.endswith(name) or name == call_str:
            return entities[0].get("unique_id") or name
    
    return None


def calculate_blast_radius(G: CodeGraph, target_function: str) -> ImpactAssessment:
    """
    Calculate blast radius for a function.
    
    Args:
        G: CodeGraph instance
        target_function: Function ID to analyze
        
    Returns:
        ImpactAssessment with full analysis
    """
    print(f"\n[*] Calculating Blast Radius for: '{target_function}'")
    
    assessment = G.calculate_blast_radius(target_function)
    
    if assessment.blast_radius == 0:
        print("[OK] Safe! No other functions depend on this.")
    else:
        print(f"[!] WARNING: Changing this affects {assessment.blast_radius} functions!")
        print(f"    Direct callers: {len(assessment.direct_callers)}")
        print(f"    Indirect callers: {len(assessment.indirect_callers)}")
        print(f"    Risk score: {assessment.risk_score:.2f}")
        
        if assessment.direct_callers:
            print("\n    Direct callers:")
            for caller in assessment.direct_callers[:5]:
                print(f"      - {caller}")
            if len(assessment.direct_callers) > 5:
                print(f"      ... and {len(assessment.direct_callers) - 5} more")
    
    return assessment


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # 1. Load Data
    with open(INPUT_FILE, "r") as f:
        data = json.load(f)
    
    # 2. Build Graph
    print("[*] Building dependency graph...")
    graph = build_dependency_graph(data)
    
    stats = graph.get_statistics()
    print(f"\n[INFO] Graph Stats: {stats['nodes']} nodes, {stats['edges']} edges")
    print(f"[INFO] Edge types: {stats['edge_types']}")
    
    # 3. Simulate a User Query
    target = "process_data"
    
    # Try to find the entity
    found = None
    for entity in data:
        if entity.get("name") == target:
            found = entity.get("unique_id") or target
            break
    
    if found:
        assessment = calculate_blast_radius(graph, found)
    else:
        print(f"[ERROR] Function '{target}' not found in graph.")