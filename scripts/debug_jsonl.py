# scripts/debug_jsonl.py
import json
import sys

def debug_jsonl(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            try:
                json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[LINE {i}] Malformed JSON:")
                print(f"  Content: {line}")
                print(f"  Error: {e}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_jsonl.py <file.jsonl>")
        sys.exit(1)
    debug_jsonl(sys.argv[1])
