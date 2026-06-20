"""
Java code parser using tree-sitter.

This module parses Java source files and extracts rich entity metadata
including classes, interfaces, methods, constructors, fields, and imports —
all mapped into the same entity models used by the Python parser so that
downstream graph, reasoning, and visualisation services work transparently
for Java repos.

Supported constructs
--------------------
- Classes, abstract classes, enums
- Interfaces (marked with is_interface=True, is_abstract=True)
- Methods and constructors (FunctionEntity)
- Import declarations (ImportEntity)
- Field declarations (VariableEntity)
- Annotations mapped to decorators
- Visibility modifiers (public / protected / private / package-private)
- throws clauses
- Generic type parameters captured as raw strings

Intentionally skipped (no stable identity for graph purposes)
-------------------------------------------------------------
- Anonymous inner classes
- Static initialiser blocks
- Lambda bodies (the lambda itself is captured as a call, not an entity)
"""

import os
from typing import List, Optional, Tuple

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
from .java_complexity import (
    calculate_java_cyclomatic_complexity,
    calculate_java_cognitive_complexity,
    count_java_lines_of_code,
    count_java_total_lines,
)


# ---------------------------------------------------------------------------
# Parser initialisation
# ---------------------------------------------------------------------------

_java_language = get_language("java")
_java_parser = get_parser("java")


# ---------------------------------------------------------------------------
# Visibility helpers
# ---------------------------------------------------------------------------

_MODIFIERS = {"public", "private", "protected", "static", "abstract",
              "final", "native", "synchronized", "transient", "volatile",
              "strictfp", "default", "sealed", "non-sealed"}

_VISIBILITY = {"public", "private", "protected"}


def _find_modifiers_node(node):
    """
    Locate the modifiers child node for a declaration.

    In some grammar versions (class_declaration, interface_declaration, enum_declaration)
    the 'modifiers' node is NOT registered as a named field — only method/constructor
    declarations expose it via child_by_field_name("modifiers").
    This helper checks the named field first, then falls back to a type-based scan.
    """
    mod = node.child_by_field_name("modifiers")
    if mod is not None:
        return mod
    for child in node.children:
        if child.type == "modifiers":
            return child
    return None


def _extract_modifiers(node) -> Tuple[Optional[str], List[str]]:
    """
    Walk the modifiers child of a declaration node.

    In tree-sitter's Java grammar, modifier keywords appear as leaf nodes
    whose *type* is the keyword itself (e.g. node.type == "public"),
    not as generic identifier nodes.

    Returns:
        (visibility, other_modifiers)
        visibility — "public" | "private" | "protected" | None (package-private)
        other_modifiers — e.g. ["static", "final"]
    """
    visibility: Optional[str] = None
    others: List[str] = []

    modifiers_node = _find_modifiers_node(node)
    if not modifiers_node:
        return visibility, others

    for child in modifiers_node.children:
        # The child node TYPE equals the keyword text in this grammar version
        # (e.g. child.type == "public").  Fall back to .text for safety.
        token = child.type if child.type in _MODIFIERS else child.text.decode("utf8").strip()
        if token in _VISIBILITY:
            visibility = token
        elif token in _MODIFIERS:
            others.append(token)
        # Annotations are handled separately in _extract_annotations.

    return visibility, others


def _extract_annotations(node) -> List[str]:
    """
    Extract annotation names from a modifiers block.

    e.g. @Override, @SuppressWarnings("unchecked") -> ["Override", "SuppressWarnings"]
    """
    annotations: List[str] = []
    modifiers_node = _find_modifiers_node(node)
    if not modifiers_node:
        return annotations

    for child in modifiers_node.children:
        if child.type in ("marker_annotation", "annotation"):
            for sub in child.children:
                if sub.type == "identifier":
                    annotations.append(sub.text.decode("utf8"))
                    break
    return annotations


def _extract_throws(node) -> List[str]:
    """
    Extract declared exception types from a throws clause.

    Tree-sitter Java grammar names this field 'throws' on
    method_declaration and constructor_declaration.
    """
    throws: List[str] = []
    throws_node = None

    # The field may be named differently across grammar versions;
    # try the field name first, then walk children.
    throws_node = node.child_by_field_name("throws")
    if throws_node is None:
        for child in node.children:
            if child.type == "throws":
                throws_node = child
                break

    if throws_node is None:
        return throws

    for child in throws_node.children:
        if child.type in ("type_identifier", "scoped_type_identifier"):
            throws.append(child.text.decode("utf8"))

    return throws


