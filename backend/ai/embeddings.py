from sentence_transformers import SentenceTransformer

class CodeEmbedder:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        # We use a lightweight local model for speed
        print(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        print("Embedding model loaded.")

    def embed_text(self, text):
        return self.model.encode(text).tolist()

    def embed_nodes(self, nodes):
        """
        Embeds a list of nodes (functions/classes) for search.
        Constructs a rich string representation for each node.
        """
        embeddings = []
        for node in nodes:
            # Construct a rich representation:
            # Type: Function/Class
            # Name: The identifier
            # File: Where it lives
            # Calls: Context of what it uses
            # (In a real app, we'd also want docstrings/code body, but we have limited data in repo_graph.json)
            
            text_rep = f"{node['type']} {node['name']}\nFile: {node['file']}"
            if 'calls' in node and node['calls']:
                text_rep += f"\nCalls: {', '.join(node['calls'])}"
            
            embeddings.append(self.embed_text(text_rep))
        return embeddings
