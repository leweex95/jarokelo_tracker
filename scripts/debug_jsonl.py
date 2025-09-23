import json
import sys
import os

MALFORMED_FILE = "debug/malformed_lines.txt"
os.makedirs(os.path.dirname(MALFORMED_FILE), exist_ok=True)

def debug_jsonl(file_path):
    with open(file_path, "rb") as f:
        raw = f.read()
        for i, line in enumerate(raw.split(b'\n'), start=1):
            if not line.strip():
                continue
            print(f"[LINE {i}] raw bytes: {line}")
            try:
                json.loads(line.decode("utf-8"))
            except json.JSONDecodeError as e:
                print(f"  JSON error: {e}")
                # Save malformed line to file
                with open(MALFORMED_FILE, "ab") as mf:
                    mf.write(line + b"\n\n")  # double newline to separate
                print(f"  Saved malformed line to {MALFORMED_FILE}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_jsonl.py <file.jsonl>")
        sys.exit(1)
    debug_jsonl(sys.argv[1])
