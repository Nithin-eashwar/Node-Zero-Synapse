"""
Stores package for Smart Blame expertise data storage.

This package contains abstract and concrete store implementations
for persisting expertise data.
"""

from .base import ExpertStore
from .memory import InMemoryStore

__all__ = ['ExpertStore', 'InMemoryStore']
