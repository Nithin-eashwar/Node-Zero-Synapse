"""
Expertise score calculator for Smart Blame.

This module orchestrates the calculation of expertise scores
using the weighted scoring factors.
"""

from typing import List, Optional, Dict
from datetime import datetime, timezone

from ..models import (
    DeveloperProfile,
    CommitAnalysis,
    ExpertiseScore,
    ScoringContext,
    SmartBlameConfig
)
from .factors import ScoringFactor, get_default_factors, validate_weights


class ExpertiseScoreCalculator:
    """
    Orchestrates the expertise scoring calculation.
    
    Combines multiple scoring factors with configurable weights
    to produce a comprehensive expertise score for each developer.
    """
    
    def __init__(
        self, 
        factors: Optional[List[ScoringFactor]] = None,
        config: Optional[SmartBlameConfig] = None
    ):
        """
        Initialize the calculator.
        
        Args:
            factors: Optional list of scoring factors (uses defaults if not provided)
            config: Optional configuration for thresholds and weights
        """
        self.factors = factors or get_default_factors()
        self.config = config or SmartBlameConfig()
        
        # Validate weights
        if not validate_weights(self.factors):
            import warnings
            total = sum(f.weight for f in self.factors)
            warnings.warn(f"Factor weights sum to {total}, expected 1.0")
    
    def calculate_expertise(
        self, 
        developer: DeveloperProfile,
        file_path: str,
        developer_commits: List[CommitAnalysis],
        all_commits: List[CommitAnalysis]
    ) -> ExpertiseScore:
        """
        Calculate comprehensive expertise score for a developer on a file.
        
        Args:
            developer: The developer profile
            file_path: Target file path
            developer_commits: Commits by this developer for the file
            all_commits: All commits for the file by all developers
            
        Returns:
            ExpertiseScore with detailed breakdown
        """
        # Build scoring context
        context = ScoringContext(
            target_path=file_path,
            all_commits=all_commits,
            developer_commits=developer_commits,
            total_commits_for_file=len(all_commits),
            recency_half_life_days=self.config.recency_half_life_days,
            min_commits_for_expertise=self.config.min_commits_for_expertise
        )
        
        # Calculate each factor score
        factor_scores: Dict[str, float] = {}
        weighted_sum = 0.0
        
        for factor in self.factors:
            score = factor.calculate(developer_commits, context)
            factor_scores[factor.name] = score
            
            # Use configured weight if available, otherwise use factor's default
            weight = self.config.weights.get(factor.name, factor.weight)
            weighted_sum += score * weight
        
        # Calculate confidence based on data quality
        confidence = self._calculate_confidence(developer_commits, context)
        
        # Generate human-readable reasoning
        reasoning = self._generate_reasoning(developer, factor_scores, confidence)
        
        # Get last activity date
        last_activity = None
        if developer_commits:
            last_activity = max(c.timestamp for c in developer_commits)
        
        return ExpertiseScore(
            developer=developer,
            target_path=file_path,
            total_score=min(weighted_sum, 1.0),
            factors=factor_scores,
            confidence=confidence,
            reasoning=reasoning,
            commit_count=len(developer_commits),
            last_activity=last_activity
        )
    
    def _calculate_confidence(
        self, 
        commits: List[CommitAnalysis], 
        context: ScoringContext
    ) -> float:
        """
        Calculate confidence in the expertise score.
        
        Confidence is based on:
        - Number of commits (more data = higher confidence)
        - Recency of commits (recent activity = higher confidence)
        - Diversity of commit types (varied contributions = higher confidence)
        """
        if not commits:
            return 0.0
        
        # Factor 1: Commit count (more commits = more confidence)
        min_commits = context.min_commits_for_expertise
        commit_factor = min(1.0, len(commits) / (min_commits * 3))
        
        # Factor 2: Recency (recent activity = more confidence)
        now = datetime.now(timezone.utc)
        most_recent = max(commits, key=lambda c: c.timestamp)
        days_since = (now - most_recent.timestamp).days
        recency_factor = max(0.0, 1.0 - (days_since / 365))  # Decays over a year
        
        # Factor 3: Diversity (varied commit types = more confidence)
        commit_types = set()
        if any(c.is_refactor for c in commits):
            commit_types.add('refactor')
        if any(c.is_bug_fix for c in commits):
            commit_types.add('bug_fix')
        if any(c.is_architectural for c in commits):
            commit_types.add('architectural')
        if any(not (c.is_refactor or c.is_bug_fix or c.is_architectural) for c in commits):
            commit_types.add('feature')
        
        diversity_factor = len(commit_types) / 4.0
        
        # Combine factors
        confidence = (commit_factor * 0.5) + (recency_factor * 0.3) + (diversity_factor * 0.2)
        
        return min(1.0, max(0.0, confidence))
    
    def _generate_reasoning(
        self, 
        developer: DeveloperProfile,
        scores: Dict[str, float], 
        confidence: float
    ) -> str:
        """
        Generate human-readable reasoning for the score.
        
        Explains why the developer is considered an expert (or not).
        """
        first_name = developer.name.split()[0] if developer.name else "This developer"
        
        # Find top contributing factors
        sorted_factors = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_factors = [(name, score) for name, score in sorted_factors if score > 0.3]
        
        if not top_factors:
            if confidence < 0.3:
                return f"Insufficient data to determine {first_name}'s expertise level."
            return f"{first_name} has limited involvement with this code."
        
        # Build reasoning based on top factors
        reasons = []
        
        for factor_name, score in top_factors[:2]:  # Top 2 factors
            if factor_name == 'refactor_depth' and score > 0.5:
                reasons.append(f"deeply refactored this code")
            elif factor_name == 'architectural_changes' and score > 0.5:
                reasons.append(f"made significant architectural contributions")
            elif factor_name == 'bug_fixes' and score > 0.4:
                reasons.append(f"fixed numerous bugs here")
            elif factor_name == 'commit_frequency' and score > 0.5:
                reasons.append(f"is a frequent contributor")
            elif factor_name == 'recency' and score > 0.7:
                reasons.append(f"has recent active involvement")
            elif factor_name == 'lines_changed' and score > 0.5:
                reasons.append(f"has made substantial code changes")
        
        if reasons:
            reason_text = " and ".join(reasons)
            return f"{first_name} {reason_text}."
        
        return f"{first_name} has contributed to this code."
    
    def calculate_multiple(
        self,
        developers: List[DeveloperProfile],
        file_path: str,
        commits_by_developer: Dict[str, List[CommitAnalysis]],
        all_commits: List[CommitAnalysis]
    ) -> List[ExpertiseScore]:
        """
        Calculate expertise scores for multiple developers.
        
        Args:
            developers: List of developer profiles
            file_path: Target file path
            commits_by_developer: Dict mapping email to commits
            all_commits: All commits for the file
            
        Returns:
            List of ExpertiseScore sorted by total_score descending
        """
        scores = []
        
        for developer in developers:
            developer_commits = commits_by_developer.get(developer.email, [])
            
            if not developer_commits:
                continue
            
            score = self.calculate_expertise(
                developer, 
                file_path, 
                developer_commits, 
                all_commits
            )
            scores.append(score)
        
        # Sort by total score descending
        scores.sort(key=lambda s: s.total_score, reverse=True)
        
        return scores
