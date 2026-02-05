"""
Scoring factors for expertise calculation.

This module implements the 7 weighted factors used to calculate
developer expertise scores as defined in the design document.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Dict
import math

from ..models import CommitAnalysis, ScoringContext


class ScoringFactor(ABC):
    """
    Abstract base class for scoring factors.
    
    Each factor calculates a normalized score (0.0 - 1.0) based on
    specific aspects of a developer's contributions.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this factor."""
        pass
    
    @property
    @abstractmethod
    def weight(self) -> float:
        """Default weight for this factor (0.0 - 1.0)."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this factor measures."""
        pass
    
    @abstractmethod
    def calculate(self, commits: List[CommitAnalysis], context: ScoringContext) -> float:
        """
        Calculate the normalized score for this factor.
        
        Args:
            commits: List of commits by the developer for the target file
            context: Additional context for normalization
            
        Returns:
            Normalized score between 0.0 and 1.0
        """
        pass


class CommitFrequencyFactor(ScoringFactor):
    """
    Measures how frequently a developer commits to the file.
    
    Weight: 0.15
    
    Rationale: Regular contributors are more familiar with the code,
    but this is a weaker signal than deep contributions.
    """
    
    @property
    def name(self) -> str:
        return "commit_frequency"
    
    @property
    def weight(self) -> float:
        return 0.15
    
    @property
    def description(self) -> str:
        return "Frequency of commits to this file relative to total commits"
    
    def calculate(self, commits: List[CommitAnalysis], context: ScoringContext) -> float:
        if context.total_commits_for_file == 0:
            return 0.0
        
        # Calculate ratio of developer commits to total commits
        ratio = len(commits) / context.total_commits_for_file
        
        # Apply logarithmic scaling to avoid extreme values
        # This ensures that having 50% of commits vs 100% isn't a huge difference
        score = min(1.0, ratio * 2)  # Cap at 1.0
        
        return score


class LinesChangedFactor(ScoringFactor):
    """
    Measures total lines modified by the developer.
    
    Weight: 0.10
    
    Rationale: More lines changed indicates more involvement,
    but quantity doesn't always mean quality or understanding.
    """
    
    @property
    def name(self) -> str:
        return "lines_changed"
    
    @property
    def weight(self) -> float:
        return 0.10
    
    @property
    def description(self) -> str:
        return "Total lines added and deleted by the developer"
    
    def calculate(self, commits: List[CommitAnalysis], context: ScoringContext) -> float:
        if not commits:
            return 0.0
        
        total_lines = sum(c.total_lines_changed for c in commits)
        
        # Calculate total lines changed across all commits
        all_lines = sum(c.total_lines_changed for c in context.all_commits)
        
        if all_lines == 0:
            return 0.0
        
        ratio = total_lines / all_lines
        
        # Apply square root scaling to reduce impact of outliers
        score = min(1.0, math.sqrt(ratio) * 1.5)
        
        return score


class RefactorDepthFactor(ScoringFactor):
    """
    Measures complexity and depth of refactoring contributions.
    
    Weight: 0.25 (highest weight)
    
    Rationale: Developers who refactor code deeply understand it.
    Refactoring requires understanding not just what code does,
    but why it was written that way and how to improve it.
    """
    
    @property
    def name(self) -> str:
        return "refactor_depth"
    
    @property
    def weight(self) -> float:
        return 0.25
    
    @property
    def description(self) -> str:
        return "Depth and complexity of refactoring commits"
    
    def calculate(self, commits: List[CommitAnalysis], context: ScoringContext) -> float:
        if not commits:
            return 0.0
        
        refactor_commits = [c for c in commits if c.is_refactor]
        
        if not refactor_commits:
            return 0.0
        
        # Calculate refactor score based on:
        # 1. Number of refactor commits
        # 2. Size of refactor commits (more lines = deeper refactoring)
        
        refactor_count = len(refactor_commits)
        total_refactor_lines = sum(c.total_lines_changed for c in refactor_commits)
        
        # Count total refactors in the file by all developers
        all_refactors = [c for c in context.all_commits if c.is_refactor]
        total_all_refactors = len(all_refactors) if all_refactors else 1
        total_all_refactor_lines = sum(c.total_lines_changed for c in all_refactors) if all_refactors else 1
        
        # Combine count and size ratios
        count_ratio = refactor_count / total_all_refactors
        size_ratio = total_refactor_lines / total_all_refactor_lines if total_all_refactor_lines > 0 else 0
        
        # Weight size slightly higher as it indicates deeper changes
        score = (count_ratio * 0.4) + (size_ratio * 0.6)
        
        return min(1.0, score)


