"""
Assembles nightly retrieval evaluation results into a single Markdown report with plots.
Appends the latest run to the top of the table and highlights it.
Usage:
    python assemble_retrieval_reports.py --results-dir ... --img-dir ... --report-path ...
"""

import json
from pathlib import Path
from datetime import datetime
import plotly.graph_objects as go
from plotly.graph_objects import Figure, Bar
import argparse
import logging
import sys

__all__ = ["update_retrieval_eval_report"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def _save_metric_plot_plotly(values, k_values, metric_name, date_str, out_dir) -> Path:
    """Save a plotly bar chart for Precision@k and Recall@k."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    fig = Figure()
    fig.add_trace(Bar(x=k_values, y=values, name=metric_name))
    fig.update_layout(
        title=f"{metric_name}@k",
        xaxis_title="k",
        yaxis_title=metric_name,
        yaxis=dict(range=[0, 1]),
        width=350,
        height=200,
        margin=dict(l=10, r=10, t=30, b=10)
    )
    img_path = Path(out_dir) / f"{metric_name}_{date_str}.svg"
    fig.write_image(str(img_path))
    return img_path

def _load_latest_run(results_dir, img_dir):
    """Load the most recent evaluation run and generate metric plots.
    Fails if no evaluation result was found in the specified results_dir location."""

    files = sorted(Path(results_dir).glob("rag_retrieval_eval_results_*.json"), reverse=True)
    if not files:
        logging.warning("No result files found.")
        return None
    file = files[0]  # Most recent file
    try:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logging.error(f"Failed to load {file}: {e}")
        return None
    dt = next(iter(data.values())).get("datetime", "")
    commit_hash = next(iter(data.values())).get("commit_hash", "unknown")

    k_values = []
    recall_values = []
    precision_values = []
    for k, summary in sorted(data.items(), key=lambda x: int(x[1].get("top_k", x[0].replace("k=", "")))):
        k_val = summary.get("top_k", int(k.replace("k=", "")))
        k_values.append(k_val)
        recall_values.append(summary.get("avg_recall@k", 0))
        precision_values.append(summary.get("avg_precision@k", 0))

    # make img paths relative to docs/ (i.e., drop the beginning docs/ from the relative path or else GH Pages won't render the images)
    recall_img_path = _save_metric_plot_plotly(recall_values, k_values, "Recall", dt, img_dir).relative_to("docs")
    precision_img_path = _save_metric_plot_plotly(precision_values, k_values, "Precision", dt, img_dir).relative_to("docs")

    # join URL as strings
    base_url = "https://leweex95.github.io/jarokelo_tracker/"
    recall_img_rel = base_url + str(recall_img_path).replace("\\", "/")
    precision_img_rel = base_url + str(precision_img_path).replace("\\", "/")
    
    json_results_base_url = "https://github.com/leweex95/jarokelo_tracker/tree/master/"
    json_results_full_url = json_results_base_url + (Path(args.results_dir) / file.name).as_posix()

    return {
        "date": dt,
        "recall_img": str(recall_img_rel).replace("\\", "/"),
        "precision_img": str(precision_img_rel).replace("\\", "/"),
        "details": str(json_results_full_url).replace("\\", "/"),
        "commit_hash": commit_hash
    }

def _parse_existing_rows(report_path):
    """Parse the existing HTML report table rows, removing old highlights and header lines."""
    if not Path(report_path).exists():
        return []
    with open(report_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    # Extract table rows only
    in_table = False
    rows = []
    for line in lines:
        if "<table" in line:
            in_table = True
        elif "</table>" in line:
            in_table = False
        elif in_table and "<tr" in line:
            # Skip header rows
            if "<th>" in line:
                continue
            rows.append(line.replace(' style="background-color: #ffeeba;"', ''))
    return rows

def _generate_row(run, highlight=False):
    """Generate a table row for a run, optionally highlighted."""
    style = ' style="background-color: #ffeeba;"' if highlight else ""
    td_style = ' style="padding:8px;vertical-align:middle;text-align:center;"'
    return (
        f'<tr{style}>'
        f'<td{td_style}>{run["date"]}</td>'
        f'<td{td_style}><img src="{run["recall_img"]}" width="200" height="120"></td>'
        f'<td{td_style}><img src="{run["precision_img"]}" width="200" height="120"></td>'
        f'<td{td_style}><a href="{run["details"]}">JSON</a></td>'
        f'<td{td_style}>{run["commit_hash"]}</td>'
        f'</tr>\n'
    )

def update_retrieval_eval_report(latest_run, report_path):
    """Insert the latest run at the top of the HTML report and update the 'report updated' info."""
    rows = _parse_existing_rows(report_path)
    new_row = _generate_row(latest_run, highlight=True)
    # Remove any previous "Report updated" lines
    rows = [row for row in rows if "_Report updated:" not in row]
    # Insert new row at the top (after header)
    header_row = (
        '<tr><th>Date</th><th>Recall@k</th><th>Precision@k</th><th>Details</th><th>Commit hash</th></tr>\n'
    )
    # Remove header if present
    rows = [row for row in rows if header_row.strip() not in row.strip()]
    # Compose HTML
    dt_now = datetime.now().strftime('%Y-%m-%d %H:%M')
    html = f"""<!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <title>RAG Retrieval Evaluation</title>
        <link rel="stylesheet" href="../style.css">
        </head>
        <body>
        <header>
        <h1>RAG Retrieval Evaluation</h1><br>
        <p><strong>This evaluation tests the performance of our Retrieval-Augmented Generation pipeline for answering questions about reported issues.</strong>
        Explore how different models, top-K values, and prompts affect retrieval quality. The charts below show recall@k and precision@k for each test run.</p><br>
        <p><a href="../index.html">← Back to Dashboard</a></p>
        </header>
        <main>
        <table>
            {header_row}
            {new_row}
            {''.join(rows)}
        </table>
        <p style="margin-top:2em; color:#666;"><em>Report updated: {dt_now}</em></p>
        </main>
        </body>
        </html>
        """
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)
    logging.info(f"Updated HTML report at {report_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update single retrieval evaluation markdown report.")
    parser.add_argument("--results-dir", type=str, default="experiments/results/retrieval_eval", help="Directory with eval output files (input to the aggregator).")
    parser.add_argument("--img-dir", type=str, default="docs/experiments/imgs", help="Directory to save plots (inside docs/ for Github Pages).")
    parser.add_argument("--report-path", type=str, default="docs/experiments/retrieval_eval_report.html", help="Path to the HTML report (inside docs/ for Github Pages).")
    args = parser.parse_args()

    # Ensure output directories exist
    Path(args.results_dir).mkdir(parents=True, exist_ok=True)
    Path(args.img_dir).mkdir(parents=True, exist_ok=True)
    Path(args.report_path).parent.mkdir(parents=True, exist_ok=True)

    latest_run = _load_latest_run(args.results_dir, args.img_dir)
    if latest_run:
        update_retrieval_eval_report(latest_run, args.report_path)
        logging.info("Report last updated successfully.")
        sys.exit(0)
    else:
        logging.error("No latest run found, report not updated.")
        sys.exit(1)
