import os
import re
import glob
from pathlib import Path
from datetime import datetime
import markdown


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
      <h1>Embedding Comparison</h1><br>
      <p><strong>This evaluation tests how well different embedding models represent the corpus so that a RAG system can retrieve the most relevant documents for a given query.</strong>
      By comparing the top results for sample queries, you see which model produces embeddings that best capture meaning and context in the data,
      <strong>directly impacting the quality of answers your RAG system will generate.</strong></p><br>
      <p><a href="../index.html">← Back to Dashboard</a></p>
    </header>
    <main>
    """
]

# --- Latest run first ---
if md_files:
    latest_file = md_files[0]

    # parse corpus info from latest MD
    with open(latest_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # extract datetime from filename: embeddings_comparison_results_YYYYMMDD_HHMM.md
    match = re.search(r"(\d{8}_\d{4})", latest_file)
    if match:
        dt = datetime.strptime(match.group(1), "%Y%m%d_%H%M")
        friendly_title = f"{dt.strftime('%Y-%m-%d %H:%M')} - Embedding comparison on 200 entries"
    else:
        friendly_title = "Latest embedding comparison"

    # clickable link
    github_url = f"https://github.com/leweex95/jarokelo_tracker/blob/master/experiments/results/{os.path.basename(latest_file)}"

    html_parts.append(f"<h2>{friendly_title}</h2>\n")
    html_parts.append(f"<p>Link: <a href='{github_url}' target='_blank'>{os.path.basename(latest_file)}</a></p>\n")

    # parse corpus info into bullets
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

    info_lines = [line.strip().lstrip("*").strip() for line in corpus_info_text.splitlines() if line.strip()]
    html_parts.append(f"<h3>Corpus info</h3>\n<ul>\n{''.join(f'<li>{line}</li>' for line in info_lines)}\n</ul>\n")

    # Remaining content (Embedding comparison results) rendered as Markdown
    content_lines = []
    in_corpus_section = False
    for line in lines:
        if line.strip().startswith("## Corpus Info"):
            in_corpus_section = True
        elif in_corpus_section and line.strip() == "---":
            in_corpus_section = False
        elif not in_corpus_section:
            content_lines.append(line)

    # Remove only the "## Corpus Info" heading lines, keep other headings (model names, etc.)
    content_lines = [line for line in content_lines if not line.strip().startswith("## Corpus Info")]

    # Convert H2 headings to H3
    content_lines = [re.sub(r"^## ", "### ", line) for line in content_lines]

    html_parts.append("<h3>Embedding comparison results</h3>\n")
    html_parts.append(markdown.markdown(''.join(content_lines), extensions=['tables', 'fenced_code']))


# --- Historical runs in collapsible <details> with clickable header & corpus info
for md_file in md_files[1:]:
    with open(md_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # parse corpus info
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("## Corpus Info"):
            start_idx = i
        elif start_idx is not None and line.strip() == "---":
            end_idx = i
            break

    if start_idx is not None and end_idx is not None:
        hist_corpus_info = "".join(lines[start_idx+1:end_idx]).strip()
    else:
        hist_corpus_info = "Failed to parse corpus info."

    github_url = f"https://github.com/leweex95/jarokelo_tracker/blob/master/experiments/results/{os.path.basename(md_file)}"
    
    # parse historical corpus info into bullets
    hist_info_lines = [line.strip().lstrip("*").strip() for line in hist_corpus_info.splitlines() if line.strip()]
    hist_info_bullets = "\n".join(f"• {line}" for line in hist_info_lines)

    # remove the ## Corpus Info section from full content
    hist_content_lines = []
    in_corpus_section = False
    for line in lines:
        if line.strip().startswith("## Corpus Info"):
            in_corpus_section = True
        elif in_corpus_section and line.strip() == "---":
            in_corpus_section = False
        elif not in_corpus_section:
            hist_content_lines.append(line)

    # Remove only the "## Corpus Info" heading lines
    hist_content_lines = [line for line in hist_content_lines if not line.strip().startswith("## Corpus Info")]

    hist_content_lines = [re.sub(r"^## ", "### ", line) for line in hist_content_lines]

    markdown_content = markdown.markdown(''.join(hist_content_lines), extensions=['tables', 'fenced_code'])


    html_parts.append(
        f"<details><summary><a href='{github_url}' target='_blank'>{os.path.basename(md_file)}</a></summary>\n"
        f"<h4>Corpus Info</h4>\n<ul>\n{''.join(f'<li>{line}</li>' for line in hist_info_lines)}\n</ul>\n"
        f"{markdown_content}\n"
        f"</details>\n"
    )


# --- Close HTML ---
html_parts.append("</main></body></html>")

# Write aggregated HTML
OUTPUT_HTML.write_text("".join(html_parts), encoding="utf-8")
print(f"Aggregator finished → {OUTPUT_HTML}")