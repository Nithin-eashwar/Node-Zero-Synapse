"""
Git-backed risk factor analyzer.

Provides real change frequency and bus factor metrics by querying
git history. Used by CodeGraph._calculate_enhanced_risk_factors()
to replace placeholder values with actual data.

This is a lightweight, synchronous analyzer (unlike SmartBlameAnalyzer
which is async and designed for the API). It caches results per-repo
to avoid repeated git operations.
"""

import os
from collections import defaultdict
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class FileRiskMetrics:
    """Git-derived risk metrics for a single file."""
    change_count: int = 0          # Total commits touching this file
    unique_authors: int = 0        # Number of distinct contributors
    author_names: list = field(default_factory=list)  # List of author names
    days_since_last_change: int = 0  # Recency
    recent_change_ratio: float = 0.0  # Fraction of changes in last 90 days


class GitRiskAnalyzer:
    """
    Analyzes git history to produce real risk metrics.
    
    Caches all results after first scan so CodeGraph can query
    per-entity without repeated git operations.
    """

    def __init__(self, repo_path: str):
        self._repo_path = repo_path
        self._file_metrics: Dict[str, FileRiskMetrics] = {}
        self._max_change_count = 1  # For normalization
        self._analyzed = False

    def analyze(self) -> None:
        """
        Scan git history and build file-level risk metrics.
        
        This runs once and caches all results. Subsequent calls
        to get_change_frequency_risk / get_bus_factor_risk are instant.
        """
        if self._analyzed:
            return

        try:
            import git
        except ImportError:
            print("[GitRisk] gitpython not installed, using defaults")
            self._analyzed = True
            return

        try:
            repo = git.Repo(self._repo_path, search_parent_directories=True)
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            print(f"[GitRisk] No git repo found at {self._repo_path}, using defaults")
            self._analyzed = True
            return

        print(f"[GitRisk] Analyzing git history at: {self._repo_path}")

        # Collect per-file stats from git log
        file_commits: Dict[str, list] = defaultdict(list)  # file -> [commit_info]
        file_authors: Dict[str, set] = defaultdict(set)     # file -> {author_emails}
        file_author_names: Dict[str, set] = defaultdict(set)

        try:
            # Walk last 500 commits for performance
            for commit in repo.iter_commits(max_count=500):
                author_email = commit.author.email if commit.author else "unknown"
                author_name = commit.author.name if commit.author else "unknown"
                committed_date = commit.committed_datetime

                # Get files changed in this commit
                try:
                    if commit.parents:
                        diffs = commit.parents[0].diff(commit)
                    else:
                        # Initial commit
                        diffs = commit.diff(git.NULL_TREE)

                    for diff in diffs:
                        # Get the file path (handle renames)
                        file_path = diff.b_path or diff.a_path
                        if file_path and file_path.endswith(".py"):
                            file_commits[file_path].append({
                                "date": committed_date,
                                "author": author_email,
                            })
                            file_authors[file_path].add(author_email)
                            file_author_names[file_path].add(author_name)
                except Exception:
                    continue  # Skip problematic commits

        except Exception as e:
            print(f"[GitRisk] Error reading git history: {e}")
            self._analyzed = True
            return

        # Build FileRiskMetrics for each file
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        ninety_days_ago = now - timedelta(days=90)

        for file_path, commits in file_commits.items():
            total = len(commits)
            authors = file_authors[file_path]
            
            # Count recent changes (last 90 days)
            recent = sum(
                1 for c in commits
                if c["date"].replace(tzinfo=timezone.utc) > ninety_days_ago
            ) if commits else 0

            # Days since last change
            if commits:
                dates = [c["date"] for c in commits]
                latest = max(dates)
                if latest.tzinfo is None:
                    latest = latest.replace(tzinfo=timezone.utc)
                days_since = (now - latest).days
            else:
                days_since = 365

            self._file_metrics[file_path] = FileRiskMetrics(
                change_count=total,
                unique_authors=len(authors),
                author_names=list(file_author_names[file_path]),
                days_since_last_change=days_since,
                recent_change_ratio=recent / max(total, 1),
            )

        # Track max for normalization
        if self._file_metrics:
            self._max_change_count = max(
                m.change_count for m in self._file_metrics.values()
            )

        self._analyzed = True
        print(f"[GitRisk] Analyzed {len(self._file_metrics)} files from git history")

    def get_change_frequency_risk(self, file_path: str) -> float:
        """
        Get change frequency risk for a file (0.0 = stable, 1.0 = volatile).
        
        Based on:
        - Total commit count relative to max in repo
        - Recency of changes (recent = higher risk)
        """
        self.analyze()

        # Normalize file path for matching
        metrics = self._find_metrics(file_path)
        if not metrics:
            return 0.3  # Default: mildly risky when unknown

        # Normalize change count against most-changed file
        frequency_score = min(metrics.change_count / max(self._max_change_count, 1), 1.0)

        # Weight recent changes more heavily
        recency_score = metrics.recent_change_ratio

        # Combine: 60% frequency, 40% recency
        return min(frequency_score * 0.6 + recency_score * 0.4, 1.0)

    def get_bus_factor_risk(self, file_path: str) -> float:
        """
        Get bus factor risk for a file (0.0 = well-distributed, 1.0 = single-author).
        
        Based on number of unique contributors:
        - 1 author  → 1.0 (critical risk)
        - 2 authors → 0.7
        - 3 authors → 0.4
        - 4+ authors → 0.1 (well-distributed)
        """
        self.analyze()

        metrics = self._find_metrics(file_path)
        if not metrics:
            return 0.5  # Default: medium risk when unknown

        authors = metrics.unique_authors
        if authors <= 1:
            return 1.0
        elif authors == 2:
            return 0.7
        elif authors == 3:
            return 0.4
        elif authors == 4:
            return 0.2
        else:
            return 0.1

    def get_file_summary(self, file_path: str) -> Optional[Dict]:
        """Get a human-readable summary of git risk for a file."""
        self.analyze()
        metrics = self._find_metrics(file_path)
        if not metrics:
            return None

        return {
            "total_commits": metrics.change_count,
            "unique_authors": metrics.unique_authors,
            "authors": metrics.author_names,
            "days_since_last_change": metrics.days_since_last_change,
            "recent_change_ratio": round(metrics.recent_change_ratio, 2),
            "change_frequency_risk": round(self.get_change_frequency_risk(file_path), 2),
            "bus_factor_risk": round(self.get_bus_factor_risk(file_path), 2),
        }

    def _find_metrics(self, file_path: str) -> Optional[FileRiskMetrics]:
        """Find metrics for a file, handling path normalization."""
        # Direct match
        normalized = file_path.replace("\\", "/")
        if normalized in self._file_metrics:
            return self._file_metrics[normalized]

        # Try basename match (entity metadata often has relative paths)
        for key, metrics in self._file_metrics.items():
            if key.endswith(normalized) or normalized.endswith(key):
                return metrics

        # Try just filename
        basename = os.path.basename(normalized)
        for key, metrics in self._file_metrics.items():
            if os.path.basename(key) == basename:
                return metrics

        return None


# ─────────────────────────────────────────────
# Module-level cache
# ─────────────────────────────────────────────

_cached_analyzers: Dict[str, GitRiskAnalyzer] = {}


def get_git_risk_analyzer(repo_path: str) -> GitRiskAnalyzer:
    """
    Get or create a cached GitRiskAnalyzer for a repo.
    
    Results are cached so the first call scans git history,
    and all subsequent calls are instant lookups.
    """
    abs_path = os.path.abspath(repo_path)
    if abs_path not in _cached_analyzers:
        analyzer = GitRiskAnalyzer(abs_path)
        analyzer.analyze()
        _cached_analyzers[abs_path] = analyzer
    return _cached_analyzers[abs_path]
