"""
Smart Blame module for developer expertise identification.

This module provides functionality to identify true code experts
beyond simple git blame, using weighted scoring factors based on:
- Commit frequency
- Lines changed
- Refactoring depth
- Architectural contributions
- Bug fixes
- Recency
- Code review participation

Usage:
    from core.blame import create_analyzer, SmartBlameAnalyzer
    
    # Create analyzer for a repository
    analyzer = await create_analyzer("/path/to/repo")
    
    # Get expert for a file
    expert = await analyzer.identify_expert("src/main.py")
    print(expert.recommendation_text)  # "Ask Sarah, she architected this"
    
    # Generate expertise heatmap
    heatmap = await analyzer.generate_heatmap()
    
    # Get bus factor analysis
    bus_factors = await analyzer.get_bus_factor_analysis()
"""

# Models
from .models import (
    CommitType,
    DeveloperProfile,
    CommitAnalysis,
    ExpertiseScore,
    ExpertRecommendation,
    ModuleExpertise,
    ExpertiseHeatmap,
    ScoringContext,
    SmartBlameConfig
)

# Providers
from .providers import GitProvider, LocalGitProvider

# Scoring
from .scoring import (
    ScoringFactor,
    CommitFrequencyFactor,
    LinesChangedFactor,
    RefactorDepthFactor,
    ArchitecturalChangesFactor,
    BugFixesFactor,
    RecencyFactor,
    CodeReviewParticipationFactor,
    get_default_factors,
    ExpertiseScoreCalculator
)

# Stores
from .stores import ExpertStore, InMemoryStore

# Main analyzer
from .analyzer import SmartBlameAnalyzer, create_analyzer

__all__ = [
    # Models
    'CommitType',
    'DeveloperProfile',
    'CommitAnalysis',
    'ExpertiseScore',
    'ExpertRecommendation',
    'ModuleExpertise',
    'ExpertiseHeatmap',
    'ScoringContext',
    'SmartBlameConfig',
    
    # Providers
    'GitProvider',
    'LocalGitProvider',
    
    # Scoring
    'ScoringFactor',
    'CommitFrequencyFactor',
    'LinesChangedFactor',
    'RefactorDepthFactor',
    'ArchitecturalChangesFactor',
    'BugFixesFactor',
    'RecencyFactor',
    'CodeReviewParticipationFactor',
    'get_default_factors',
    'ExpertiseScoreCalculator',
    
    # Stores
    'ExpertStore',
    'InMemoryStore',
    
    # Analyzer
    'SmartBlameAnalyzer',
    'create_analyzer'
]
