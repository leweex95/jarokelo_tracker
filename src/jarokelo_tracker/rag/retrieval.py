import faiss
import json
import os
import glob
import textwrap
from pathlib import Path
from jarokelo_tracker.rag.embedding import embed_query


def load_vector_store(vector_backend, vector_path, vector_base_dir):
    if vector_path:
        vector_dir = Path(vector_path)
    else:
        pattern = os.path.join(vector_base_dir, f"{vector_backend}_*")
        dirs = sorted(glob.glob(pattern), reverse=True)
        if not dirs:
            raise FileNotFoundError(f"No vector store found for backend '{vector_backend}'")
        vector_dir = Path(dirs[0])
    index = faiss.read_index(str(vector_dir / "index.faiss"))
    with open(vector_dir / "metadata.jsonl", "r", encoding="utf-8") as f:
        metas = [json.loads(l) for l in f]
    return index, metas

def retrieve_chunks(index, metas, query, embedding_provider, local_model, top_k):
    q_vec = embed_query(query, embedding_provider, local_model)
    distances, indices = index.search(q_vec, top_k)
    retrieved, used_ids = [], []
    for idx in indices[0]:
        if idx < 0:
            continue
        meta = metas[idx]
        snippet = textwrap.shorten(meta["text"], 400)
        retrieved.append(
            f"ID: {meta['id']} | URL: {meta.get('url')} | "
            f"District: {meta.get('district')} | Status: {meta.get('status')}\n{snippet}"
        )
        used_ids.append(meta["id"])
    return retrieved, used_ids
