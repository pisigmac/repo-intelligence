import os
import numpy as np

class EmbeddingClient:
    def __init__(self):
        self.model = None
        self.use_mock = os.getenv("USE_MOCK_EMBEDDINGS", "false").lower() == "true"
        
        if not self.use_mock:
            try:
                from sentence_transformers import SentenceTransformer
                # all-MiniLM-L6-v2 produces 384-dimensional vectors
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                import logging
                logging.getLogger(__name__).warning("sentence-transformers not installed. Falling back to mock embeddings.")
                self.use_mock = True

    def get_embedding(self, text: str) -> list[float]:
        if not text:
            text = ""
            
        if self.use_mock or not self.model:
            dim = 384
            np.random.seed(hash(text) % (2**32))
            return np.random.randn(dim).astype(np.float32).tolist()
            
        # sentence-transformers encodes text into a numpy array
        vector = self.model.encode(text)
        return vector.tolist()

# Global singleton instance
embedding_client = None

def get_embedding(text: str) -> list[float]:
    global embedding_client
    if embedding_client is None:
        embedding_client = EmbeddingClient()
    return embedding_client.get_embedding(text)