class ArchitecturalChangesFactor(ScoringFactor):
    """
    Measures contributions to structural/architectural changes.
    
    Weight: 0.20
    
    Rationale: Developers who make architectural changes understand
    the system at a deeper level than those who just fix bugs or
    add features within existing structures.
    """
    
    @property
    def name(self) -> str:
        return "architectural_changes"
    
    @property
    def weight(self) -> float:
        return 0.20
    
    @property
    def description(self) -> str:
        return "Contributions to architectural and structural changes"
    
    def calculate(self, commits: List[CommitAnalysis], context: ScoringContext) -> float:
        if not commits:
            return 0.0
        
        arch_commits = [c for c in commits if c.is_architectural]
        
        if not arch_commits:
            return 0.0
        
        # Count architectural commits by this developer
        arch_count = len(arch_commits)
        
        # Count total architectural commits for the file
        all_arch = [c for c in context.all_commits if c.is_architectural]
        total_arch = len(all_arch) if all_arch else 1
        
        # Calculate ratio
        ratio = arch_count / total_arch
        
        # Boost score for architectural contributions (they're rare and valuable)
        score = min(1.0, ratio * 1.5)
        
        return score


class BugFixesFactor(ScoringFactor):
    """
    Measures bug fix contributions.
    
    Weight: 0.15
    
    Rationale: Fixing bugs requires deep understanding of the code,
    its edge cases, and its interactions with other components.
    """
    
    @property
    def name(self) -> str:
        return "bug_fixes"
    
    @property
    def weight(self) -> float:
        return 0.15
    
    @property
    def description(self) -> str:
        return "Number and complexity of bug fixes contributed"
    
    def calculate(self, commits: List[CommitAnalysis], context: ScoringContext) -> float:
        if not commits:
            return 0.0
        
        bug_fix_commits = [c for c in commits if c.is_bug_fix]
        
        if not bug_fix_commits:
            return 0.0
        
        # Count bug fixes by this developer
        fix_count = len(bug_fix_commits)
        
        # Count total bug fixes for the file
        all_fixes = [c for c in context.all_commits if c.is_bug_fix]
        total_fixes = len(all_fixes) if all_fixes else 1
        
        # Calculate ratio
        ratio = fix_count / total_fixes
        
        return min(1.0, ratio)


class RecencyFactor(ScoringFactor):
    """
    Measures how recently the developer has contributed.
    
    Weight: 0.10
    
    Rationale: Recent contributors are more likely to remember
    the code details and current state. Uses exponential decay
    with configurable half-life.
    """
    
    @property
    def name(self) -> str:
        return "recency"
    
    @property
    def weight(self) -> float:
        return 0.10
    
    @property
    def description(self) -> str:
        return "Recency of contributions (exponential decay)"
    
    def calculate(self, commits: List[CommitAnalysis], context: ScoringContext) -> float:
        if not commits:
            return 0.0
        
        now = datetime.now(timezone.utc)
        half_life_days = context.recency_half_life_days
        
        # Find most recent commit
        most_recent = max(commits, key=lambda c: c.timestamp)
        days_since = (now - most_recent.timestamp).days
        
        # Apply exponential decay
        # score = 0.5 ^ (days_since / half_life)
        # After half_life days, score is 0.5
        # After 2*half_life days, score is 0.25
        decay_rate = math.log(2) / half_life_days
        score = math.exp(-decay_rate * days_since)
        
        return min(1.0, max(0.0, score))


class CodeReviewParticipationFactor(ScoringFactor):
    """
    Measures participation in code reviews.
    
    Weight: 0.05
    
    Rationale: Reviewing code shows understanding even without
    direct commits. However, this data may not always be available.
    """
    
    @property
    def name(self) -> str:
        return "code_review_participation"
    
    @property
    def weight(self) -> float:
        return 0.05
    
    @property
    def description(self) -> str:
        return "Participation in code reviews for this file"
    
    def calculate(self, commits: List[CommitAnalysis], context: ScoringContext) -> float:
        # This factor relies on code review data which may not be available
        # from git alone. For now, we use a placeholder that gives partial
        # credit based on the number of commits (proxy for involvement)
        
        if not commits:
            return 0.0
        
        # Check if any commits have reviewer information
        reviewed_commits = [c for c in commits if c.reviewers]
        
        if reviewed_commits:
            # If we have review data, use it
            total_reviews = sum(len(c.reviewers) for c in commits)
            return min(1.0, total_reviews / 10)  # Normalize to ~10 reviews = 1.0
        
        # Fallback: use commit count as a weak proxy
        # (developers who commit more are likely more involved in reviews)
        if context.total_commits_for_file > 0:
            involvement_ratio = len(commits) / context.total_commits_for_file
            return involvement_ratio * 0.5  # Reduced weight for proxy metric
        
        return 0.0


def get_default_factors() -> List[ScoringFactor]:
    """
    Get the default set of scoring factors.
    
    Returns:
        List of all 7 scoring factors with default weights
    """
    return [
        CommitFrequencyFactor(),
        LinesChangedFactor(),
        RefactorDepthFactor(),
        ArchitecturalChangesFactor(),
        BugFixesFactor(),
        RecencyFactor(),
        CodeReviewParticipationFactor()
    ]


def validate_weights(factors: List[ScoringFactor]) -> bool:
    """
    Validate that factor weights sum to 1.0.
    
    Args:
        factors: List of scoring factors
        
    Returns:
        True if weights are valid
    """
    total = sum(f.weight for f in factors)
    return abs(total - 1.0) < 0.001
