import chromadb
import uuid

class VectorStore:
    def __init__(self, collection_name="codebase_vectors"):
        # PersistentClient saves data to disk so we don't re-index every restart
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_nodes(self, nodes, embeddings):
        """
        Upserts nodes into the vector store in batches.
        """
        batch_size = 100
        total_nodes = len(nodes)
        
        for i in range(0, total_nodes, batch_size):
            batch_nodes = nodes[i : i + batch_size]
            batch_embeddings = embeddings[i : i + batch_size]
            
            ids = []
            documents = []
            metadatas = []
            
            for node in batch_nodes:
                # Generate unique ID: file:name:line
                # Use '0' default if range/line missing to allow partial data
                start_line = node.get('range', [0])[0] if 'range' in node else node.get('line', 0)
                unique_id = f"{node['file']}:{node['name']}:{start_line}"
                ids.append(unique_id)
                
                # Document text for display/context
                text_rep = f"Type: {node['type']}\nName: {node['name']}\nFile: {node['file']}"
                if 'calls' in node and node['calls']:
                    text_rep += f"\nCalls: {', '.join(node['calls'])}"
                documents.append(text_rep)
                
                # Metadata for filtering
                metadatas.append({
                    "file": node['file'],
                    "type": node['type'],
                    "name": node['name']
                })

            try:
                self.collection.upsert(
                    ids=ids,
                    documents=documents,
                    embeddings=batch_embeddings,
                    metadatas=metadatas
                )
                print(f"Indexed batch {i} to {i+len(batch_nodes)}")
            except Exception as e:
                print(f"Error indexing batch {i}: {e}")
                # Continue to next batch instead of crashing entirely
                continue

    def search(self, query_embedding, n_results=5):
        """
        Search using a pre-computed query embedding.
        """
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
