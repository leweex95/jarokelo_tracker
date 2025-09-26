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
import argparse
import logging
import sys

__all__ = ["update_retrieval_eval_report"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def _save_metric_plot_plotly(values, k_values, metric_name, date_str, out_dir):
    """Save a plotly bar chart for Precision@k and Recall@k."""
    from plotly.graph_objects import Figure, Bar
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
    k_values = []
    recall_values = []
    precision_values = []
    for k, summary in sorted(data.items(), key=lambda x: int(x[1].get("top_k", x[0].replace("k=", "")))):
        k_val = summary.get("top_k", int(k.replace("k=", "")))
        k_values.append(k_val)
        recall_values.append(summary.get("avg_recall@k", 0))
        precision_values.append(summary.get("avg_precision@k", 0))
    recall_img = _save_metric_plot_plotly(recall_values, k_values, "Recall", dt, img_dir)
    precision_img = _save_metric_plot_plotly(precision_values, k_values, "Precision", dt, img_dir)
    return {
        "date": dt,
        "recall_img": recall_img,
        "precision_img": precision_img,
        "details": str(file)
    }

def _parse_existing_table(report_path):
    """Parse the existing markdown report table, removing old highlights and update lines.
    Note that the most recent evaluation row is always highlighted and arranged on the top."""

    if not Path(report_path).exists():
        # Create header if file does not exist
        return [
            "<table>\n",
            "<tr><th>Date</th><th>Recall@k</th><th>Precision@k</th><th>Details</th></tr>\n"
        ]
    with open(report_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    # Remove previous highlight
    lines = [line.replace(' style="background-color: #ffeeba;"', '') for line in lines]
    return lines

def _generate_row(run, highlight=False):
    """Generate a table row for a run, optionally highlighted.
    Note that only the most recent (and hence, top-most) row is highlighted."""

    style = ' style="background-color: #ffeeba;"' if highlight else ""
    return (
        f'<tr{style}>'
        f'<td>{run["date"]}</td>'
        f'<td><img src="{run["recall_img"]}" width="150"></td>'
        f'<td><img src="{run["precision_img"]}" width="150"></td>'
        f'<td><a href="{run["details"]}">JSON</a></td>'
        f'</tr>\n'
    )

def update_retrieval_eval_report(latest_run, report_path):
    """Insert the latest run at the top of the report and update the 'report updated' 
    info under the table."""
    lines = _parse_existing_table(report_path)
    try:
        header_idx = next(i for i, line in enumerate(lines) if "<tr><th" in line)
    except StopIteration:
        lines = [
            "<table>\n",
            "<tr><th>Date</th><th>Recall@k</th><th>Precision@k</th><th>Details</th></tr>\n"
        ]
        header_idx = 1
    new_row = _generate_row(latest_run, highlight=True)
    lines.insert(header_idx + 1, new_row)
    # Remove any previous "Report updated" lines
    lines = [line for line in lines if not line.strip().startswith("_Report updated:")]
    # Add the latest update info
    lines.append(f"\n_Report updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    logging.info(f"Updated report at {report_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update single retrieval evaluation markdown report.")
    parser.add_argument("--results-dir", type=str, default="experiments/results/retrieval_eval", help="Directory with JSON result files.")
    parser.add_argument("--img-dir", type=str, default="experiments/results/retrieval_eval/imgs", help="Directory to save plots.")
    parser.add_argument("--report-path", type=str, default="experiments/results/retrieval_eval/retrieval_eval_report.md", help="Path to the markdown report.")
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
