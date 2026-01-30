"""
Core module for Node-Zero-Synapse code analysis.
"""

from .entities import (
    EntityType,
    Parameter,
    FunctionEntity,
    ClassEntity,
    ImportEntity,
    ModuleEntity,
    VariableEntity,
    ParsedFile
)

from .complexity import (
    calculate_cyclomatic_complexity,
    calculate_cognitive_complexity,
    count_lines_of_code,
    count_total_lines,
    contains_yield,
    contains_await,
    get_accessed_globals,
    extract_local_definitions,
    ScopeTracker,
    PYTHON_BUILTINS
)

from .parser import (
    parse_file,
    scan_repository,
    get_all_entities
)

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

from .relationship_extractor import (
    RelationshipExtractor,
    extract_relationships
)

from .graph import (
    CodeGraph,
    ImpactAssessment,
    build_dependency_graph,
    calculate_blast_radius
)

__all__ = [
    # Entities
    "EntityType",
    "Parameter",
    "FunctionEntity", 
    "ClassEntity",
    "ImportEntity",
    "ModuleEntity",
    "VariableEntity",
    "ParsedFile",
    # Complexity
    "calculate_cyclomatic_complexity",
    "calculate_cognitive_complexity",
    "count_lines_of_code",
    "count_total_lines",
    "contains_yield",
    "contains_await",
    "get_accessed_globals",
    "extract_local_definitions",
    "ScopeTracker",
    "PYTHON_BUILTINS",
    # Parser
    "parse_file",
    "scan_repository",
    "get_all_entities",
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
    # Relationship Extractor
    "RelationshipExtractor",
    "extract_relationships",
    # Graph
    "CodeGraph",
    "ImpactAssessment",
    "build_dependency_graph",
    "calculate_blast_radius",
]
