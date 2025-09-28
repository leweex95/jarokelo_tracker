# Embeddings Visualization

This module provides interactive 2D visualization of text embeddings from the Járőkelő tracker dataset. It creates beautiful, interactive scatter plots that help explore patterns and clusters in civic issues based on their content similarity.

## Features

- **Interactive 2D scatter plots** using Plotly with hover information
- **Multiple coloring schemes** by district, status, category, or institution
- **Dark mode interface** optimized for better visibility
- **Full-screen layouts** that utilize the entire browser window
- **Smart hover positioning** that doesn't cover the highlighted point
- **Optimized file sizes** with data sampling and text truncation
- **Dimensionality reduction** using t-SNE
- **Automatic integration** with the vector store building pipeline
- **Standalone CLI tool** for on-demand visualization
- **HTML output** suitable for web deployment or sharing

## Quick Start

### Generate visualization from existing vector store

```bash
# Basic usage - creates visualization colored by district
python -m jarokelo_tracker.eda.embeddings_visualization

# Color by different metadata fields
python -m jarokelo_tracker.eda.embeddings_visualization --color-by status
python -m jarokelo_tracker.eda.embeddings_visualization --color-by category
python -m jarokelo_tracker.eda.embeddings_visualization --color-by institution

# Reduce file size by sampling (recommended for large datasets)
python -m jarokelo_tracker.eda.embeddings_visualization --max-points 5000

# Save to specific location
python -m jarokelo_tracker.eda.embeddings_visualization --output-path my_visualization.html

# Use specific vector store
python -m jarokelo_tracker.eda.embeddings_visualization --vector-path data/vector_store/faiss_20250927T175705Z
```

### Generate comprehensive demo visualizations

```bash
# Creates multiple visualizations with different color schemes + index page (1000 points default)
python -m jarokelo_tracker.eda.embeddings_visualization --demo

# With custom sampling for full dataset visualization
python -m jarokelo_tracker.eda.embeddings_visualization --demo --max-points 15000

# Or run the module directly
python src/jarokelo_tracker/eda/embeddings_visualization.py --demo
```

### Automatic generation during pipeline

```bash
# Build vector store and automatically generate visualization
python scripts/build_vector_store.py --backend faiss --embedding sentence-transformers/distiluse-base-multilingual-cased-v2

# Skip visualization during build
python scripts/build_vector_store.py --backend faiss --embedding sentence-transformers/distiluse-base-multilingual-cased-v2 --no-visualization
```

## Command Line Options

### Basic Options

- `--vector-base-dir`: Base directory containing vector stores (default: `data/vector_store`)
- `--vector-backend`: Vector store backend (`faiss` or `chroma`)
- `--vector-path`: Specific path to vector store (uses latest if not specified)
- `--color-by`: Metadata field for coloring (`district`, `status`, `category`, `institution`)
- `--output-path`: Path to save HTML file
- `--no-show`: Don't display plot (useful for automated processing)
- `--max-points`: Maximum number of points to include (reduces file size, default: all points)

### Dimensionality Reduction Parameters

- `--demo`: Generate comprehensive demo with all color schemes and index page
- `--perplexity`: t-SNE perplexity parameter (default: 30)
- `--max-iter`: t-SNE maximum number of iterations (default: 1000)
- `--metric`: Distance metric (default: cosine)
- `--random-state`: Random state for reproducibility (default: 42)

## Understanding the Visualizations

### What do the plots show?

The 2D scatter plots map high-dimensional text embeddings to a 2D space where:

- **Proximity indicates similarity**: Points close together represent issues with similar content
- **Distance indicates difference**: Points far apart represent very different types of issues  
- **Colors show metadata**: Different colors highlight patterns in districts, statuses, categories, etc.

### Interpreting clusters

- **Tight clusters**: Groups of very similar issues (e.g., same problem type, location)
- **Scattered points**: Unique or rare issue types
- **Color patterns**: Can reveal geographic patterns, institutional responsibilities, or issue resolution patterns

