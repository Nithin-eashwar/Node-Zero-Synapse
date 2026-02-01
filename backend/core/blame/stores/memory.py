"""
In-memory expert store implementation.

This module provides an in-memory implementation of the ExpertStore
interface for local development and testing.
"""

from typing import List, Optional, Dict
from collections import defaultdict
import os

from .base import ExpertStore
from ..models import (
    ExpertiseScore, 
    ExpertiseHeatmap, 
    ModuleExpertise,
    DeveloperProfile,
    SmartBlameConfig
)


class InMemoryStore(ExpertStore):
    """
    In-memory implementation of ExpertStore.
    
    Suitable for:
    - Local development
    - Testing
    - Small codebases
    
    For production with large codebases, use NeptuneStore (AWS Neptune).
    """
    
    def __init__(self, config: Optional[SmartBlameConfig] = None):
        """
        Initialize the in-memory store.
        
        Args:
            config: Optional configuration for thresholds
        """
        self.config = config or SmartBlameConfig()
        
        # Storage indexed by file path
        self._by_file: Dict[str, List[ExpertiseScore]] = defaultdict(list)
        
        # Storage indexed by developer email
        self._by_developer: Dict[str, List[ExpertiseScore]] = defaultdict(list)
        
        # Developer profiles
        self._developers: Dict[str, DeveloperProfile] = {}
    
    async def store_expertise(self, score: ExpertiseScore) -> None:
        """Store an expertise score."""
        file_path = score.target_path
        email = score.developer.email
        
        # Remove existing score for this file/developer combo
        self._by_file[file_path] = [
            s for s in self._by_file[file_path]
            if s.developer.email != email
        ]
        self._by_developer[email] = [
            s for s in self._by_developer[email]
            if s.target_path != file_path
        ]
        
        # Add new score
        self._by_file[file_path].append(score)
        self._by_developer[email].append(score)
        
        # Sort by score
        self._by_file[file_path].sort(key=lambda s: s.total_score, reverse=True)
        
        # Store developer profile
        if email not in self._developers:
            self._developers[email] = score.developer
    
    async def store_expertise_batch(self, scores: List[ExpertiseScore]) -> None:
        """Store multiple expertise scores in a batch."""
        for score in scores:
            await self.store_expertise(score)
    
    async def get_experts_for_file(
        self, 
        file_path: str, 
        limit: int = 5
    ) -> List[ExpertiseScore]:
        """Get top experts for a file."""
        scores = self._by_file.get(file_path, [])
        return scores[:limit]
    
    async def get_experts_for_module(
        self,
        module_path: str,
        limit: int = 10
    ) -> List[ExpertiseScore]:
        """Get top experts for a module/directory."""
        # Aggregate scores across all files in the module
        developer_scores: Dict[str, float] = defaultdict(float)
        developer_profiles: Dict[str, DeveloperProfile] = {}
        developer_commit_counts: Dict[str, int] = defaultdict(int)
        
        for file_path, scores in self._by_file.items():
            # Check if file is in the module
            if file_path.startswith(module_path) or module_path in file_path:
                for score in scores:
                    email = score.developer.email
                    developer_scores[email] += score.total_score
                    developer_profiles[email] = score.developer
                    developer_commit_counts[email] += score.commit_count
        
        # Create aggregated scores
        aggregated = []
        for email, total_score in developer_scores.items():
            file_count = len([
                fp for fp, scores in self._by_file.items()
                if fp.startswith(module_path) or module_path in fp
                for s in scores
                if s.developer.email == email
            ])
            
            # Normalize by number of files
            avg_score = total_score / max(file_count, 1)
            
            aggregated.append(ExpertiseScore(
                developer=developer_profiles[email],
                target_path=module_path,
                total_score=avg_score,
                factors={},
                confidence=0.8,  # Aggregated data has lower confidence
                reasoning=f"Aggregated expertise across {file_count} files in {module_path}",
                commit_count=developer_commit_counts[email]
            ))
        
        # Sort by score
        aggregated.sort(key=lambda s: s.total_score, reverse=True)
        
        return aggregated[:limit]
    
    async def get_developer_expertise(
        self,
        developer_email: str
    ) -> List[ExpertiseScore]:
        """Get all expertise scores for a specific developer."""
        return self._by_developer.get(developer_email, [])
    
    async def get_expertise_heatmap(
        self, 
        root_path: Optional[str] = None
    ) -> ExpertiseHeatmap:
        """Generate expertise heatmap for the codebase."""
        modules: Dict[str, ModuleExpertise] = {}
        risk_areas: List[str] = []
        knowledge_gaps: List[str] = []
        
        # Group files by directory
        dir_files: Dict[str, List[str]] = defaultdict(list)
        
        for file_path in self._by_file.keys():
            if root_path and not file_path.startswith(root_path):
                continue
            
            dir_path = os.path.dirname(file_path)
            dir_files[dir_path].append(file_path)
        
        # Analyze each directory
        for dir_path, files in dir_files.items():
            dir_experts: List[ExpertiseScore] = []
            
            for file_path in files:
                scores = self._by_file.get(file_path, [])
                dir_experts.extend(scores)
            
            if not dir_experts:
                continue
            
            # Calculate bus factor for this directory
            bus_factor = await self.get_bus_factor(dir_path)
            
            # Get top experts
            expert_scores = sorted(dir_experts, key=lambda s: s.total_score, reverse=True)
            top_score = expert_scores[0].total_score if expert_scores else 0.0
            
            # Check for knowledge gap
            has_gap = top_score < self.config.knowledge_gap_threshold
            
            modules[dir_path] = ModuleExpertise(
                module_path=dir_path,
                experts=expert_scores[:5],
                bus_factor=bus_factor,
                top_expert_score=top_score,
                has_knowledge_gap=has_gap
            )
            
            # Track risk areas and gaps
            if bus_factor <= self.config.bus_factor_warning_threshold:
                risk_areas.append(dir_path)
            
            if has_gap:
                knowledge_gaps.append(dir_path)
        
        # Calculate averages
        total_files = len(self._by_file)
        total_developers = len(self._developers)
        avg_bus_factor = (
            sum(m.bus_factor for m in modules.values()) / len(modules)
            if modules else 0.0
        )
        
        return ExpertiseHeatmap(
            modules=modules,
            risk_areas=risk_areas,
            knowledge_gaps=knowledge_gaps,
            total_files_analyzed=total_files,
            total_developers=total_developers,
            average_bus_factor=avg_bus_factor
        )
    
    async def get_bus_factor(self, module_path: str) -> int:
        """
        Calculate bus factor for a module.
        
        Bus factor = number of developers with significant expertise
        (score > threshold).
        """
        threshold = self.config.expert_confidence_threshold
        
        # Get all experts for files in this module
        experts_with_significant_score = set()
        
        for file_path, scores in self._by_file.items():
            if file_path.startswith(module_path) or module_path in file_path:
                for score in scores:
                    if score.total_score > threshold:
                        experts_with_significant_score.add(score.developer.email)
        
        return len(experts_with_significant_score)
    
    async def get_knowledge_gaps(
        self,
        threshold: float = 0.3
    ) -> List[str]:
        """Identify files with insufficient expertise coverage."""
        gaps = []
        
        for file_path, scores in self._by_file.items():
            if not scores:
                gaps.append(file_path)
                continue
            
            top_score = max(s.total_score for s in scores)
            if top_score < threshold:
                gaps.append(file_path)
        
        return gaps
    
    async def get_all_developers(self) -> List[DeveloperProfile]:
        """Get all developers with expertise data."""
        return list(self._developers.values())
    
    async def clear(self) -> None:
        """Clear all stored expertise data."""
        self._by_file.clear()
        self._by_developer.clear()
        self._developers.clear()
    
    async def get_statistics(self) -> Dict:
        """Get store statistics."""
        total_scores = sum(len(scores) for scores in self._by_file.values())
        
        return {
            "total_files": len(self._by_file),
            "total_developers": len(self._developers),
            "total_expertise_scores": total_scores,
            "average_experts_per_file": (
                total_scores / len(self._by_file) if self._by_file else 0
            )
        }
