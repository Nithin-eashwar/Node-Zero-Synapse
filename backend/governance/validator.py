"""
Architectural Governance - Validator

Validates entire codebase against architectural rules.
Integrates with the parsing layer to extract imports and check boundaries.
"""

import os
from typing import List, Dict, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, field

from .models import Violation, ValidationResult, ViolationSeverity
from .rules import RuleEngine


@dataclass
class FileValidationResult:
    """Result of validating a single file."""
    file_path: str
    violations: List[Violation] = field(default_factory=list)
    warnings: List[Violation] = field(default_factory=list)
    imports_checked: int = 0
    
    @property
    def has_errors(self) -> bool:
        return len(self.violations) > 0
    
    @property  
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
    
    def to_dict(self) -> Dict:
        return {
            "file_path": self.file_path,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": [w.to_dict() for w in self.warnings],
            "imports_checked": self.imports_checked,
            "has_errors": self.has_errors,
            "has_warnings": self.has_warnings
        }


@dataclass
class RepositoryValidationResult:
    """Result of validating an entire repository."""
    root_path: str
    file_results: List[FileValidationResult] = field(default_factory=list)
    total_files: int = 0
    total_imports: int = 0
    
    @property
    def total_violations(self) -> int:
        return sum(len(f.violations) for f in self.file_results)
    
    @property
    def total_warnings(self) -> int:
        return sum(len(f.warnings) for f in self.file_results)
    
    @property
    def files_with_violations(self) -> List[str]:
        return [f.file_path for f in self.file_results if f.has_errors]
    
    @property
    def all_violations(self) -> List[Violation]:
        violations = []
        for fr in self.file_results:
            violations.extend(fr.violations)
        return violations
    
    @property
    def all_warnings(self) -> List[Violation]:
        warnings = []
        for fr in self.file_results:
            warnings.extend(fr.warnings)
        return warnings
    
    def to_dict(self) -> Dict:
        return {
            "root_path": self.root_path,
            "total_files": self.total_files,
            "total_imports": self.total_imports,
            "total_violations": self.total_violations,
            "total_warnings": self.total_warnings,
            "files_with_violations": self.files_with_violations,
            "file_results": [f.to_dict() for f in self.file_results if f.has_errors or f.has_warnings]
        }


