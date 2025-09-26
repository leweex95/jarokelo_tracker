import os
import random
import json
import pandas as pd
from collections import defaultdict

DATA_DIR = "data/raw"
N = 10
OUTPUT_FILE = os.path.join(DATA_DIR, "sampled_entries.xlsx")

entries_by_category = defaultdict(list)

for filename in os.listdir(DATA_DIR):
    if filename.endswith(".jsonl"):
        with open(os.path.join(DATA_DIR, filename), encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    category = entry.get('category')
                    description = entry.get('description', '')
                    # Only keep entries with description longer than 50 chars
                    if category and isinstance(description, str) and len(description) > 50:
                        # Drop image-related fields
                        entry = {k: v for k, v in entry.items() if 'image' not in k.lower()}
                        entry['category'] = category  # Ensure category column is present
                        entries_by_category[category].append(entry)
                except json.JSONDecodeError:
                    continue  # Skip malformed lines

# Sample N entries per category
sampled_entries = []
for category, items in entries_by_category.items():
    sampled = random.sample(items, min(N, len(items)))
    sampled_entries.extend(sampled)

# Export to Excel (single sheet)
df = pd.DataFrame(sampled_entries)
df.to_excel(OUTPUT_FILE, index=False)

print(f"Sampled entries saved to {OUTPUT_FILE}")


QUERIES_OUTPUT_FILE = os.path.join(DATA_DIR, "queries.json")

queries = []
for entry in sampled_entries:
    category = entry.get('category', '').lower()
    address = entry.get('address', '')
    url = entry.get('url', '')
    description = entry.get('description', '')
    if category and address and url:
        query_text = f"Report about {category} at {address}"
        queries.append({
            "query": query_text,
            "description": description,
            "gold_doc_ids": [url]
        })

with open(QUERIES_OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(queries, f, ensure_ascii=False, indent=2)

print(f"Queries saved to {QUERIES_OUTPUT_FILE}")
