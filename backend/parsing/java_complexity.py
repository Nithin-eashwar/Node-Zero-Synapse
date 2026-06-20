"""
Complexity metrics calculation for Java code analysis.

This module provides functions to calculate various complexity metrics
from parsed Java AST nodes, including cyclomatic and cognitive complexity.
It mirrors the structure of complexity.py but uses Java-specific tree-sitter
node type names and Java comment syntax rules.
"""

from typing import Optional, Set


# Common Java standard-library identifiers used for global-read filtering.
# Calls to these are not treated as cross-boundary dependencies.
JAVA_BUILTINS: Set[str] = {
    # Primitive wrapper types & core classes
    "String", "Integer", "Long", "Double", "Float", "Boolean", "Byte",
    "Short", "Character", "Object", "Class", "Enum", "Record",
    # Common collections
    "List", "ArrayList", "LinkedList", "Map", "HashMap", "TreeMap",
    "LinkedHashMap", "Set", "HashSet", "TreeSet", "LinkedHashSet",
    "Queue", "Deque", "ArrayDeque", "Stack", "Vector",
    "Collections", "Arrays",
    # I/O & system
    "System", "Math", "Runtime", "Thread", "Runnable",
    "StringBuilder", "StringBuffer", "StringJoiner",
    "Optional", "Stream",
    # Common exceptions
    "Exception", "RuntimeException", "Error", "Throwable",
    "IllegalArgumentException", "IllegalStateException",
    "NullPointerException", "IndexOutOfBoundsException",
    "UnsupportedOperationException", "ClassCastException",
    "NumberFormatException", "ArithmeticException",
    "IOException", "FileNotFoundException",
    "StackOverflowError", "OutOfMemoryError",
    # Literals / keywords that surface as identifiers
    "true", "false", "null", "this", "super",
    # Annotations that appear as identifiers in some grammars
    "Override", "Deprecated", "SuppressWarnings", "FunctionalInterface",
    "SafeVarargs",
}


# ---------------------------------------------------------------------------
# Cyclomatic Complexity
# ---------------------------------------------------------------------------

def calculate_java_cyclomatic_complexity(node) -> int:
    """
    Calculate McCabe's cyclomatic complexity for a Java method/constructor.

    Decision points counted:
    - if statements (and implicit else-if children)
    - for / enhanced-for loops
    - while / do-while loops
    - catch clauses
    - switch labels (case entries)
    - conditional (ternary) expressions
    - boolean binary operators (&& / ||)
    - assert statements
    - break / continue with labels (uncommon but valid)

    Args:
        node: A tree-sitter node for method_declaration or
              constructor_declaration.

    Returns:
        Integer complexity score (minimum 1).
    """
    complexity = 1  # base

    # Node types that unconditionally add one decision point each.
    decision_types = {
        "if_statement",
        "for_statement",
        "enhanced_for_statement",   # for (Type x : collection)
        "while_statement",
        "do_statement",
        "catch_clause",
        "switch_label",             # each 'case X:' or 'default:'
        "assert_statement",
        "conditional_expression",   # ternary  a ? b : c
        "lambda_expression",        # lambdas add a path
    }

    def _traverse(n) -> int:
        count = 0

        if n.type in decision_types:
            count += 1

        # && and || inside binary_expression
        if n.type == "binary_expression":
            op_node = n.child_by_field_name("operator")
            if op_node and op_node.type in ("&&", "||"):
                count += 1

        for child in n.children:
            count += _traverse(child)

        return count

    body = _get_method_body(node)
    if body:
        complexity += _traverse(body)

    return complexity


# ---------------------------------------------------------------------------
# Cognitive Complexity
# ---------------------------------------------------------------------------

