"""
Relationship extraction from parsed code entities.

This module extracts all relationships between code entities,
building the complete knowledge graph edge set.
"""

from typing import List, Dict, Optional, Set
from backend.parsing.entities import (
    FunctionEntity, ClassEntity, ImportEntity, 
    ModuleEntity, VariableEntity, ParsedFile
)
from .relationships import Relationship, RelationType, RelationshipGraph
from .resolver import CallResolver, EntityRegistry, build_registry_from_parsed_files


class RelationshipExtractor:
    """
    Extracts relationships from parsed code entities.
    
    Analyzes parsed files to identify all relationships:
    - Call relationships (function calls)
    - Inheritance relationships (class extends)
    - Import relationships (module imports)
    - Decorator relationships
    - Type usage relationships
    - Global variable access
    """
    
    def __init__(self, parsed_files: List[ParsedFile]):
        """
        Initialize the extractor with parsed files.
        
        Args:
            parsed_files: List of ParsedFile objects from parser
        """
        self.parsed_files = parsed_files
        self.registry = build_registry_from_parsed_files(parsed_files)
        self.resolver = CallResolver(self.registry)
        
        # Set up import mappings for each file
        for pf in parsed_files:
            self.resolver.set_imports(pf.file_path, pf.imports)
        
        self.graph = RelationshipGraph()
    
    def extract_all(self) -> RelationshipGraph:
        """
        Extract all relationships from the parsed files.
        
        Returns:
            RelationshipGraph containing all extracted relationships
        """
        for pf in self.parsed_files:
            self._extract_containment(pf)
            self._extract_imports(pf)
            self._extract_global_access(pf)
            
            for func in pf.functions:
                self._extract_function_relationships(func)
            
            for cls in pf.classes:
                self._extract_class_relationships(cls, pf.file_path)
        
        return self.graph
    
    def _extract_containment(self, pf: ParsedFile):
        """Extract CONTAINS relationships (file contains entities)."""
        file_id = pf.file_path
        
        for func in pf.functions:
            if not func.parent_class:  # Only top-level functions
                self.graph.add(Relationship(
                    source=file_id,
                    target=func.unique_id,
                    rel_type=RelationType.CONTAINS,
                    line=func.start_line
                ))
        
        for cls in pf.classes:
            self.graph.add(Relationship(
                source=file_id,
                target=cls.unique_id,
                rel_type=RelationType.CONTAINS,
                line=cls.start_line
            ))
    
    def _extract_imports(self, pf: ParsedFile):
        """Extract import relationships."""
        file_id = pf.file_path
        
        for imp in pf.imports:
            if imp.imported_names:
                # from X import a, b, c
                for name in imp.imported_names:
                    target = f"{imp.module}.{name}" if imp.module else name
                    self.graph.add(Relationship(
                        source=file_id,
                        target=target,
                        rel_type=RelationType.IMPORTS_FROM,
                        line=imp.line,
                        metadata={
                            "module": imp.module,
                            "alias": imp.alias,
                            "import_type": imp.import_type.value if imp.import_type else None
                        }
                    ))
            else:
                # import X or import X as Y
                self.graph.add(Relationship(
                    source=file_id,
                    target=imp.module,
                    rel_type=RelationType.IMPORTS,
                    line=imp.line,
                    metadata={
                        "alias": imp.alias,
                        "import_type": imp.import_type.value if imp.import_type else None
                    }
                ))
    
    def _extract_function_relationships(self, func: FunctionEntity):
        """Extract relationships from a function entity."""
        func_id = func.unique_id
        
        # Extract call relationships
        for call in func.calls:
            resolved = self.resolver.resolve(call, func)
            
            if resolved.resolved_target:
                rel_type = RelationType.CALLS
                
                # Check if it's an instantiation
                if resolved.resolution_type == "instantiation":
                    rel_type = RelationType.INSTANTIATES
                
                self.graph.add(Relationship(
                    source=func_id,
                    target=resolved.resolved_target,
                    rel_type=rel_type,
                    context=call,
                    weight=resolved.confidence,
                    metadata={
                        "resolution_type": resolved.resolution_type,
                        "original_call": resolved.original_call
                    }
                ))
            else:
                # Still record unresolved calls for analysis
                self.graph.add(Relationship(
                    source=func_id,
                    target=call,
                    rel_type=RelationType.CALLS,
                    weight=0.5,
                    metadata={
                        "resolution_type": "unresolved",
                        "reason": resolved.metadata.get("reason", "unknown")
                    }
                ))
        
        # Extract decorator relationships
        for decorator in func.decorators:
            self.graph.add(Relationship(
                source=decorator,
                target=func_id,
                rel_type=RelationType.DECORATES,
                line=func.start_line - 1  # Decorators are typically on preceding lines
            ))
        
        # Extract type usage from return type
        if func.return_type:
            self._extract_type_usage(func_id, func.return_type, RelationType.RETURNS_TYPE)
        
        # Extract type usage from parameters
        for param in func.parameters:
            if param.type_hint:
                self._extract_type_usage(func_id, param.type_hint, RelationType.USES_TYPE)
    
    def _extract_type_usage(self, source_id: str, type_str: str, rel_type: RelationType):
        """Extract type usage relationships from type annotations."""
        # Parse type string to extract type names
        # Handle Optional[X], List[X], Dict[K, V], etc.
        types = self._parse_type_string(type_str)
        
        for type_name in types:
            # Skip builtins and primitives
            if type_name.lower() in {'int', 'str', 'float', 'bool', 'none', 'any', 
                                     'list', 'dict', 'set', 'tuple', 'optional',
                                     'union', 'callable'}:
                continue
            
            self.graph.add(Relationship(
                source=source_id,
                target=type_name,
                rel_type=rel_type,
                metadata={"type_annotation": type_str}
            ))
    
    def _parse_type_string(self, type_str: str) -> List[str]:
        """Parse a type annotation string to extract type names."""
        # Remove brackets and split
        clean = type_str.replace('[', ' ').replace(']', ' ')
        clean = clean.replace(',', ' ').replace('|', ' ')
        
        types = []
        for part in clean.split():
            part = part.strip()
            if part and not part.startswith('...'):
                types.append(part)
        
        return types
    
    def _extract_class_relationships(self, cls: ClassEntity, file_path: str):
        """Extract relationships from a class entity."""
        cls_id = cls.unique_id
        
        # Extract inheritance relationships
        for base in cls.bases:
            # Try to resolve base class
            base_entities = self.registry.find_by_name(base)
            if base_entities:
                base_id = base_entities[0].unique_id
            else:
                base_id = base  # Keep as unresolved name
            
            # Determine if it's INHERITS or IMPLEMENTS
            rel_type = RelationType.INHERITS
            if base in {'ABC', 'Protocol'} or base.endswith('Protocol'):
                rel_type = RelationType.IMPLEMENTS
            
            self.graph.add(Relationship(
                source=cls_id,
                target=base_id,
                rel_type=rel_type,
                line=cls.start_line,
                metadata={"is_abstract_base": base in {'ABC', 'Protocol'}}
            ))
        
        # Extract decorator relationships for class
        for decorator in cls.decorators:
            self.graph.add(Relationship(
                source=decorator,
                target=cls_id,
                rel_type=RelationType.DECORATES,
                line=cls.start_line - 1
            ))
        
        # Extract method override relationships
        self._extract_overrides(cls, file_path)
    
    def _extract_overrides(self, cls: ClassEntity, file_path: str):
        """Extract OVERRIDES relationships for class methods."""
        if not cls.bases:
            return
        
        # Get methods defined in this class
        class_methods = set(cls.methods)
        
        # For each base class, check if we override any methods
        for base_name in cls.bases:
            base_cls = self.registry.get_class(base_name)
            if base_cls:
                # Find methods that exist in both classes
                base_methods = set(base_cls.methods)
                overridden = class_methods & base_methods
                
                for method_name in overridden:
                    if method_name.startswith('_') and not method_name.startswith('__'):
                        continue  # Skip private methods
                    
                    # Find the actual method entities
                    child_method_id = f"{file_path}:{cls.name}.{method_name}"
                    parent_method_id = f"{base_cls.file_path}:{base_name}.{method_name}"
                    
                    self.graph.add(Relationship(
                        source=child_method_id,
                        target=parent_method_id,
                        rel_type=RelationType.OVERRIDES,
                        metadata={"parent_class": base_name}
                    ))
    
    def _extract_global_access(self, pf: ParsedFile):
        """Extract global variable read/write relationships."""
        for func in pf.functions:
            func_id = func.unique_id
            
            # Reads
            for global_var in func.reads_globals:
                self.graph.add(Relationship(
                    source=func_id,
                    target=global_var,
                    rel_type=RelationType.READS_GLOBAL,
                    metadata={"file": pf.file_path}
                ))
            
            # Writes
            for global_var in func.writes_globals:
                self.graph.add(Relationship(
                    source=func_id,
                    target=global_var,
                    rel_type=RelationType.WRITES_GLOBAL,
                    metadata={"file": pf.file_path}
                ))


def extract_relationships(parsed_files: List[ParsedFile]) -> RelationshipGraph:
    """
    Convenience function to extract all relationships from parsed files.
    
    Args:
        parsed_files: List of ParsedFile objects
        
    Returns:
        RelationshipGraph with all extracted relationships
    """
    extractor = RelationshipExtractor(parsed_files)
    return extractor.extract_all()
