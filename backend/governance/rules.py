"""
Architectural Governance - Rule Engine

Loads and evaluates architectural boundary rules from YAML configuration.
"""

import os
import fnmatch
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from .models import (
    Layer, BoundaryRule, RuleAction, ArchitectureConfig,
    ValidationResult, Violation, ViolationSeverity
)


# Default rules for common patterns
DEFAULT_CLEAN_ARCHITECTURE_RULES = [
    BoundaryRule(
        name="API cannot access Data directly",
        from_layer="api",
        to_layer="data",
        action=RuleAction.BLOCK,
        message="API layer should not directly access data layer. Use service layer instead."
    ),
    BoundaryRule(
        name="Data cannot access Service",
        from_layer="data",
        to_layer="service",
        action=RuleAction.BLOCK,
        message="Data layer should not depend on service layer (inverted dependency)."
    ),
    BoundaryRule(
        name="Data cannot access API",
        from_layer="data",
        to_layer="api",
        action=RuleAction.BLOCK,
        message="Data layer should not depend on API layer."
    ),
]


class RuleEngine:
    """
    Rule engine for evaluating architectural boundaries.
    
    Loads layer definitions and rules from YAML config,
    classifies modules into layers, and validates imports.
    """
    
    def __init__(self, config: Optional[ArchitectureConfig] = None):
        """
        Initialize the rule engine.
        
        Args:
            config: Optional pre-loaded config. If None, uses defaults.
        """
        self.config = config or ArchitectureConfig()
        self._layer_cache: Dict[str, str] = {}  # module_path -> layer_name
    
    @classmethod
    def from_yaml(cls, config_path: str) -> "RuleEngine":
        """
        Load rules from a YAML configuration file.
        
        Args:
            config_path: Path to .synapse/architecture.yaml
            
        Returns:
            Configured RuleEngine instance
        """
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML is required for YAML config. Install with: pip install pyyaml")
        
        with open(config_path, 'r') as f:
            raw_config = yaml.safe_load(f)
        
        config = ArchitectureConfig()
        
        # Parse layers
        for layer_name, layer_data in raw_config.get('layers', {}).items():
            config.layers[layer_name] = Layer(
                name=layer_name,
                patterns=layer_data.get('patterns', []),
                description=layer_data.get('description', ''),
                allowed_dependencies=layer_data.get('allowed_dependencies', [])
            )
        
        # Parse rules
        for rule_data in raw_config.get('rules', []):
            action = RuleAction(rule_data.get('action', 'warn'))
            config.rules.append(BoundaryRule(
                name=rule_data.get('name', 'Unnamed Rule'),
                from_layer=rule_data.get('from', ''),
                to_layer=rule_data.get('to', ''),
                action=action,
                message=rule_data.get('message', '')
            ))
        
        config.strict_mode = raw_config.get('strict_mode', False)
        
        return cls(config)
    
    @classmethod
    def with_clean_architecture(cls, custom_patterns: Optional[Dict[str, List[str]]] = None) -> "RuleEngine":
        """
        Create a RuleEngine with default Clean Architecture rules.
        
        Args:
            custom_patterns: Optional custom patterns for layer detection.
                           Keys: 'api', 'service', 'data'
                           Values: List of glob patterns
        
        Returns:
            RuleEngine with clean architecture rules
        """
        default_patterns = {
            'api': ['**/api/**', '**/routes/**', '**/endpoints/**', '**/controllers/**'],
            'service': ['**/services/**', '**/core/**', '**/domain/**', '**/usecases/**'],
            'data': ['**/data/**', '**/models/**', '**/storage/**', '**/repositories/**', '**/db/**'],
        }
        
        patterns = {**default_patterns, **(custom_patterns or {})}
        
        config = ArchitectureConfig(
            layers={
                'api': Layer(name='api', patterns=patterns['api'], 
                            description='API/Controller layer',
                            allowed_dependencies=['service']),
                'service': Layer(name='service', patterns=patterns['service'],
                                description='Business logic layer',
                                allowed_dependencies=['data']),
                'data': Layer(name='data', patterns=patterns['data'],
                             description='Data access layer',
                             allowed_dependencies=[]),
            },
            rules=DEFAULT_CLEAN_ARCHITECTURE_RULES,
            strict_mode=False
        )
        
        return cls(config)
    
    def classify_layer(self, module_path: str) -> Optional[str]:
        """
        Determine which layer a module belongs to.
        
        Args:
            module_path: Path to the module (file or import path)
            
        Returns:
            Layer name or None if not classified
        """
        # Check cache first
        if module_path in self._layer_cache:
            return self._layer_cache[module_path]
        
        # Normalize path
        normalized = module_path.replace("\\", "/")
        
        # Try each layer
        for layer_name, layer in self.config.layers.items():
            if layer.matches(normalized):
                self._layer_cache[module_path] = layer_name
                return layer_name
        
        return None
    
    def validate_import(
        self,
        from_module: str,
        to_module: str,
        file_path: str = "",
        line_number: int = 0
    ) -> ValidationResult:
        """
        Validate if an import is allowed.
        
        Args:
            from_module: The importing module path
            to_module: The imported module path
            file_path: Source file path (for violation reporting)
            line_number: Line number of import (for violation reporting)
            
        Returns:
            ValidationResult indicating if import is allowed
        """
        from_layer = self.classify_layer(from_module)
        to_layer = self.classify_layer(to_module)
        
        # If either module isn't classified, allow by default (unless strict mode)
        if from_layer is None or to_layer is None:
            if self.config.strict_mode:
                return ValidationResult(
                    valid=False,
                    violation=Violation(
                        file_path=file_path,
                        line_number=line_number,
                        from_module=from_module,
                        to_module=to_module,
                        from_layer=from_layer or "unknown",
                        to_layer=to_layer or "unknown",
                        rule=BoundaryRule(
                            name="Strict Mode",
                            from_layer="unknown",
                            to_layer="unknown",
                            action=RuleAction.BLOCK,
                            message="Module not classified in strict mode"
                        ),
                        severity=ViolationSeverity.WARNING,
                        message=f"Unclassified import: {from_module} -> {to_module}"
                    )
                )
            return ValidationResult(valid=True)
        
        # Same layer imports are always allowed
        if from_layer == to_layer:
            return ValidationResult(valid=True)
        
        # Check rules
        for rule in self.config.rules:
            if rule.matches(from_layer, to_layer):
                if rule.action == RuleAction.ALLOW:
                    return ValidationResult(valid=True)
                
                severity = (ViolationSeverity.WARNING if rule.action == RuleAction.WARN 
                           else ViolationSeverity.ERROR)
                
                return ValidationResult(
                    valid=(rule.action == RuleAction.WARN),
                    violation=Violation(
                        file_path=file_path,
                        line_number=line_number,
                        from_module=from_module,
                        to_module=to_module,
                        from_layer=from_layer,
                        to_layer=to_layer,
                        rule=rule,
                        severity=severity,
                        message=rule.message or f"Import from {from_layer} to {to_layer} violates {rule.name}"
                    )
                )
        
        # Check allowed_dependencies on source layer
        source_layer = self.config.layers.get(from_layer)
        if source_layer and source_layer.allowed_dependencies:
            if to_layer not in source_layer.allowed_dependencies:
                return ValidationResult(
                    valid=False,
                    violation=Violation(
                        file_path=file_path,
                        line_number=line_number,
                        from_module=from_module,
                        to_module=to_module,
                        from_layer=from_layer,
                        to_layer=to_layer,
                        rule=BoundaryRule(
                            name="Allowed Dependencies",
                            from_layer=from_layer,
                            to_layer=to_layer,
                            action=RuleAction.BLOCK
                        ),
                        severity=ViolationSeverity.ERROR,
                        message=f"{from_layer} layer can only depend on: {source_layer.allowed_dependencies}"
                    )
                )
        
        # Default: allow
        return ValidationResult(valid=True)
    
    def get_layer_summary(self) -> Dict[str, Dict]:
        """Get summary of all defined layers."""
        return {
            name: {
                "description": layer.description,
                "patterns": layer.patterns,
                "allowed_dependencies": layer.allowed_dependencies
            }
            for name, layer in self.config.layers.items()
        }
    
    def get_rules_summary(self) -> List[Dict]:
        """Get summary of all defined rules."""
        return [
            {
                "name": rule.name,
                "from_layer": rule.from_layer,
                "to_layer": rule.to_layer,
                "action": rule.action.value,
                "message": rule.message
            }
            for rule in self.config.rules
        ]
