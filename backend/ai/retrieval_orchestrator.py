"""
Hybrid retrieval and context assembly utilities for GraphRAG.

This module adds:
- Semantic + lexical retrieval fusion (RRF)
- Dynamic top-k selection
- Lightweight reranking
- Metadata-aware filtering
- Entity resolution and graph expansion helpers
- Token-aware context packing
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_./:-]*")
_FILE_HINT_RE = re.compile(r"(?:file|module|path)\s*:\s*([A-Za-z0-9_./\\-]+)", re.IGNORECASE)
_TYPE_HINT_RE = re.compile(r"\b(function|class|method|module)\b", re.IGNORECASE)


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _estimate_tokens(text: str) -> int:
    # Good-enough estimate for budgeting without tokenizer dependencies.
    if not text:
        return 0
    return max(1, int(len(text.split()) * 1.25))


@dataclass
class RetrievalCandidate:
    id: str
    unique_id: str
    name: str
    file: str
    source_type: str
    document: str
    metadata: Dict[str, Any]
    semantic_rank: Optional[int] = None
    lexical_rank: Optional[int] = None
    semantic_score: float = 0.0
    lexical_score: float = 0.0
    fused_score: float = 0.0
    rerank_score: float = 0.0

    def to_evidence(self, rank: int) -> Dict[str, Any]:
        return {
            "id": self.id,
            "unique_id": self.unique_id,
            "name": self.name,
            "file": self.file,
            "snippet": self.document,
            "score": round(self.rerank_score or self.fused_score, 6),
            "source_type": self.source_type,
            "rank": rank,
        }


class LocalLexicalIndex:
    """
    Local lexical sidecar index with BM25-like ranking.
    Uses rank_bm25 when available and falls back to overlap scoring.
    """

    def __init__(self) -> None:
        self._docs: List[Dict[str, Any]] = []
        self._tokenized_docs: List[List[str]] = []
        self._bm25 = None

    def index(self, docs: Sequence[Dict[str, Any]]) -> None:
        self._docs = list(docs)
        self._tokenized_docs = [_tokenize(d.get("document", "")) for d in self._docs]
        self._bm25 = None
        try:
            from rank_bm25 import BM25Okapi  # type: ignore

            self._bm25 = BM25Okapi(self._tokenized_docs)
        except Exception:
            # Optional dependency; fallback path is acceptable.
            self._bm25 = None

    def search(self, query: str, n_results: int = 20) -> List[Tuple[int, float]]:
        if not self._docs:
            return []
        q = _tokenize(query)
        if not q:
            return []

        if self._bm25 is not None:
            scores = self._bm25.get_scores(q)
            ranked = sorted(enumerate(scores), key=lambda x: float(x[1]), reverse=True)
            return [(idx, float(score)) for idx, score in ranked[:n_results] if score > 0]

        # Fallback: normalized token overlap score.
        ranked_scores: List[Tuple[int, float]] = []
        qset = set(q)
        for idx, dtoks in enumerate(self._tokenized_docs):
            if not dtoks:
                continue
            dset = set(dtoks)
            overlap = len(qset.intersection(dset))
            if overlap == 0:
                continue
            score = overlap / max(len(qset), 1)
            ranked_scores.append((idx, float(score)))
        ranked_scores.sort(key=lambda x: x[1], reverse=True)
        return ranked_scores[:n_results]


class RetrievalOrchestrator:
    def __init__(self, vector_store) -> None:
        self.vector_store = vector_store
        self.lexical = LocalLexicalIndex()
        self._documents: List[Dict[str, Any]] = []

    def index_nodes(self, nodes: Sequence[Dict[str, Any]]) -> None:
        docs: List[Dict[str, Any]] = []
        build_document = getattr(self.vector_store, "build_document", None)
        build_unique_id = getattr(self.vector_store, "build_unique_id", None)
        build_metadata = getattr(self.vector_store, "build_metadata", None)
        if not build_document or not build_unique_id or not build_metadata:
            return

        for node in nodes:
            unique_id = build_unique_id(node)
            if not unique_id:
                continue
            meta = build_metadata(node, unique_id)
            docs.append(
                {
                    "id": unique_id,
                    "unique_id": unique_id,
                    "document": build_document(node),
                    "metadata": meta,
                }
            )
        self._documents = docs
        self.lexical.index(docs)

    def dynamic_top_k(self, intent: str, confidence: float) -> int:
        # Default 4. Raise to 6-8 for low confidence or heavier intents.
        base = 4
        if intent in {"architecture", "governance", "blast_radius", "debug"}:
            base = 6
        if confidence < 0.45:
            base = max(base, 8)
        return base

    def parse_query_filters(self, query: str) -> Dict[str, str]:
        filters: Dict[str, str] = {}
        file_match = _FILE_HINT_RE.search(query)
        if file_match:
            filters["file"] = file_match.group(1).replace("\\", "/").lower()
        type_match = _TYPE_HINT_RE.search(query)
        if type_match:
            filters["type"] = type_match.group(1).lower()
        return filters

    def _vector_candidates(self, query_embedding: List[float], n_results: int) -> List[RetrievalCandidate]:
        results = self.vector_store.search(query_embedding, n_results=n_results)
        docs = (results.get("documents") or [[]])[0]
        metas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]
        candidates: List[RetrievalCandidate] = []
        for idx, doc in enumerate(docs):
            meta = metas[idx] if idx < len(metas) and metas[idx] else {}
            distance = float(distances[idx]) if idx < len(distances) else 1.0
            score = max(0.0, 1.0 - distance)
            unique_id = str(meta.get("unique_id") or meta.get("name") or f"semantic:{idx}")
            candidates.append(
                RetrievalCandidate(
                    id=unique_id,
                    unique_id=unique_id,
                    name=str(meta.get("name", "")),
                    file=str(meta.get("file", "")),
                    source_type="semantic",
                    document=doc,
                    metadata=meta,
                    semantic_rank=idx + 1,
                    semantic_score=score,
                )
            )
        return candidates

    def _lexical_candidates(self, query: str, n_results: int) -> List[RetrievalCandidate]:
        ranked = self.lexical.search(query, n_results=n_results)
        out: List[RetrievalCandidate] = []
        for rank_idx, (doc_idx, score) in enumerate(ranked, start=1):
            doc = self._documents[doc_idx]
            meta = doc.get("metadata", {})
            unique_id = str(meta.get("unique_id") or doc.get("unique_id") or f"lexical:{doc_idx}")
            out.append(
                RetrievalCandidate(
                    id=unique_id,
                    unique_id=unique_id,
                    name=str(meta.get("name", "")),
                    file=str(meta.get("file", "")),
                    source_type="lexical",
                    document=str(doc.get("document", "")),
                    metadata=meta,
                    lexical_rank=rank_idx,
                    lexical_score=float(score),
                )
            )
        return out

    def _apply_filters(self, candidates: Iterable[RetrievalCandidate], query_filters: Dict[str, str]) -> List[RetrievalCandidate]:
        file_filter = query_filters.get("file")
        type_filter = query_filters.get("type")
        filtered: List[RetrievalCandidate] = []
        for c in candidates:
            if file_filter and file_filter not in (c.file or "").replace("\\", "/").lower():
                continue
            if type_filter and str(c.metadata.get("type", "")).lower() != type_filter:
                continue
            filtered.append(c)
        return filtered

    @staticmethod
    def _fuse_rrf(
        semantic: Sequence[RetrievalCandidate],
        lexical: Sequence[RetrievalCandidate],
        k_constant: int = 60,
    ) -> List[RetrievalCandidate]:
        merged: Dict[str, RetrievalCandidate] = {}

        for c in semantic:
            key = c.unique_id
            if key not in merged:
                merged[key] = c
            merged[key].semantic_rank = c.semantic_rank
            merged[key].semantic_score = c.semantic_score

        for c in lexical:
            key = c.unique_id
            if key not in merged:
                merged[key] = c
            else:
                # Keep richer semantic metadata/document but update lexical signals.
                merged[key].lexical_score = max(merged[key].lexical_score, c.lexical_score)
                merged[key].lexical_rank = c.lexical_rank
                continue
            merged[key].lexical_rank = c.lexical_rank
            merged[key].lexical_score = c.lexical_score

        for m in merged.values():
            sem_rrf = 0.0 if not m.semantic_rank else 1.0 / (k_constant + m.semantic_rank)
            lex_rrf = 0.0 if not m.lexical_rank else 1.0 / (k_constant + m.lexical_rank)
            m.fused_score = sem_rrf + lex_rrf
        return sorted(merged.values(), key=lambda c: c.fused_score, reverse=True)

    @staticmethod
    def _rerank(query: str, candidates: Sequence[RetrievalCandidate], strong_mode: bool = False) -> List[RetrievalCandidate]:
        q_tokens = set(_tokenize(query))
        for cand in candidates:
            d_tokens = set(_tokenize(cand.document))
            overlap = len(q_tokens.intersection(d_tokens))
            lexical_boost = overlap / max(len(q_tokens), 1)
            entity_boost = 0.0
            name = (cand.name or "").lower()
            for qt in q_tokens:
                if qt in name:
                    entity_boost += 0.06
            alpha = 0.72 if strong_mode else 0.58
            cand.rerank_score = alpha * cand.fused_score + (1.0 - alpha) * lexical_boost + entity_boost
        return sorted(candidates, key=lambda c: c.rerank_score, reverse=True)

    def search(
        self,
        query: str,
        query_embedding: List[float],
        intent: str,
        use_hybrid: bool = True,
        use_reranker: bool = True,
        strong_reranker: bool = False,
        score_threshold: float = 0.0,
    ) -> Tuple[List[RetrievalCandidate], Dict[str, Any]]:
        t0 = time.perf_counter()
        semantic = self._vector_candidates(query_embedding, n_results=24)
        semantic_conf = float(semantic[0].semantic_score) if semantic else 0.0
        top_k = self.dynamic_top_k(intent=intent, confidence=semantic_conf)
        q_filters = self.parse_query_filters(query)

        lexical: List[RetrievalCandidate] = []
        if use_hybrid:
            lexical = self._lexical_candidates(query, n_results=30)

        fused = self._fuse_rrf(semantic, lexical if use_hybrid else [])
        filtered = self._apply_filters(fused, q_filters)
        if score_threshold > 0:
            filtered = [c for c in filtered if c.fused_score >= score_threshold]

        ranked = self._rerank(query, filtered, strong_mode=strong_reranker) if use_reranker else filtered
        final = ranked[:top_k]
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        trace = {
            "semantic_count": len(semantic),
            "lexical_count": len(lexical),
            "fused_count": len(fused),
            "filtered_count": len(filtered),
            "final_count": len(final),
            "dynamic_top_k": top_k,
            "query_filters": q_filters,
            "semantic_confidence": round(semantic_conf, 6),
            "latency_ms": elapsed_ms,
        }
        return final, trace


class EntityResolver:
    def __init__(self, raw_data: Optional[Sequence[Dict[str, Any]]] = None) -> None:
        self._by_uid: Dict[str, Dict[str, Any]] = {}
        self._by_name: Dict[str, List[Dict[str, Any]]] = {}
        for node in raw_data or []:
            uid = str(node.get("unique_id") or "")
            name = str(node.get("name") or "")
            if uid:
                self._by_uid[uid] = node
            if name:
                self._by_name.setdefault(name, []).append(node)

    def resolve(
        self,
        query: str,
        retrieval_candidates: Sequence[RetrievalCandidate],
        prefer_rerank: bool = True,
    ) -> List[str]:
        query_l = query.lower()
        file_hint = ""
        m = _FILE_HINT_RE.search(query)
        if m:
            file_hint = m.group(1).replace("\\", "/").lower()

        scored: List[Tuple[str, float]] = []
        for cand in retrieval_candidates:
            uid = cand.unique_id
            if not uid:
                continue
            score = cand.rerank_score if prefer_rerank else cand.fused_score
            if file_hint and file_hint in (cand.file or "").replace("\\", "/").lower():
                score += 0.1
            name = (cand.name or "").lower()
            if name and name in query_l:
                score += 0.08
            scored.append((uid, score))

        # Disambiguate colliding names via best scored unique_id.
        scored.sort(key=lambda x: x[1], reverse=True)
        dedup: List[str] = []
        seen: set[str] = set()
        for uid, _ in scored:
            if uid in seen:
                continue
            seen.add(uid)
            dedup.append(uid)
        return dedup

    def expand_for_intent(
        self,
        entity_ids: Sequence[str],
        graph_store,
        intent: str,
        enabled: bool = True,
    ) -> List[str]:
        if not enabled or graph_store is None:
            return list(entity_ids)

        if intent in {"governance", "blast_radius", "architecture"}:
            hop_limit = 2
            cap = 20
        elif intent in {"complexity"}:
            hop_limit = 1
            cap = 14
        else:
            hop_limit = 1
            cap = 10

        expanded: List[str] = []
        queue: List[Tuple[str, int]] = [(eid, 0) for eid in entity_ids]
        seen: set[str] = set()

        while queue and len(expanded) < cap:
            curr, hop = queue.pop(0)
            if curr in seen:
                continue
            seen.add(curr)
            expanded.append(curr)
            if hop >= hop_limit:
                continue
            if graph_store.has_node(curr):
                for n in list(graph_store.predecessors(curr))[:6]:
                    queue.append((n, hop + 1))
                for n in list(graph_store.successors(curr))[:6]:
                    queue.append((n, hop + 1))
        return expanded


class ContextBudgetManager:
    """
    Token-aware context packing with dedupe and intent templates.
    """

    def __init__(self, token_budget: int = 1700):
        self.token_budget = token_budget

    @staticmethod
    def _intent_header(intent: str) -> str:
        templates = {
            "blast_radius": "[INTENT: DEBUG IMPACT]",
            "governance": "[INTENT: ARCHITECTURE/GOVERNANCE]",
            "expertise": "[INTENT: OWNERSHIP]",
            "complexity": "[INTENT: COMPLEXITY REFACTOR]",
            "general": "[INTENT: HOW-TO]",
        }
        return templates.get(intent, "[INTENT: HOW-TO]")

    def pack(
        self,
        intent: str,
        candidates: Sequence[RetrievalCandidate],
        graph_context: str,
        feature_data: str,
    ) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        header = self._intent_header(intent)
        chunks: List[str] = [header]
        used = _estimate_tokens(header)
        evidence: List[Dict[str, Any]] = []
        seen_docs: set[str] = set()

        for rank, c in enumerate(candidates, start=1):
            sig = f"{c.unique_id}:{hash(c.document)}"
            if sig in seen_docs:
                continue
            seen_docs.add(sig)
            t_cost = _estimate_tokens(c.document)
            if used + t_cost > self.token_budget:
                continue
            used += t_cost
            chunks.append(c.document)
            evidence.append(c.to_evidence(rank=rank))

        # Add compact graph/feature summaries if budget allows.
        for block_name, block in (("graph", graph_context), ("feature", feature_data)):
            if not block:
                continue
            t_cost = _estimate_tokens(block)
            if used + t_cost > self.token_budget:
                continue
            used += t_cost
            chunks.append(f"[{block_name.upper()}]\n{block}")

        trace = {
            "token_budget": self.token_budget,
            "token_used_estimate": used,
            "packed_evidence_count": len(evidence),
        }
        return "\n\n---\n\n".join(chunks), evidence, trace


def evaluate_grounding(answer: str, evidence: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Lightweight grounding check:
    - Counts answer sentences with little overlap to evidence text.
    """
    if not answer:
        return {"grounded": False, "unsupported_claim_count": 1, "uncertainty_reason": "empty_answer"}

    ev_tokens: set[str] = set()
    for e in evidence:
        ev_tokens.update(_tokenize(str(e.get("snippet", ""))))

    sentences = [s.strip() for s in re.split(r"[.!?]\s+", answer) if s.strip()]
    unsupported = 0
    for s in sentences:
        s_tokens = set(_tokenize(s))
        if not s_tokens:
            continue
        overlap_ratio = len(s_tokens.intersection(ev_tokens)) / max(len(s_tokens), 1)
        if overlap_ratio < 0.15:
            unsupported += 1

    grounded = unsupported == 0
    reason = "" if grounded else "insufficient_evidence_overlap"
    return {
        "grounded": grounded,
        "unsupported_claim_count": unsupported,
        "uncertainty_reason": reason,
    }


def estimate_cost_usd(
    input_tokens: int,
    output_tokens: int,
    input_per_million: float = 0.2,
    output_per_million: float = 0.6,
) -> float:
    return round(
        (max(input_tokens, 0) / 1_000_000.0) * input_per_million
        + (max(output_tokens, 0) / 1_000_000.0) * output_per_million,
        8,
    )


def p95(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * 0.95) - 1))
    return float(ordered[rank])