# ---------------------------------------------------------------------------
# Parameter extraction
# ---------------------------------------------------------------------------

def _extract_java_parameters(node) -> List[Parameter]:
    """
    Extract method/constructor parameters from a formal_parameters node.
    """
    parameters: List[Parameter] = []
    params_node = node.child_by_field_name("parameters")
    if not params_node:
        return parameters

    for child in params_node.children:
        if child.type == "formal_parameter":
            type_node = child.child_by_field_name("type")
            name_node = child.child_by_field_name("name")
            type_hint = type_node.text.decode("utf8") if type_node else None
            name = name_node.text.decode("utf8") if name_node else ""
            parameters.append(Parameter(name=name, type_hint=type_hint))

        elif child.type == "spread_parameter":
            # varargs: String... args
            type_node = child.child_by_field_name("type")
            name_node = child.child_by_field_name("name")
            # In some grammar versions the name is the last identifier child
            if name_node is None:
                for sub in reversed(child.children):
                    if sub.type in ("variable_declarator", "identifier"):
                        name_node = sub
                        break
            type_hint = type_node.text.decode("utf8") + "..." if type_node else "..."
            name = name_node.text.decode("utf8") if name_node else "args"
            parameters.append(Parameter(name=name, type_hint=type_hint, is_args=True))

    return parameters


# ---------------------------------------------------------------------------
# Call extraction
# ---------------------------------------------------------------------------

def _find_java_calls(node) -> List[str]:
    """
    Recursively find all method invocations within a node.

    Captures both simple calls (foo()) and qualified calls (obj.foo(), Cls.foo()).
    """
    calls: List[str] = []

    if node.type == "method_invocation":
        # name field holds the method name identifier
        name_node = node.child_by_field_name("name")
        obj_node = node.child_by_field_name("object")
        if name_node:
            method_name = name_node.text.decode("utf8")
            if obj_node:
                calls.append(f"{obj_node.text.decode('utf8')}.{method_name}")
            else:
                calls.append(method_name)

    for child in node.children:
        calls.extend(_find_java_calls(child))

    return calls


# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------

def _extract_java_field(node, file_path: str, parent_class: Optional[str] = None) -> List[VariableEntity]:
    """
    Extract VariableEntity objects from a field_declaration node.

    A single declaration may introduce multiple variables:
        private int x, y, z;
    """
    variables: List[VariableEntity] = []

    visibility, others = _extract_modifiers(node)
    is_static = "static" in others
    is_constant = "final" in others

    type_node = node.child_by_field_name("type")
    type_annotation = type_node.text.decode("utf8") if type_node else None

    for child in node.children:
        if child.type == "variable_declarator":
            name_node = child.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode("utf8")
                scope = "class" if not is_static else "module"
                variables.append(VariableEntity(
                    name=name,
                    file_path=file_path,
                    line=node.start_point[0] + 1,
                    type_annotation=type_annotation,
                    scope=scope,
                    parent=parent_class,
                    is_constant=is_constant or (name.isupper() and "_" in name),
                ))
    return variables


# ---------------------------------------------------------------------------
# Method / Constructor extraction
# ---------------------------------------------------------------------------

def _extract_java_method(
    node,
    file_path: str,
    parent_class: Optional[str] = None,
) -> FunctionEntity:
    """
    Extract a FunctionEntity from a method_declaration or
    constructor_declaration node.
    """
    is_constructor = node.type == "constructor_declaration"

    name_node = node.child_by_field_name("name")
    func_name = name_node.text.decode("utf8") if name_node else "unknown"

    visibility, other_mods = _extract_modifiers(node)
    annotations = _extract_annotations(node)
    decorators = annotations + other_mods  # e.g. ["Override", "static", "final"]

    parameters = _extract_java_parameters(node)
    throws = _extract_throws(node)

    # Return type (methods only; constructors have none)
    return_type: Optional[str] = None
    if not is_constructor:
        ret_node = node.child_by_field_name("type")
        if ret_node:
            return_type = ret_node.text.decode("utf8")

    is_static = "static" in other_mods
    is_abstract = "abstract" in other_mods

    # Complexity metrics
    try:
        cyclomatic = calculate_java_cyclomatic_complexity(node)
        cognitive = calculate_java_cognitive_complexity(node, func_name)
    except Exception:
        cyclomatic, cognitive = 1, 0

    loc = count_java_lines_of_code(node)

    # Call graph
    body_node = node.child_by_field_name("body")
    calls = _find_java_calls(body_node) if body_node else []

    return FunctionEntity(
        name=func_name,
        file_path=file_path,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        parameters=parameters,
        return_type=return_type,
        decorators=decorators,
        docstring=None,          # Javadoc not extracted in this phase
        visibility=visibility,
        throws=throws,
        is_async=False,
        is_generator=False,
        is_method=parent_class is not None,
        is_static=is_static,
        is_classmethod=False,    # Not applicable for Java
        is_property=False,       # Not applicable for Java
        parent_class=parent_class,
        cyclomatic_complexity=cyclomatic,
        cognitive_complexity=cognitive,
        lines_of_code=loc,
        calls=calls,
    )


