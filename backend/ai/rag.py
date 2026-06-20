import os
import asyncio
import time
import dotenv
from langchain_core.prompts import ChatPromptTemplate
from .embeddings import CodeEmbedder
from .store_factory import create_vector_store
from .llm_factory import create_llm
from .graph_context import GraphContextBuilder
from .context_aggregator import ContextAggregator
from .prompts import get_prompt_for_query, QueryIntent
from .retrieval_orchestrator import (
    RetrievalOrchestrator,
    EntityResolver,
    ContextBudgetManager,
    evaluate_grounding,
    estimate_cost_usd,
)

# Load environment variables
dotenv.load_dotenv()


class RAGPipeline:
    def __init__(self):
        print("Initializing RAG Pipeline...")
        self.embedder = CodeEmbedder()
        self.vector_store = create_vector_store()
        self.retrieval = RetrievalOrchestrator(self.vector_store)
        self.graph_context: GraphContextBuilder = None
        self.context_aggregator: ContextAggregator = None
        self.entity_resolver: EntityResolver = EntityResolver([])
        self.context_budget = ContextBudgetManager(
            token_budget=int(os.getenv("SYNAPSE_RAG_TOKEN_BUDGET", "1700"))
        )
        self._repo_path: str = None
        self._indexed_node_count: int = 0
        
        # Initialize LLM via factory (provider selected by LLM_PROVIDER env var)
        self.llm = create_llm(temperature=0.2)
        if not self.llm:
            print("Warning: LLM not available. AI features will not work.")

        # Fallback prompt when no graph context is available
        self.basic_prompt = ChatPromptTemplate.from_template("""You are Synapse, an expert AI coding assistant.
Use the provided code context to answer the user's question about the repository.
If the context doesn't contain the answer, say so, but try to infer from what is available.

Context:
{context}

Question: {question}

Answer:
""")

    def set_graph_context(self, graph_store, raw_data, repo_path: str = None):
        """
        Initialize graph context builder and context aggregator with loaded graph data.
        Called after the graph is loaded in the API.
        """
        self.graph_context = GraphContextBuilder(graph_store, raw_data)
        self.context_aggregator = ContextAggregator(graph_store, raw_data)
        self.entity_resolver = EntityResolver(raw_data)
        self._repo_path = repo_path
        print("Graph context builder + context aggregator initialized for RAG pipeline.")

    def index_codebase(self, nodes):
        """Embeds and stores the given nodes."""
        if not nodes:
            return 0
            
        print(f"Indexing {len(nodes)} nodes...")
        embeddings = self.embedder.embed_nodes(nodes)
        self.vector_store.add_nodes(nodes, embeddings)
        self.retrieval.index_nodes(nodes)
        self._indexed_node_count = len(nodes)
        print("Indexing complete.")
        return len(nodes)

    def reset_index(self) -> None:
        """Clear the vector store before re-indexing the active repo."""
        self.vector_store.delete_collection()
        self.vector_store = create_vector_store()
        self.retrieval = RetrievalOrchestrator(self.vector_store)
        self._indexed_node_count = 0

    def ensure_indexed(self, nodes, force_reindex: bool = False) -> int:
        """
        Ensure the active graph is present in the vector store.
        """
        if not nodes:
            return 0

        should_index = force_reindex
        if not should_index:
            should_index = self._indexed_node_count != len(nodes)

        if not should_index:
            try:
                collection = getattr(self.vector_store, "collection", None)
                if collection is not None and collection.count() == 0:
                    should_index = True
            except Exception:
                should_index = True

        if should_index:
            print("Vector index missing or stale; rebuilding for active repo...")
            self.reset_index()
            return self.index_codebase(nodes)

        return self._indexed_node_count

    async def ask(self, query):
        if not self.llm:
            return {"answer": "Error: GOOGLE_API_KEY not configured.", "context": []}

        ask_start = time.perf_counter()
        stage_ms = {}
        failure_reason = ""

        # 1. Detect query intent for feature-specific prompting
        t0 = time.perf_counter()
        prompt, intent = get_prompt_for_query(query)
        stage_ms["intent"] = round((time.perf_counter() - t0) * 1000.0, 3)

        # 2. Embed query for vector search
        t0 = time.perf_counter()
        query_embedding = self.embedder.embed_text(query)
        stage_ms["embed"] = round((time.perf_counter() - t0) * 1000.0, 3)

        use_hybrid = os.getenv("SYNAPSE_RAG_HYBRID", "1").lower() in ("1", "true", "yes")
        use_reranker = os.getenv("SYNAPSE_RAG_RERANKER", "1").lower() in ("1", "true", "yes")
        use_intent_expansion = os.getenv("SYNAPSE_RAG_INTENT_EXPANSION", "1").lower() in ("1", "true", "yes")
        grounded_only = os.getenv("SYNAPSE_RAG_GROUNDED_ONLY", "0").lower() in ("1", "true", "yes")
        strong_reranker = os.getenv("SYNAPSE_RAG_STRONG_RERANKER", "0").lower() in ("1", "true", "yes")
        score_threshold = float(os.getenv("SYNAPSE_RAG_SCORE_THRESHOLD", "0"))

        # 3. Retrieve with hybrid strategy + reranking
        t0 = time.perf_counter()
        candidates, retrieval_trace = self.retrieval.search(
            query=query,
            query_embedding=query_embedding,
            intent=intent.value,
            use_hybrid=use_hybrid,
            use_reranker=use_reranker,
            strong_reranker=strong_reranker,
            score_threshold=score_threshold,
        )
        stage_ms["retrieve_rerank"] = round((time.perf_counter() - t0) * 1000.0, 3)

        if not candidates:
            if retrieval_trace.get("semantic_count", 0) > 0 and retrieval_trace.get("filtered_count", 0) == 0:
                failure_reason = "ranking_miss"
            else:
                failure_reason = "retrieval_miss"
            total_ms = round((time.perf_counter() - ask_start) * 1000.0, 3)
            return {
                "answer": "No relevant code context found.",
                "context": [],
                "evidence": [],
                "retrieval_trace": retrieval_trace,
                "grounding": {
                    "grounded": False,
                    "unsupported_claim_count": 0,
                    "uncertainty_reason": "no_retrieval",
                },
                "metrics": {
                    "stage_ms": stage_ms,
                    "total_latency_ms": total_ms,
                    "cost_query_usd_estimate": 0.0,
                    "failure_reason": failure_reason,
                },
                "intent": intent.value,
                "mode": "no_context",
            }

        retrieved_docs = [c.document for c in candidates]
        entity_names = self.entity_resolver.resolve(query, candidates, prefer_rerank=use_reranker)
        graph_store = self.graph_context.graph if self.graph_context else None
        t0 = time.perf_counter()
        expanded_entities = self.entity_resolver.expand_for_intent(
            entity_ids=entity_names,
            graph_store=graph_store,
            intent=intent.value,
            enabled=use_intent_expansion,
        )
        stage_ms["graph_expand"] = round((time.perf_counter() - t0) * 1000.0, 3)

        # 4. Build graph-aware context if available
        if self.graph_context and expanded_entities:
            result = await self._ask_with_full_context(
                query=query,
                prompt=prompt,
                intent=intent,
                entity_names=expanded_entities,
                retrieval_candidates=candidates,
                retrieval_trace=retrieval_trace,
                stage_ms=stage_ms,
                ask_start=ask_start,
                grounded_only=grounded_only,
            )
        else:
            packed_context, packed_evidence, pack_trace = self.context_budget.pack(
                intent=intent.value,
                candidates=candidates,
                graph_context="",
                feature_data="",
            )
            retrieval_trace["context_pack"] = pack_trace
            result = self._ask_basic(
                query=query,
                context_str=packed_context,
                retrieved_docs=retrieved_docs,
                evidence=packed_evidence,
                retrieval_trace=retrieval_trace,
                stage_ms=stage_ms,
                ask_start=ask_start,
                grounded_only=grounded_only,
            )
        return result

    async def _ask_with_full_context(
        self,
        query,
        prompt,
        intent,
        entity_names,
        retrieval_candidates,
        retrieval_trace,
        stage_ms,
        ask_start,
        grounded_only: bool,
    ):
        """Generate response using multi-source context injection."""
        try:
            # Build all context sources in parallel (saves ~300-400ms)
            async def _get_graph_context():
                # Run sync graph traversal in a thread to not block event loop
                ctx = await asyncio.to_thread(
                    self.graph_context.get_query_context, entity_names
                )
                if len(ctx) > 1500:
                    ctx = ctx[:1500] + "\n... (truncated for brevity)"
                return ctx

            async def _get_graph_summary():
                return await asyncio.to_thread(
                    self.graph_context.get_graph_summary
                )

            async def _get_feature_data():
                if self.context_aggregator and intent != QueryIntent.GENERAL:
                    return await self.context_aggregator.gather(
                        intent, entity_names, self._repo_path
                    )
                return ""

            # Run all 3 concurrently
            t0 = time.perf_counter()
            graph_context_str, graph_summary, feature_data = await asyncio.gather(
                _get_graph_context(),
                _get_graph_summary(),
                _get_feature_data(),
            )
            stage_ms["graph_feature_context"] = round((time.perf_counter() - t0) * 1000.0, 3)

            # Token-aware context packing + evidence
            t0 = time.perf_counter()
            packed_context, evidence, pack_trace = self.context_budget.pack(
                intent=intent.value,
                candidates=retrieval_candidates,
                graph_context=graph_context_str,
                feature_data=feature_data,
            )
            retrieval_trace["context_pack"] = pack_trace
            stage_ms["context_pack"] = round((time.perf_counter() - t0) * 1000.0, 3)
            
            chain = prompt | self.llm
            t0 = time.perf_counter()
            response = chain.invoke({
                "feature_data": feature_data,
                "graph_context": graph_context_str,
                "code_context": packed_context,
                "graph_summary": graph_summary,
                "question": query
            })
            stage_ms["generate"] = round((time.perf_counter() - t0) * 1000.0, 3)

            grounding = evaluate_grounding(response.content, evidence)
            grounding_miss = grounded_only and not grounding.get("grounded", False)
            if grounding_miss:
                response_text = (
                    "I don't have enough grounded evidence to answer confidently. "
                    "Try narrowing the question to a specific file/module/entity."
                )
            else:
                response_text = response.content

            input_tokens = max(1, len(packed_context.split()))
            output_tokens = max(1, len(response_text.split()))
            total_ms = round((time.perf_counter() - ask_start) * 1000.0, 3)

            return {
                "answer": response_text,
                "context": [c.document for c in retrieval_candidates[:3]],
                "graph_entities": entity_names[:10],
                "evidence": evidence,
                "retrieval_trace": retrieval_trace,
                "grounding": grounding,
                "metrics": {
                    "stage_ms": stage_ms,
                    "total_latency_ms": total_ms,
                    "token_estimate": {
                        "input": input_tokens,
                        "output": output_tokens,
                    },
                    "cost_query_usd_estimate": estimate_cost_usd(input_tokens, output_tokens),
                    "failure_reason": "grounding_miss" if grounding_miss else "",
                },
                "intent": intent.value,
                "mode": "multi_source"
            }
        except Exception as e:
            print(f"Multi-source RAG failed, falling back to basic: {e}")
            return self._ask_basic(
                query=query,
                context_str="\n\n---\n\n".join([c.document for c in retrieval_candidates]),
                retrieved_docs=[c.document for c in retrieval_candidates],
                evidence=[c.to_evidence(rank=i + 1) for i, c in enumerate(retrieval_candidates)],
                retrieval_trace=retrieval_trace,
                stage_ms=stage_ms,
                ask_start=ask_start,
                grounded_only=grounded_only,
            )

    def _ask_basic(
        self,
        query,
        context_str,
        retrieved_docs,
        evidence,
        retrieval_trace,
        stage_ms,
        ask_start,
        grounded_only: bool,
    ):
        """Fallback: generate response using only code context."""
        try:
            t0 = time.perf_counter()
            chain = self.basic_prompt | self.llm
            response = chain.invoke({"context": context_str, "question": query})
            stage_ms["generate"] = round((time.perf_counter() - t0) * 1000.0, 3)
            grounding = evaluate_grounding(response.content, evidence)
            grounding_miss = grounded_only and not grounding.get("grounded", False)
            if grounding_miss:
                response_text = (
                    "I don't have enough grounded evidence to answer confidently. "
                    "Try asking about a specific file or symbol."
                )
            else:
                response_text = response.content
            input_tokens = max(1, len(context_str.split()))
            output_tokens = max(1, len(response_text.split()))
            total_ms = round((time.perf_counter() - ask_start) * 1000.0, 3)
            return {
                "answer": response_text,
                "context": retrieved_docs,
                "evidence": evidence,
                "retrieval_trace": retrieval_trace,
                "grounding": grounding,
                "metrics": {
                    "stage_ms": stage_ms,
                    "total_latency_ms": total_ms,
                    "token_estimate": {
                        "input": input_tokens,
                        "output": output_tokens,
                    },
                    "cost_query_usd_estimate": estimate_cost_usd(input_tokens, output_tokens),
                    "failure_reason": "grounding_miss" if grounding_miss else "",
                },
                "intent": "general",
                "mode": "basic"
            }
        except Exception as e:
            total_ms = round((time.perf_counter() - ask_start) * 1000.0, 3)
            return {
                "answer": f"Error generating response: {str(e)}", 
                "context": retrieved_docs,
                "evidence": evidence,
                "retrieval_trace": retrieval_trace,
                "grounding": {
                    "grounded": False,
                    "unsupported_claim_count": 0,
                    "uncertainty_reason": "provider_error",
                },
                "metrics": {
                    "stage_ms": stage_ms,
                    "total_latency_ms": total_ms,
                    "cost_query_usd_estimate": 0.0,
                    "failure_reason": "provider_error",
                },
                "intent": "error",
                "mode": "error"
            }

    def _extract_entity_names(self, results) -> list:
        """Extract entity identifiers from ChromaDB search results metadata."""
        names = []
        if results.get('metadatas') and results['metadatas'][0]:
            for meta in results['metadatas'][0]:
                if not meta:
                    continue
                if meta.get("unique_id"):
                    names.append(meta["unique_id"])
                elif meta.get("name"):
                    names.append(meta["name"])
        return names
