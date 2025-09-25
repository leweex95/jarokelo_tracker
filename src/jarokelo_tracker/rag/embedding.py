import faiss
from sentence_transformers import SentenceTransformer

def embed_query(query, embedding_provider, local_model):
    if embedding_provider == "local":
        model = SentenceTransformer(local_model)
        vec = model.encode([query], convert_to_numpy=True)[0].astype("float32")
    else:
        raise ValueError(f"Unknown embedding provider: {embedding_provider}")
    vec = vec.reshape(1, -1)
    faiss.normalize_L2(vec)
    return vec