class ArchitectureValidator:
    """
    Validates codebase architecture against defined rules.
    
    Scans Python files, extracts imports, and checks each
    import against the rule engine.
    """
    
    def __init__(self, rule_engine: Optional[RuleEngine] = None):
        """
        Initialize validator.
        
        Args:
            rule_engine: RuleEngine to use. If None, uses clean architecture defaults.
        """
        self.rule_engine = rule_engine or RuleEngine.with_clean_architecture()
        self._violations: List[Violation] = []
        self._warnings: List[Violation] = []
    
    @classmethod
    def from_config(cls, config_path: str) -> "ArchitectureValidator":
        """Create validator from YAML config file."""
        rule_engine = RuleEngine.from_yaml(config_path)
        return cls(rule_engine)
    
    def validate_file(self, file_path: str, repo_root: str = "") -> FileValidationResult:
        """
        Validate a single Python file.
        
        Args:
            file_path: Path to the Python file
            repo_root: Root of the repository (for relative paths)
            
        Returns:
            FileValidationResult with any violations found
        """
        result = FileValidationResult(file_path=file_path)
        
        if not file_path.endswith('.py'):
            return result
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            return result
        
        # Extract imports using AST
        imports = self._extract_imports(content, file_path)
        
        # Determine the module path of this file
        if repo_root:
            relative_path = os.path.relpath(file_path, repo_root)
        else:
            relative_path = file_path
        
        # Validate each import
        for import_info in imports:
            result.imports_checked += 1
            
            validation = self.rule_engine.validate_import(
                from_module=relative_path,
                to_module=import_info['module'],
                file_path=file_path,
                line_number=import_info['line']
            )
            
            if validation.violation:
                if validation.violation.severity == ViolationSeverity.WARNING:
                    result.warnings.append(validation.violation)
                    self._warnings.append(validation.violation)
                else:
                    result.violations.append(validation.violation)
                    self._violations.append(validation.violation)
        
        return result
    
    def validate_repository(
        self, 
        repo_path: str,
        exclude_patterns: Optional[List[str]] = None
    ) -> RepositoryValidationResult:
        """
        Validate an entire repository.
        
        Args:
            repo_path: Path to repository root
            exclude_patterns: Patterns to exclude (e.g., ['**/test_*', '**/__pycache__/**'])
            
        Returns:
            RepositoryValidationResult with all violations
        """
        import fnmatch
        
        exclude_patterns = exclude_patterns or [
            '**/__pycache__/**',
            '**/venv/**',
            '**/.venv/**',
            '**/node_modules/**',
            '**/.git/**',
            '**/test_*.py',
            '**/*_test.py',
        ]
        
        result = RepositoryValidationResult(root_path=repo_path)
        self._violations = []
        self._warnings = []
        
        # Walk directory
        for root, dirs, files in os.walk(repo_path):
            # Filter directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, repo_path).replace("\\", "/")
                
                # Check exclude patterns
                excluded = False
                for pattern in exclude_patterns:
                    if fnmatch.fnmatch(relative_path, pattern):
                        excluded = True
                        break
                
                if excluded:
                    continue
                
                result.total_files += 1
                file_result = self.validate_file(file_path, repo_path)
                result.total_imports += file_result.imports_checked
                
                if file_result.has_errors or file_result.has_warnings:
                    result.file_results.append(file_result)
        
        return result
    
    def get_violations(self) -> List[Violation]:
        """Get all violations found during validation."""
        return self._violations.copy()
    
    def get_warnings(self) -> List[Violation]:
        """Get all warnings found during validation."""
        return self._warnings.copy()
    
    def _extract_imports(self, content: str, file_path: str) -> List[Dict]:
        """
        Extract import statements from Python code.
        
        Args:
            content: Python source code
            file_path: Path to file (for error context)
            
        Returns:
            List of dicts with 'module' and 'line' keys
        """
        import ast
        
        imports = []
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return imports
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'module': alias.name,
                        'line': node.lineno
                    })
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # Convert relative imports
                    module = node.module
                    if node.level > 0:
                        # Relative import - convert to absolute based on file location
                        module = self._resolve_relative_import(
                            file_path, node.module or '', node.level
                        )
                    imports.append({
                        'module': module,
                        'line': node.lineno
                    })
        
        return imports
    
    def _resolve_relative_import(self, file_path: str, module: str, level: int) -> str:
        """
        Resolve a relative import to an absolute module path.
        
        Args:
            file_path: Path to the importing file
            module: The imported module name
            level: Number of dots (1 = ., 2 = .., etc.)
            
        Returns:
            Resolved module path
        """
        parts = Path(file_path).parts
        
        # Go up 'level' directories
        if level > 0 and len(parts) > level:
            base_parts = parts[:-level]
            if module:
                return "/".join(base_parts) + "/" + module.replace(".", "/")
            return "/".join(base_parts)
        
        return module


def print_validation_report(result: RepositoryValidationResult) -> None:
    """Print a human-readable validation report."""
    print(f"\n{'='*60}")
    print(f"ARCHITECTURAL VALIDATION REPORT")
    print(f"{'='*60}")
    print(f"Repository: {result.root_path}")
    print(f"Files scanned: {result.total_files}")
    print(f"Imports checked: {result.total_imports}")
    print(f"{'='*60}")
    
    if result.total_violations == 0 and result.total_warnings == 0:
        print("[OK] No violations found! Architecture is clean.")
    else:
        if result.total_violations > 0:
            print(f"\n[ERROR] VIOLATIONS ({result.total_violations}):")
            for v in result.all_violations:
                print(f"  [{v.severity.value.upper()}] {v.file_path}:{v.line_number}")
                print(f"    {v.from_layer} -> {v.to_layer}: {v.message}")
        
        if result.total_warnings > 0:
            print(f"\n[WARN] WARNINGS ({result.total_warnings}):")
            for w in result.all_warnings:
                print(f"  [{w.severity.value.upper()}] {w.file_path}:{w.line_number}")
                print(f"    {w.from_layer} -> {w.to_layer}: {w.message}")
    
    print(f"\n{'='*60}\n")


# CLI entrypoint
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m backend.governance.validator <repo_path> [config_path]")
        sys.exit(1)
    
    repo_path = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if config_path:
        validator = ArchitectureValidator.from_config(config_path)
    else:
        validator = ArchitectureValidator()
    
    result = validator.validate_repository(repo_path)
    print_validation_report(result)
    
    sys.exit(1 if result.total_violations > 0 else 0)
