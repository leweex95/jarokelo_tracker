import argparse
import glob
import json
import os
import textwrap
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from levisllmhub.chatgpt import chatgpt as chatgpt_client


class RAGClient:
    def __init__(self, vector_backend: str, embedding_provider: str,
                 vector_path: str = None,
                 local_model: str = "distiluse-base-multilingual-cased-v2",
                 answering_llm: str = "chatgpt", 
                 vector_base_dir: str = "data/vector_store"):

        self.vector_backend = vector_backend
        self.embedding_provider = embedding_provider
        self.local_model = local_model
        self.answering_llm = answering_llm

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
        else:
            raise ValueError(f"Unknown embedding provider: {self.embedding_provider}")

        vec = vec.reshape(1, -1)
        faiss.normalize_L2(vec)
        return vec

    def retrieve_chunks(self, query: str, top_k: int):
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

    def answer_query(self, query: str, top_k: int, headless: bool):
        """Retrieve context and call LLM."""
        retrieved, used_ids = self.retrieve_chunks(query, top_k)
        context = "\n\n".join(retrieved)

        prompt = f"""You are a civic assistant. Use the following retrieved issues to answer the user’s question. If you don’t know the answer, say so. Always include issue IDs and URLs if relevant. 
            
            Context: 
            {context}
            
            Question: {query}
        """

        if self.answering_llm.lower() == "chatgpt":
            answer = chatgpt_client.ask_chatgpt(prompt=prompt, headless=headless)
            return {"answer": answer, "used_ids": used_ids}
        else:
            # Local fallback: just return concatenated retrieved context as "answer"
            return {"answer": context, "used_ids": used_ids}


def main():

    parser = argparse.ArgumentParser(description="RAG query for civic issues")
    parser.add_argument("--query", required=True, help="User query")
    parser.add_argument("--vector-backend", choices=["faiss", "chroma"], required=True,
                        help="Vector store backend to use")
    parser.add_argument("--vector-path", default=None,
                        help="Optional exact path to vector store folder")
    parser.add_argument("--embedding-provider", choices=["local"], required=True,
                        help="Embedding provider: 'local' uses Sentence-Transformers.")
    parser.add_argument("--local-model", default="distiluse-base-multilingual-cased-v2",
                        help="Local embeddings model if using 'local'")
    parser.add_argument("--top_k", type=int, default=5, help="Number of chunks to retrieve (default: 5)")
    parser.add_argument("--headless", type=lambda x: x.lower() == "true", default=True, help="Run answer generation in headless mode or not (default: true)")

    args = parser.parse_args()

    client = RAGClient(
        vector_backend=args.vector_backend,
        embedding_provider=args.embedding_provider,
        vector_path=args.vector_path,
        local_model=args.local_model,
    )

    result = client.answer_query(args.query, top_k=args.top_k, headless=args.headless)
    print("Raw result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\n"*5, "="*100)
    print("FINAL RAG OUTPUT:")
    print(result["answer"])


if __name__ == "__main__":
    main()
