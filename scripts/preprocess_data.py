import os
import re
import glob
import json
import locale
import pandas as pd
from datetime import datetime

RAW_PATTERN = "data/raw/*.jsonl"
PROCESSED_DIR = "data/processed"
CHUNK_TARGET_TOKENS = 400
DATE_FORMAT = "%Y-%m-%d"

locale.setlocale(locale.LC_TIME, "hu_HU.UTF-8")

os.makedirs(PROCESSED_DIR, exist_ok=True)


def load_raw_files(pattern: str) -> pd.DataFrame:
    """Load and concatenate all JSONL files matching the glob pattern."""
    files = sorted(glob.glob(pattern))
    dfs = [pd.read_json(f, lines=True) for f in files]
    return pd.concat(dfs, ignore_index=True)


# extract district from address if district column is missing
def extract_district(row):
    if pd.notna(row.get("district")) and row.get("district") != "":
        return row["district"]
    addr = row.get("address", "")
    if addr:
        parts = [p.strip() for p in addr.split(",")]
        if len(parts) > 1:
            return parts[1]  # "III. kerület"
    return "Unknown"


def parse_hu_date(d):
    if pd.isna(d):
        return pd.NaT
    try:
        return datetime.strptime(d, "%Y. %B %d.")
    except:
        return pd.NaT


def normalize_text(df: pd.DataFrame) -> pd.DataFrame:
    """Clean description text and normalize district/date fields."""
    df["description"] = (
        df["description"]
        .astype(str)
        .str.replace(r"<[^>]+>", " ", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.lower()
    )
    df = df[df["description"].str.strip() != ""]
    df["district"] = df.apply(extract_district, axis=1)
    df["date"] = df["date"].apply(parse_hu_date)
    df["original_id"] = df.get("url", pd.Series(df.index.astype(str)))
    return df


def split_sentences(text: str) -> list[str]:
    """Split text into sentences using punctuation."""
    return re.split(r"(?<=[.!?])\s+", text)


def chunk_text(text: str, target: int = CHUNK_TARGET_TOKENS) -> list[str]:
    """Split text into chunks aiming at target token size (approx)."""
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


def build_chunks(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """Create chunks with metadata, return (chunks, long_entries)."""
    chunks_out, long_entries = [], []

    for _, row in df.iterrows():
        chunks = chunk_text(row["description"])
        if len(chunks) > 1:
            long_entries.append({
                "original_id": row["original_id"],
                "url": row.get("url", None),
                "num_chunks": len(chunks),
            })
        for i, ch in enumerate(chunks):
            cid = f"{row['original_id']}__{i}"
            metadata = {
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

            chunks_out.append({"id": cid, "text": ch, "metadata": metadata})

    return chunks_out, long_entries


def save_chunks(chunks: list[dict], out_path: str) -> None:
    """Save chunks as JSONL."""
    with open(out_path, "w", encoding="utf8") as fh:
        for item in chunks:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")


def main() -> None:
    df = load_raw_files(RAW_PATTERN)
    df = normalize_text(df)
    chunks_out, long_entries = build_chunks(df)

    chunks_path = os.path.join(PROCESSED_DIR, "issues_chunks.jsonl")
    save_chunks(chunks_out, chunks_path)

    print(f"Saved {len(chunks_out)} chunks to {chunks_path}")
    if long_entries:
        print("\nEntries split into multiple chunks:")
        for entry in long_entries:
            print(f"- {entry['original_id']} ({entry['url']}): {entry['num_chunks']} chunks")
    else:
        print("No entries needed splitting into multiple chunks.")


if __name__ == "__main__":
    main()
