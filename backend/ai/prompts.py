"""
Feature-Specific Prompt Templates for Synapse RAG Pipeline.

Instead of one generic prompt, routes queries to specialized prompts
that produce higher quality answers by leveraging feature-specific data
(blast radius metrics, governance violations, expertise scores, etc).
"""

from langchain_core.prompts import ChatPromptTemplate
from enum import Enum
from typing import Optional
import re


class QueryIntent(Enum):
    """Detected intent category for a user query."""
    BLAST_RADIUS = "blast_radius"
    GOVERNANCE = "governance"
    EXPERTISE = "expertise"
    COMPLEXITY = "complexity"
    GENERAL = "general"


# ─────────────────────────────────────────────
# Intent Detection
# ─────────────────────────────────────────────

# Keyword patterns for each intent (case-insensitive matching)
_INTENT_PATTERNS = {
    QueryIntent.BLAST_RADIUS: [
        r"\bblast\s*radius\b", r"\bimpact\b", r"\baffect(?:s|ed)?\b",
        r"\bbreak(?:s|ing)?\b", r"\bdependen(?:cy|cies|t|ts)\b",
        r"\bripple\b", r"\bdownstream\b", r"\bupstream\b",
        r"\brisk(?:y|s)?\b", r"\bchange.*(?:safe|dangerous)\b",
        r"\bwhat.*(?:breaks?|happens)\b",
    ],
    QueryIntent.GOVERNANCE: [
        r"\barchitect(?:ure|ural)\b", r"\bviolat(?:ion|ions|es?|ing)\b",
        r"\blayer(?:s|ing)?\b", r"\bboundar(?:y|ies)\b",
        r"\bdrift\b", r"\brule(?:s)?\b", r"\bgovernance\b",
        r"\bcoupling\b", r"\bcohesion\b", r"\bimport.*(?:cross|violat)\b",
    ],
    QueryIntent.EXPERTISE: [
        r"\bwho\b.*\b(?:knows?|expert|owns?|wrote|author)\b",
        r"\bexpert(?:ise|s)?\b", r"\bblame\b", r"\bowner(?:ship)?\b",
        r"\bbus\s*factor\b", r"\bheatmap\b", r"\bknowledge\s*gap\b",
        r"\bask\s+(?:about|for)\b", r"\bcontribut(?:or|ions?)\b",
        r"\bresponsib(?:le|ility)\b",
    ],
    QueryIntent.COMPLEXITY: [
        r"\bcomplex(?:ity)?\b", r"\bcyclomatic\b", r"\bcognitive\b",
        r"\brefactor\b", r"\bsimplif(?:y|ied|ication)\b",
        r"\blines?\s*of\s*code\b", r"\bloc\b",
        r"\btoo\s*(?:big|long|complex)\b", r"\bcode\s*smell\b",
    ],
}


def detect_intent(query: str) -> QueryIntent:
    """
    Detect the intent of a user query using keyword matching.
    
    Returns the most likely intent based on pattern match count.
    Falls back to GENERAL if no strong signal is found.
    """
    query_lower = query.lower()
    scores = {}
    
    for intent, patterns in _INTENT_PATTERNS.items():
        score = sum(1 for p in patterns if re.search(p, query_lower))
        if score > 0:
            scores[intent] = score
    
    if not scores:
        return QueryIntent.GENERAL
    
    return max(scores, key=scores.get)


# ─────────────────────────────────────────────
# Prompt Templates
# ─────────────────────────────────────────────

SYSTEM_PREAMBLE = """You are Synapse, an AI-powered codebase intelligence assistant built for the "AI for Bharat" initiative.
You analyze code repositories using a Knowledge Graph (relationships between entities) and Vector Search (semantic code understanding).
Always be specific and cite entity names, file paths, and metrics when available."""


BLAST_RADIUS_PROMPT = ChatPromptTemplate.from_template(
    SYSTEM_PREAMBLE + """

Your task is to analyze the IMPACT and BLAST RADIUS of code entities.

=== LIVE FEATURE DATA ===
{feature_data}

=== GRAPH CONTEXT (Dependencies & Impact Data) ===
{graph_context}

=== CODE CONTEXT ===
{code_context}

=== CODEBASE OVERVIEW ===
{graph_summary}

Question: {question}

Provide your analysis covering:
1. **Direct Impact**: Which functions/classes directly depend on the entity in question
2. **Transitive Impact**: The full chain of entities that would be affected by a change
3. **Risk Assessment**: Based on complexity metrics and dependency count, how risky is this change
4. **Recommendations**: Whether changes are safe, and what tests should be run

Use the LIVE FEATURE DATA and graph context metrics to support your answer.

Answer:""")


