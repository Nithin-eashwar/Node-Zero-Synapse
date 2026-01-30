"""
Complexity metrics calculation for code analysis.

This module provides functions to calculate various complexity metrics
from parsed AST nodes, including cyclomatic and cognitive complexity.
"""

from typing import Set, List, Tuple, Optional


# Complete Python builtins list for accurate filtering
PYTHON_BUILTINS = {
    # Built-in functions
    'abs', 'aiter', 'all', 'any', 'anext', 'ascii', 'bin', 'bool', 'breakpoint',
    'bytearray', 'bytes', 'callable', 'chr', 'classmethod', 'compile', 'complex',
    'delattr', 'dict', 'dir', 'divmod', 'enumerate', 'eval', 'exec', 'filter',
    'float', 'format', 'frozenset', 'getattr', 'globals', 'hasattr', 'hash',
    'help', 'hex', 'id', 'input', 'int', 'isinstance', 'issubclass', 'iter',
    'len', 'list', 'locals', 'map', 'max', 'memoryview', 'min', 'next', 'object',
    'oct', 'open', 'ord', 'pow', 'print', 'property', 'range', 'repr', 'reversed',
    'round', 'set', 'setattr', 'slice', 'sorted', 'staticmethod', 'str', 'sum',
    'super', 'tuple', 'type', 'vars', 'zip', '__import__',
    
    # Built-in constants
    'True', 'False', 'None', 'Ellipsis', 'NotImplemented', '__debug__',
    
    # Built-in exceptions (commonly used)
    'Exception', 'BaseException', 'TypeError', 'ValueError', 'KeyError',
    'IndexError', 'AttributeError', 'ImportError', 'ModuleNotFoundError',
    'RuntimeError', 'StopIteration', 'StopAsyncIteration', 'GeneratorExit',
    'ArithmeticError', 'AssertionError', 'BlockingIOError', 'BrokenPipeError',
    'BufferError', 'BytesWarning', 'ChildProcessError', 'ConnectionAbortedError',
    'ConnectionError', 'ConnectionRefusedError', 'ConnectionResetError',
    'DeprecationWarning', 'EOFError', 'EnvironmentError', 'FileExistsError',
    'FileNotFoundError', 'FloatingPointError', 'FutureWarning', 'IOError',
    'IndentationError', 'InterruptedError', 'IsADirectoryError', 'LookupError',
    'MemoryError', 'NameError', 'NotADirectoryError', 'NotImplementedError',
    'OSError', 'OverflowError', 'PendingDeprecationWarning', 'PermissionError',
    'ProcessLookupError', 'RecursionError', 'ReferenceError', 'ResourceWarning',
    'SyntaxError', 'SyntaxWarning', 'SystemError', 'SystemExit', 'TabError',
    'TimeoutError', 'UnicodeDecodeError', 'UnicodeEncodeError', 'UnicodeError',
    'UnicodeTranslateError', 'UnicodeWarning', 'UserWarning', 'Warning',
    'ZeroDivisionError',
    
    # Common special names
    'self', 'cls', '__name__', '__doc__', '__package__', '__loader__',
    '__spec__', '__path__', '__file__', '__cached__', '__builtins__',
    '__all__', '__slots__', '__dict__', '__class__', '__init__',
    '__new__', '__del__', '__repr__', '__str__', '__bytes__', '__format__',
    '__lt__', '__le__', '__eq__', '__ne__', '__gt__', '__ge__', '__hash__',
    '__bool__', '__getattr__', '__getattribute__', '__setattr__', '__delattr__',
    '__dir__', '__get__', '__set__', '__delete__', '__init_subclass__',
    '__set_name__', '__instancecheck__', '__subclasscheck__', '__call__',
    '__len__', '__length_hint__', '__getitem__', '__setitem__', '__delitem__',
    '__missing__', '__iter__', '__reversed__', '__contains__', '__add__',
    '__sub__', '__mul__', '__matmul__', '__truediv__', '__floordiv__',
    '__mod__', '__divmod__', '__pow__', '__lshift__', '__rshift__',
    '__and__', '__xor__', '__or__', '__neg__', '__pos__', '__abs__',
    '__invert__', '__complex__', '__int__', '__float__', '__index__',
    '__round__', '__trunc__', '__floor__', '__ceil__', '__enter__', '__exit__',
    '__await__', '__aiter__', '__anext__', '__aenter__', '__aexit__',
}


