"""
Relationship types and models for code graph analysis.

This module defines all the relationship types that can exist
between code entities in the knowledge graph.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class RelationType(Enum):
    """
    Types of relationships between code entities.
    
    These represent the edges in the knowledge graph.
    """
    
    # === Structural Relationships ===
    CONTAINS = "CONTAINS"           # File/Module contains Function/Class
    DEFINES = "DEFINES"             # Module defines a variable/constant
    
    # === Call Relationships ===
    CALLS = "CALLS"                 # Function calls another function
    INSTANTIATES = "INSTANTIATES"   # Function creates instance of class
    
    # === Inheritance Relationships ===
    INHERITS = "INHERITS"           # Class extends another class
    IMPLEMENTS = "IMPLEMENTS"       # Class implements Protocol/ABC
    OVERRIDES = "OVERRIDES"         # Method overrides parent method
    
    # === Import Relationships ===
    IMPORTS = "IMPORTS"             # Module imports from another module
    IMPORTS_FROM = "IMPORTS_FROM"   # Specific name imported from module
    
    # === Decorator Relationships ===
    DECORATES = "DECORATES"         # Decorator wraps function/class
    
    # === Type Relationships ===
    USES_TYPE = "USES_TYPE"         # Function/param uses type in annotation
    RETURNS_TYPE = "RETURNS_TYPE"   # Function returns a specific type
    
    # === Data Flow Relationships ===
    READS_GLOBAL = "READS_GLOBAL"   # Function reads global variable
    WRITES_GLOBAL = "WRITES_GLOBAL" # Function writes global variable
    
    # === Exception Relationships ===
    RAISES = "RAISES"               # Function raises exception type
    CATCHES = "CATCHES"             # Function catches exception type


@dataclass
class Relationship:
    """
    Represents a relationship (edge) between two code entities.
    
    Attributes:
        source: Unique identifier of the source entity
        target: Unique identifier of the target entity
        rel_type: Type of relationship
        weight: Coupling strength (0.0 to 1.0)
        line: Line number where relationship occurs
        context: Additional context about the relationship
        metadata: Any extra metadata
    """
    source: str
    target: str
    rel_type: RelationType
    
    # Optional metadata
    weight: float = 1.0
    line: Optional[int] = None
    context: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize relationship to dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "type": self.rel_type.value,
            "weight": self.weight,
            "line": self.line,
            "context": self.context,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relationship":
        """Deserialize relationship from dictionary."""
        return cls(
            source=data["source"],
            target=data["target"],
            rel_type=RelationType(data["type"]),
            weight=data.get("weight", 1.0),
            line=data.get("line"),
            context=data.get("context"),
            metadata=data.get("metadata", {})
        )


@dataclass
class RelationshipGraph:
    """
    Collection of relationships extracted from a codebase.
    
    Provides methods to query and analyze relationships.
    """
    relationships: List[Relationship] = field(default_factory=list)
    
    def add(self, rel: Relationship):
        """Add a relationship to the graph."""
        self.relationships.append(rel)
    
    def add_all(self, rels: List[Relationship]):
        """Add multiple relationships."""
        self.relationships.extend(rels)
    
    def get_by_source(self, source: str) -> List[Relationship]:
        """Get all relationships from a source entity."""
        return [r for r in self.relationships if r.source == source]
    
    def get_by_target(self, target: str) -> List[Relationship]:
        """Get all relationships pointing to a target entity."""
        return [r for r in self.relationships if r.target == target]
    
    def get_by_type(self, rel_type: RelationType) -> List[Relationship]:
        """Get all relationships of a specific type."""
        return [r for r in self.relationships if r.rel_type == rel_type]
    
    def get_callers(self, entity_id: str) -> List[str]:
        """Get all entities that call this entity."""
        return [r.source for r in self.relationships 
                if r.target == entity_id and r.rel_type == RelationType.CALLS]
    
    def get_callees(self, entity_id: str) -> List[str]:
        """Get all entities that this entity calls."""
        return [r.target for r in self.relationships 
                if r.source == entity_id and r.rel_type == RelationType.CALLS]
    
    def get_inheritance_chain(self, class_id: str) -> List[str]:
        """Get the inheritance chain for a class (ancestors)."""
        chain = []
        current = class_id
        visited = set()
        
        while current and current not in visited:
            visited.add(current)
            parents = [r.target for r in self.relationships 
                      if r.source == current and r.rel_type == RelationType.INHERITS]
            if parents:
                chain.extend(parents)
                current = parents[0]  # Follow first parent
            else:
                break
        
        return chain
    
    def get_subclasses(self, class_id: str) -> List[str]:
        """Get all classes that inherit from this class."""
        return [r.source for r in self.relationships 
                if r.target == class_id and r.rel_type == RelationType.INHERITS]
    
    def get_dependents(self, entity_id: str) -> List[str]:
        """Get all entities that depend on this entity (callers, inheritors, importers)."""
        dependent_types = {RelationType.CALLS, RelationType.INHERITS, 
                          RelationType.IMPORTS, RelationType.USES_TYPE}
        return list(set(r.source for r in self.relationships 
                       if r.target == entity_id and r.rel_type in dependent_types))
    
    def get_dependencies(self, entity_id: str) -> List[str]:
        """Get all entities that this entity depends on."""
        dependent_types = {RelationType.CALLS, RelationType.INHERITS, 
                          RelationType.IMPORTS, RelationType.USES_TYPE}
        return list(set(r.target for r in self.relationships 
                       if r.source == entity_id and r.rel_type in dependent_types))
    
    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Serialize all relationships to list of dictionaries."""
        return [r.to_dict() for r in self.relationships]
    
    def statistics(self) -> Dict[str, int]:
        """Get statistics about relationship types."""
        stats = {}
        for rel_type in RelationType:
            count = len([r for r in self.relationships if r.rel_type == rel_type])
            if count > 0:
                stats[rel_type.value] = count
        stats["total"] = len(self.relationships)
        return stats
