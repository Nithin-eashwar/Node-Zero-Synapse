"""
Smart call resolution for linking function calls to their definitions.

This module handles the complex task of resolving call expressions
to actual function/method definitions, accounting for:
- Import aliasing
- Method calls (self.method)
- Class instantiation
- Super() calls
- Module-qualified calls
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from .entities import FunctionEntity, ClassEntity, ImportEntity, ParsedFile


@dataclass
class ImportMapping:
    """
    Tracks how names are imported and aliased in a file.
    
    For example:
    - `import numpy as np` -> module_aliases["np"] = "numpy"
    - `from os.path import join` -> name_imports["join"] = "os.path.join"
    - `from utils import helper` -> name_imports["helper"] = "utils.helper"
    """
    # Alias -> Full module path
    module_aliases: Dict[str, str] = field(default_factory=dict)
    
    # Imported name -> Full qualified path
    name_imports: Dict[str, str] = field(default_factory=dict)
    
    # Star imports - modules where * was imported
    star_imports: List[str] = field(default_factory=list)
    
    @classmethod
    def from_imports(cls, imports: List[ImportEntity]) -> "ImportMapping":
        """Build import mapping from list of import entities."""
        mapping = cls()
        
        for imp in imports:
            if imp.alias:
                # import X as alias
                mapping.module_aliases[imp.alias] = imp.module
            elif imp.imported_names:
                # from X import a, b, c
                for name in imp.imported_names:
                    if name == "*":
                        mapping.star_imports.append(imp.module)
                    else:
                        full_path = f"{imp.module}.{name}" if imp.module else name
                        mapping.name_imports[name] = full_path
            else:
                # import X (no alias)
                # The module itself can be used as a prefix
                # e.g., import os -> os.path.join
                parts = imp.module.split(".")
                mapping.module_aliases[parts[0]] = parts[0]
        
        return mapping


@dataclass
class EntityRegistry:
    """
    Registry of all known entities for resolution.
    
    Provides fast lookup of entities by name and qualified path.
    """
    # Full unique_id -> Entity
    entities_by_id: Dict[str, object] = field(default_factory=dict)
    
    # Simple name -> List of entities with that name
    entities_by_name: Dict[str, List[object]] = field(default_factory=dict)
    
    # Class name -> ClassEntity
    classes: Dict[str, ClassEntity] = field(default_factory=dict)
    
    # File path -> List of entities in that file
    entities_by_file: Dict[str, List[object]] = field(default_factory=dict)
    
    def register(self, entity):
        """Register an entity for lookup."""
        unique_id = entity.unique_id
        name = entity.name
        
        self.entities_by_id[unique_id] = entity
        
        if name not in self.entities_by_name:
            self.entities_by_name[name] = []
        self.entities_by_name[name].append(entity)
        
        if hasattr(entity, 'file_path'):
            file_path = entity.file_path
            if file_path not in self.entities_by_file:
                self.entities_by_file[file_path] = []
            self.entities_by_file[file_path].append(entity)
        
        if isinstance(entity, ClassEntity):
            self.classes[name] = entity
    
    def register_all(self, entities: List):
        """Register multiple entities."""
        for entity in entities:
            self.register(entity)
    
    def find_by_name(self, name: str) -> List[object]:
        """Find all entities with a given name."""
        return self.entities_by_name.get(name, [])
    
    def find_by_id(self, unique_id: str) -> Optional[object]:
        """Find entity by unique ID."""
        return self.entities_by_id.get(unique_id)
    
    def find_in_file(self, file_path: str, name: str) -> Optional[object]:
        """Find entity by name within a specific file."""
        for entity in self.entities_by_file.get(file_path, []):
            if entity.name == name:
                return entity
        return None
    
    def get_class(self, name: str) -> Optional[ClassEntity]:
        """Get class entity by name."""
        return self.classes.get(name)


@dataclass
class ResolvedCall:
    """Result of resolving a call expression."""
    original_call: str           # The original call text (e.g., "self.validate")
    resolved_target: Optional[str]  # The resolved entity ID
    resolution_type: str         # "direct", "import", "method", "super", "instantiation", "unresolved"
    confidence: float            # Confidence in resolution (0.0 - 1.0)
    metadata: Dict = field(default_factory=dict)


class CallResolver:
    """
    Resolves function calls to their actual definitions.
    
    Handles various call patterns:
    - Direct calls: func_name()
    - Module calls: module.func_name()
    - Method calls: self.method_name(), obj.method()
    - Super calls: super().method()
    - Class instantiation: ClassName()
    - Import aliases: np.array() -> numpy.array()
    """
    
    def __init__(self, registry: EntityRegistry):
        self.registry = registry
        self._import_cache: Dict[str, ImportMapping] = {}
    
    def set_imports(self, file_path: str, imports: List[ImportEntity]):
        """Set import mapping for a file."""
        self._import_cache[file_path] = ImportMapping.from_imports(imports)
    
    def resolve(self, call_str: str, context: FunctionEntity) -> ResolvedCall:
        """
        Resolve a call string to a target entity.
        
        Args:
            call_str: The call expression (e.g., "helper.fetch_data", "self.validate")
            context: The function making the call (provides file and class context)
            
        Returns:
            ResolvedCall with resolution details
        """
        file_path = context.file_path
        parent_class = context.parent_class
        imports = self._import_cache.get(file_path, ImportMapping())
        
        # Case 1: self.method() - method call on current instance
        if call_str.startswith("self."):
            return self._resolve_self_call(call_str, parent_class, file_path)
        
        # Case 2: super().method() - call to parent class method
        if call_str.startswith("super()."):
            return self._resolve_super_call(call_str, parent_class, file_path)
        
        # Case 3: super().__init__() or super(Class, self).method()
        if call_str.startswith("super("):
            return self._resolve_super_call(call_str, parent_class, file_path)
        
        # Case 4: ClassName() - class instantiation (check if call is a known class)
        if call_str in self.registry.classes:
            return self._resolve_instantiation(call_str)
        
        # Case 5: module.function() or alias.function()
        if "." in call_str:
            return self._resolve_qualified_call(call_str, imports, file_path)
        
        # Case 6: Direct call - check local, then imports
        return self._resolve_direct_call(call_str, imports, file_path)
    
    def _resolve_self_call(self, call_str: str, parent_class: Optional[str], 
                           file_path: str) -> ResolvedCall:
        """Resolve self.method() calls."""
        method_name = call_str.split(".", 1)[1]
        # Remove any trailing () or arguments
        method_name = method_name.split("(")[0]
        
        if parent_class:
            # Look for method in current class
            target_id = f"{file_path}:{parent_class}.{method_name}"
            if self.registry.find_by_id(target_id):
                return ResolvedCall(
                    original_call=call_str,
                    resolved_target=target_id,
                    resolution_type="method",
                    confidence=1.0
                )
            
            # Check if method exists in parent classes
            parent_cls = self.registry.get_class(parent_class)
            if parent_cls and parent_cls.bases:
                for base in parent_cls.bases:
                    # Try to find the method in base class
                    base_entities = self.registry.find_by_name(method_name)
                    for entity in base_entities:
                        if hasattr(entity, 'parent_class') and entity.parent_class == base:
                            return ResolvedCall(
                                original_call=call_str,
                                resolved_target=entity.unique_id,
                                resolution_type="inherited_method",
                                confidence=0.9
                            )
        
        return ResolvedCall(
            original_call=call_str,
            resolved_target=None,
            resolution_type="unresolved",
            confidence=0.0,
            metadata={"reason": "method not found in class hierarchy"}
        )
    
    def _resolve_super_call(self, call_str: str, parent_class: Optional[str],
                            file_path: str) -> ResolvedCall:
        """Resolve super().method() calls."""
        # Extract method name
        if "()." in call_str:
            method_name = call_str.split("().", 1)[1].split("(")[0]
        else:
            method_name = "__init__"  # super() alone usually means super().__init__
        
        if parent_class:
            parent_cls = self.registry.get_class(parent_class)
            if parent_cls and parent_cls.bases:
                # Look in first base class (MRO simplified)
                base_name = parent_cls.bases[0]
                
                # Find the method in base class
                candidates = self.registry.find_by_name(method_name)
                for entity in candidates:
                    if hasattr(entity, 'parent_class') and entity.parent_class == base_name:
                        return ResolvedCall(
                            original_call=call_str,
                            resolved_target=entity.unique_id,
                            resolution_type="super",
                            confidence=0.95,
                            metadata={"base_class": base_name}
                        )
        
        return ResolvedCall(
            original_call=call_str,
            resolved_target=None,
            resolution_type="unresolved",
            confidence=0.0,
            metadata={"reason": "super class method not found"}
        )
    
    def _resolve_instantiation(self, call_str: str) -> ResolvedCall:
        """Resolve class instantiation like ClassName()."""
        class_entity = self.registry.get_class(call_str)
        if class_entity:
            return ResolvedCall(
                original_call=call_str,
                resolved_target=class_entity.unique_id,
                resolution_type="instantiation",
                confidence=1.0
            )
        
        return ResolvedCall(
            original_call=call_str,
            resolved_target=None,
            resolution_type="unresolved",
            confidence=0.0
        )
    
    def _resolve_qualified_call(self, call_str: str, imports: ImportMapping,
                                file_path: str) -> ResolvedCall:
        """Resolve module.function() or alias.function() calls."""
        parts = call_str.split(".")
        first_part = parts[0]
        rest = ".".join(parts[1:]).split("(")[0]  # Remove any arguments
        
        # Check if first part is an import alias
        if first_part in imports.module_aliases:
            full_module = imports.module_aliases[first_part]
            full_call = f"{full_module}.{rest}"
            
            # Try to find this in registry
            candidates = self.registry.find_by_name(rest)
            for entity in candidates:
                if full_module in entity.file_path or full_module in entity.unique_id:
                    return ResolvedCall(
                        original_call=call_str,
                        resolved_target=entity.unique_id,
                        resolution_type="import_alias",
                        confidence=0.9
                    )
            
            return ResolvedCall(
                original_call=call_str,
                resolved_target=full_call,
                resolution_type="external_module",
                confidence=0.7,
                metadata={"module": full_module, "function": rest}
            )
        
        # Check if it's an object method call (not self, but some other object)
        # e.g., processor.validate() where processor is a local variable
        candidates = self.registry.find_by_name(rest)
        if candidates:
            # Return first match with lower confidence
            return ResolvedCall(
                original_call=call_str,
                resolved_target=candidates[0].unique_id,
                resolution_type="object_method",
                confidence=0.6,
                metadata={"object": first_part}
            )
        
        return ResolvedCall(
            original_call=call_str,
            resolved_target=None,
            resolution_type="unresolved",
            confidence=0.0,
            metadata={"reason": "qualified name not found"}
        )
    
    def _resolve_direct_call(self, call_str: str, imports: ImportMapping,
                             file_path: str) -> ResolvedCall:
        """Resolve direct function calls like func_name()."""
        func_name = call_str.split("(")[0]
        
        # Check if it's a direct import
        if func_name in imports.name_imports:
            full_path = imports.name_imports[func_name]
            
            # Try to find in registry
            candidates = self.registry.find_by_name(func_name)
            for entity in candidates:
                return ResolvedCall(
                    original_call=call_str,
                    resolved_target=entity.unique_id,
                    resolution_type="import",
                    confidence=0.9
                )
            
            return ResolvedCall(
                original_call=call_str,
                resolved_target=full_path,
                resolution_type="external_import",
                confidence=0.7,
                metadata={"imported_from": full_path}
            )
        
        # Check local file
        local_entity = self.registry.find_in_file(file_path, func_name)
        if local_entity:
            return ResolvedCall(
                original_call=call_str,
                resolved_target=local_entity.unique_id,
                resolution_type="direct",
                confidence=1.0
            )
        
        # Check all entities by name
        candidates = self.registry.find_by_name(func_name)
        if candidates:
            return ResolvedCall(
                original_call=call_str,
                resolved_target=candidates[0].unique_id,
                resolution_type="global",
                confidence=0.8
            )
        
        # Check if it's a class instantiation
        if func_name in self.registry.classes:
            return self._resolve_instantiation(func_name)
        
        return ResolvedCall(
            original_call=call_str,
            resolved_target=None,
            resolution_type="unresolved",
            confidence=0.0,
            metadata={"reason": "function not found in scope"}
        )
    
    def resolve_all(self, context: FunctionEntity) -> List[ResolvedCall]:
        """Resolve all calls made by a function."""
        results = []
        for call in context.calls:
            results.append(self.resolve(call, context))
        return results


def build_registry_from_parsed_files(parsed_files: List[ParsedFile]) -> EntityRegistry:
    """
    Build an entity registry from a list of parsed files.
    
    Args:
        parsed_files: List of ParsedFile objects
        
    Returns:
        Populated EntityRegistry
    """
    registry = EntityRegistry()
    
    for pf in parsed_files:
        for func in pf.functions:
            registry.register(func)
        for cls in pf.classes:
            registry.register(cls)
    
    return registry
