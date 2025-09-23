#!/usr/bin/env python3
"""
Debug JSONL files in data/raw/ — detect encoding issues, empty/truncated lines,
and JSON objects split across multiple physical lines. On first real error
prints exact file, line number, raw bytes, and surrounding context and exits 1.
"""
from __future__ import annotations
import os
import sys
import json
import hashlib
import argparse
from datetime import datetime
from typing import Optional

def log(msg: str, out_f):
    ts = datetime.utcnow().isoformat() + "Z"
    out_f.write(f"{ts} {msg}\n")
    out_f.flush()
    print(msg)

def sha256_hex(b: bytes) -> str:
    import hashlib
    return hashlib.sha256(b).hexdigest()

def analyze_file(path: str, max_join: int, out_f) -> bool:
    """
    Returns True if an error was found (and reported), False otherwise.
    """
    log(f"\n=== ANALYZE: {path}", out_f)
    if not os.path.exists(path):
        log(f"[SKIP] file does not exist: {path}", out_f)
        return False

    b = open(path, "rb").read()
    size = len(b)
    log(f"size={size} bytes sha256={sha256_hex(b)}", out_f)

    # BOM check and decode test
    bom = b.startswith(b"\xef\xbb\xbf")
    if bom:
        log("[INFO] UTF-8 BOM detected", out_f)

    try:
        text = b.decode("utf-8")
    except UnicodeDecodeError as e:
        log(f"[ERROR] UTF-8 decoding failed: {e!r}", out_f)
        # show bytes around problem
        bad_offset = getattr(e, "start", None)
        if bad_offset is not None:
            start = max(0, bad_offset - 40)
            end = min(len(b), bad_offset + 40)
            snippet = b[start:end]
            log(f"bytes[{start}:{end}] = {snippet[:200].hex()}", out_f)
        return True

    # preserve physical lines and raw bytes-per-line
    lines = text.splitlines(keepends=True)
    b_lines = b.splitlines(keepends=True)
    n_lines = len(lines)
    log(f"physical_lines={n_lines}", out_f)

    # check file termination (must end with newline for robust JSONL)
    if not b.endswith(b"\n"):
        log("[WARN] file does not end with newline (possible truncation)", out_f)

    # quick heads/tails
    head_n = min(5, n_lines)
    tail_n = min(5, n_lines)
    log("---- HEAD ----", out_f)
    for i in range(head_n):
        log(f"{i+1:6d}: {repr(lines[i][:200])}", out_f)
    log("---- TAIL ----", out_f)
    for i in range(n_lines - tail_n, n_lines):
        if i >= 0:
            log(f"{i+1:6d}: {repr(lines[i][:200])}", out_f)

    # iterate and try strict JSON per physical line; attempt to join up to max_join lines
    i = 0
    while i < n_lines:
        raw = lines[i]
        if not raw.strip():
            # blank physical line
            i += 1
            continue

        try:
            json.loads(raw)
            i += 1
            continue
        except json.JSONDecodeError as e:
            # attempt to join subsequent physical lines (object spanned multiple lines)
            joined = raw
            found = False
            for j in range(i + 1, min(n_lines, i + 1 + max_join)):
                joined += lines[j]
                try:
                    json.loads(joined)
                    # found: object was multi-line starting at i ending at j
                    log(f"[INFO] Multi-line JSON object reconstructed in {path}: lines {i+1}-{j+1}", out_f)
                    # show reconstructed object's head
                    snippet = joined[:1000].replace("\n", "\\n")
                    log(f"reconstructed_prefix={repr(snippet)}", out_f)
                    i = j + 1
                    found = True
                    break
                except json.JSONDecodeError:
                    continue

            if found:
                continue

            # Not reconstructable within max_join -> report detailed debug context and fail
            log(f"[ERROR] JSONDecodeError at file={path} line={i+1}: {e.msg} (pos={e.pos})", out_f)
            # show the problematic physical line text and raw bytes
            line_text = raw.rstrip("\r\n")
            log(f"problem_line[{i+1}] (text repr): {repr(line_text[:1000])}", out_f)
            # find raw bytes for the same line index in b_lines (best-effort)
            raw_bytes = b_lines[i] if i < len(b_lines) else b""
            log(f"problem_line[{i+1}] (raw bytes hex, first 200b): {raw_bytes[:200].hex()}", out_f)

            # print a small context window
            start_ctx = max(0, i - 3)
            end_ctx = min(n_lines, i + 4)
            log("---- CONTEXT ----", out_f)
            for k in range(start_ctx, end_ctx):
                prefix = ">" if k == i else " "
                txt = lines[k].rstrip("\r\n")
                log(f"{prefix} {k+1:6d}: {repr(txt[:1000])}", out_f)

            # also print a helpful heuristic: does the problematic line start with '{' ?
            starts_brace = line_text.lstrip().startswith("{")
            log(f"line_starts_with_brace={starts_brace}", out_f)

            # return failing code
            return True

    # if we reached here, file looks OK
    log(f"[OK] {path} parsed line-by-line as JSONL", out_f)
    return False

def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--dir", "-d", default="data/raw", help="Directory with .jsonl files")
    p.add_argument("--file", "-f", default=None, help="Single file to analyze (overrides --dir)")
    p.add_argument("--max-join", type=int, default=20, help="Max physical lines to join when reconstructing multi-line objects")
    p.add_argument("--output", "-o", default="debug-jsonl-output.txt", help="Write verbose debug output here")
    args = p.parse_args(argv)

    out_path = args.output
    with open(out_path, "w", encoding="utf-8") as out_f:
        log("Starting debug_jsonl.py", out_f)
        targets = []
        if args.file:
            targets = [args.file]
        else:
            if not os.path.isdir(args.dir):
                log(f"[ERROR] directory not found: {args.dir}", out_f)
                return 2
            targets = sorted([os.path.join(args.dir, f) for f in os.listdir(args.dir) if f.endswith(".jsonl")])

        if not targets:
            log("[INFO] No .jsonl files found to analyze.", out_f)
            return 0

        any_error = False
        for t in targets:
            err = analyze_file(t, args.max_join, out_f)
            if err:
                any_error = True
                log(f"[FATAL] Stopping analysis due to detected problem in {t}", out_f)
                break

        if any_error:
            log("Debugger detected problems. See above output.", out_f)
            return 1
        else:
            log("All files OK.", out_f)
            return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
