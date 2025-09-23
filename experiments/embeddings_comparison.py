import argparse
import pandas as pd
from datetime import datetime
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
from utils.get_corpus_info import get_corpus_info

# --- CLI Arguments ---
def parse_args():
    parser = argparse.ArgumentParser(description="Compare sentence embedding models on a corpus.")
    parser.add_argument("--sample-size", type=int, default=200, help="Number of corpus samples to use.")
    parser.add_argument("--top-n", type=int, default=3, help="Number of top results to retrieve per query.")
    return parser.parse_args()

args = parse_args()

# --- Config ---
SAMPLE_SIZE = args.sample_size
TOP_N = args.top_n

# --- Paths ---
DATA_PATH = Path(__file__).resolve().parents[1] / "data/processed/rag/issues_chunks.jsonl"
OUT_PATH = Path(__file__).parent / "results" / f"embeddings_comparison_results_{datetime.now():%Y%m%d_%H%M}.md"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# --- Queries ---
queries = [
    ("kátyú az úton", "pothole in the road"),
    ("hibás közvilágítás", "broken streetlight"),
    ("csőtörés a főutcán", "water pipe burst on the main street"),
    # ("szemét nincs elszállítva", "garbage not collected"),
    # ("illegális hulladéklerakó", "illegal dumping site"),
    # ("zajos építkezés éjszaka", "noisy construction at night"),
    # ("buszmegálló megrongálva", "damaged bus stop"),
    # ("nem működik a jelzőlámpa", "traffic light not working"),
    # ("veszélyes zebra", "dangerous pedestrian crossing"),
    # ("parkban nincs világítás", "no lighting in the park"),
    # ("játszótér karbantartás", "playground maintenance"),
    # ("padok megrongálva", "benches damaged"),
    # ("hajléktalanok az aluljáróban", "homeless people in the underpass"),
    # ("graffitik a falon", "graffiti on the wall"),
    # ("szivárgó csatorna", "leaking sewer"),
    # ("bűz a környéken", "bad smell in the neighborhood"),
]

# --- Models to compare ---
MODELS = {
    # "English-only": [
    #     "sentence-transformers/all-MiniLM-L6-v2",
    #     "sentence-transformers/all-mpnet-base-v2"
    # ],
    # "Multilingual": [
    #     "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    #     "sentence-transformers/distiluse-base-multilingual-cased-v2",
    #     "sentence-transformers/LaBSE"
    # ],
    "Hungarian-only": [
        "SZTAKI-HLT/hubert-base-cc",
        "NYTK/PULI-BERT-Large"
    ]
}

# --- Load corpus ---
with open(DATA_PATH, "r", encoding="utf-8") as f:
    df = pd.read_json(f, lines=True)

corpus = df["text"]
if SAMPLE_SIZE:
    corpus = corpus.sample(SAMPLE_SIZE, random_state=42)
corpus = corpus.tolist()

# --- Compute corpus info string for Markdown ---
corpus_info_md = get_corpus_info(df, corpus)

# --- Experiment ---
results = []
metrics = {}

for category, model_names in MODELS.items():
    for model_name in model_names:
        print(f"Running {model_name}...")
        model = SentenceTransformer(model_name)
        corpus_emb = model.encode(corpus, convert_to_tensor=True, show_progress_bar=True)

        model_metrics = {"top1_scores": [], "topn_scores": [], "all_scores": []}

        for hu, en in queries:
            for q in (hu, en):
                q_emb = model.encode(q, convert_to_tensor=True)
                scores = util.cos_sim(q_emb, corpus_emb)[0]
                top_idx = scores.topk(TOP_N).indices.cpu().numpy()
                top_scores = scores[top_idx].cpu().numpy()
                retrieved = [corpus[i] for i in top_idx]

                # Store results
                results.append({
                    "Model": model_name,
                    "Category": category,
                    "Query": q,
                    "TopN": retrieved,
                    "TopN_Scores": top_scores
                })

                # For metrics
                model_metrics["top1_scores"].append(top_scores[0])
                model_metrics["topn_scores"].extend(top_scores)
                model_metrics["all_scores"].extend(scores.cpu().numpy())

        # Aggregate metrics
        metrics[model_name] = {
            "avg_top1": sum(model_metrics["top1_scores"]) / len(model_metrics["top1_scores"]),
            "avg_topn": sum(model_metrics["topn_scores"]) / len(model_metrics["topn_scores"]),
            "avg_all": sum(model_metrics["all_scores"]) / len(model_metrics["all_scores"]),
        }

# --- Save results ---
friendly_title = f"{datetime.now():%Y-%m-%d %H:%M} - Embedding comparison on {len(corpus)} entries"
md_lines = [
    f"## {friendly_title}\n",
    f"**Sample size:** {SAMPLE_SIZE}, **Top-N:** {TOP_N}\n",
    "### Corpus info\n",
    corpus_info_md,
    "### Embedding comparison results\n",
    "---\n"
]

for category, model_names in MODELS.items():
    for model_name in model_names:
        md_lines.append(f"### {model_name} ({category})\n")
        md_lines.append(f"**Average Top-1 Cosine Similarity:** {metrics[model_name]['avg_top1']:.4f}")
        md_lines.append(f"**Average Top-{TOP_N} Cosine Similarity:** {metrics[model_name]['avg_topn']:.4f}")
        md_lines.append(f"**Average Overall Cosine Similarity:** {metrics[model_name]['avg_all']:.4f}\n")
        md_lines.append(f"| Query | TopN Results | TopN Cosine Scores |")
        md_lines.append(f"|-------|--------------|-------------------|")
        for r in filter(lambda x: x["Model"] == model_name, results):
            topn_str = "<br>".join(r["TopN"])
            scores_str = ", ".join([f"{s:.4f}" for s in r["TopN_Scores"]])
            md_lines.append(f"| {r['Query']} | {topn_str} | {scores_str} |")
        md_lines.append("")

OUT_PATH.write_text("\n".join(md_lines), encoding="utf-8")
print(f"Results saved to {OUT_PATH}")
