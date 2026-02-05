"""
Architectural Governance Package

Provides architectural boundary enforcement, validation, and drift detection.

Usage:
    from backend.governance import ArchitectureValidator, DriftDetector
    
    # Validate with default Clean Architecture rules
    validator = ArchitectureValidator()
    result = validator.validate_repository("path/to/repo")
    
    # Or load custom rules from YAML
    validator = ArchitectureValidator.from_config(".synapse/architecture.yaml")
    
    # Detect drift
    detector = DriftDetector(baseline_path="baseline.json")
    report = detector.detect_drift("path/to/repo")
"""

from .models import (
    Layer,
    BoundaryRule,
    RuleAction,
    Violation,
    ViolationSeverity,
    ValidationResult,
    DriftMetrics,
    DriftReport,
    ArchitectureConfig,
)

from .rules import RuleEngine

from .validator import (
    ArchitectureValidator,
    FileValidationResult,
    RepositoryValidationResult,
    print_validation_report,
)

from .drift import (
    DriftDetector,
    print_drift_report,
)


__all__ = [
    # Models
    "Layer",
    "BoundaryRule",
    "RuleAction",
    "Violation",
    "ViolationSeverity",
    "ValidationResult",
    "DriftMetrics",
    "DriftReport",
    "ArchitectureConfig",
    # Rules
    "RuleEngine",
    # Validator
    "ArchitectureValidator",
    "FileValidationResult",
    "RepositoryValidationResult",
    "print_validation_report",
    # Drift
    "DriftDetector",
    "print_drift_report",
]
