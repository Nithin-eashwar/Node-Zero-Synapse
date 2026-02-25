import os
import dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from .embeddings import CodeEmbedder
from .store import VectorStore

# Load environment variables
dotenv.load_dotenv()

class RAGPipeline:
    def __init__(self):
        print("Initializing RAG Pipeline...")
        self.embedder = CodeEmbedder()
        self.vector_store = VectorStore()
        
        # Check API Key
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("Warning: GOOGLE_API_KEY not found. AI features will not work until set.")
            self.llm = None
        else:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=api_key,
                temperature=0.2,
                convert_system_message_to_human=True
            )

        self.prompt = ChatPromptTemplate.from_template("""
        You are Synapse, an expert AI coding assistant.
        Use the provided code context to answer the user's question about the repository.
        If the context doesn't contain the answer, say so, but try to infer from what is available.
        
        Context:
        {context}
        
        Question: {question}
        
        Answer:
        """)

    def index_codebase(self, nodes):
        """
        Embeds and stores the given nodes.
        """
        if not nodes:
            return 0
            
        print(f"Indexing {len(nodes)} nodes...")
        embeddings = self.embedder.embed_nodes(nodes)
        self.vector_store.add_nodes(nodes, embeddings)
        print("Indexing complete.")
        return len(nodes)

    def ask(self, query):
        if not self.llm:
            return {"answer": "Error: GOOGLE_API_KEY not configured.", "context": []}

        # 1. Embed query
        query_embedding = self.embedder.embed_text(query)
        
        # 2. Retrieve
        results = self.vector_store.search(query_embedding, n_results=5)
        
        if not results['documents'] or not results['documents'][0]:
            return {"answer": "No relevant code context found.", "context": []}
            
        retrieved_docs = results['documents'][0]
        context_str = "\n\n---\n\n".join(retrieved_docs)
        
        # 3. Generate
        try:
            chain = self.prompt | self.llm
            response = chain.invoke({"context": context_str, "question": query})
            return {
                "answer": response.content,
                "context": retrieved_docs
            }
        except Exception as e:
            return {"answer": f"Error generating response: {str(e)}", "context": retrieved_docs}
