import os
import glob
from pathlib import Path
import json
import textwrap
import argparse
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import openai

TOP_K = 6


class RAGClient:
    def __init__(self, vector_backend: str, embedding_provider: str,
                 vector_path: str = None,
                 local_model: str = "distiluse-base-multilingual-cased-v2",
                 openai_model: str = "text-embedding-3-small",
                 llm_model: str = "gpt-4o-mini",
                 vector_base_dir: str = "data/vector_store"):
        self.vector_backend = vector_backend
        self.embedding_provider = embedding_provider
        self.local_model = local_model
        self.openai_model = openai_model
        self.llm_model = llm_model

        # determine vector dir
        if vector_path:
            self.vector_dir = Path(vector_path)
        else:
            # pick latest folder matching backend
            pattern = os.path.join(vector_base_dir, f"{vector_backend}_*")
            dirs = sorted(glob.glob(pattern), reverse=True)
            if not dirs:
                raise FileNotFoundError(f"No vector store found for backend '{vector_backend}'")
            self.vector_dir = Path(dirs[0])

        self.index, self.metas = self.load_vector_store()

    def load_vector_store(self):
        index_path = self.vector_dir / "index.faiss"
        meta_path = self.vector_dir / "metadata.jsonl"

        index = faiss.read_index(str(index_path))

        with open(meta_path, "r", encoding="utf-8") as f:
            metas = [json.loads(l) for l in f]

        return index, metas

    def embed_query(self, query: str):
        """Compute embedding for the query."""
        if self.embedding_provider == "local":
            model = SentenceTransformer(self.local_model)
            vec = model.encode([query], convert_to_numpy=True)[0].astype("float32")
        elif self.embedding_provider == "openai":
            resp = openai.Embedding.create(model=self.openai_model, input=query)
            vec = np.array(resp["data"][0]["embedding"], dtype="float32")
        else:
            raise ValueError(f"Unknown embedding provider: {self.embedding_provider}")

        vec = vec.reshape(1, -1)
        faiss.normalize_L2(vec)
        return vec

    def retrieve_chunks(self, query: str, top_k: int = TOP_K):
        """Retrieve top_k chunks from vector store."""
        q_vec = self.embed_query(query)
        distances, indices = self.index.search(q_vec, top_k)

        retrieved = []
        used_ids = []

        for idx in indices[0]:
            if idx < 0:
                continue
            meta = self.metas[idx]
            snippet = textwrap.shorten(meta["text"], 400)
            retrieved.append(
                f"ID: {meta['id']} | URL: {meta.get('url')} | "
                f"District: {meta.get('district')} | Status: {meta.get('status')}\n{snippet}"
            )
            used_ids.append(meta["id"])

        return retrieved, used_ids

    def answer_query(self, query: str, top_k: int = TOP_K):
        """Retrieve context and call LLM."""
        retrieved, used_ids = self.retrieve_chunks(query, top_k)
        context = "\n\n".join(retrieved)

        prompt = f"""You are a civic assistant. Use the following retrieved issues to answer the user’s question. If you don’t know the answer, say so. Always include issue IDs and URLs if relevant.

Context:
{context}

Question:
{query}
"""

        if self.embedding_provider == "openai":
            client = openai.OpenAI()
            resp = client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=512,
            )
            answer = resp.choices[0].message.content.strip()
            return {"answer": answer, "used_ids": used_ids, "raw": resp}
        else:
            # Local fallback: just return concatenated retrieved context as "answer"
            return {"answer": context, "used_ids": used_ids, "raw": None}


def main():
    parser = argparse.ArgumentParser(description="RAG query for civic issues")
    parser.add_argument("--query", required=True, help="User query")
    parser.add_argument("--vector_backend", choices=["faiss", "chroma"], required=True,
                        help="Vector store backend to use")
    parser.add_argument("--vector_path", default=None,
                        help="Optional exact path to vector store folder")
    parser.add_argument("--embedding_provider", choices=["local", "openai"], required=True,
                        help="Embedding provider: 'local' uses Sentence-Transformers, 'openai' uses OpenAI API")
    parser.add_argument("--local_model", default="distiluse-base-multilingual-cased-v2",
                        help="Local embeddings model if using 'local'")
    parser.add_argument("--openai_model", default="text-embedding-3-small",
                        help="OpenAI embeddings model if using 'openai'")
    parser.add_argument("--top_k", type=int, default=TOP_K, help="Number of chunks to retrieve")
    args = parser.parse_args()

    client = RAGClient(
        vector_backend=args.vector_backend,
        embedding_provider=args.embedding_provider,
        vector_path=args.vector_path,
        local_model=args.local_model,
        openai_model=args.openai_model,
    )

    result = client.answer_query(args.query, top_k=args.top_k)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
