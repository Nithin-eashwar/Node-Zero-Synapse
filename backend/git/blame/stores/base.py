"""
Abstract expert store interface for Smart Blame.

This module defines the abstract interface for storing and querying
expertise data, designed for future migration to AWS Neptune.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict

from ..models import ExpertiseScore, ExpertiseHeatmap, DeveloperProfile


class ExpertStore(ABC):
    """
    Abstract interface for storing and querying expertise data.
    
    Designed for future migration to AWS Neptune graph database.
    Implementations include:
    - InMemoryStore (for local development/testing)
    - NeptuneStore (future AWS Neptune integration)
    """
    
    @abstractmethod
    async def store_expertise(self, score: ExpertiseScore) -> None:
        """
        Store an expertise score.
        
        Args:
            score: The expertise score to store
        """
        pass
    
    @abstractmethod
    async def store_expertise_batch(self, scores: List[ExpertiseScore]) -> None:
        """
        Store multiple expertise scores in a batch.
        
        Args:
            scores: List of expertise scores to store
        """
        pass
    
    @abstractmethod
    async def get_experts_for_file(
        self, 
        file_path: str, 
        limit: int = 5
    ) -> List[ExpertiseScore]:
        """
        Get top experts for a file, ordered by score.
        
        Args:
            file_path: Path to the file
            limit: Maximum number of experts to return
            
        Returns:
            List of ExpertiseScore objects, sorted by total_score descending
        """
        pass
    
    @abstractmethod
    async def get_experts_for_module(
        self,
        module_path: str,
        limit: int = 10
    ) -> List[ExpertiseScore]:
        """
        Get top experts for a module/directory.
        
        Aggregates expertise across all files in the module.
        
        Args:
            module_path: Path to the module/directory
            limit: Maximum number of experts to return
            
        Returns:
            List of ExpertiseScore objects
        """
        pass
    
    @abstractmethod
    async def get_developer_expertise(
        self,
        developer_email: str
    ) -> List[ExpertiseScore]:
        """
        Get all expertise scores for a specific developer.
        
        Args:
            developer_email: The developer's email
            
        Returns:
            List of ExpertiseScore objects for files they've contributed to
        """
        pass
    
    @abstractmethod
    async def get_expertise_heatmap(
        self, 
        root_path: Optional[str] = None
    ) -> ExpertiseHeatmap:
        """
        Generate expertise heatmap for the codebase or a specific module.
        
        Args:
            root_path: Optional root path to filter by
            
        Returns:
            ExpertiseHeatmap with expertise distribution
        """
        pass
    
    @abstractmethod
    async def get_bus_factor(self, module_path: str) -> int:
        """
        Calculate bus factor for a module.
        
        Bus factor = number of developers who would need to leave
        before the module becomes orphaned.
        
        Args:
            module_path: Path to the module
            
        Returns:
            Bus factor (integer)
        """
        pass
    
    @abstractmethod
    async def get_knowledge_gaps(
        self,
        threshold: float = 0.3
    ) -> List[str]:
        """
        Identify modules with insufficient expertise coverage.
        
        Args:
            threshold: Score below which a module is considered a gap
            
        Returns:
            List of file paths with knowledge gaps
        """
        pass
    
    @abstractmethod
    async def get_all_developers(self) -> List[DeveloperProfile]:
        """
        Get all developers with expertise data.
        
        Returns:
            List of DeveloperProfile objects
        """
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all stored expertise data."""
        pass
    
    @abstractmethod
    async def get_statistics(self) -> Dict:
        """
        Get store statistics.
        
        Returns:
            Dict with statistics (total files, developers, etc.)
        """
        pass
