"""
C++ code parser using tree-sitter.

This module parses C++ source and header files and extracts rich entity metadata
including classes, structs, functions, methods, fields, and includes.
"""

import os
from typing import List, Optional, Tuple, Dict, Any

from tree_sitter_languages import get_language, get_parser

from .entities import (
    FunctionEntity,
    ClassEntity,
    ImportEntity,
    ModuleEntity,
    VariableEntity,
    Parameter,
    ParsedFile,
)
from .cpp_complexity import (
    calculate_cpp_cyclomatic_complexity,
    calculate_cpp_cognitive_complexity,
    count_cpp_lines_of_code,
    count_cpp_total_lines,
)

_cpp_language = get_language("cpp")
_cpp_parser = get_parser("cpp")


# ---------------------------------------------------------------------------
# Type and Dependency Helpers
# ---------------------------------------------------------------------------

def _extract_type_string(node) -> str:
    """Extract a clean string representation of a type node."""
    if not node:
        return "unknown"
    return node.text.decode("utf8").strip()


def _find_cpp_calls(node) -> List[str]:
    """Recursively find all function calls within a node."""
    calls: List[str] = []
    
    if node.type == "call_expression":
        func_node = node.child_by_field_name("function")
        if func_node:
            calls.append(func_node.text.decode("utf8"))
            
    for child in node.children:
        calls.extend(_find_cpp_calls(child))
        
    return calls


def _extract_cpp_parameters(node) -> List[Parameter]:
    """Extract parameters from a parameter_list node."""
    parameters: List[Parameter] = []
    if not node:
        return parameters
        
    for child in node.children:
        if child.type in ("parameter_declaration", "optional_parameter_declaration"):
            type_node = child.child_by_field_name("type")
            decl_node = child.child_by_field_name("declarator")
            
            type_hint = _extract_type_string(type_node) if type_node else "auto"
            name = ""
            
            # Extract name from declarator (could be identifier, reference_declarator, etc.)
            if decl_node:
                if decl_node.type == "identifier":
                    name = decl_node.text.decode("utf8")
                else:
                    # e.g. pointer_declarator, reference_declarator
                    ident_node = None
                    for sub in decl_node.children:
                        if sub.type == "identifier":
                            ident_node = sub
                            break
                    name = ident_node.text.decode("utf8") if ident_node else decl_node.text.decode("utf8")
            
            parameters.append(Parameter(name=name, type_hint=type_hint))
            
    return parameters


# ---------------------------------------------------------------------------
# Function / Method Extraction
# ---------------------------------------------------------------------------

def _extract_cpp_function(
    node,
    file_path: str,
    namespace: str,
    parent_class: Optional[str] = None,
    current_visibility: Optional[str] = None
) -> FunctionEntity:
    """Extract a FunctionEntity from a function_definition or declaration."""
    
    # Try to find the declarator which contains the name and parameters
    decl_node = node.child_by_field_name("declarator")
    type_node = node.child_by_field_name("type")
    
    return_type = _extract_type_string(type_node) if type_node else None
    func_name = "unknown"
    parameters: List[Parameter] = []
    is_static = False
    
    # Check for static modifier in front of type/decl
    for child in node.children:
        if child.type == "storage_class_specifier" and child.text.decode("utf8") == "static":
            is_static = True
    
    if decl_node:
        # It could be an init_declarator, function_declarator, etc.
        # Dig down to find the actual identifier and parameter list
        current_decl = decl_node
        while current_decl and current_decl.type not in ("function_declarator", "identifier"):
            if current_decl.type == "pointer_declarator" or current_decl.type == "reference_declarator":
                current_decl = current_decl.child_by_field_name("declarator")
            else:
                break
                
        if current_decl and current_decl.type == "function_declarator":
            ident_node = current_decl.child_by_field_name("declarator")
            params_node = current_decl.child_by_field_name("parameters")
            
            if ident_node:
                func_name = ident_node.text.decode("utf8")
            if params_node:
                parameters = _extract_cpp_parameters(params_node)
        elif current_decl and current_decl.type == "identifier":
            func_name = current_decl.text.decode("utf8")

    # If it's a scoped identifier (e.g., MyClass::myMethod defined outside class)
    if "::" in func_name:
        parts = func_name.split("::")
        parent_class = parts[-2]
        func_name = parts[-1]

    # Prepend namespace if available and not a class method
    if namespace and not parent_class and "::" not in func_name:
        qual_name = f"{namespace}::{func_name}"
    else:
        qual_name = func_name

    # Complexity
    try:
        cyclomatic = calculate_cpp_cyclomatic_complexity(node)
        cognitive = calculate_cpp_cognitive_complexity(node, qual_name)
    except Exception:
        cyclomatic, cognitive = 1, 0

    loc = count_cpp_lines_of_code(node)
    
    body_node = node.child_by_field_name("body")
    calls = _find_cpp_calls(body_node) if body_node else []

    return FunctionEntity(
        name=qual_name,
        file_path=file_path,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        parameters=parameters,
        return_type=return_type,
        decorators=[],
        docstring=None,
        visibility=current_visibility if parent_class else "public",
        throws=[],
        is_async=False,
        is_generator=False,
        is_method=parent_class is not None,
        is_static=is_static,
        is_classmethod=False,
        is_property=False,
        parent_class=parent_class,
        cyclomatic_complexity=cyclomatic,
        cognitive_complexity=cognitive,
        lines_of_code=loc,
        calls=calls,
    )


