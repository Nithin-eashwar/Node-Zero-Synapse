import sys
import os
import chromadb

# Add project root to path
sys.path.append(os.getcwd())

from backend.ai.store import VectorStore
from backend.ai.embeddings import CodeEmbedder

def test_retrieval():
    print("--- Debugging Retrieval ---")
    
    # 1. Check Store
    try:
        store = VectorStore()
        count = store.collection.count()
        print(f"Collection count: {count}")
        
        if count == 0:
            print("ERROR: Collection is empty! Indexing didn't persist.")
            return
            
        # 2. Test Embedding
        embedder = CodeEmbedder()
        query = "blast radius"
        print(f"Embedding query: '{query}'...")
        query_vec = embedder.embed_text(query)
        
        # 3. Test Search
        print("Searching...")
        results = store.search(query_vec, n_results=5)
        
        print("\nSearch Results:")
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                print(f"[{i}] {doc[:100]}...")
        else:
            print("No documents found in search result.")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_retrieval()
