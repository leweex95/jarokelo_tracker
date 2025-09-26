import argparse
import json
import textwrap

from jarokelo_tracker.rag.retrieval import load_vector_store
from jarokelo_tracker.rag.embedding import embed_query
from jarokelo_tracker.rag.llm import answer_with_llm
from jarokelo_tracker.rag.prompts import build_prompt


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

def answer_query(query, top_k, headless, vector_backend, embedding_provider, vector_path, local_model, answering_llm, vector_base_dir):
    index, metas = load_vector_store(vector_backend, vector_path, vector_base_dir)
    retrieved, used_ids = retrieve_chunks(index, metas, query, embedding_provider, local_model, top_k)
    context = "\n\n".join(retrieved)
    prompt = build_prompt(context, query)
    answer = answer_with_llm(prompt, answering_llm, headless)
    if answer is None:
        answer = context
    return {"answer": answer, "used_ids": used_ids}

def main():
    parser = argparse.ArgumentParser(description="RAG query for civic issues")
    parser.add_argument("--query", required=True, help="User query")
    parser.add_argument("--vector-backend", choices=["faiss", "chroma"], required=True)
    parser.add_argument("--vector-path", default=None)
    parser.add_argument("--embedding-provider", choices=["local"], required=True)
    parser.add_argument("--local-model", default="distiluse-base-multilingual-cased-v2")
    parser.add_argument("--top_k", type=int, default=5)
    parser.add_argument("--headless", type=lambda x: x.lower() == "true", default=True)
    parser.add_argument("--answering-llm", default="chatgpt")
    parser.add_argument("--vector-base-dir", default="data/vector_store")
    args = parser.parse_args()

    result = answer_query(
        args.query, args.top_k, args.headless,
        args.vector_backend, args.embedding_provider,
        args.vector_path, args.local_model,
        args.answering_llm, args.vector_base_dir
    )
    print("Raw result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("\n"*5, "="*100)
    print("FINAL RAG OUTPUT:")
    print(result["answer"])

if __name__ == "__main__":
    main()