# ---------------------------------------------------------------------------
# Class / Struct Extraction
# ---------------------------------------------------------------------------

def _extract_cpp_class(
    node, file_path: str, namespace: str
) -> Tuple[ClassEntity, List[FunctionEntity], List[VariableEntity]]:
    """Extract a ClassEntity and its members from a class_specifier or struct_specifier."""
    
    is_struct = node.type == "struct_specifier"
    name_node = node.child_by_field_name("name")
    
    base_name = name_node.text.decode("utf8") if name_node else "unknown"
    class_name = f"{namespace}::{base_name}" if namespace else base_name
    
    # Base classes
    bases: List[str] = []
    base_clause = node.child_by_field_name("base_classes")
    if base_clause:
        for child in base_clause.children:
            if child.type == "base_class_clause":
                for sub in child.children:
                    if sub.type in ("type_identifier", "scoped_type_identifier"):
                        bases.append(sub.text.decode("utf8"))

    methods: List[FunctionEntity] = []
    method_names: List[str] = []
    field_entities: List[VariableEntity] = []
    class_variables: List[str] = []
    instance_variables: List[str] = []
    nested_classes: List[str] = []

    # In C++, default visibility for class is private, for struct is public
    current_visibility = "public" if is_struct else "private"

    body_node = node.child_by_field_name("body")
    if body_node:
        for child in body_node.children:
            # Access specifiers (e.g., public:)
            if child.type == "access_specifier":
                # The first child is usually the keyword (public, private, protected)
                if child.children:
                    current_visibility = child.children[0].type
                    
            elif child.type in ("function_definition", "declaration"):
                # Could be a method or a field
                is_function = False
                for sub in child.children:
                    if sub.type in ("function_declarator", "init_declarator") or sub.type == "declarator":
                        if "function_declarator" in sub.type or (sub.children and "function_declarator" in [s.type for s in sub.children]):
                            is_function = True
                            
                if is_function or child.type == "function_definition":
                    method = _extract_cpp_function(
                        child, file_path, namespace, class_name, current_visibility
                    )
                    methods.append(method)
                    method_names.append(method.name)
                else:
                    # Treat as field
                    type_node = child.child_by_field_name("type")
                    type_str = _extract_type_string(type_node) if type_node else "unknown"
                    
                    for sub in child.children:
                        if sub.type in ("identifier", "field_identifier"):
                            name = sub.text.decode("utf8")
                            field_entities.append(VariableEntity(
                                name=name,
                                file_path=file_path,
                                line=child.start_point[0] + 1,
                                type_annotation=type_str,
                                scope="class",
                                parent=class_name,
                                is_constant="const" in type_str
                            ))
                            instance_variables.append(name)
                            
            elif child.type in ("class_specifier", "struct_specifier"):
                nested_name = child.child_by_field_name("name")
                if nested_name:
                    nested_classes.append(nested_name.text.decode("utf8"))

    class_entity = ClassEntity(
        name=class_name,
        file_path=file_path,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        bases=bases,
        metaclass=None,
        visibility="public",
        is_abstract=False, # Would require checking for pure virtual methods = 0
        is_dataclass=is_struct,
        is_protocol=False,
        is_interface=False,
        decorators=[],
        docstring=None,
        methods=method_names,
        class_variables=class_variables,
        instance_variables=instance_variables,
        nested_classes=nested_classes,
    )

    return class_entity, methods, field_entities


