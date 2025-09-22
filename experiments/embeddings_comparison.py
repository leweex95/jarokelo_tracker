import pandas as pd
from datetime import datetime
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
from utils.get_corpus_info import get_corpus_info

POC = True

# --- Paths ---
DATA_PATH = Path(__file__).resolve().parents[1] / "data/processed/rag/issues_chunks.jsonl"
OUT_PATH = Path(__file__).parent / "results" / f"embeddings_comparison_results_{datetime.now():%Y%m%d_%H%M}.md"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# --- Queries ---
queries = [
    ("kátyú az úton", "pothole in the road"),
    ("hibás közvilágítás", "broken streetlight"),
    ("csőtörés a főutcán", "water pipe burst on the main street"),
    ("szemét nincs elszállítva", "garbage not collected"),
    ("illegális hulladéklerakó", "illegal dumping site"),
    ("zajos építkezés éjszaka", "noisy construction at night"),
    ("buszmegálló megrongálva", "damaged bus stop"),
    ("nem működik a jelzőlámpa", "traffic light not working"),
    ("veszélyes zebra", "dangerous pedestrian crossing"),
    ("parkban nincs világítás", "no lighting in the park"),
    ("játszótér karbantartás", "playground maintenance"),
    ("padok megrongálva", "benches damaged"),
    ("hajléktalanok az aluljáróban", "homeless people in the underpass"),
    ("graffitik a falon", "graffiti on the wall"),
    ("szivárgó csatorna", "leaking sewer"),
    ("bűz a környéken", "bad smell in the neighborhood"),
]

# --- Models to compare ---
MODELS = {
    "English-only":
        ["sentence-transformers/all-MiniLM-L6-v2",
        #  "sentence-transformers/all-mpnet-base-v2"
        ],
    "Multilingual":
        [
         "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        #  "sentence-transformers/distiluse-base-multilingual-cased-v2",
        #  "sentence-transformers/LaBSE"
        ],
    "Hungarian-only": [
        "SZTAKI-HLT/hubert-base-cc",
        # "NYTK/PULI-BERT-Large"
    ]
}

# --- Load corpus ---
with open(DATA_PATH, "r", encoding="utf-8") as f:
    df = pd.read_json(f, lines=True)

corpus = df["text"]

# For the purposes of a quick proof of concept, let's drastically downscale the corpus
if POC:
    corpus = corpus.sample(200, random_state=42)

corpus = corpus.tolist()

# --- Compute corpus info string for Markdown ---
corpus_info_md = get_corpus_info(df, corpus)

# --- Experiment ---
results = []
for category, model_names in MODELS.items():
    for model_name in model_names:
        print(f"Running {model_name}...")
        model = SentenceTransformer(model_name)
        corpus_emb = model.encode(corpus, convert_to_tensor=True, show_progress_bar=True)

        for hu, en in queries:
            for q in (hu, en):
                q_emb = model.encode(q, convert_to_tensor=True)
                scores = util.cos_sim(q_emb, corpus_emb)[0]
                top_idx = scores.topk(3).indices.cpu().numpy()
                retrieved = [corpus[i] for i in top_idx]

                results.append({
                    "Model": model_name,
                    "Category": category,
                    "Query": q,
                    "Top1": retrieved[0],
                    "Top2": retrieved[1],
                    "Top3": retrieved[2]
                })

# --- Save results ---
friendly_title = f"{datetime.now():%Y-%m-%d %H:%M} - Embedding comparison on {len(corpus)} entries"
md_lines = [f"## {friendly_title}\n", "### Corpus info\n", corpus_info_md,  "### Embedding comparison results\n", "---\n"]


for category, model_names in MODELS.items():
    for model_name in model_names:
        md_lines.append(f"### {model_name} ({category})\n")
        md_lines.append("| Query | Top1 | Top2 | Top3 |")
        md_lines.append("|-------|------|------|------|")
        for r in filter(lambda x: x["Model"]==model_name, results):
            md_lines.append(f"| {r['Query']} | {r['Top1']} | {r['Top2']} | {r['Top3']} |")
        md_lines.append("")

OUT_PATH.write_text("\n".join(md_lines), encoding="utf-8")
print(f"Results saved to {OUT_PATH}")
