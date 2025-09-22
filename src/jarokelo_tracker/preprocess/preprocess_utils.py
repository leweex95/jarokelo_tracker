import os
import re
import glob
import json
import pandas as pd
from datetime import datetime
import locale

DATE_FORMAT = "%Y-%m-%d"
CHUNK_TARGET_TOKENS = 400

locale.setlocale(locale.LC_TIME, "hu_HU.UTF-8")

def load_raw_files(pattern: str) -> pd.DataFrame:
    files = sorted(glob.glob(pattern))
    dfs = [pd.read_json(f, lines=True) for f in files]
    return pd.concat(dfs, ignore_index=True)

def extract_district(row):
    if pd.notna(row.get("district")) and row.get("district") != "":
        return row["district"]
    addr = row.get("address", "")
    if addr:
        parts = [p.strip() for p in addr.split(",")]
        if len(parts) > 1:
            return parts[1]
    return "Unknown"

def parse_hu_date(d):
    if pd.isna(d):
        return pd.NaT
    try:
        return datetime.strptime(d, "%Y. %B %d.")
    except:
        return pd.NaT

def normalize_text(df: pd.DataFrame) -> pd.DataFrame:
    df["description"] = (
        df["description"]
        .astype(str)
        .str.replace(r"<[^>]+>", " ", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.lower()
    )
    df = df[df["description"].str.strip() != ""]
    df["district"] = df.apply(extract_district, axis=1)
    # df["date"] = df["date"].apply(parse_hu_date)
    df["original_id"] = df.get("url", pd.Series(df.index.astype(str)))
    return df

def save_jsonl(data: list[dict], out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf8") as fh:
        for item in data:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")
