"""
Utility to get the size of the corpus and the date duration (i.e., earliest and latest available dates)
for reporting purposes. This information will be reflected on the Github Pages page, allowing us to
track the evolution of our RAG system against different evaluation metrics and hyperparameters, as the
scraped corpus size grows.
"""

import pandas as pd


def get_corpus_info(df: pd.DataFrame, eval_corpus: list):
    """
    Returns a string with corpus info for embedding results Markdown.
    """
    
    # Extract dates from metadata
    dates = df["metadata"].apply(lambda m: m.get("date", None)).dropna()
    dates = dates.sort_values()
    
    start_date = dates.iloc[0]
    end_date = dates.iloc[-1] 
    
    return (
        f"**Full corpus size:** {len(df)}\n"
        f"**Eval corpus size:** {len(eval_corpus)}\n"
        f"**Date range:** {start_date} → {end_date}\n"
    )
