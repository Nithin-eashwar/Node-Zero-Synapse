"""
Graph module - Relationship extraction and code graph analysis.

This module handles building and analyzing the code knowledge graph,
including relationship types, call resolution, and blast radius calculation.
"""

from .relationships import (
    RelationType,
    Relationship,
    RelationshipGraph
)

from .resolver import (
    ImportMapping,
    EntityRegistry,
    CallResolver,
    ResolvedCall,
    build_registry_from_parsed_files
)

from .extractor import (
    RelationshipExtractor,
    extract_relationships
)

from .code_graph import (
    CodeGraph,
    ImpactAssessment,
    RiskFactors,
    build_dependency_graph,
    calculate_blast_radius
)

__all__ = [
    # Relationships
    "RelationType",
    "Relationship",
    "RelationshipGraph",
    # Resolver
    "ImportMapping",
    "EntityRegistry",
    "CallResolver",
    "ResolvedCall",
    "build_registry_from_parsed_files",
    # Extractor
    "RelationshipExtractor",
    "extract_relationships",
    # Graph
    "CodeGraph",
    "ImpactAssessment",
    "RiskFactors",
    "build_dependency_graph",
    "calculate_blast_radius",
]
