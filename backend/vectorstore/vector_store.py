import os
import logging
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from langchain_core.embeddings import Embeddings
from backend.utils.security import validate_path, get_relative_path, WORKSPACE_DIR

logger = logging.getLogger(__name__)

# Fallback custom mock embedding class to prevent crash when keys are missing
class SimpleMockEmbeddings(Embeddings):
    def __init__(self, size: int = 1536):
        self.size = size

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Return simple deterministic mock vectors
        results = []
        for text in texts:
            vector = [0.1 * (i % 10) for i in range(self.size)]
            # Add basic hash-based variation
            val = float(hash(text) % 100) / 1000.0
            vector[0] += val
            results.append(vector)
        return results

    def embed_query(self, text: str) -> List[float]:
        vector = [0.1 * (i % 10) for i in range(self.size)]
        val = float(hash(text) % 100) / 1000.0
        vector[0] += val
        return vector

def get_embeddings_model():
    """Returns OpenAI, Google, or Mock embeddings based on environment variables."""
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if openai_key:
        try:
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings()
        except ImportError:
            logger.warning("langchain-openai not installed, using mock embeddings")
    elif gemini_key:
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            return GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        except ImportError:
            logger.warning("langchain-google-genai not installed, using mock embeddings")
            
    logger.warning("No API key configured for embeddings. Using Mock Embeddings.")
    return SimpleMockEmbeddings()

class VectorStoreManager:
    def __init__(self):
        persist_dir = "d:/File-system/backend/vectorstore/.chroma"
        os.makedirs(persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.embeddings = get_embeddings_model()
        # Initialize or fetch the collection
        self.collection_name = "workspace_code"
        
    def _chunk_file(self, content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Simple sliding window text chunker."""
        chunks = []
        if not content:
            return chunks
        start = 0
        while start < len(content):
            end = start + chunk_size
            chunks.append(content[start:end])
            start += chunk_size - overlap
        return chunks

    def index_file(self, file_path_str: str):
        """Indexes a single file's content into ChromaDB."""
        try:
            target_path = validate_path(file_path_str)
            if not target_path.is_file():
                return
            
            # Supported extensions
            if target_path.suffix not in ['.py', '.js', '.ts', '.md', '.yaml', '.yml', '.txt', '.json']:
                return
                
            content = target_path.read_text(encoding="utf-8", errors="ignore")
            chunks = self._chunk_file(content)
            
            rel_path = get_relative_path(target_path)
            
            # Remove existing entries for this file
            self.delete_file_indices(rel_path)
            
            if not chunks:
                return
                
            # Create unique IDs
            ids = [f"{rel_path}_chunk_{i}" for i in range(len(chunks))]
            metadatas = [{"path": rel_path, "chunk_idx": i} for i in range(len(chunks))]
            
            # Embed chunks
            embeddings = self.embeddings.embed_documents(chunks)
            
            collection = self.client.get_or_create_collection(self.collection_name)
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas
            )
        except Exception as e:
            logger.error(f"Error indexing file {file_path_str}: {str(e)}")

    def delete_file_indices(self, rel_path: str):
        """Removes all indexed chunks for a file."""
        try:
            collection = self.client.get_or_create_collection(self.collection_name)
            # Query and delete
            results = collection.get(where={"path": rel_path})
            if results and results['ids']:
                collection.delete(ids=results['ids'])
        except Exception as e:
            logger.error(f"Error deleting index for {rel_path}: {str(e)}")

    def index_all_workspace(self):
        """Walks the workspace and indexes all valid files."""
        for root, _, files in os.walk(WORKSPACE_DIR):
            for file in files:
                file_path = Path(root) / file
                self.index_file(str(file_path))

    def semantic_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Searches ChromaDB for code fragments matching the query."""
        try:
            collection = self.client.get_or_create_collection(self.collection_name)
            query_vector = self.embeddings.embed_query(query)
            
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=limit
            )
            
            hits = []
            if results and results['documents']:
                docs = results['documents'][0]
                metas = results['metadatas'][0]
                distances = results['distances'][0] if 'distances' in results and results['distances'] else [0.0]*len(docs)
                ids = results['ids'][0]
                
                for doc, meta, dist, chunk_id in zip(docs, metas, distances, ids):
                    # Convert distance to similarity score
                    # ChromaDB distance is L2 by default, so lower is closer.
                    similarity = round(1.0 / (1.0 + dist), 4)
                    hits.append({
                        "id": chunk_id,
                        "path": meta.get("path", "unknown"),
                        "preview": doc[:300] + ("..." if len(doc) > 300 else ""),
                        "content": doc,
                        "similarity": similarity
                    })
            return hits
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return []
            
# Singleton manager
vector_store = VectorStoreManager()
