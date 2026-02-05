"""
Scoring package for Smart Blame expertise calculation.

This package contains the scoring factors and calculator
for determining developer expertise.
"""

from .factors import (
    ScoringFactor,
    CommitFrequencyFactor,
    LinesChangedFactor,
    RefactorDepthFactor,
    ArchitecturalChangesFactor,
    BugFixesFactor,
    RecencyFactor,
    CodeReviewParticipationFactor,
    get_default_factors,
    validate_weights
)
from .calculator import ExpertiseScoreCalculator

__all__ = [
    'ScoringFactor',
    'CommitFrequencyFactor',
    'LinesChangedFactor',
    'RefactorDepthFactor',
    'ArchitecturalChangesFactor',
    'BugFixesFactor',
    'RecencyFactor',
    'CodeReviewParticipationFactor',
    'get_default_factors',
    'validate_weights',
    'ExpertiseScoreCalculator'
]