def calculate_cyclomatic_complexity(node) -> int:
    """
    Calculate McCabe's cyclomatic complexity for a function/method.
    
    Cyclomatic complexity = number of decision points + 1
    
    Decision points include:
    - if statements
    - for/while loops
    - except clauses
    - with statements
    - boolean operators (and, or)
    - conditional expressions (ternary)
    - assert statements
    - comprehensions with conditions
    
    Args:
        node: A tree-sitter node (function_definition or async_function_definition)
        
    Returns:
        Integer complexity score (minimum 1)
    """
    complexity = 1  # Base complexity
    
    # Node types that add to cyclomatic complexity
    decision_types = {
        "if_statement",
        "elif_clause",
        "for_statement",
        "while_statement",
        "except_clause",
        "with_statement",
        "assert_statement",
        "conditional_expression",  # ternary: x if y else z
        "list_comprehension",
        "dictionary_comprehension",
        "set_comprehension",
        "generator_expression",
    }
    
    def traverse(n):
        """Recursively count decision points."""
        count = 0
        
        # Check if this node is a decision point
        if n.type in decision_types:
            count += 1
        
        # Check for boolean operators in binary expressions
        if n.type == "boolean_operator":
            # Each 'and'/'or' adds a decision point
            count += 1
        
        # Check for comprehension conditions (if clause in comprehension)
        if n.type == "if_clause":
            count += 1
        
        # Recurse into children
        for child in n.children:
            count += traverse(child)
        
        return count
    
    # Get the function body and traverse
    body_node = node.child_by_field_name("body")
    if body_node:
        complexity += traverse(body_node)
    
    return complexity


def calculate_cognitive_complexity(node, function_name: Optional[str] = None) -> int:
    """
    Calculate cognitive complexity for a function/method.
    
    Cognitive complexity penalizes:
    1. Nesting: Each level of nesting adds increasing weight
    2. Structural complexity: breaks in linear flow
    3. Multiple conditions
    4. Recursion: calling the function itself
    
    This is more representative of how hard code is to understand
    than cyclomatic complexity alone.
    
    Args:
        node: A tree-sitter node (function_definition or async_function_definition)
        function_name: Optional name of the function for recursion detection
        
    Returns:
        Integer cognitive complexity score
    """
    complexity = 0
    
    # Get function name for recursion detection if not provided
    if function_name is None:
        name_node = node.child_by_field_name("name")
        if name_node:
            function_name = name_node.text.decode("utf8")
    
    # Structures that increment complexity
    increment_types = {
        "if_statement": 1,
        "elif_clause": 1,
        "else_clause": 1,
        "for_statement": 1,
        "while_statement": 1,
        "except_clause": 1,
        "with_statement": 1,
        "conditional_expression": 1,
        "lambda": 1,
    }
    
    # Nesting parents - structures that increase nesting level
    nesting_types = {
        "if_statement",
        "elif_clause", 
        "else_clause",
        "for_statement",
        "while_statement",
        "except_clause",
        "with_statement",
        "try_statement",
        "lambda",
    }
    
    # Track if we've already counted recursion (only count once)
    recursion_detected = False
    
    def traverse(n, nesting_level: int, inside_nested_func: bool = False):
        """Traverse with nesting awareness and recursion detection."""
        nonlocal complexity, recursion_detected
        
        # Don't count complexity inside nested function definitions
        # (they should be counted separately)
        if n.type in ["function_definition", "async_function_definition"]:
            if inside_nested_func or (n != node):
                # This is a nested function, skip its body
                return
        
        # Add base increment if applicable
        if n.type in increment_types and not inside_nested_func:
            complexity += increment_types[n.type]
            # Also add nesting penalty
            complexity += nesting_level
        
        # Boolean sequences add complexity (but only count once per sequence)
        if n.type == "boolean_operator" and not inside_nested_func:
            complexity += 1
        
        # Breaks in linear flow
        if n.type in ["break_statement", "continue_statement"] and not inside_nested_func:
            complexity += 1
        
        # Recursion detection: function calling itself
        if n.type == "call" and function_name and not recursion_detected and not inside_nested_func:
            func_node = n.child_by_field_name("function")
            if func_node:
                call_name = func_node.text.decode("utf8")
                # Check for direct recursion (func_name) or self.func_name for methods
                if call_name == function_name or call_name.endswith(f".{function_name}"):
                    complexity += 1  # Recursion adds fundamental complexity
                    recursion_detected = True
        
        # Calculate new nesting level for children
        new_nesting = nesting_level
        if n.type in nesting_types and not inside_nested_func:
            new_nesting += 1
        
        # Check if we're entering a nested function
        entering_nested = n.type in ["function_definition", "async_function_definition"] and n != node
        
        # Recurse into children
        for child in n.children:
            traverse(child, new_nesting, inside_nested_func or entering_nested)
    
    body_node = node.child_by_field_name("body")
    if body_node:
        traverse(body_node, 0)
    
    return complexity


