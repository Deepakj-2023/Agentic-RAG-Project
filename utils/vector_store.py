import os
os.environ["USE_TF"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pickle

class VectorStore:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(VectorStore, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, index_path="faiss.index", meta_path="meta.pkl"):
        if self._initialized:
            return
            
        print("Initializing VectorStore (Loading SentenceTransformer)...")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.index_path = index_path
        self.meta_path = meta_path

        self.index = None
        self.documents = []  # List of dicts: {"text": ..., "source": ..., "url": ...}
        
        self._load()
        self._initialized = True

    def _load(self):
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
        if os.path.exists(self.meta_path):
            with open(self.meta_path, "rb") as f:
                self.documents = pickle.load(f)

    def _save(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "wb") as f:
            pickle.dump(self.documents, f)

    def add_documents(self, docs_with_meta: list[dict]):
        texts = [d["text"] for d in docs_with_meta]
        embeddings = self.model.encode(texts)

        if self.index is None:
            dim = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dim)

        self.index.add(np.array(embeddings))
        self.documents.extend(docs_with_meta)
        self._save()

    def search(self, query: str, k: int = 3):
        if self.index is None:
            return []

        query_embedding = self.model.encode([query])
        distances, indices = self.index.search(np.array(query_embedding), k)

        results = []
        for idx in indices[0]:
            if idx < len(self.documents):
                results.append(self.documents[idx])

        return results

# Singleton instance
vector_store_instance = VectorStore()