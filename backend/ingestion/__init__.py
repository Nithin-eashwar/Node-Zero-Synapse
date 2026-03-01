"""
Ingestion module - AWS Lambda handlers for code processing.

This module provides Lambda-compatible handlers for:
- Repository parsing triggered by S3 events
- Manual ingestion via direct invocation
"""

from .lambda_handler import handler, local_test

__all__ = ["handler", "local_test"]