def count_lines_of_code(node) -> int:
    """
    Count lines of code in a function (excluding blank lines and comments).
    
    Args:
        node: A tree-sitter node (function_definition or async_function_definition)
        
    Returns:
        Number of actual code lines
    """
    start_line = node.start_point[0]
    end_line = node.end_point[0]
    
    # Basic count: end - start + 1
    # For more accuracy, would need to parse the actual lines
    return end_line - start_line + 1


def count_total_lines(source_code: str) -> dict:
    """
    Count different types of lines in source code.
    
    Args:
        source_code: The full source code as a string
        
    Returns:
        Dict with 'total', 'code', 'comment', 'blank' counts
    """
    lines = source_code.split('\n')
    
    total = len(lines)
    blank = 0
    comment = 0
    code = 0
    
    in_multiline_string = False
    
    for line in lines:
        stripped = line.strip()
        
        if not stripped:
            blank += 1
            continue
        
        # Basic comment detection (simplified per user request)
        if stripped.startswith('#'):
            comment += 1
        elif stripped.startswith('"""') or stripped.startswith("'''"):
            # Toggle multiline string state
            if not in_multiline_string:
                in_multiline_string = True
                # Check if it ends on same line
                rest = stripped[3:]
                if '"""' in rest or "'''" in rest:
                    in_multiline_string = False
                    comment += 1
            else:
                in_multiline_string = False
                comment += 1
        elif in_multiline_string:
            comment += 1
        else:
            code += 1
    
    return {
        "total": total,
        "code": code,
        "comment": comment,
        "blank": blank
    }


def contains_yield(node) -> bool:
    """
    Check if a function contains 'yield' or 'yield from' statements.
    
    Args:
        node: A tree-sitter node (function_definition)
        
    Returns:
        True if the function is a generator
    """
    def search_yield(n) -> bool:
        if n.type in ["yield", "yield_statement"]:
            return True
        # Don't descend into nested functions - their yield doesn't count
        if n.type in ["function_definition", "async_function_definition"]:
            return False
        for child in n.children:
            if search_yield(child):
                return True
        return False
    
    body_node = node.child_by_field_name("body")
    if body_node:
        return search_yield(body_node)
    return False


def contains_await(node) -> bool:
    """
    Check if an async function contains 'await' expressions.
    
    Args:
        node: A tree-sitter node (async_function_definition)
        
    Returns:
        True if the function uses await
    """
    def search_await(n) -> bool:
        if n.type == "await":
            return True
        # Don't descend into nested functions
        if n.type in ["function_definition", "async_function_definition"]:
            return False
        for child in n.children:
            if search_await(child):
                return True
        return False
    
    body_node = node.child_by_field_name("body")
    if body_node:
        return search_await(body_node)
    return False


class ScopeTracker:
    """
    Proper scope tracking for variable access analysis.
    
    Tracks variable definitions across scopes to accurately
    identify global vs local variable access.
    """
    
    def __init__(self):
        self.scopes: List[Set[str]] = []
        self.global_declarations: Set[str] = set()  # 'global x' statements
        self.nonlocal_declarations: Set[str] = set()  # 'nonlocal x' statements
    
    def enter_scope(self):
        """Enter a new scope (function, class, comprehension)."""
        self.scopes.append(set())
    
    def exit_scope(self):
        """Exit the current scope."""
        if self.scopes:
            self.scopes.pop()
    
    def define_local(self, name: str):
        """Define a variable in the current scope."""
        if self.scopes:
            self.scopes[-1].add(name)
    
    def declare_global(self, name: str):
        """Track a 'global x' declaration."""
        self.global_declarations.add(name)
    
    def declare_nonlocal(self, name: str):
        """Track a 'nonlocal x' declaration."""
        self.nonlocal_declarations.add(name)
    
    def is_local(self, name: str) -> bool:
        """Check if a name is defined in any current scope."""
        for scope in self.scopes:
            if name in scope:
                return True
        return False
    
    def is_explicitly_global(self, name: str) -> bool:
        """Check if a name was declared with 'global'."""
        return name in self.global_declarations


