import os
import dotenv
from langchain_core.prompts import ChatPromptTemplate
from .embeddings import CodeEmbedder
from .store_factory import create_vector_store
from .llm_factory import create_llm
from .graph_context import GraphContextBuilder
from .context_aggregator import ContextAggregator
from .prompts import get_prompt_for_query, QueryIntent

# Load environment variables
dotenv.load_dotenv()


class RAGPipeline:
    def __init__(self):
        print("Initializing RAG Pipeline...")
        self.embedder = CodeEmbedder()
        self.vector_store = create_vector_store()
        self.graph_context: GraphContextBuilder = None
        self.context_aggregator: ContextAggregator = None
        self._repo_path: str = None
        
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
        self._repo_path = repo_path
        print("Graph context builder + context aggregator initialized for RAG pipeline.")

    def index_codebase(self, nodes):
        """Embeds and stores the given nodes."""
        if not nodes:
            return 0
            
        print(f"Indexing {len(nodes)} nodes...")
        embeddings = self.embedder.embed_nodes(nodes)
        self.vector_store.add_nodes(nodes, embeddings)
        print("Indexing complete.")
        return len(nodes)

    async def ask(self, query):
        if not self.llm:
            return {"answer": "Error: GOOGLE_API_KEY not configured.", "context": []}

        # 1. Detect query intent for feature-specific prompting
        prompt, intent = get_prompt_for_query(query)

        # 2. Embed query for vector search
        query_embedding = self.embedder.embed_text(query)
        
        # 3. Retrieve from vector store
        results = self.vector_store.search(query_embedding, n_results=5)
        
        if not results['documents'] or not results['documents'][0]:
            return {"answer": "No relevant code context found.", "context": []}
            
        retrieved_docs = results['documents'][0]
        code_context_str = "\n\n---\n\n".join(retrieved_docs)
        
        # 4. Extract entity names from retrieved results for graph lookup
        entity_names = self._extract_entity_names(results)
        
        # 5. Build graph-aware context if available
        if self.graph_context and entity_names:
            return self._ask_with_full_context(
                query, prompt, intent, code_context_str, entity_names, retrieved_docs
            )
        else:
            return self._ask_basic(query, code_context_str, retrieved_docs)

    async def _ask_with_full_context(self, query, prompt, intent, code_context_str, entity_names, retrieved_docs):
        """Generate response using multi-source context injection."""
        try:
            # Source 1: Graph-aware structural context
            graph_context_str = self.graph_context.get_query_context(entity_names)
            graph_summary = self.graph_context.get_graph_summary()
            
            # Source 2: Live feature data from backend services
            feature_data = ""
            if self.context_aggregator:
                feature_data = await self.context_aggregator.gather(
                    intent, entity_names, self._repo_path
                )
            
            chain = prompt | self.llm
            response = chain.invoke({
                "feature_data": feature_data,
                "graph_context": graph_context_str,
                "code_context": code_context_str,
                "graph_summary": graph_summary,
                "question": query
            })
            
            return {
                "answer": response.content,
                "context": retrieved_docs,
                "graph_entities": entity_names,
                "intent": intent.value,
                "mode": "multi_source"
            }
        except Exception as e:
            print(f"Multi-source RAG failed, falling back to basic: {e}")
            return self._ask_basic(query, code_context_str, retrieved_docs)

    def _ask_basic(self, query, context_str, retrieved_docs):
        """Fallback: generate response using only code context."""
        try:
            chain = self.basic_prompt | self.llm
            response = chain.invoke({"context": context_str, "question": query})
            return {
                "answer": response.content,
                "context": retrieved_docs,
                "intent": "general",
                "mode": "basic"
            }
        except Exception as e:
            return {
                "answer": f"Error generating response: {str(e)}", 
                "context": retrieved_docs,
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
