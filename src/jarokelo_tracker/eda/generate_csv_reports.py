import json
import pandas as pd
from pathlib import Path
from collections import Counter
import re

# --- Paths ---
RAW_DIR = Path(__file__).resolve().parents[3] / "data/raw"
DATA_DIR = Path(__file__).resolve().parents[3] / "data/processed/powerbi"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- Load all monthly JSONL files ---
records = []
for file in sorted(RAW_DIR.glob("*.jsonl")):
    with open(file, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line.strip()))

df = pd.DataFrame(records)

# --- Feature extraction ---
df["date"] = pd.to_datetime(df["date"])
df["day"] = df["date"].dt.date
df["month"] = df["date"].dt.to_period("M")
df["day_of_week"] = df["date"].dt.day_name()
df["year"] = df["date"].dt.year

# Coordinates from description
def extract_coords(desc):
    match = re.search(r"([0-9]+\.[0-9]+),\s*([0-9]+\.[0-9]+)", desc)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None

df["latitude"], df["longitude"] = zip(*df["description"].map(extract_coords))

# Open vs solved
df["is_solved"] = df["status"].str.contains("MEGOLDÁS")

# --- CSV outputs ---

# 1. Volume & activity
df.groupby("day").size().reset_index(name="reports_count").to_csv(DATA_DIR/"reports_per_day.csv", index=False)
df.groupby("month").size().reset_index(name="reports_count").to_csv(DATA_DIR/"reports_per_month.csv", index=False)
df.groupby("category").size().reset_index(name="reports_count").to_csv(DATA_DIR/"reports_per_category.csv", index=False)

# 2. Institution breakdown
df.groupby("institution").size().reset_index(name="reports_count").to_csv(DATA_DIR/"reports_per_institution.csv", index=False)

# 3. Status / resolution
df.groupby(["day", "is_solved"]).size().reset_index(name="count").to_csv(DATA_DIR/"reports_status_trend.csv", index=False)
df.groupby("is_solved").size().reset_index(name="count").to_csv(DATA_DIR/"reports_status_summary.csv", index=False)

# 4. Geographic insights
df_geo = df[["url","title","address","latitude","longitude","category","status","is_solved"]].dropna(subset=["latitude","longitude"])
df_geo.to_csv(DATA_DIR/"reports_geo.csv", index=False)

# 5. Word cloud keywords
def tokenize(text):
    text = re.sub(r"\W+", " ", text.lower())
    return text.split()

all_tokens = sum(df["description"].map(tokenize).tolist(), [])
top_keywords = pd.DataFrame(Counter(all_tokens).most_common(100), columns=["keyword","count"])
top_keywords.to_csv(DATA_DIR/"wordcloud_keywords.csv", index=False)

print(f"EDA CSVs saved to {DATA_DIR}")
