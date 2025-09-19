import os
import json
import argparse
from pathlib import Path
from datetime import datetime
import numpy as np


CHUNKS_PATH = "data/processed/issues_chunks.jsonl"
VECTOR_DIR = "data/vector_store"


class VectorStoreBuilder:
    def __init__(self, backend: str, embedding: str, api_key: str = None):
        self.backend = backend
        self.embedding = embedding
        self.api_key = api_key
        self.texts, self.metadatas = self.load_chunks(CHUNKS_PATH)

    @staticmethod
    def load_chunks(path: str):
        with open(path, "r", encoding="utf-8") as fh:
            chunks = [json.loads(line) for line in fh]
        texts = [c["text"] for c in chunks]
        metadatas = [{**c["metadata"], "id": c["id"], "text": c["text"]} for c in chunks]
        return texts, metadatas

    def compute_embeddings(self):
        if self.embedding.startswith("sentence-transformers"):
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(self.embedding)
            embeddings = model.encode(self.texts, convert_to_numpy=True).astype("float32")
        else:
            import openai
            openai.api_key = self.api_key
            embeddings = []
            for t in self.texts:
                resp = openai.Embedding.create(input=[t], model=self.embedding)
                embeddings.append(np.array(resp["data"][0]["embedding"], dtype="float32"))
            embeddings = np.vstack(embeddings)
        return embeddings

    @staticmethod
    def build_faiss(embeddings, metadatas, outdir: Path):
        import faiss
        faiss.normalize_L2(embeddings)
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        faiss.write_index(index, str(outdir / "index.faiss"))

        with open(outdir / "metadata.jsonl", "w", encoding="utf-8") as fh:
            for m in metadatas:
                fh.write(json.dumps(m, ensure_ascii=False) + "\n")

    @staticmethod
    def build_chroma(embeddings, metadatas, outdir: Path):
        import chromadb
        client = chromadb.PersistentClient(path=str(outdir))
        ids = [m["id"] for m in metadatas]
        docs = [m["text"] for m in metadatas]
        metas = [{k: v for k, v in m.items() if k not in ("text", "id")} for m in metadatas]

        collection = client.create_collection(name="issues")
        collection.add(ids=ids, embeddings=embeddings.tolist(), metadatas=metas, documents=docs)

    def build(self):
        embeddings = self.compute_embeddings()
        os.makedirs(VECTOR_DIR, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        outdir = Path(VECTOR_DIR) / f"{self.backend}_{timestamp}"
        outdir.mkdir(parents=True, exist_ok=True)

        if self.backend == "faiss":
            self.build_faiss(embeddings, self.metadatas, outdir)
        elif self.backend == "chroma":
            self.build_chroma(embeddings, self.metadatas, outdir)
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")

        print(f"Vector store saved to {outdir}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build vector store from processed issues.")
    parser.add_argument("--backend", choices=["faiss", "chroma"], required=True,
                        help="Vector store backend")
    parser.add_argument("--embedding", required=True,
                        help="Embedding provider (e.g. 'sentence-transformers/all-MiniLM-L6-v2' or 'text-embedding-ada-002')")
    parser.add_argument("--api-key", default=None,
                        help="OpenAI API key (only if using OpenAI embeddings)")
    args = parser.parse_args()

    builder = VectorStoreBuilder(args.backend, args.embedding, args.api_key)
    builder.build()
