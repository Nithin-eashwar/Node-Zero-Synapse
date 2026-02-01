"""
Providers package for Smart Blame git integration.

This package contains abstract and concrete git provider implementations.
"""

from .base import GitProvider
from .local_git import LocalGitProvider

__all__ = ['GitProvider', 'LocalGitProvider']