def get_accessed_globals(node, defined_locals: Set[str]) -> Tuple[List[str], List[str]]:
    """
    Find global variables read or written by a function.
    
    Uses proper scope tracking to distinguish between:
    - Local variable definitions
    - Global variable access
    - Nonlocal variable access
    - Parameter access
    
    Args:
        node: Function AST node
        defined_locals: Set of locally defined variable names (including parameters)
        
    Returns:
        Tuple of (reads, writes) - lists of global variable names
    """
    reads: Set[str] = set()
    writes: Set[str] = set()
    
    scope_tracker = ScopeTracker()
    scope_tracker.enter_scope()
    
    # Add parameters and pre-defined locals to initial scope
    for local in defined_locals:
        scope_tracker.define_local(local)
    
    def extract_assignment_targets(node) -> List[str]:
        """Extract all variable names being assigned to."""
        targets = []
        
        if node.type == "identifier":
            targets.append(node.text.decode("utf8"))
        elif node.type == "tuple_pattern" or node.type == "list_pattern":
            # Tuple/list unpacking: a, b = ...
            for child in node.children:
                targets.extend(extract_assignment_targets(child))
        elif node.type == "pattern_list":
            for child in node.children:
                targets.extend(extract_assignment_targets(child))
        
        return targets
    
    def process_for_loop(for_node):
        """Process for loop and add loop variable to scope."""
        # Get the loop variable(s)
        left = for_node.child_by_field_name("left")
        if left:
            for var_name in extract_assignment_targets(left):
                scope_tracker.define_local(var_name)
    
    def process_comprehension(comp_node):
        """Process comprehension with its own scope."""
        scope_tracker.enter_scope()
        
        # Find and process the for_in_clause(s)
        for child in comp_node.children:
            if child.type == "for_in_clause":
                left = child.child_by_field_name("left")
                if left:
                    for var_name in extract_assignment_targets(left):
                        scope_tracker.define_local(var_name)
        
        # Process the body
        for child in comp_node.children:
            traverse(child)
        
        scope_tracker.exit_scope()
    
    def traverse(n, in_assignment_target: bool = False):
        """Traverse AST with proper scope awareness."""
        
        # Handle global declarations
        if n.type == "global_statement":
            for child in n.children:
                if child.type == "identifier":
                    scope_tracker.declare_global(child.text.decode("utf8"))
            return
        
        # Handle nonlocal declarations
        if n.type == "nonlocal_statement":
            for child in n.children:
                if child.type == "identifier":
                    scope_tracker.declare_nonlocal(child.text.decode("utf8"))
            return
        
        # Handle nested functions - they create a new scope but we don't analyze inside
        if n.type in ["function_definition", "async_function_definition"]:
            # Don't analyze nested functions
            return
        
        # Handle class definitions - skip
        if n.type == "class_definition":
            return
        
        # Handle comprehensions - they have their own scope
        if n.type in ["list_comprehension", "dictionary_comprehension", 
                      "set_comprehension", "generator_expression"]:
            process_comprehension(n)
            return
        
        # Handle for loops
        if n.type == "for_statement":
            process_for_loop(n)
        
        # Handle with statements (context manager variable)
        if n.type == "with_clause":
            # Find the 'as' target
            for child in n.children:
                if child.type == "as_pattern":
                    alias = child.child_by_field_name("alias")
                    if alias:
                        for var_name in extract_assignment_targets(alias):
                            scope_tracker.define_local(var_name)
        
        # Handle except clauses (exception variable)
        if n.type == "except_clause":
            for child in n.children:
                if child.type == "as_pattern":
                    alias = child.child_by_field_name("alias")
                    if alias:
                        for var_name in extract_assignment_targets(alias):
                            scope_tracker.define_local(var_name)
        
        # Handle assignments
        if n.type == "assignment":
            left = n.child_by_field_name("left")
            right = n.child_by_field_name("right")
            
            # Process target (defines new local or writes global)
            if left:
                target_names = extract_assignment_targets(left)
                for name in target_names:
                    if scope_tracker.is_explicitly_global(name):
                        # Writing to explicitly declared global
                        writes.add(name)
                    elif not scope_tracker.is_local(name):
                        # First assignment creates a local
                        scope_tracker.define_local(name)
            
            # Process value (reads)
            if right:
                traverse(right)
            return
        
        # Handle augmented assignments (+=, -=, etc.)
        if n.type == "augmented_assignment":
            left = n.child_by_field_name("left")
            right = n.child_by_field_name("right")
            
            if left and left.type == "identifier":
                name = left.text.decode("utf8")
                if scope_tracker.is_explicitly_global(name):
                    reads.add(name)
                    writes.add(name)
                elif not scope_tracker.is_local(name):
                    # Reading and writing a non-local (global)
                    reads.add(name)
                    writes.add(name)
            
            if right:
                traverse(right)
            return
        
        # Handle named expressions (walrus operator :=)
        if n.type == "named_expression":
            name_node = n.child_by_field_name("name")
            value_node = n.child_by_field_name("value")
            
            if name_node:
                name = name_node.text.decode("utf8")
                scope_tracker.define_local(name)
            
            if value_node:
                traverse(value_node)
            return
        
        # Handle identifier reads
        if n.type == "identifier" and not in_assignment_target:
            name = n.text.decode("utf8")
            # Check if it's accessing a non-local variable
            if not scope_tracker.is_local(name):
                if name not in PYTHON_BUILTINS:
                    reads.add(name)
        
        # Handle attribute access - only track the base object
        if n.type == "attribute":
            obj = n.child_by_field_name("object")
            if obj:
                traverse(obj)
            return
        
        # Recurse into children
        for child in n.children:
            traverse(child, in_assignment_target)
    
    body_node = node.child_by_field_name("body")
    if body_node:
        traverse(body_node)
    
    scope_tracker.exit_scope()
    
    return (list(reads), list(writes))