# ---------------------------------------------------------------------------
# Includes Extraction
# ---------------------------------------------------------------------------

def _extract_cpp_include(node, file_path: str) -> ImportEntity:
    """Extract an ImportEntity from a preproc_include node."""
    
    path_node = node.child_by_field_name("path")
    if not path_node:
        return ImportEntity(
            file_path=file_path,
            line=node.start_point[0] + 1,
            module="unknown",
            imported_names=[],
            alias=None,
            is_relative=False,
            is_star=False,
            relative_level=0,
            import_type="include",
        )
        
    path_str = path_node.text.decode("utf8")
    is_relative = path_str.startswith('"')
    
    # Strip quotes or angle brackets
    clean_path = path_str.strip('\'"<>')

    return ImportEntity(
        file_path=file_path,
        line=node.start_point[0] + 1,
        module=clean_path,
        imported_names=[],
        alias=None,
        is_relative=is_relative,
        is_star=False,
        relative_level=0,
        import_type="include",
    )


# ---------------------------------------------------------------------------
# Core Parser
# ---------------------------------------------------------------------------

def _traverse_and_extract(
    node, 
    file_path: str, 
    result: ParsedFile, 
    current_namespace: str = ""
):
    """Recursively traverse the AST and populate the ParsedFile."""
    
    if node.type == "preproc_include":
        imp = _extract_cpp_include(node, file_path)
        result.imports.append(imp)
        result.module.imports.append(imp.module)
        
    elif node.type == "namespace_definition":
        name_node = node.child_by_field_name("name")
        ns_name = name_node.text.decode("utf8") if name_node else ""
        new_namespace = f"{current_namespace}::{ns_name}" if current_namespace else ns_name
        
        body = node.child_by_field_name("body")
        if body:
            for child in body.children:
                _traverse_and_extract(child, file_path, result, new_namespace)
                
    elif node.type in ("class_specifier", "struct_specifier"):
        class_ent, methods, fields = _extract_cpp_class(node, file_path, current_namespace)
        result.classes.append(class_ent)
        result.functions.extend(methods)
        result.variables.extend(fields)
        
        result.module.classes.append(class_ent.name)
        for m in methods:
            result.module.functions.append(m.name)
        for f in fields:
            result.module.global_variables.append(f.name)
            
    elif node.type == "function_definition":
        func_ent = _extract_cpp_function(node, file_path, current_namespace)
        result.functions.append(func_ent)
        result.module.functions.append(func_ent.name)
        
    elif node.type == "ERROR":
        result.parse_errors.append(f"Parse error near line {node.start_point[0] + 1}")
        
    else:
        # Continue traversing down
        for child in node.children:
            _traverse_and_extract(child, file_path, result, current_namespace)


def parse_cpp_file(file_path: str) -> ParsedFile:
    """
    Parse a C++ source/header file and extract all entities.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception as e:
        return ParsedFile(
            file_path=file_path,
            language="cpp",
            parse_success=False,
            parse_errors=[str(e)],
        )

    tree = _cpp_parser.parse(bytes(source, "utf-8"))
    root = tree.root_node

    result = ParsedFile(file_path=file_path, language="cpp")

    line_counts = count_cpp_total_lines(source)

    result.module = ModuleEntity(
        file_path=file_path,
        docstring=None,
        total_lines=line_counts["total"],
        code_lines=line_counts["code"],
        comment_lines=line_counts["comment"],
    )

    _traverse_and_extract(root, file_path, result, current_namespace="")

    if result.parse_errors:
        result.parse_success = False

    return result
