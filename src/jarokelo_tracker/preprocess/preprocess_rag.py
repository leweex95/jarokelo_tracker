import re
import os
import pandas as pd
from preprocess_utils import load_raw_files, normalize_text, save_jsonl, DATE_FORMAT

RAW_PATTERN = "data/raw/*.jsonl"
OUTPUT_DIR = "data/processed/rag"
CHUNK_TARGET_TOKENS = 400


def split_sentences(text: str) -> list[str]:
    return re.split(r"(?<=[.!?])\s+", text)

def chunk_text(text: str, target: int = CHUNK_TARGET_TOKENS) -> list[str]:
    sents = split_sentences(text)
    chunks, cur, cur_len = [], [], 0
    for s in sents:
        t_len = len(s.split())
        if cur_len + t_len > target and cur:
            chunks.append(" ".join(cur).strip())
            cur, cur_len = [s], t_len
        else:
            cur.append(s)
            cur_len += t_len
    if cur:
        chunks.append(" ".join(cur).strip())
    return chunks

def build_chunks(df):
    chunks_out = []
    for _, row in df.iterrows():
        for i, ch in enumerate(chunk_text(row["description"])):
            cid = f"{row['original_id']}__{i}"
            chunks_out.append({
                "id": cid,
                "text": ch,
                "metadata": {
                    "original_id": row["original_id"],
                    "title": row.get("title", ""),
                    "district": row.get("district", "Unknown"),
                    "status": row.get("status", ""),
                    "date": row["date"].strftime(DATE_FORMAT) if pd.notna(row["date"]) else None,
                    "url": row.get("url", None),
                    "author": row.get("author", ""),
                    "author_profile": row.get("author_profile", ""),
                    "category": row.get("category", ""),
                    "institution": row.get("institution", ""),
                    "supporter": row.get("supporter", ""),
                    "address": row.get("address", ""),
                    "images": row.get("images", []),
                }
            })
    return chunks_out

def main():
    df = load_raw_files(RAW_PATTERN)
    df = normalize_text(df)
    chunks = build_chunks(df)
    save_jsonl(chunks, os.path.join(OUTPUT_DIR, "issues_chunks.jsonl"))
    print(f"Saved {len(chunks)} RAG chunks to {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
