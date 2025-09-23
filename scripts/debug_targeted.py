#!/usr/bin/env python3
"""
Targeted debug for the specific JSONL file and line that's failing
"""
import json
import sys

def debug_specific_file():
    filename = "data/raw/2025-09.jsonl"
    
    print(f"Analyzing file: {filename}")
    print("=" * 60)
    
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"Total lines: {len(lines)}")
    print()
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:  # Skip empty lines
            print(f"Line {i}: EMPTY LINE")
            continue
            
        print(f"Line {i}: {line[:100]}...")
        
        # Check first character
        if line and line[0] != '{':
            print(f"  ⚠️  WARNING: Line does not start with '{{' - starts with: {repr(line[0])}")
            
        try:
            data = json.loads(line)
            # Specifically check if 'date' field exists and is accessible
            if 'date' in data:
                print(f"  ✅ Valid JSON, date: {data['date']}")
            else:
                print(f"  ⚠️  Valid JSON but missing 'date' field")
        except json.JSONDecodeError as e:
            print(f"  ❌ JSON DECODE ERROR: {e}")
            print(f"  Raw line bytes: {line.encode('utf-8')}")
            print(f"  First 50 chars: {repr(line[:50])}")
            
            # Show character codes around the error position
            if e.pos is not None:
                start = max(0, e.pos - 10)
                end = min(len(line), e.pos + 10)
                problem_area = line[start:end]
                print(f"  Around error position {e.pos}: {repr(problem_area)}")
                print(f"  Character codes: {[ord(c) for c in problem_area]}")
            
            return i  # Return the problematic line number
    
    print("All lines parsed successfully!")
    return None

if __name__ == "__main__":
    problematic_line = debug_specific_file()
    if problematic_line:
        print(f"\n❌ Problem found at line {problematic_line}")
        sys.exit(1)
    else:
        print("\n✅ No problems found")
        sys.exit(0)
