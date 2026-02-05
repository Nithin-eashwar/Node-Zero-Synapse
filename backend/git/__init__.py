"""
Git module - Git analysis and expertise scoring.

This module handles git blame analysis, expertise scoring,
and code ownership tracking.
"""

from .blame import (
    # Main analyzer
    SmartBlameAnalyzer,
    create_analyzer,
    
    # Models
    CommitType,
    DeveloperProfile,
    CommitAnalysis,
    ExpertiseScore,
    ExpertRecommendation,
    ModuleExpertise,
    ExpertiseHeatmap,
    ScoringContext,
    SmartBlameConfig,
    
    # Providers
    GitProvider,
    LocalGitProvider,
    
    # Scoring
    ScoringFactor,
    ExpertiseScoreCalculator,
    
    # Stores
    ExpertStore,
    InMemoryStore,
)

from .smart_git import (
    get_git_blame,
    get_expertise_heatmap,
    get_bus_factor_analysis,
    get_knowledge_gaps,
    get_developer_expertise,
    get_analyzer,
    reset_analyzer,
)

__all__ = [
    # Analyzer
    "SmartBlameAnalyzer",
    "create_analyzer",
    # Models
    "CommitType",
    "DeveloperProfile", 
    "CommitAnalysis",
    "ExpertiseScore",
    "ExpertRecommendation",
    "ModuleExpertise",
    "ExpertiseHeatmap",
    "ScoringContext",
    "SmartBlameConfig",
    # Providers
    "GitProvider",
    "LocalGitProvider",
    # Scoring
    "ScoringFactor",
    "ExpertiseScoreCalculator",
    # Stores
    "ExpertStore",
    "InMemoryStore",
    # Smart Git functions
    "get_git_blame",
    "get_expertise_heatmap",
    "get_bus_factor_analysis",
    "get_knowledge_gaps",
    "get_developer_expertise",
    "get_analyzer",
    "reset_analyzer",
]
