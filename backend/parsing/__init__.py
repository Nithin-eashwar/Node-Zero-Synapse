"""
Parsing module - Code parsing and entity extraction.

This module handles AST parsing using tree-sitter and extracts
rich metadata from code including functions, classes, and complexity metrics.
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
]
