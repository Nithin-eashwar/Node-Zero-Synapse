"""
Architectural Governance - Data Models

Data classes for representing architectural layers, rules, violations, and drift metrics.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set
from datetime import datetime


class RuleAction(Enum):
    """Action to take when a rule matches."""
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


class ViolationSeverity(Enum):
    """Severity level of a violation."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Layer:
    """
    Represents an architectural layer in the codebase.
    
    Attributes:
        name: Unique identifier for the layer (e.g., 'api', 'service', 'data')
        patterns: Glob patterns that match modules in this layer
        description: Human-readable description
        allowed_dependencies: Layers this layer can depend on
    """
    name: str
    patterns: List[str]
    description: str = ""
    allowed_dependencies: List[str] = field(default_factory=list)
    
    def matches(self, module_path: str) -> bool:
        """Check if a module path belongs to this layer."""
        import fnmatch
        normalized = module_path.replace("\\", "/")
        return any(fnmatch.fnmatch(normalized, pattern) for pattern in self.patterns)


@dataclass 
class BoundaryRule:
    """
    Defines a rule for architectural boundary enforcement.
    
    Attributes:
        name: Human-readable rule name
        from_layer: Source layer name
        to_layer: Target layer name  
        action: What to do when rule matches (allow/warn/block)
        message: Custom message for violations
    """
    name: str
    from_layer: str
    to_layer: str
    action: RuleAction
    message: str = ""
    
    def matches(self, source_layer: str, target_layer: str) -> bool:
        """Check if this rule applies to the given import."""
        return self.from_layer == source_layer and self.to_layer == target_layer


@dataclass
class Violation:
    """
    Records a detected architectural violation.
    
    Attributes:
        file_path: File where violation occurred
        line_number: Line number of the import
        from_module: Importing module
        to_module: Imported module
        from_layer: Layer of importing module
        to_layer: Layer of imported module
        rule: The rule that was violated
        severity: Severity level
        message: Description of the violation
    """
    file_path: str
    line_number: int
    from_module: str
    to_module: str
    from_layer: str
    to_layer: str
    rule: BoundaryRule
    severity: ViolationSeverity
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "from_module": self.from_module,
            "to_module": self.to_module,
            "from_layer": self.from_layer,
            "to_layer": self.to_layer,
            "rule_name": self.rule.name,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class DriftMetrics:
    """
    Captures architectural metrics at a point in time.
    
    Attributes:
        timestamp: When metrics were captured
        coupling_score: Overall coupling between layers (0-1, lower is better)
        cohesion_score: Internal cohesion within layers (0-1, higher is better)
        violation_count: Number of active violations
        layer_balance: Distribution of code across layers
        dependency_depth: Maximum dependency chain length
    """
    timestamp: datetime
    coupling_score: float
    cohesion_score: float
    violation_count: int
    layer_balance: Dict[str, float]  # layer_name -> percentage
    dependency_depth: int
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "coupling_score": self.coupling_score,
            "cohesion_score": self.cohesion_score,
            "violation_count": self.violation_count,
            "layer_balance": self.layer_balance,
            "dependency_depth": self.dependency_depth
        }


@dataclass
class DriftReport:
    """
    Summary of architectural drift between two points in time.
    
    Attributes:
        baseline: Metrics from baseline/previous snapshot
        current: Current metrics
        drift_score: Overall drift score (0-1, lower is better)
        indicators: Specific drift indicators
        recommendations: Suggested actions
    """
    baseline: Optional[DriftMetrics]
    current: DriftMetrics
    drift_score: float
    indicators: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "baseline": self.baseline.to_dict() if self.baseline else None,
            "current": self.current.to_dict(),
            "drift_score": self.drift_score,
            "indicators": self.indicators,
            "recommendations": self.recommendations
        }


@dataclass
class ValidationResult:
    """
    Result of validating an import or module.
    
    Attributes:
        valid: Whether the import is allowed
        violation: Violation details if not valid
    """
    valid: bool
    violation: Optional[Violation] = None
    
    def to_dict(self) -> Dict:
        return {
            "valid": self.valid,
            "violation": self.violation.to_dict() if self.violation else None
        }


@dataclass
class ArchitectureConfig:
    """
    Complete architectural configuration.
    
    Attributes:
        layers: Defined layers
        rules: Boundary rules
        strict_mode: If True, undefined imports are blocked
    """
    layers: Dict[str, Layer] = field(default_factory=dict)
    rules: List[BoundaryRule] = field(default_factory=list)
    strict_mode: bool = False
