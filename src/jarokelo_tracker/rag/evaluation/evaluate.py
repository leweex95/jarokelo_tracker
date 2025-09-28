import json
import subprocess
from pathlib import Path
from tqdm import tqdm
from datetime import datetime
import argparse
import sys
import logging
from typing import List, Dict, Tuple, Any

from jarokelo_tracker.rag.pipeline import retrieve_chunks
from jarokelo_tracker.rag.retrieval import load_vector_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def get_git_commit_hash():
    commit_hash = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], 
        cwd=Path(__file__).parent, 
        text=True
    ).strip()
    return commit_hash

def load_eval_set(path: str) -> List[Dict[str, Any]]:
    """Load the evaluation set from a JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load eval set from {path}: {e}")
        sys.exit(1)

def aggregate_metrics(results: List[Dict[str, Any]], top_k: int) -> Tuple[Dict[str, Any], str]:
    """Aggregate hit rate, recall@k, and precision@k metrics."""
    hit_rate: float = sum(r["hit"] for r in results) / len(results) if results else 0
    avg_recall: float = sum(r["recall@k"] for r in results) / len(results) if results else 0
    avg_precision: float = sum(r["precision@k"] for r in results) / len(results) if results else 0
    dt_str: str = datetime.now().strftime("%Y%m%d_%H%M")
    summary: Dict[str, Any] = {
        "datetime": dt_str,
        "hit_rate": hit_rate,
        "avg_recall@k": avg_recall,
        "avg_precision@k": avg_precision,
        "results": results,
        "commit_hash": get_git_commit_hash()
    }
    logging.info(f"Hit rate: {hit_rate:.2f}, Avg recall@{top_k}: {avg_recall:.2f}, Avg precision@{top_k}: {avg_precision:.2f}")
    return summary, dt_str

def save_results(summary: Dict[str, Any], save_dir: str, dt_str: str, lang: str) -> None:
    """Save the evaluation results to a JSON file."""
    save_dir_path: Path = Path(save_dir)
    save_dir_path.mkdir(parents=True, exist_ok=True)
    filename: str = f"rag_retrieval_eval_results_{lang}_{dt_str}.json"
    save_path: Path = save_dir_path / filename
    try:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        logging.info(f"Results saved to: {save_path}")
    except Exception as e:
        logging.error(f"Failed to save results: {e}")
        sys.exit(1)

def main(
    eval_set_path: str,
    vector_backend: str,
    embedding_provider: str,
    vector_path: str,
    local_model: str,
    vector_base_dir: str,
    save_dir: str,
    topk_list: list,
    lang: str
) -> None:
    logging.info("Running RAG retrieval evaluation with the following arguments:")
    logging.info(f"  eval_set_path: {eval_set_path}")
    logging.info(f"  vector_backend: {vector_backend}")
    logging.info(f"  embedding_provider: {embedding_provider}")
    logging.info(f"  vector_path: {vector_path}")
    logging.info(f"  local_model: {local_model}")
    logging.info(f"  vector_base_dir: {vector_base_dir}")
    logging.info(f"  save_dir: {save_dir}")
    logging.info(f"  top_k: {topk_list}")
    logging.info(f"  lang: {lang}")

    if not Path(eval_set_path).exists():
        logging.error(f"Eval set path does not exist: {eval_set_path}")
        sys.exit(1)
    if not Path(vector_base_dir).exists():
        logging.error(f"Vector base dir does not exist: {vector_base_dir}")
        sys.exit(1)

    eval_set: List[Dict[str, Any]] = load_eval_set(eval_set_path)
    try:
        index, metas = load_vector_store(vector_backend, vector_path, vector_base_dir)
    except Exception as e:
        logging.error(f"Failed to load vector store: {e}")
        sys.exit(1)

    all_k_results = {}
    dt_str = datetime.now().strftime("%Y%m%d_%H%M")
    for top_k in topk_list:
        logging.info(f"Running evaluation for top_k={top_k}")
        results: List[Dict[str, Any]] = []
        for item in tqdm(eval_set, desc=f"Evaluating Retrieval ({lang}, k={top_k})", unit="query", disable=not sys.stdout.isatty()):
            query: str = item["query"].get(lang)
            if not query:
                continue
            gold_doc_ids: set = set(item["gold_doc_ids"])
            try:
                retrieved, used_ids = retrieve_chunks(
                    index, metas, query, embedding_provider, local_model, top_k
                )
            except Exception as e:
                logging.warning(f"Retrieval failed for query '{query}': {e}")
                continue
            retrieved_ids: set = set(used_ids)
            hit: bool = bool(retrieved_ids & gold_doc_ids)
            recall: float = len(retrieved_ids & gold_doc_ids) / len(gold_doc_ids) if gold_doc_ids else 0
            precision: float = len(retrieved_ids & gold_doc_ids) / len(retrieved_ids) if retrieved_ids else 0
            results.append({
                "query": query,
                "gold_doc_ids": list(gold_doc_ids),
                "retrieved_ids": list(retrieved_ids),
                "hit": hit,
                "recall@k": recall,
                "precision@k": precision
            })
        summary, _ = aggregate_metrics(results, top_k)
        all_k_results[f"k={top_k}"] = summary

    # Save all results in one file
    save_dir_path: Path = Path(save_dir)
    save_dir_path.mkdir(parents=True, exist_ok=True)
    filename: str = f"rag_retrieval_eval_results_{lang}_{dt_str}.json"
    save_path: Path = save_dir_path / filename
    try:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(all_k_results, f, indent=2, ensure_ascii=False)
        logging.info(f"Results saved to: {save_path}")
    except Exception as e:
        logging.error(f"Failed to save results: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval")
    parser.add_argument(
        "--eval-set-path",
        type=str,
        default="data/eval/eval_set.json",
        help="Path to the evaluation set JSON file"
    )
    parser.add_argument(
        "--vector-backend",
        type=str,
        choices=["faiss", "chroma"],
        default="faiss",
        help="Vector store backend to use"
    )
    parser.add_argument(
        "--embedding-provider",
        type=str,
        choices=["local"],
        default="local",
        help="Embedding provider to use"
    )
    parser.add_argument(
        "--vector-path",
        type=str,
        default=None,
        help="Path to the vector store file (if needed)"
    )
    parser.add_argument(
        "--local-model",
        type=str,
        default="distiluse-base-multilingual-cased-v2",
        help="Local embedding model name"
    )
    parser.add_argument(
        "--vector-base-dir",
        type=str,
        default="data/vector_store",
        help="Base directory for vector store"
    )
    parser.add_argument(
        "--save-dir",
        type=str,
        default="experiments/results/retrieval_eval",
        help="Directory to save the RAG retrieval evaluation results"
    )
    parser.add_argument(
        "--topk",
        type=str,
        default="5",
        help="Single integer or a comma-separated list of top-k values to evaluate (e.g. '1,5,10')"
    )
    parser.add_argument(
        "--lang",
        type=str,
        choices=["en", "hu"],
        default="en",
        help="Language of queries to evaluate (en or hu)"
    )
    args = parser.parse_args()
    args.topk = [int(k) for k in args.topk.split(",")]
    main(
        args.eval_set_path,
        args.vector_backend,
        args.embedding_provider,
        args.vector_path,
        args.local_model,
        args.vector_base_dir,
        args.save_dir,
        args.topk,
        args.lang
    )