def calculate_java_cognitive_complexity(
    node, method_name: Optional[str] = None
) -> int:
    """
    Calculate cognitive complexity for a Java method/constructor.

    Penalises:
    1. Structural complexity (breaks in linear flow)
    2. Nesting: each additional level multiplies the penalty
    3. Boolean operator sequences
    4. Direct recursion (calling the same method by name)

    Args:
        node: tree-sitter node for method_declaration or
              constructor_declaration.
        method_name: Optional method name for recursion detection.

    Returns:
        Integer cognitive complexity score.
    """
    complexity = 0

    if method_name is None:
        name_node = node.child_by_field_name("name")
        if name_node:
            method_name = name_node.text.decode("utf8")

    # Structures that add a flat +1 (before nesting penalty).
    increment_types = {
        "if_statement",
        "for_statement",
        "enhanced_for_statement",
        "while_statement",
        "do_statement",
        "catch_clause",
        "switch_expression",
        "switch_statement",
        "conditional_expression",
        "lambda_expression",
    }

    # Structures that increase the nesting depth for children.
    nesting_types = {
        "if_statement",
        "for_statement",
        "enhanced_for_statement",
        "while_statement",
        "do_statement",
        "catch_clause",
        "try_statement",
        "switch_expression",
        "switch_statement",
        "lambda_expression",
        "block",                   # anonymous blocks
    }

    recursion_detected = False

    def _traverse(n, depth: int, inside_nested_method: bool = False):
        nonlocal complexity, recursion_detected

        # Don't descend into nested method/class definitions —
        # they are separate entities and counted independently.
        if n.type in (
            "method_declaration", "constructor_declaration",
            "class_declaration", "interface_declaration",
            "enum_declaration",
        ) and n is not node:
            return

        if not inside_nested_method:
            if n.type in increment_types:
                complexity += 1 + depth   # base + nesting penalty

            # Boolean operators: each distinct operator type adds +1
            if n.type == "binary_expression":
                op_node = n.child_by_field_name("operator")
                if op_node and op_node.type in ("&&", "||"):
                    complexity += 1

            # Breaks in linear flow
            if n.type in ("break_statement", "continue_statement"):
                complexity += 1

            # Direct recursion
            if (
                n.type == "method_invocation"
                and method_name
                and not recursion_detected
            ):
                name_node = n.child_by_field_name("name")
                if name_node and name_node.text.decode("utf8") == method_name:
                    complexity += 1
                    recursion_detected = True

        new_depth = depth + (1 if n.type in nesting_types and not inside_nested_method else 0)

        for child in n.children:
            _traverse(child, new_depth, inside_nested_method)

    body = _get_method_body(node)
    if body:
        _traverse(body, 0)

    return complexity


# ---------------------------------------------------------------------------
# Line Counting
# ---------------------------------------------------------------------------

def count_java_lines_of_code(node) -> int:
    """
    Count physical lines spanned by a method/constructor node.

    Args:
        node: tree-sitter node.

    Returns:
        Line count (end - start + 1).
    """
    return node.end_point[0] - node.start_point[0] + 1


def count_java_total_lines(source_code: str) -> dict:
    """
    Count different types of lines in Java source code.

    Handles:
    - Single-line comments: // ...
    - Block comments:       /* ... */ (potentially multi-line)
    - Javadoc comments:     /** ... */
    - Blank lines
    - Code lines (everything else)

    Args:
        source_code: Full Java source as a string.

    Returns:
        Dict with 'total', 'code', 'comment', 'blank' counts.
    """
    lines = source_code.split("\n")
    total = len(lines)
    blank = 0
    comment = 0
    code = 0

    in_block_comment = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            blank += 1
            continue

        if in_block_comment:
            comment += 1
            if "*/" in stripped:
                in_block_comment = False
            continue

        # Line starts a block/javadoc comment
        if stripped.startswith("/*"):
            comment += 1
            # Check if the block comment closes on the same line
            after_open = stripped[2:]
            if "*/" in after_open:
                in_block_comment = False
            else:
                in_block_comment = True
            continue

        # Single-line comment
        if stripped.startswith("//"):
            comment += 1
            continue

        # Mixed line: code followed by //
        # Treat as code (the comment portion doesn't make it a comment line)
        code += 1

    return {
        "total": total,
        "code": code,
        "comment": comment,
        "blank": blank,
    }


# ---------------------------------------------------------------------------
# Recursion helper
# ---------------------------------------------------------------------------

def contains_java_recursion(node, method_name: str) -> bool:
    """
    Check whether a method directly calls itself by name.

    Args:
        node: tree-sitter method/constructor node.
        method_name: Name of the method to check recursion against.

    Returns:
        True if a recursive call is detected.
    """
    def _search(n) -> bool:
        # Don't descend into nested type declarations
        if n.type in (
            "class_declaration", "interface_declaration",
            "enum_declaration",
        ):
            return False

        if n.type == "method_invocation":
            name_node = n.child_by_field_name("name")
            if name_node and name_node.text.decode("utf8") == method_name:
                return True

        for child in n.children:
            if _search(child):
                return True
        return False

    body = _get_method_body(node)
    if body:
        return _search(body)
    return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_method_body(node):
    """
    Return the body block of a method or constructor node.

    For method_declaration and constructor_declaration the field is 'body'.
    """
    return node.child_by_field_name("body")
