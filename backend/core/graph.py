"""
Knowledge graph construction and analysis for code dependencies.

This module builds a NetworkX graph from extracted relationships
and provides advanced analysis capabilities including:
- Blast radius calculation
- Dependency analysis
- Change impact assessment
"""

import json
import networkx as nx
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass

from .relationships import Relationship, RelationType, RelationshipGraph
from .entities import ParsedFile


# --- CONFIGURATION ---
INPUT_FILE = "repo_graph.json"


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
        affected_by_type: Breakdown of affected entities by relationship type
    """
    target: str
    direct_callers: List[str]
    indirect_callers: List[str]
    affected_tests: List[str]
    risk_score: float
    affected_by_type: Dict[str, List[str]]
    blast_radius: int  # Total count of affected entities
    
    def to_dict(self) -> Dict:
        return {
            "target": self.target,
            "blast_radius": self.blast_radius,
            "risk_score": self.risk_score,
            "direct_callers": self.direct_callers,
            "indirect_callers": self.indirect_callers,
            "affected_tests": self.affected_tests,
            "affected_by_type": self.affected_by_type
        }


class CodeGraph:
    """
    Knowledge graph for code analysis.
    
    Wraps a NetworkX DiGraph with relationship-aware operations.
    """
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.entity_metadata: Dict[str, Dict] = {}
        self.relationships: List[Relationship] = []
    
    def add_entity(self, entity_id: str, metadata: Optional[Dict] = None):
        """Add a code entity node to the graph."""
        self.graph.add_node(entity_id)
        if metadata:
            self.entity_metadata[entity_id] = metadata
    
    def add_relationship(self, rel: Relationship):
        """Add a relationship edge to the graph."""
        self.relationships.append(rel)
        
        # Add edge with relationship metadata
        self.graph.add_edge(
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
        for pred in self.graph.predecessors(entity_id):
            edge_data = self.graph.get_edge_data(pred, entity_id)
            if edge_data and edge_data.get("type") == RelationType.CALLS.value:
                callers.append(pred)
        return callers
    
    def get_callees(self, entity_id: str) -> List[str]:
        """Get all entities that this entity calls."""
        callees = []
        for succ in self.graph.successors(entity_id):
            edge_data = self.graph.get_edge_data(entity_id, succ)
            if edge_data and edge_data.get("type") == RelationType.CALLS.value:
                callees.append(succ)
        return callees
    
    def get_dependencies(self, entity_id: str, rel_types: Optional[Set[RelationType]] = None) -> List[str]:
        """Get all entities this entity depends on."""
        if rel_types is None:
            rel_types = {RelationType.CALLS, RelationType.IMPORTS, 
                        RelationType.INHERITS, RelationType.USES_TYPE}
        
        deps = []
        for succ in self.graph.successors(entity_id):
            edge_data = self.graph.get_edge_data(entity_id, succ)
            if edge_data and edge_data.get("type") in {rt.value for rt in rel_types}:
                deps.append(succ)
        return deps
    
    def get_dependents(self, entity_id: str, rel_types: Optional[Set[RelationType]] = None) -> List[str]:
        """Get all entities that depend on this entity."""
        if rel_types is None:
            rel_types = {RelationType.CALLS, RelationType.IMPORTS, 
                        RelationType.INHERITS, RelationType.USES_TYPE}
        
        deps = []
        for pred in self.graph.predecessors(entity_id):
            edge_data = self.graph.get_edge_data(pred, entity_id)
            if edge_data and edge_data.get("type") in {rt.value for rt in rel_types}:
                deps.append(pred)
        return deps
    
    def calculate_blast_radius(self, target: str) -> ImpactAssessment:
        """
        Calculate the full blast radius of changing an entity.
        
        Args:
            target: Entity ID to analyze
            
        Returns:
            ImpactAssessment with full impact analysis
        """
        if target not in self.graph:
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
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(
            len(direct_callers), 
            len(indirect_callers),
            len(affected_tests)
        )
        
        return ImpactAssessment(
            target=target,
            direct_callers=direct_callers,
            indirect_callers=indirect_callers,
            affected_tests=affected_tests,
            risk_score=risk_score,
            affected_by_type=affected_by_type,
            blast_radius=len(all_affected)
        )
    
    def _collect_upstream(self, entity_id: str, collected: Set[str]):
        """Recursively collect all upstream dependencies."""
        for pred in self.graph.predecessors(entity_id):
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
            for succ in self.graph.successors(entity):
                if succ == target or succ in affected:
                    edge_data = self.graph.get_edge_data(entity, succ)
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
    
    def _calculate_risk_score(self, direct: int, indirect: int, tests: int) -> float:
        """Calculate a risk score based on impact."""
        # Base score from direct callers
        score = min(direct * 0.2, 0.5)
        
        # Add for indirect impact
        score += min(indirect * 0.05, 0.3)
        
        # Reduce if tests exist (they'll catch issues)
        if tests > 0:
            score *= 0.8
        
        return min(score, 1.0)
    
    def get_inheritance_tree(self, class_id: str) -> Dict:
        """Get the inheritance tree for a class."""
        tree = {"class": class_id, "bases": [], "subclasses": []}
        
        # Get bases
        for succ in self.graph.successors(class_id):
            edge_data = self.graph.get_edge_data(class_id, succ)
            if edge_data and edge_data.get("type") == RelationType.INHERITS.value:
                tree["bases"].append(succ)
        
        # Get subclasses
        for pred in self.graph.predecessors(class_id):
            edge_data = self.graph.get_edge_data(pred, class_id)
            if edge_data and edge_data.get("type") == RelationType.INHERITS.value:
                tree["subclasses"].append(pred)
        
        return tree
    
    def find_cycles(self) -> List[List[str]]:
        """Find all cycles in the dependency graph."""
        try:
            cycles = list(nx.simple_cycles(self.graph))
            return cycles
        except:
            return []
    
    def get_statistics(self) -> Dict:
        """Get graph statistics."""
        stats = {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "density": nx.density(self.graph) if self.graph.number_of_nodes() > 0 else 0,
        }
        
        # Count edge types
        edge_types = {}
        for u, v, data in self.graph.edges(data=True):
            edge_type = data.get("type", "unknown")
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
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