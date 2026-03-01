import sys
import os
import json
import traceback

# Add project root to path
sys.path.append(os.getcwd())

from backend.ai.rag import RAGPipeline

def main():
    print("--- Synapse Indexing Utility ---")
    
    # Check if repo_graph.json exists
    if not os.path.exists("repo_graph.json"):
        print("Error: repo_graph.json not found. Run 'python main.py' (parser) first.")
        return

    print("Loading graph data...")
    try:
        with open("repo_graph.json", "r") as f:
            data = json.load(f)
        print(f"Loaded {len(data)} items.")
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    print("\nInitializing AI Pipeline...")
    print("(This may take a minute to download models on first run)")
    try:
        # Initialize RAG Pipeline
        pipeline = RAGPipeline()
        
        print("\nStarting indexing...")
        count = pipeline.index_codebase(data)
        print(f"\nSUCCESS: Indexed {count} items into vector store.")
        print("You can now start the server and use the AI features.")
        
    except Exception:
        print("\nCRITICAL ERROR:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