# ---------------------------------------------------------------------------
# Class / Interface / Enum extraction
# ---------------------------------------------------------------------------

def _extract_java_class(
    node, file_path: str
) -> Tuple[ClassEntity, List[FunctionEntity], List[VariableEntity]]:
    """
    Extract a ClassEntity and its contained methods and fields from
    a class_declaration, interface_declaration, or enum_declaration node.

    Returns:
        (class_entity, methods, fields)
    """
    is_interface = node.type == "interface_declaration"
    is_enum = node.type == "enum_declaration"

    name_node = node.child_by_field_name("name")
    class_name = name_node.text.decode("utf8") if name_node else "unknown"

    visibility, other_mods = _extract_modifiers(node)
    annotations = _extract_annotations(node)
    decorators = annotations + other_mods

    is_abstract = "abstract" in other_mods or is_interface

    # Bases: superclass (extends) and implemented interfaces
    bases: List[str] = []

    superclass_node = node.child_by_field_name("superclass")
    if superclass_node:
        # The type name is directly inside superclass
        for child in superclass_node.children:
            if child.type in ("type_identifier", "generic_type", "scoped_type_identifier"):
                bases.append(child.text.decode("utf8"))

    interfaces_node = node.child_by_field_name("interfaces")
    if interfaces_node:
        for child in interfaces_node.children:
            if child.type == "type_list":
                for t in child.children:
                    if t.type in ("type_identifier", "generic_type", "scoped_type_identifier"):
                        bases.append(t.text.decode("utf8"))
            elif child.type in ("type_identifier", "generic_type", "scoped_type_identifier"):
                bases.append(child.text.decode("utf8"))

    # For interfaces: 'extends' also uses 'interfaces' field in some grammars
    extends_interfaces_node = node.child_by_field_name("extends_interfaces")
    if extends_interfaces_node:
        for child in extends_interfaces_node.children:
            if child.type == "type_list":
                for t in child.children:
                    if t.type in ("type_identifier", "generic_type", "scoped_type_identifier"):
                        bases.append(t.text.decode("utf8"))

    methods: List[FunctionEntity] = []
    method_names: List[str] = []
    class_variables: List[str] = []
    instance_variables: List[str] = []
    nested_class_names: List[str] = []
    field_entities: List[VariableEntity] = []

    # Walk the class body
    body_node = node.child_by_field_name("body")
    if body_node:
        for child in body_node.children:
            # Methods
            if child.type in ("method_declaration", "constructor_declaration"):
                method = _extract_java_method(child, file_path, parent_class=class_name)
                methods.append(method)
                method_names.append(method.name)

            # Fields
            elif child.type == "field_declaration":
                fields = _extract_java_field(child, file_path, parent_class=class_name)
                field_entities.extend(fields)
                for f in fields:
                    if f.scope == "class":
                        instance_variables.append(f.name)
                    else:
                        class_variables.append(f.name)

            # Nested classes / interfaces / enums
            elif child.type in ("class_declaration", "interface_declaration", "enum_declaration"):
                nested_name_node = child.child_by_field_name("name")
                if nested_name_node:
                    nested_class_names.append(nested_name_node.text.decode("utf8"))

            # Enum constants (enum_declaration body contains enum_body_declarations)
            elif child.type == "enum_body":
                for enum_child in child.children:
                    if enum_child.type == "enum_constant":
                        const_name_node = enum_child.child_by_field_name("name")
                        if const_name_node:
                            class_variables.append(const_name_node.text.decode("utf8"))

    class_entity = ClassEntity(
        name=class_name,
        file_path=file_path,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        bases=bases,
        metaclass=None,
        visibility=visibility,
        is_abstract=is_abstract,
        is_dataclass=is_enum,   # Enums are the closest Java equivalent
        is_protocol=False,
        is_interface=is_interface,
        decorators=decorators,
        docstring=None,
        methods=method_names,
        class_variables=class_variables,
        instance_variables=instance_variables,
        nested_classes=nested_class_names,
    )

    return class_entity, methods, field_entities


