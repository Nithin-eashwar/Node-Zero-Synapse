"""
Architectural Governance - Drift Detection

Tracks architectural metrics over time to detect drift from baseline.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from collections import defaultdict

from .models import DriftMetrics, DriftReport
from .rules import RuleEngine
from .validator import ArchitectureValidator, RepositoryValidationResult


class DriftDetector:
    """
    Detects architectural drift by comparing current metrics to baseline.
    
    Calculates metrics like coupling, cohesion, and violation counts,
    then compares to historical data to identify drift.
    """
    
    def __init__(
        self,
        rule_engine: Optional[RuleEngine] = None,
        baseline_path: Optional[str] = None
    ):
        """
        Initialize drift detector.
        
        Args:
            rule_engine: RuleEngine for layer classification
            baseline_path: Path to baseline metrics JSON file
        """
        self.rule_engine = rule_engine or RuleEngine.with_clean_architecture()
        self.baseline_path = baseline_path
        self._baseline: Optional[DriftMetrics] = None
        
        if baseline_path and os.path.exists(baseline_path):
            self._baseline = self._load_baseline(baseline_path)
    
    def calculate_metrics(self, repo_path: str) -> DriftMetrics:
        """
        Calculate current architectural metrics for a repository.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            DriftMetrics with current state
        """
        # Run validation to get import data
        validator = ArchitectureValidator(self.rule_engine)
        validation_result = validator.validate_repository(repo_path)
        
        # Collect layer statistics
        layer_files: Dict[str, int] = defaultdict(int)
        layer_imports: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        total_files = 0
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, repo_path)
                layer = self.rule_engine.classify_layer(relative_path)
                
                if layer:
                    layer_files[layer] += 1
                total_files += 1
        
        # Calculate layer balance
        layer_balance = {}
        if total_files > 0:
            for layer_name, count in layer_files.items():
                layer_balance[layer_name] = round(count / total_files, 3)
        
        # Calculate coupling score (violations / total imports)
        total_imports = validation_result.total_imports
        coupling_score = 0.0
        if total_imports > 0:
            violation_weight = validation_result.total_violations + (validation_result.total_warnings * 0.5)
            coupling_score = min(violation_weight / total_imports, 1.0)
        
        # Calculate cohesion score (intra-layer imports / total imports)
        # For now, use inverse of coupling as a proxy
        cohesion_score = 1.0 - coupling_score
        
        # Calculate dependency depth (simplified: max violation chain)
        dependency_depth = self._calculate_dependency_depth(validation_result)
        
        return DriftMetrics(
            timestamp=datetime.now(),
            coupling_score=round(coupling_score, 3),
            cohesion_score=round(cohesion_score, 3),
            violation_count=validation_result.total_violations,
            layer_balance=layer_balance,
            dependency_depth=dependency_depth
        )
    
    def detect_drift(self, repo_path: str) -> DriftReport:
        """
        Detect architectural drift compared to baseline.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            DriftReport with comparison and recommendations
        """
        current = self.calculate_metrics(repo_path)
        
        if self._baseline is None:
            # No baseline - report current state only
            return DriftReport(
                baseline=None,
                current=current,
                drift_score=0.0,
                indicators={},
                recommendations=["No baseline found. Run 'save_baseline' to establish one."]
            )
        
        # Calculate drift indicators
        indicators = self._calculate_indicators(self._baseline, current)
        
        # Calculate overall drift score (0-1)
        drift_score = self._calculate_drift_score(indicators)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(indicators, current)
        
        return DriftReport(
            baseline=self._baseline,
            current=current,
            drift_score=round(drift_score, 3),
            indicators=indicators,
            recommendations=recommendations
        )
    
    def save_baseline(self, repo_path: str, output_path: str) -> DriftMetrics:
        """
        Calculate and save current metrics as baseline.
        
        Args:
            repo_path: Path to repository
            output_path: Path to save baseline JSON
            
        Returns:
            Calculated metrics
        """
        metrics = self.calculate_metrics(repo_path)
        
        with open(output_path, 'w') as f:
            json.dump(metrics.to_dict(), f, indent=2)
        
        self._baseline = metrics
        self.baseline_path = output_path
        
        return metrics
    
    def _load_baseline(self, path: str) -> DriftMetrics:
        """Load baseline metrics from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        
        return DriftMetrics(
            timestamp=datetime.fromisoformat(data['timestamp']),
            coupling_score=data['coupling_score'],
            cohesion_score=data['cohesion_score'],
            violation_count=data['violation_count'],
            layer_balance=data['layer_balance'],
            dependency_depth=data['dependency_depth']
        )
    
    def _calculate_dependency_depth(self, result: RepositoryValidationResult) -> int:
        """Calculate maximum dependency chain depth."""
        # Simplified: count unique layers in violation chains
        layers_in_violations: Set[str] = set()
        for v in result.all_violations:
            layers_in_violations.add(v.from_layer)
            layers_in_violations.add(v.to_layer)
        return len(layers_in_violations)
    
    def _calculate_indicators(
        self,
        baseline: DriftMetrics,
        current: DriftMetrics
    ) -> Dict[str, float]:
        """Calculate drift indicators between baseline and current."""
        indicators = {}
        
        # Coupling drift (positive = worse)
        indicators['coupling_increase'] = round(
            current.coupling_score - baseline.coupling_score, 3
        )
        
        # Cohesion drift (negative = worse)
        indicators['cohesion_decrease'] = round(
            baseline.cohesion_score - current.cohesion_score, 3
        )
        
        # Violation drift
        indicators['violation_increase'] = current.violation_count - baseline.violation_count
        
        # Layer balance drift (how much distribution changed)
        balance_drift = 0.0
        all_layers = set(baseline.layer_balance.keys()) | set(current.layer_balance.keys())
        for layer in all_layers:
            old_val = baseline.layer_balance.get(layer, 0)
            new_val = current.layer_balance.get(layer, 0)
            balance_drift += abs(new_val - old_val)
        indicators['balance_drift'] = round(balance_drift, 3)
        
        # Dependency depth drift
        indicators['depth_increase'] = (
            current.dependency_depth - baseline.dependency_depth
        )
        
        return indicators
    
    def _calculate_drift_score(self, indicators: Dict[str, float]) -> float:
        """
        Calculate overall drift score from indicators.
        
        Returns value between 0 (no drift) and 1 (severe drift).
        """
        weights = {
            'coupling_increase': 0.25,
            'cohesion_decrease': 0.20,
            'violation_increase': 0.30,
            'balance_drift': 0.15,
            'depth_increase': 0.10,
        }
        
        normalized_score = 0.0
        
        # Normalize each indicator to 0-1 range
        for key, weight in weights.items():
            value = indicators.get(key, 0)
            
            if key == 'violation_increase':
                # Cap at 10 violations for normalization
                normalized = min(abs(value) / 10, 1.0) if value > 0 else 0
            elif key == 'depth_increase':
                # Cap at 3 levels
                normalized = min(abs(value) / 3, 1.0) if value > 0 else 0
            else:
                # Already 0-1 range (roughly)
                normalized = min(abs(value), 1.0) if value > 0 else 0
            
            normalized_score += normalized * weight
        
        return min(normalized_score, 1.0)
    
    def _generate_recommendations(
        self,
        indicators: Dict[str, float],
        current: DriftMetrics
    ) -> List[str]:
        """Generate recommendations based on drift indicators."""
        recommendations = []
        
        if indicators.get('coupling_increase', 0) > 0.1:
            recommendations.append(
                "⚠️ Coupling has increased significantly. Review new cross-layer imports."
            )
        
        if indicators.get('violation_increase', 0) > 0:
            count = int(indicators['violation_increase'])
            recommendations.append(
                f"❌ {count} new architecture violations detected. Address these before they accumulate."
            )
        
        if indicators.get('balance_drift', 0) > 0.2:
            recommendations.append(
                "📊 Code distribution across layers has shifted. Ensure new code is in appropriate layers."
            )
        
        if current.violation_count > 5:
            recommendations.append(
                "🔧 Consider refactoring to reduce violation count below 5."
            )
        
        if not recommendations:
            recommendations.append("✅ Architecture is stable. No significant drift detected.")
        
        return recommendations


