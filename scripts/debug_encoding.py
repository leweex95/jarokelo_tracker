#!/usr/bin/env python3
"""
Check file encoding and invisible characters
"""
import binascii

def check_file_encoding():
    filename = "data/raw/2025-09.jsonl"
    
    print("Checking file encoding and invisible characters...")
    print("=" * 60)
    
    # Read as bytes to see exactly what's in the file
    with open(filename, 'rb') as f:
        content = f.read()
    
    print(f"File size: {len(content)} bytes")
    print(f"First 100 bytes hex: {binascii.hexlify(content[:100])}")
    
    # Check for BOM
    if content.startswith(b'\xef\xbb\xbf'):
        print("⚠️  UTF-8 BOM detected at start of file")
    elif content.startswith(b'\xff\xfe') or content.startswith(b'\xfe\xff'):
        print("⚠️  UTF-16 BOM detected")
    
    # Look for null bytes or other control characters
    lines = content.split(b'\n')
    for i, line_bytes in enumerate(lines, 1):
        if not line_bytes.strip():
            continue
            
        # Check for problematic bytes
        problematic_chars = [b for b in line_bytes if b < 32 and b not in [9, 10, 13]]  # TAB, LF, CR are OK
        if problematic_chars:
            print(f"Line {i}: Found control characters: {problematic_chars}")
            
        # Check if line starts with something other than {
        if line_bytes and line_bytes.strip()[0] != ord(b'{'):
            print(f"Line {i}: Does not start with '{{' - starts with: {chr(line_bytes[0]) if line_bytes[0] < 128 else 'non-ASCII'} (byte: {line_bytes[0]})")
            print(f"  First 50 bytes: {line_bytes[:50]}")
    
    # Try different encodings
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1250']
    for encoding in encodings:
        try:
            with open(filename, 'r', encoding=encoding) as f:
                content = f.read()
            print(f"✅ Successfully read with {encoding} encoding")
            break
        except UnicodeDecodeError as e:
            print(f"❌ Failed to read with {encoding}: {e}")

if __name__ == "__main__":
    check_file_encoding()