# ---------------------------------------------------------------------------
# Import extraction
# ---------------------------------------------------------------------------

def _extract_java_import(node, file_path: str) -> ImportEntity:
    """
    Extract an ImportEntity from an import_declaration node.

    Handles:
    - import com.example.Foo;
    - import static com.example.Utils.helper;
    - import com.example.*;
    """
    is_static = False
    is_star = False

    # Detect 'static' keyword and wildcard
    for child in node.children:
        if child.type == "static":
            is_static = True
        if child.type == "asterisk":
            is_star = True

    # The scoped identifier carries the full path
    scope_node = None
    for child in node.children:
        if child.type in ("scoped_identifier", "identifier"):
            scope_node = child
            break

    module = scope_node.text.decode("utf8") if scope_node else ""

    # Imported name: last segment of the path for non-wildcard imports
    imported_names: List[str] = []
    if not is_star and "." in module:
        imported_names = [module.rsplit(".", 1)[-1]]
    elif is_star:
        imported_names = ["*"]

    # The module path is everything except the last segment for non-wildcard
    if not is_star and "." in module:
        module_path = module.rsplit(".", 1)[0]
    else:
        module_path = module

    decorators = ["static"] if is_static else []

    return ImportEntity(
        file_path=file_path,
        line=node.start_point[0] + 1,
        module=module_path,
        imported_names=imported_names,
        alias=None,
        is_relative=False,   # Java has no relative imports
        is_star=is_star,
        relative_level=0,
        import_type="unknown",
    )


# ---------------------------------------------------------------------------
# Package declaration
# ---------------------------------------------------------------------------

def _extract_package_name(root_node) -> Optional[str]:
    """Return the package name from a package_declaration node, if present."""
    for child in root_node.children:
        if child.type == "package_declaration":
            for sub in child.children:
                if sub.type in ("scoped_identifier", "identifier"):
                    return sub.text.decode("utf8")
    return None


# ---------------------------------------------------------------------------
# Public API: parse a single Java file
# ---------------------------------------------------------------------------

def parse_java_file(file_path: str) -> ParsedFile:
    """
    Parse a Java source file and extract all entities.

    Args:
        file_path: Absolute or relative path to the .java file.

    Returns:
        ParsedFile containing all extracted entities with language="java".
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception as e:
        return ParsedFile(
            file_path=file_path,
            language="java",
            parse_success=False,
            parse_errors=[str(e)],
        )

    tree = _java_parser.parse(bytes(source, "utf-8"))
    root = tree.root_node

    result = ParsedFile(file_path=file_path, language="java")

    # Line metrics
    line_counts = count_java_total_lines(source)
    package_name = _extract_package_name(root)

    result.module = ModuleEntity(
        file_path=file_path,
        docstring=package_name,   # Re-purpose docstring to carry the package name
        total_lines=line_counts["total"],
        code_lines=line_counts["code"],
        comment_lines=line_counts["comment"],
    )

    for child in root.children:
        # -------------------------------------------------------------------
        # Import declarations
        # -------------------------------------------------------------------
        if child.type == "import_declaration":
            imp = _extract_java_import(child, file_path)
            result.imports.append(imp)
            result.module.imports.append(imp.module)

        # -------------------------------------------------------------------
        # Top-level type declarations
        # -------------------------------------------------------------------
        elif child.type in (
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
        ):
            class_entity, methods, fields = _extract_java_class(child, file_path)
            result.classes.append(class_entity)
            result.functions.extend(methods)
            result.variables.extend(fields)

            result.module.classes.append(class_entity.name)
            for m in methods:
                result.module.functions.append(m.name)
            for fld in fields:
                result.module.global_variables.append(fld.name)

        # -------------------------------------------------------------------
        # Error nodes — record but don't crash
        # -------------------------------------------------------------------
        elif child.type == "ERROR":
            result.parse_errors.append(
                f"Parse error near line {child.start_point[0] + 1}"
            )

    if result.parse_errors:
        result.parse_success = False

    return result
