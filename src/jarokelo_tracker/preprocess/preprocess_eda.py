import os
import re
import pandas as pd
from preprocess_utils import load_raw_files, normalize_text, save_jsonl, DATE_FORMAT, extract_district

RAW_PATTERN = "data/raw/*.jsonl"
OUTPUT_DIR = "data/processed/eda"
STOPWORDS = {"és", "a", "az", "hogy", "nem", "de", "is", "mert", "van", "ezt", "itt", "e", "meg", "ha", "már"}

def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = [t for t in text.split() if t not in STOPWORDS]
    return " ".join(tokens)

def main():
    df = load_raw_files(RAW_PATTERN)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = normalize_text(df)
    df["description_clean"] = df["description"].map(clean_text)
    df["district"] = df.apply(extract_district, axis=1)
    
    out_data = []
    for _, row in df.iterrows():
        out_data.append({
            "url": row.get("url"),
            "title": row.get("title"),
            "author": row.get("author"),
            "author_profile": row.get("author_profile"),
            "date": row["date"].strftime(DATE_FORMAT) if pd.notna(row["date"]) else None,
            "category": row.get("category"),
            "institution": row.get("institution"),
            "supporter": row.get("supporter"),
            "address": row.get("address"),
            "district": row.get("district"),
            "status": row.get("status"),
            "description": row.get("description_clean"),
            "images": row.get("images", []),
        })
    save_jsonl(out_data, os.path.join(OUTPUT_DIR, "issues_for_eda.jsonl"))
    print(f"Saved {len(df)} cleaned reports for EDA to {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
