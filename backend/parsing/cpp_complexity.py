"""
Complexity metrics calculation for C++ code analysis.

This module provides functions to calculate various complexity metrics
from parsed C++ AST nodes, including cyclomatic and cognitive complexity.
"""

from typing import Optional, Set

# Common C++ standard-library identifiers used for global-read filtering.
CPP_BUILTINS: Set[str] = {
    "std", "cout", "cin", "cerr", "endl", "string", "vector", "map", 
    "unordered_map", "set", "unordered_set", "list", "array", "deque",
    "shared_ptr", "unique_ptr", "weak_ptr", "make_shared", "make_unique",
    "move", "forward", "size_t", "nullptr", "true", "false", "this",
    "exception", "runtime_error", "logic_error", "out_of_range",
    "thread", "mutex", "lock_guard", "unique_lock", "atomic"
}


# ---------------------------------------------------------------------------
# Cyclomatic Complexity
# ---------------------------------------------------------------------------

def calculate_cpp_cyclomatic_complexity(node) -> int:
    """
    Calculate McCabe's cyclomatic complexity for a C++ function/method.
    """
    complexity = 1  # base

    decision_types = {
        "if_statement",
        "for_statement",
        "for_range_loop",
        "while_statement",
        "do_statement",
        "catch_clause",
        "case_statement",
        "conditional_expression",
        "lambda_expression",
    }

    def _traverse(n) -> int:
        count = 0

        if n.type in decision_types:
            count += 1

        # &&, ||, and, or inside binary_expression
        if n.type == "binary_expression":
            op_node = n.child_by_field_name("operator")
            if op_node and op_node.type in ("&&", "||", "and", "or"):
                count += 1

        for child in n.children:
            count += _traverse(child)

        return count

    body = _get_function_body(node)
    if body:
        complexity += _traverse(body)

    return complexity


# ---------------------------------------------------------------------------
# Cognitive Complexity
# ---------------------------------------------------------------------------

def calculate_cpp_cognitive_complexity(
    node, method_name: Optional[str] = None
) -> int:
    """
    Calculate cognitive complexity for a C++ function/method.
    """
    complexity = 0

    if method_name is None:
        name_node = node.child_by_field_name("declarator")
        # In C++, finding the name might require traversing declarators.
        # This is a fallback if name is not explicitly provided.
        if name_node:
            method_name = name_node.text.decode("utf8")

    increment_types = {
        "if_statement",
        "for_statement",
        "for_range_loop",
        "while_statement",
        "do_statement",
        "catch_clause",
        "switch_statement",
        "conditional_expression",
        "lambda_expression",
    }

    nesting_types = {
        "if_statement",
        "for_statement",
        "for_range_loop",
        "while_statement",
        "do_statement",
        "catch_clause",
        "try_statement",
        "switch_statement",
        "lambda_expression",
        "compound_statement",  # blocks
    }

    recursion_detected = False

    def _traverse(n, depth: int, inside_nested_method: bool = False):
        nonlocal complexity, recursion_detected

        if n.type in (
            "function_definition", "class_specifier", "struct_specifier"
        ) and n is not node:
            return

        if not inside_nested_method:
            if n.type in increment_types:
                complexity += 1 + depth

            if n.type == "binary_expression":
                op_node = n.child_by_field_name("operator")
                if op_node and op_node.type in ("&&", "||", "and", "or"):
                    complexity += 1

            if n.type in ("break_statement", "continue_statement", "goto_statement"):
                complexity += 1

            if (
                n.type == "call_expression"
                and method_name
                and not recursion_detected
            ):
                func_node = n.child_by_field_name("function")
                if func_node and func_node.text.decode("utf8").endswith(method_name):
                    complexity += 1
                    recursion_detected = True

        new_depth = depth + (1 if n.type in nesting_types and not inside_nested_method else 0)

        for child in n.children:
            _traverse(child, new_depth, inside_nested_method)

    body = _get_function_body(node)
    if body:
        _traverse(body, 0)

    return complexity


# ---------------------------------------------------------------------------
# Line Counting
# ---------------------------------------------------------------------------

def count_cpp_lines_of_code(node) -> int:
    return node.end_point[0] - node.start_point[0] + 1


def count_cpp_total_lines(source_code: str) -> dict:
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

        if stripped.startswith("/*"):
            comment += 1
            after_open = stripped[2:]
            if "*/" in after_open:
                in_block_comment = False
            else:
                in_block_comment = True
            continue

        if stripped.startswith("//"):
            comment += 1
            continue

        code += 1

    return {
        "total": total,
        "code": code,
        "comment": comment,
        "blank": blank,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_function_body(node):
    return node.child_by_field_name("body")
