import faiss
import json
import os
import glob
from pathlib import Path

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
