import glob, os
from pathlib import Path

# --- Paths ---
EXPERIMENTS_DIR = Path(__file__).parents[1]
EXPERIMENTS_RESULTS_DIR = EXPERIMENTS_DIR / "results"
DOCS_DIR = Path(__file__).parents[2] / "docs"
DOCS_EXPERIMENTS_DIR = DOCS_DIR / "experiments"
DOCS_EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_HTML = DOCS_EXPERIMENTS_DIR / "embeddings_comparison_results_aggregated.html"


# --- Find all historical embedding results ---
md_files = sorted(
    glob.glob(str(EXPERIMENTS_RESULTS_DIR / "embeddings_comparison_results_*.md")),
    reverse=True
)

html_parts = [
    """<!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <title>Embedding Comparison</title>
    <link rel="stylesheet" href="../style.css">
    </head>
    <body>
    <header>
      <h1>Embedding Comparison</h1>
      <p><a href="../index.html">← Back to Dashboard</a></p>
    </header>
    <main>
    <h2>Corpus Info</h2>
    """
]

# --- Latest run first ---
if md_files:
    latest_file = md_files[0]

    # parse corpus info from latest MD
    with open(latest_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("## Corpus Info"):
            start_idx = i
        elif start_idx is not None and line.strip() == "---":
            end_idx = i
            break

    if start_idx is not None and end_idx is not None:
        corpus_info_text = "".join(lines[start_idx+1:end_idx]).strip()
    else:
        corpus_info_text = "Failed to parse corpus info."

    # inject corpus info
    html_parts.append(f"<pre id='corpus_info'>{corpus_info_text}</pre>\n")

    # include latest run full content
    html_parts.append(f"<h3>Latest Run: {os.path.basename(latest_file)}</h3>\n<pre>{''.join(lines)}</pre>\n")

# --- Historical runs in collapsible <details> ---
for md_file in md_files[1:]:
    with open(md_file, "r", encoding="utf-8") as f:
        html_parts.append(
            f"<details><summary>{os.path.basename(md_file)}</summary>\n<pre>{f.read()}</pre></details>\n"
        )

# --- Close HTML ---
html_parts.append("</main></body></html>")

# Write aggregated HTML
OUTPUT_HTML.write_text("".join(html_parts), encoding="utf-8")
print(f"Aggregator finished → {OUTPUT_HTML}")