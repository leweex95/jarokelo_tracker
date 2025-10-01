#!/bin/bash
# Quick script to update all poetry references and buffer sizes in the workflow

echo "Applying comprehensive workflow fixes..."

# Replace all poetry run python with python
sed -i 's/poetry run python/python/g' .github/workflows/scraper.yml

# Replace all buffer size references
sed -i "s/\${{ github.event.inputs.buffer_size || '50' }}/\${{ github.event.inputs.buffer_size || '25' }}/g" .github/workflows/scraper.yml

echo "✅ Applied workflow fixes"
echo "Note: You still need to manually update Poetry installations to pip in all jobs"