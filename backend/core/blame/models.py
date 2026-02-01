"""
Data models for Smart Blame feature.

This module defines comprehensive dataclasses for developer expertise
analysis, commit classification, and expertise scoring.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum


class CommitType(Enum):
    """Classification of commit types for expertise analysis."""
    FEATURE = "feature"
    BUG_FIX = "bug_fix"
    REFACTOR = "refactor"
    ARCHITECTURAL = "architectural"
    DOCUMENTATION = "documentation"
    TEST = "test"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


@dataclass
class DeveloperProfile:
    """
    Represents a developer with their identity and expertise metrics.
    
    Designed to be compatible with future AWS Neptune graph storage.
    """
    name: str
    email: str
    expertise_areas: List[str] = field(default_factory=list)
    overall_expertise_score: float = 0.0
    total_commits: int = 0
    first_commit_date: Optional[datetime] = None
    last_commit_date: Optional[datetime] = None
    
    @property
    def unique_id(self) -> str:
        """Generate unique identifier for graph storage."""
        return f"developer:{self.email}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "email": self.email,
            "expertise_areas": self.expertise_areas,
            "overall_expertise_score": self.overall_expertise_score,
            "total_commits": self.total_commits,
            "first_commit_date": self.first_commit_date.isoformat() if self.first_commit_date else None,
            "last_commit_date": self.last_commit_date.isoformat() if self.last_commit_date else None
        }


@dataclass
class CommitAnalysis:
    """
    Analysis of a single commit for expertise scoring.
    
    Captures metadata needed for all 7 scoring factors.
    """
    commit_hash: str
    author_name: str
    author_email: str
    timestamp: datetime
    message: str
    files_changed: List[str] = field(default_factory=list)
    lines_added: int = 0
    lines_deleted: int = 0
    
    # Classified commit type
    commit_type: CommitType = CommitType.UNKNOWN
    
    # Flags for scoring factors
    is_refactor: bool = False
    is_architectural: bool = False
    is_bug_fix: bool = False
    is_test: bool = False
    
    # Complexity metrics (if available)
    complexity_delta: float = 0.0
    
    # Code review participation (for future integration)
    reviewers: List[str] = field(default_factory=list)
    
    @property
    def total_lines_changed(self) -> int:
        return self.lines_added + self.lines_deleted
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "commit_hash": self.commit_hash,
            "author_name": self.author_name,
            "author_email": self.author_email,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "files_changed": self.files_changed,
            "lines_added": self.lines_added,
            "lines_deleted": self.lines_deleted,
            "commit_type": self.commit_type.value,
            "is_refactor": self.is_refactor,
            "is_architectural": self.is_architectural,
            "is_bug_fix": self.is_bug_fix,
            "total_lines_changed": self.total_lines_changed
        }


@dataclass
class ExpertiseScore:
    """
    Detailed expertise score breakdown for a developer on a file/module.
    
    Contains individual factor scores and human-readable reasoning.
    """
    developer: DeveloperProfile
    target_path: str  # File or module path
    total_score: float  # 0.0 - 1.0
    factors: Dict[str, float]  # Individual factor scores
    confidence: float  # 0.0 - 1.0, based on data quality
    reasoning: str  # Human-readable explanation
    
    # Metadata
    commit_count: int = 0
    last_activity: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "developer": self.developer.to_dict(),
            "target_path": self.target_path,
            "total_score": round(self.total_score, 4),
            "factors": {k: round(v, 4) for k, v in self.factors.items()},
            "confidence": round(self.confidence, 4),
            "reasoning": self.reasoning,
            "commit_count": self.commit_count,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None
        }


@dataclass
class ExpertRecommendation:
    """
    The final expert recommendation for a code entity.
    
    Includes primary expert, alternatives, and bus factor analysis.
    """
    target: str  # File path or function name
    primary_expert: Optional[DeveloperProfile]
    score: Optional[ExpertiseScore]
    secondary_experts: List[Tuple[DeveloperProfile, ExpertiseScore]] = field(default_factory=list)
    recommendation_text: str = ""  # "Ask Sarah, she architected this"
    bus_factor: int = 0  # Number of critical experts
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "primary_expert": self.primary_expert.to_dict() if self.primary_expert else None,
            "score": self.score.to_dict() if self.score else None,
            "secondary_experts": [
                {"developer": dev.to_dict(), "score": score.to_dict()}
                for dev, score in self.secondary_experts
            ],
            "recommendation_text": self.recommendation_text,
            "bus_factor": self.bus_factor
        }


@dataclass
class ModuleExpertise:
    """Expertise data for a single module/directory."""
    module_path: str
    experts: List[ExpertiseScore] = field(default_factory=list)
    bus_factor: int = 0
    top_expert_score: float = 0.0
    has_knowledge_gap: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_path": self.module_path,
            "experts": [e.to_dict() for e in self.experts[:5]],  # Top 5
            "bus_factor": self.bus_factor,
            "top_expert_score": round(self.top_expert_score, 4),
            "has_knowledge_gap": self.has_knowledge_gap
        }


@dataclass
class ExpertiseHeatmap:
    """
    Expertise distribution across the codebase.
    
    Used for visualization and risk analysis.
    """
    modules: Dict[str, ModuleExpertise] = field(default_factory=dict)
    risk_areas: List[str] = field(default_factory=list)  # Modules with bus_factor <= 1
    knowledge_gaps: List[str] = field(default_factory=list)  # Modules with no clear expert
    total_files_analyzed: int = 0
    total_developers: int = 0
    average_bus_factor: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "modules": {k: v.to_dict() for k, v in self.modules.items()},
            "risk_areas": self.risk_areas,
            "knowledge_gaps": self.knowledge_gaps,
            "total_files_analyzed": self.total_files_analyzed,
            "total_developers": self.total_developers,
            "average_bus_factor": round(self.average_bus_factor, 2)
        }


@dataclass
class ScoringContext:
    """
    Context information passed to scoring factors.
    
    Provides normalization data and configuration.
    """
    target_path: str
    all_commits: List[CommitAnalysis]
    developer_commits: List[CommitAnalysis]
    total_commits_for_file: int
    total_lines_in_file: int = 0
    file_age_days: int = 0
    
    # Configuration
    recency_half_life_days: int = 180
    min_commits_for_expertise: int = 3


@dataclass 
class SmartBlameConfig:
    """
    Configuration for Smart Blame feature.
    
    All weights and thresholds are configurable for tuning.
    """
    # Scoring weights (must sum to 1.0)
    weights: Dict[str, float] = field(default_factory=lambda: {
        'commit_frequency': 0.15,
        'lines_changed': 0.10,
        'refactor_depth': 0.25,
        'architectural_changes': 0.20,
        'bug_fixes': 0.15,
        'recency': 0.10,
        'code_review_participation': 0.05
    })
    
    # Recency decay configuration
    recency_half_life_days: int = 180
    
    # Thresholds
    min_commits_for_expertise: int = 3
    expert_confidence_threshold: float = 0.6
    bus_factor_warning_threshold: int = 2
    knowledge_gap_threshold: float = 0.3  # Below this score = knowledge gap
    
    # Commit classification keywords
    refactor_keywords: List[str] = field(default_factory=lambda: [
        'refactor', 'restructure', 'cleanup', 'reorganize', 'simplify',
        'extract', 'rename', 'move', 'split', 'merge', 'consolidate'
    ])
    
    bug_fix_keywords: List[str] = field(default_factory=lambda: [
        'fix', 'bug', 'patch', 'hotfix', 'issue', 'resolve', 'repair',
        'correct', 'handle', 'error', 'crash', 'failure'
    ])
    
    architectural_keywords: List[str] = field(default_factory=lambda: [
        'architect', 'design', 'structure', 'module', 'interface', 'api',
        'layer', 'service', 'component', 'framework', 'pattern', 'abstraction'
    ])
    
    test_keywords: List[str] = field(default_factory=lambda: [
        'test', 'spec', 'unittest', 'pytest', 'coverage', 'mock', 'stub'
    ])
    
    documentation_keywords: List[str] = field(default_factory=lambda: [
        'doc', 'readme', 'comment', 'docstring', 'documentation', 'explain'
    ])
    
    def validate(self) -> bool:
        """Validate that weights sum to 1.0."""
        total = sum(self.weights.values())
        return abs(total - 1.0) < 0.001