def print_drift_report(report: DriftReport) -> None:
    """Print a human-readable drift report."""
    print(f"\n{'='*60}")
    print("ARCHITECTURAL DRIFT REPORT")
    print(f"{'='*60}")
    print(f"Timestamp: {report.current.timestamp.isoformat()}")
    print(f"Drift Score: {report.drift_score:.1%}")
    
    if report.baseline:
        print(f"\n--- INDICATORS ---")
        for key, value in report.indicators.items():
            direction = "↑" if value > 0 else "↓" if value < 0 else "→"
            print(f"  {key}: {value:+.3f} {direction}")
    
    print(f"\n--- CURRENT METRICS ---")
    print(f"  Coupling Score: {report.current.coupling_score:.1%}")
    print(f"  Cohesion Score: {report.current.cohesion_score:.1%}")
    print(f"  Violations: {report.current.violation_count}")
    print(f"  Layer Balance: {report.current.layer_balance}")
    
    print(f"\n--- RECOMMENDATIONS ---")
    for rec in report.recommendations:
        print(f"  {rec}")
    
    print(f"\n{'='*60}\n")


# CLI entrypoint
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m backend.governance.drift <repo_path> [baseline_path]")
        print("  python -m backend.governance.drift --save-baseline <repo_path> <output_path>")
        sys.exit(1)
    
    if sys.argv[1] == "--save-baseline":
        if len(sys.argv) < 4:
            print("Usage: python -m backend.governance.drift --save-baseline <repo_path> <output_path>")
            sys.exit(1)
        detector = DriftDetector()
        metrics = detector.save_baseline(sys.argv[2], sys.argv[3])
        print(f"✅ Baseline saved to {sys.argv[3]}")
        print(f"   Coupling: {metrics.coupling_score:.1%}")
        print(f"   Violations: {metrics.violation_count}")
    else:
        repo_path = sys.argv[1]
        baseline_path = sys.argv[2] if len(sys.argv) > 2 else None
        
        detector = DriftDetector(baseline_path=baseline_path)
        report = detector.detect_drift(repo_path)
        print_drift_report(report)