### Interactive features

- **Hover information**: Shows issue title, district, status, category, institution, and text preview
- **Zoom and pan**: Explore different regions of the embedding space
- **Legend**: Click to highlight/hide specific categories
- **Clickable links**: Some hover information includes links to original issues

## Integration Points

### Pipeline Integration

The visualization automatically runs after vector store creation:

1. **Data scraping** → Raw JSONL files
2. **Preprocessing** → Chunked issues for RAG
3. **Vector store building** → FAISS index + embeddings
4. **🆕 Visualization generation** → Interactive HTML plots

### File Locations

- **Module**: `src/jarokelo_tracker/eda/embeddings_visualization.py`
- **Main module**: `src/jarokelo_tracker/eda/embeddings_visualization.py`
- **CLI usage**: `python -m jarokelo_tracker.eda.embeddings_visualization`
- **Default output**: `docs/embeddings_visualization_latest.html`
- **Timestamped output**: `docs/embeddings_visualization_{backend}_{timestamp}.html`

## Technical Details

### Dependencies

- **Core**: numpy, pandas, plotly, scikit-learn
- **Vector stores**: faiss-cpu (or chromadb)
- **Embeddings**: sentence-transformers

### Dimensionality Reduction

**t-SNE (t-Distributed Stochastic Neighbor Embedding)**:
- Excellent preservation of local neighborhood structure  
- Well-established and reliable algorithm
- Good separation of clusters in civic issues data
- Stable implementation in scikit-learn

### Performance

- **Dataset size**: Tested on ~14K civic issues
- **Embedding dimensions**: 512D → 2D reduction
- **Processing time**: ~30-60 seconds for full visualization
- **Output size**: 
  - Full dataset (~14K points): ~140MB HTML files
  - Sampled dataset (3K-5K points): ~20-40MB HTML files
  - Status visualizations (6 categories): ~7-20MB HTML files
- **Recommended sampling**: 3K-5K points for optimal balance of detail and file size

## Examples

### Basic district visualization

```python
from jarokelo_tracker.eda.embeddings_visualization import EmbeddingsVisualizer

visualizer = EmbeddingsVisualizer()
df, fig = visualizer.generate_visualization(color_by='district')
```

### Custom parameters

```python
visualizer = EmbeddingsVisualizer(
    vector_path='data/vector_store/faiss_20250927T175705Z',
    tsne_params={'perplexity': 15, 'max_iter': 1500}
)
df, fig = visualizer.generate_visualization(
    color_by='status',
    output_path='custom_viz.html',
    show_plot=False
)
```

## Troubleshooting

### Memory issues with large datasets

For very large datasets (>50K embeddings):

```bash
# Use smaller perplexity for t-SNE
python scripts/visualize_embeddings.py --perplexity 15

# Reduce iterations for faster processing
python scripts/visualize_embeddings.py --max-iter 500
```

### Vector store not found

Make sure you have built a vector store first:

```bash
python scripts/build_vector_store.py --backend faiss --embedding sentence-transformers/distiluse-base-multilingual-cased-v2
```

### Large file sizes

If HTML files are too large (>100MB):

```bash
# Use sampling to reduce file size
python scripts/visualize_embeddings.py --max-points 3000

# Status visualizations are typically smaller due to fewer categories
python scripts/visualize_embeddings.py --color-by status --max-points 5000

# Institution visualizations can be very large due to many unique values
python scripts/visualize_embeddings.py --color-by institution --max-points 2000
```

## Future Enhancements

- [ ] 3D visualization option
- [ ] Animated visualizations showing temporal patterns
- [ ] Custom clustering algorithms overlay
- [ ] Export to other formats (PNG, SVG, PDF)
- [ ] Integration with Streamlit dashboard
- [ ] Real-time visualization updates