GOVERNANCE_PROMPT = ChatPromptTemplate.from_template(
    SYSTEM_PREAMBLE + """

Your task is to analyze ARCHITECTURAL patterns, boundary violations, and drift.

=== LIVE FEATURE DATA ===
{feature_data}

=== GRAPH CONTEXT (Structure & Relationships) ===
{graph_context}

=== CODE CONTEXT ===
{code_context}

=== CODEBASE OVERVIEW ===
{graph_summary}

Question: {question}

Provide your analysis covering:
1. **Architecture Overview**: How the codebase is structured into layers/modules
2. **Violations**: Any boundary violations or improper cross-layer imports found in the LIVE DATA
3. **Drift**: Whether the architecture is drifting from intended design
4. **Recommendations**: Specific fixes for violations and how to enforce boundaries

Reference specific files, layer names, and import paths from the live data.

Answer:""")


EXPERTISE_PROMPT = ChatPromptTemplate.from_template(
    SYSTEM_PREAMBLE + """

Your task is to identify CODE EXPERTS and OWNERSHIP patterns.

=== LIVE FEATURE DATA ===
{feature_data}

=== GRAPH CONTEXT (Entity Relationships & File Structure) ===
{graph_context}

=== CODE CONTEXT ===
{code_context}

=== CODEBASE OVERVIEW ===
{graph_summary}

Question: {question}

Provide your analysis covering:
1. **Expert Identification**: Use the live ownership data and code structure to identify experts
2. **Knowledge Distribution**: Whether knowledge is concentrated or spread across the team
3. **Bus Factor Risk**: If key contributors are concentrated, flag the risk
4. **Knowledge Gaps**: Areas where expertise coverage may be insufficient

Cite specific expertise scores and file ownership data from the live feature data.

Answer:""")


COMPLEXITY_PROMPT = ChatPromptTemplate.from_template(
    SYSTEM_PREAMBLE + """

Your task is to analyze CODE COMPLEXITY and suggest improvements.

=== LIVE FEATURE DATA ===
{feature_data}

=== GRAPH CONTEXT (Complexity Metrics & Dependencies) ===
{graph_context}

=== CODE CONTEXT ===
{code_context}

=== CODEBASE OVERVIEW ===
{graph_summary}

Question: {question}

Provide your analysis covering:
1. **Complexity Breakdown**: Use the live metrics — cyclomatic, cognitive, LOC for each entity
2. **Hotspots**: Identify the top complex functions from the codebase hotspots data
3. **Root Causes**: Why complexity is high (deep nesting, many branches, long methods, etc.)
4. **Refactoring Plan**: Specific, actionable steps to reduce complexity
   - Extract method opportunities
   - Simplify conditionals
   - Break down large functions

Use the specific numbers from the LIVE FEATURE DATA to support your recommendations.

Answer:""")


GENERAL_PROMPT = ChatPromptTemplate.from_template(
    SYSTEM_PREAMBLE + """

=== LIVE FEATURE DATA ===
{feature_data}

=== GRAPH CONTEXT (Structural Relationships & Metrics) ===
{graph_context}

=== CODE CONTEXT (Semantic Search Results) ===
{code_context}

=== CODEBASE OVERVIEW ===
{graph_summary}

Question: {question}

Provide a thorough answer using the live feature data, structural graph data, and code context.
When relevant, mention impact/blast radius, complexity, relationships, and risk factors.

Answer:""")


# Map intents to their prompt templates
PROMPT_REGISTRY = {
    QueryIntent.BLAST_RADIUS: BLAST_RADIUS_PROMPT,
    QueryIntent.GOVERNANCE: GOVERNANCE_PROMPT,
    QueryIntent.EXPERTISE: EXPERTISE_PROMPT,
    QueryIntent.COMPLEXITY: COMPLEXITY_PROMPT,
    QueryIntent.GENERAL: GENERAL_PROMPT,
}


def get_prompt_for_query(query: str) -> tuple[ChatPromptTemplate, QueryIntent]:
    """
    Detect query intent and return the appropriate prompt template.
    
    Returns:
        Tuple of (prompt_template, detected_intent)
    """
    intent = detect_intent(query)
    prompt = PROMPT_REGISTRY[intent]
    return prompt, intent
