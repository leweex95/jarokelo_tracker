import json
import sys
import re

def debug_jsonl(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        raw = f.read()
        # Normalize line endings
        raw = raw.replace('\r\n', '\n').replace('\r', '\n')
        # Split by newline first
        lines = [l for l in raw.split('\n') if l.strip()]

        for i, line in enumerate(lines, start=1):
            # Detect multiple JSON objects on same line using '}{' pattern
            parts = re.split(r'(?<=})\s*(?={)', line)
            for j, part in enumerate(parts, start=1):
                try:
                    json.loads(part)
                except json.JSONDecodeError as e:
                    print(f"[LINE {i}, PART {j}] Malformed JSON:")
                    print(f"  Content: {part}")
                    print(f"  Error: {e}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_jsonl.py <file.jsonl>")
        sys.exit(1)
    debug_jsonl(sys.argv[1])
