"""
Abstract Git provider interface for Smart Blame.

This module defines the abstract interface for git operations,
enabling future migration to AWS CodeCommit or other git providers.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Iterator

from ..models import CommitAnalysis, DeveloperProfile


class GitProvider(ABC):
    """
    Abstract interface for git operations.
    
    Designed to allow swapping between:
    - LocalGitProvider (GitPython for local repos)
    - AWSCodeCommitProvider (boto3 for AWS CodeCommit)
    - GitHubProvider (GitHub API)
    - GitLabProvider (GitLab API)
    """
    
    @abstractmethod
    def get_commits_for_file(
        self, 
        file_path: str, 
        author: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> List[CommitAnalysis]:
        """
        Get all commits that touched a specific file.
        
        Args:
            file_path: Path to the file (relative to repo root)
            author: Optional filter by author email
            since: Optional start date filter
            until: Optional end date filter
            
        Returns:
            List of CommitAnalysis objects
        """
        pass
    
    @abstractmethod
    def get_blame_for_file(self, file_path: str) -> Dict[int, DeveloperProfile]:
        """
        Get line-by-line blame information.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dict mapping line numbers to developer profiles
        """
        pass
    
    @abstractmethod
    def get_all_contributors(self, file_path: Optional[str] = None) -> List[DeveloperProfile]:
        """
        Get all contributors to the repository or a specific file.
        
        Args:
            file_path: Optional file to filter contributors
            
        Returns:
            List of DeveloperProfile objects
        """
        pass
    
    @abstractmethod
    def get_file_history(
        self, 
        file_path: str,
        max_commits: Optional[int] = None
    ) -> Iterator[CommitAnalysis]:
        """
        Stream file history for large repositories.
        
        Args:
            file_path: Path to the file
            max_commits: Optional limit on number of commits
            
        Yields:
            CommitAnalysis objects
        """
        pass
    
    @abstractmethod
    def get_all_files(self) -> List[str]:
        """
        Get all tracked files in the repository.
        
        Returns:
            List of file paths
        """
        pass
    
    @abstractmethod
    def get_file_content(self, file_path: str, commit_hash: Optional[str] = None) -> Optional[str]:
        """
        Get file content at a specific commit or HEAD.
        
        Args:
            file_path: Path to the file
            commit_hash: Optional commit hash (defaults to HEAD)
            
        Returns:
            File content as string, or None if not found
        """
        pass
    
    @abstractmethod
    def get_commit_diff(self, commit_hash: str) -> Dict[str, Dict[str, int]]:
        """
        Get diff statistics for a commit.
        
        Args:
            commit_hash: The commit hash
            
        Returns:
            Dict mapping file paths to {additions, deletions}
        """
        pass
    
    @property
    @abstractmethod
    def repo_path(self) -> str:
        """Get the repository path."""
        pass
    
    @property
    @abstractmethod
    def is_valid(self) -> bool:
        """Check if the provider is properly initialized."""
        pass