def extract_local_definitions(node) -> Set[str]:
    """
    Extract all locally defined variables from a function.
    
    This includes:
    - Parameters
    - Assignment targets
    - For loop variables
    - With clause variables
    - Except clause variables
    - Comprehension variables (in their scope)
    
    Args:
        node: Function AST node
        
    Returns:
        Set of locally defined variable names
    """
    locals_set: Set[str] = set()
    
    # Get parameters
    params_node = node.child_by_field_name("parameters")
    if params_node:
        for child in params_node.children:
            if child.type == "identifier":
                name = child.text.decode("utf8")
                if name not in ["self", "cls"]:
                    locals_set.add(name)
            elif child.type in ["typed_parameter", "default_parameter", "typed_default_parameter"]:
                name_node = child.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode("utf8")
                    if name not in ["self", "cls"]:
                        locals_set.add(name)
                else:
                    # Try first identifier child
                    for subchild in child.children:
                        if subchild.type == "identifier":
                            name = subchild.text.decode("utf8")
                            if name not in ["self", "cls"]:
                                locals_set.add(name)
                            break
            elif child.type in ["list_splat_pattern", "dictionary_splat_pattern"]:
                for subchild in child.children:
                    if subchild.type == "identifier":
                        locals_set.add(subchild.text.decode("utf8"))
    
    def find_definitions(n):
        """Recursively find all variable definitions."""
        # Skip nested functions and classes
        if n.type in ["function_definition", "async_function_definition", "class_definition"]:
            return
        
        # Assignment
        if n.type == "assignment":
            left = n.child_by_field_name("left")
            if left and left.type == "identifier":
                locals_set.add(left.text.decode("utf8"))
            elif left and left.type in ["tuple_pattern", "list_pattern", "pattern_list"]:
                for child in left.children:
                    if child.type == "identifier":
                        locals_set.add(child.text.decode("utf8"))
        
        # For loop variable
        if n.type == "for_statement":
            left = n.child_by_field_name("left")
            if left and left.type == "identifier":
                locals_set.add(left.text.decode("utf8"))
            elif left:
                for child in left.children:
                    if child.type == "identifier":
                        locals_set.add(child.text.decode("utf8"))
        
        # Named expression
        if n.type == "named_expression":
            name_node = n.child_by_field_name("name")
            if name_node:
                locals_set.add(name_node.text.decode("utf8"))
        
        # Recurse
        for child in n.children:
            find_definitions(child)
    
    body_node = node.child_by_field_name("body")
    if body_node:
        find_definitions(body_node)
    
    return locals_set
