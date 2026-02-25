import sys
import os
import json
import traceback

# Add current directory to path
sys.path.append(os.getcwd())

from backend.ai.rag import RAGPipeline

def test_indexing():
    print("Loading graph data...")
    try:
        with open("repo_graph.json", "r") as f:
            data = json.load(f)
        print(f"Loaded {len(data)} items from repo_graph.json")
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    print("Initializing Pipeline...")
    try:
        pipeline = RAGPipeline()
        print("Pipeline initialized.")
        
        print("Starting indexing...")
        count = pipeline.index_codebase(data)
        print(f"SUCCESS: Indexed {count} items.")
        
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    test_indexing()
