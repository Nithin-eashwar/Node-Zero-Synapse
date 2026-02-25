import sys
import os
import chromadb

# Add current directory to path
sys.path.append(os.getcwd())

from backend.ai.store import VectorStore

def test_chroma():
    print("Initializing VectorStore...")
    try:
        # Use a separate test collection to avoid messing with main one, 
        # but same DB path to test locking.
        store = VectorStore(collection_name="test_collection")
        print("VectorStore initialized.")
        
        nodes = [{"name": "test_node", "type": "function", "file": "test.py", "calls": []}]
        # Mock 384-dim embedding (standard for MiniLM)
        embeddings = [[0.1] * 384]
        
        print("Adding nodes...")
        store.add_nodes(nodes, embeddings)
        print("SUCCESS: Nodes added to ChromaDB.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chroma()
