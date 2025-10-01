#!/bin/bash
# Resource monitoring script for GitHub Actions

echo "=== RESOURCE MONITORING ==="
echo "Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo ""

echo "📊 DISK SPACE:"
df -h
echo ""

echo "💾 MEMORY USAGE:"
free -h
echo ""

echo "🔧 SYSTEM INFO:"
echo "CPU cores: $(nproc)"
echo "Total memory: $(free -h | awk '/^Mem:/ {print $2}')"
echo "Available memory: $(free -h | awk '/^Mem:/ {print $7}')"
echo ""

echo "📁 CURRENT DIRECTORY SIZE:"
du -sh . 2>/dev/null || echo "Could not determine size"
echo ""

echo "🗂️ LARGEST DIRECTORIES:"
du -sh * 2>/dev/null | sort -hr | head -10 || echo "Could not list directories"
echo ""

echo "📋 PYTHON PACKAGES (if available):"
if command -v python >/dev/null 2>&1; then
    python -c "
import pkg_resources
import sys
total_size = 0
large_packages = []
try:
    for pkg in pkg_resources.working_set:
        try:
            import os
            pkg_path = pkg.location
            if os.path.exists(pkg_path):
                size = sum(os.path.getsize(os.path.join(dirpath, filename))
                          for dirpath, dirnames, filenames in os.walk(pkg_path)
                          for filename in filenames) / (1024*1024)
                total_size += size
                if size > 50:  # Packages larger than 50MB
                    large_packages.append((pkg.project_name, size))
        except:
            pass
    
    print(f'Total Python packages size: {total_size:.1f}MB')
    if large_packages:
        print('Large packages (>50MB):')
        for name, size in sorted(large_packages, key=lambda x: x[1], reverse=True):
            print(f'  {name}: {size:.1f}MB')
except Exception as e:
    print(f'Could not analyze packages: {e}')
" 2>/dev/null || echo "Python package analysis failed"
else
    echo "Python not available"
fi
echo ""

echo "🧹 CACHE DIRECTORIES:"
echo "Home cache dirs:"
du -sh ~/.cache/* 2>/dev/null | head -10 || echo "No cache directories found"
echo ""

echo "=========================="