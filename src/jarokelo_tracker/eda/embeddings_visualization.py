#!/usr/bin/env python3
"""
Interactive 2D embeddings visualization tool for Járőkelő tracker data.

This module provides t-SNE-based dimensionality reduction and interactive Plotly
visualization of text embeddings. Can be used as a standalone CLI tool or
integrated into the data processing pipeline.

Usage:
    python -m jarokelo_tracker.eda.embeddings_visualization --demo
    python src/jarokelo_tracker/eda/embeddings_visualization.py --color-by category
"""

import argparse
import json
import os
import glob
from pathlib import Path
from typing import Tuple, List, Dict, Optional, Any
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer

# Import t-SNE for dimensionality reduction
from sklearn.manifold import TSNE

try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    raise ImportError("Plotly is required. Install with: pip install plotly")


class EmbeddingsVisualizer:
    """
    Interactive 2D visualization of text embeddings using UMAP and Plotly.
    """
    
    def __init__(
        self,
        vector_base_dir: str = "data/vector_store",
        vector_backend: str = "faiss",
        vector_path: Optional[str] = None,
        tsne_params: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the embeddings visualizer.
        
        Args:
            vector_base_dir: Base directory containing vector stores
            vector_backend: Vector store backend (faiss or chroma)
            vector_path: Specific path to vector store (if None, uses latest)
            tsne_params: Custom t-SNE parameters
        """
        self.vector_base_dir = vector_base_dir
        self.vector_backend = vector_backend
        self.vector_path = vector_path
        
        # Default t-SNE parameters - optimized for text embeddings
        self.reduction_params = {
            'n_components': 2,
            'random_state': 42,
            'perplexity': 30,  # Will be adjusted based on data size
            'max_iter': 1000,
            'verbose': 1
        }
        self.reduction_method = 'tsne'
        
        if tsne_params:
            self.reduction_params.update(tsne_params)
    
    def load_vector_store(self) -> Tuple[faiss.Index, List[Dict]]:
        """
        Load FAISS index and metadata from vector store.
        
        Returns:
            Tuple of (faiss_index, metadata_list)
        """
        if self.vector_path:
            vector_dir = Path(self.vector_path)
        else:
            pattern = os.path.join(self.vector_base_dir, f"{self.vector_backend}_*")
            dirs = sorted(glob.glob(pattern), reverse=True)
            if not dirs:
                raise FileNotFoundError(f"No vector store found for backend '{self.vector_backend}' in {self.vector_base_dir}")
            vector_dir = Path(dirs[0])
        
        print(f"Loading vector store from: {vector_dir}")
        
        # Load FAISS index
        index_path = vector_dir / "index.faiss"
        if not index_path.exists():
            raise FileNotFoundError(f"FAISS index not found at {index_path}")
        
        index = faiss.read_index(str(index_path))
        
        # Load metadata
        metadata_path = vector_dir / "metadata.jsonl"
        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata file not found at {metadata_path}")
        
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = [json.loads(line) for line in f]
        
        print(f"Loaded {len(metadata)} embeddings from vector store")
        return index, metadata
    
    def extract_embeddings_from_faiss(self, index: faiss.Index) -> np.ndarray:
        """
        Extract embeddings from FAISS index.
        
        Args:
            index: FAISS index
            
        Returns:
            Numpy array of embeddings (n_samples, n_features)
        """
        # For IndexFlatIP, we can reconstruct vectors directly
        if hasattr(index, 'reconstruct_n'):
            embeddings = np.zeros((index.ntotal, index.d), dtype=np.float32)
            for i in range(index.ntotal):
                embeddings[i] = index.reconstruct(i)
        else:
            raise ValueError(f"Cannot extract embeddings from index type: {type(index)}")
        
        return embeddings
    
    def reduce_dimensionality(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Reduce embeddings to 2D using t-SNE.
        
        Args:
            embeddings: High-dimensional embeddings
            
        Returns:
            2D embeddings
        """
        print("Applying t-SNE dimensionality reduction...")
        print(f"t-SNE parameters: {self.reduction_params}")
        
        # Adjust perplexity based on data size
        params = self.reduction_params.copy()
        max_perplexity = max(5, (embeddings.shape[0] - 1) // 3)
        params['perplexity'] = min(params.get('perplexity', 30), max_perplexity)
        params['n_components'] = 2  # Ensure 2D output
        
        print("Using sklearn t-SNE...")
        reducer = TSNE(**params)
        
        embeddings_2d = reducer.fit_transform(embeddings)
        
        print(f"Reduced {embeddings.shape[0]} embeddings from {embeddings.shape[1]}D to 2D")
        return embeddings_2d
    
    def create_dataframe(self, embeddings_2d: np.ndarray, metadata: List[Dict]) -> pd.DataFrame:
        """
        Create DataFrame with 2D embeddings and metadata for visualization.
        
        Args:
            embeddings_2d: 2D embeddings from t-SNE
            metadata: List of metadata dictionaries
            
        Returns:
            DataFrame ready for plotting
        """
        # Process text more efficiently to reduce file size
        def format_text(text, max_length=100):  # Reduced from 150 to save space
            """Format text for hover display - truncate and add line breaks."""
            if len(text) > max_length:
                text = text[:max_length] + '...'
            # Add line breaks for better readability (every ~40 characters at word boundaries)
            words = text.split()
            lines = []
            current_line = []
            current_length = 0
            
            for word in words:
                if current_length + len(word) + 1 > 40 and current_line:  # Shorter lines
                    lines.append(' '.join(current_line))
                    current_line = [word]
                    current_length = len(word)
                else:
                    current_line.append(word)
                    current_length += len(word) + 1
            
            if current_line:
                lines.append(' '.join(current_line))
            
            return '<br>'.join(lines[:4])  # Max 4 lines to reduce data
        
        def format_title(title, max_length=60):  # Reduced from 80
            """Format title with length limit."""
            if len(title) > max_length:
                return title[:max_length] + '...'
            return title
        
        def format_institution(institution, max_length=40):  # Truncate long institution names
            """Format institution name with length limit."""
            if institution is None:
                return 'Unknown'
            if len(institution) > max_length:
                return institution[:max_length] + '...'
            return institution
        
        df = pd.DataFrame({
            'x': np.round(embeddings_2d[:, 0], 3),  # Round coordinates to reduce precision
            'y': np.round(embeddings_2d[:, 1], 3),
            'text_formatted': [format_text(m['text']) for m in metadata],
            'district': [m.get('district', 'Unknown') for m in metadata],
            'status': [m.get('status', 'Unknown') for m in metadata],
            'category': [m.get('category', 'Unknown') for m in metadata],
            'institution': [format_institution(m.get('institution', 'Unknown')) for m in metadata],
            'title_formatted': [format_title(m.get('title', 'No title')) for m in metadata]
            # Removed 'id' and 'url' to save space - these are rarely needed in hover
        })
        
        print(f"Created DataFrame with {len(df)} samples")
        print(f"Unique districts: {df['district'].nunique()}")
        print(f"Unique statuses: {df['status'].nunique()}")
        print(f"Unique categories: {df['category'].nunique()}")
        
        return df
    
    def create_interactive_plot(
        self, 
        df: pd.DataFrame, 
        color_by: str = 'district',
        title: Optional[str] = None
    ) -> go.Figure:
        """
        Create interactive Plotly scatter plot.
        
        Args:
            df: DataFrame with embeddings and metadata
            color_by: Column to color points by
            title: Plot title
            
        Returns:
            Plotly figure
        """
        # Set default title if not provided
        if title is None:
            method_name = "UMAP" if self.reduction_method == 'umap' else "t-SNE"
            title = f"Interactive 2D Embedding Map - Járőkelő Issues ({method_name})"
        
        print(f"Creating interactive plot colored by: {color_by}")
        
        # Create scatter plot with proper color mapping and hover info
        fig = px.scatter(
            df,
            x='x',
            y='y',
            color=color_by,
            title=title,
            template='plotly_dark',
            height=800,
            color_discrete_sequence=px.colors.qualitative.Set3,
            hover_name='title_formatted',
            hover_data={
                'x': False,
                'y': False,
                color_by: True,
                'status': True,
                'district': True,
                'category': True,
                'institution': True,
                'text_formatted': True
            },
            labels={
                'title_formatted': 'Title',
                'status': 'Status',
                'district': 'District', 
                'category': 'Category',
                'institution': 'Institution',
                'text_formatted': 'Description'
            }
        )
        
        # Update marker styling
        fig.update_traces(
            marker=dict(
                size=4,
                opacity=0.7,
                line=dict(width=0.3, color='rgba(255,255,255,0.2)')
            )
        )
        
        # Update layout for better appearance and full-screen usage
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18, 'color': 'white'}
            },
            xaxis_title=f"{self.reduction_method.upper()} Dimension 1",
            yaxis_title=f"{self.reduction_method.upper()} Dimension 2",
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.01,
                bgcolor="rgba(0,0,0,0.5)",
                bordercolor="rgba(255,255,255,0.2)",
                borderwidth=1
            ),
            # Full-screen layout
            autosize=True,
            margin=dict(l=50, r=150, t=60, b=50),
            # Dark mode styling
            paper_bgcolor='rgba(17,17,17,1)',
            plot_bgcolor='rgba(17,17,17,1)',
            font=dict(color='white'),
            xaxis=dict(
                gridcolor='rgba(128,128,128,0.2)',
                zerolinecolor='rgba(128,128,128,0.3)'
            ),
            yaxis=dict(
                gridcolor='rgba(128,128,128,0.2)',
                zerolinecolor='rgba(128,128,128,0.3)'
            ),
            # Hover styling
            hoverlabel=dict(
                bgcolor="rgba(0,0,0,0.8)",
                bordercolor="rgba(255,255,255,0.3)",
                font_size=12,
                font_family="Arial",
                align="left"
            )
        )
        
        # Configure hover behavior for better positioning
        fig.update_layout(
            hovermode='closest',
            hoverdistance=100  # Increase hover sensitivity area
        )
        
        return fig
    
    def generate_visualization(
        self, 
        color_by: str = 'district',
        output_path: Optional[str] = None,
        show_plot: bool = True,
        max_points: Optional[int] = None
    ) -> Tuple[pd.DataFrame, go.Figure]:
        """
        Generate complete embeddings visualization.
        
        Args:
            color_by: Column to color points by
            output_path: Path to save HTML file (optional)
            show_plot: Whether to display plot
            max_points: Maximum number of points to include (for file size optimization)
            
        Returns:
            Tuple of (dataframe, plotly_figure)
        """
        # Load data
        index, metadata = self.load_vector_store()
        
        # Extract embeddings
        embeddings = self.extract_embeddings_from_faiss(index)
        
        # Sample data if max_points is specified and dataset is larger
        if max_points and len(embeddings) > max_points:
            print(f"Sampling {max_points} points from {len(embeddings)} total points for file size optimization")
            # Stratified sampling to maintain color distribution
            indices = np.random.choice(len(embeddings), size=max_points, replace=False)
            embeddings = embeddings[indices]
            metadata = [metadata[i] for i in indices]
        
        # Reduce dimensionality
        embeddings_2d = self.reduce_dimensionality(embeddings)
        
        # Create dataframe
        df = self.create_dataframe(embeddings_2d, metadata)
        
        # Create plot
        fig = self.create_interactive_plot(df, color_by=color_by)
        
        # Save if requested
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create custom HTML with full-screen styling and better hover positioning
            html_string = fig.to_html(
                include_plotlyjs='cdn',
                div_id="plotly-div",
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': 'embeddings_visualization',
                        'height': 1080,
                        'width': 1920,
                        'scale': 2
                    }
                }
            )
            
            # Add custom CSS for full-screen and better hover positioning
            custom_css = """
            <style>
                body {
                    margin: 0;
                    padding: 0;
                    background-color: #111;
                    overflow: hidden;
                }
                
                #plotly-div {
                    width: 100vw !important;
                    height: 100vh !important;
                }
                
                .plotly-graph-div {
                    width: 100% !important;
                    height: 100% !important;
                }
                
                /* Custom hover label positioning */
                .hoverlayer .hovertext {
                    max-width: 300px !important;
                    word-wrap: break-word !important;
                    background-color: rgba(0, 0, 0, 0.85) !important;
                    border: 1px solid rgba(255, 255, 255, 0.3) !important;
                    border-radius: 4px !important;
                    padding: 8px !important;
                    font-size: 11px !important;
                    line-height: 1.3 !important;
                }
                
                /* Ensure hover labels don't get cut off */
                .hoverlayer {
                    pointer-events: none !important;
                }
                
                /* Style the plotly toolbar */
                .modebar {
                    background-color: rgba(0, 0, 0, 0.3) !important;
                    border-radius: 4px !important;
                }
                
                .modebar-btn {
                    color: rgba(255, 255, 255, 0.7) !important;
                }
                
                .modebar-btn:hover {
                    background-color: rgba(255, 255, 255, 0.1) !important;
                    color: white !important;
                }
            </style>
            """
            
            # Insert custom CSS into the HTML
            html_string = html_string.replace('<head>', f'<head>{custom_css}')
            
            # Write the customized HTML
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_string)
                
            print(f"Saved visualization to: {output_path}")
        
        # Show plot
        if show_plot:
            fig.show()
        
        return df, fig


def generate_demo(output_dir: str = "docs/embeddings", max_points: int = 1000):
    """
    Generate comprehensive demo visualizations with different color schemes.
    
    Args:
        output_dir: Directory to save demo files
        max_points: Maximum number of points to include in demo
    """
    from pathlib import Path
    
    print("=== Jarokelo Embeddings Visualization Demo ===\n")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    try:
        # Initialize visualizer
        visualizer = EmbeddingsVisualizer()
        
        # Generate different visualizations
        color_schemes = [
            ("district", "Districts"),
            ("status", "Issue Status"),
            ("category", "Categories"),
            ("institution", "Responsible Institutions")
        ]
        
        for color_by, description in color_schemes:
            print(f"Creating visualization colored by {description.lower()}...")
            
            # Generate visualization with sampling for demo
            df, fig = visualizer.generate_visualization(
                color_by=color_by,
                max_points=max_points,
                show_plot=False
            )
            
            # Update the title after generation
            title = f"Járőkelő Issues - {description} (t-SNE)"
            fig.update_layout(title=title)
            
            # Save to file using the same logic as generate_visualization
            output_file = output_path / f"embeddings_{color_by}.html"
            
            # Create custom HTML with full-screen styling
            html_string = fig.to_html(
                include_plotlyjs='cdn',
                div_id="plotly-div",
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': f'embeddings_{color_by}',
                        'height': 1080,
                        'width': 1920,
                        'scale': 2
                    }
                }
            )
            
            # Add custom CSS for full-screen and better hover positioning
            custom_css = """
            <style>
                body {
                    margin: 0;
                    padding: 0;
                    background-color: #111;
                    overflow: hidden;
                }
                
                #plotly-div {
                    width: 100vw !important;
                    height: 100vh !important;
                }
                
                .plotly-graph-div {
                    width: 100% !important;
                    height: 100% !important;
                }
                
                .hoverlayer .hovertext {
                    max-width: 300px !important;
                    word-wrap: break-word !important;
                    background-color: rgba(0, 0, 0, 0.85) !important;
                    border: 1px solid rgba(255, 255, 255, 0.3) !important;
                    border-radius: 4px !important;
                    padding: 8px !important;
                    font-size: 11px !important;
                    line-height: 1.3 !important;
                }
                
                .hoverlayer {
                    pointer-events: none !important;
                }
                
                .modebar {
                    background-color: rgba(0, 0, 0, 0.3) !important;
                    border-radius: 4px !important;
                }
                
                .modebar-btn {
                    color: rgba(255, 255, 255, 0.7) !important;
                }
                
                .modebar-btn:hover {
                    background-color: rgba(255, 255, 255, 0.1) !important;
                    color: white !important;
                }
            </style>
            """
            
            # Insert custom CSS into the HTML
            html_string = html_string.replace('<head>', f'<head>{custom_css}')
            
            # Write the customized HTML
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_string)
            
            # File size info
            if output_file.exists():
                size_mb = output_file.stat().st_size / (1024 * 1024)
                print(f"  → Saved: {output_file} ({size_mb:.1f} MB)")
        
        # Create index page
        create_demo_index(output_path, color_schemes)
        
        print(f"\n✅ Demo completed successfully!")
        print(f"✅ Demo completed successfully!")
        print(f"📊 Visualizations show {max_points} sampled points from full dataset")
        print(f"🌐 Open {output_path}/index.html to view all visualizations")
        
    except Exception as e:
        print(f"Error generating demo: {e}")
        raise


def create_demo_index(output_dir: Path, color_schemes: list):
    """Create an index HTML page for the demo visualizations."""
    
    index_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Járőkelő Embeddings Visualizations</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
            background-color: #f5f5f5;
        }
        .header {
            text-align: center;
            margin-bottom: 3rem;
            padding: 2rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 12px;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5rem;
        }
        .header p {
            margin: 0.5rem 0 0 0;
            font-size: 1.1rem;
            opacity: 0.9;
        }
        .visualization-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .visualization-card {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 1.5rem;
            text-decoration: none;
            color: inherit;
            transition: transform 0.2s, box-shadow 0.2s;
            background: white;
        }
        .visualization-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .card-title {
            font-size: 1.2rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
            color: #2c3e50;
        }
        .card-description {
            color: #666;
            font-size: 0.9rem;
        }
        .info-section {
            background-color: white;
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 2rem;
            border: 1px solid #ddd;
        }
        .tech-info {
            font-size: 0.9rem;
            color: #666;
            text-align: center;
            background-color: white;
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid #ddd;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🗺️ Járőkelő Embeddings Visualizations</h1>
        <p>Interactive 2D visualizations of civic issue embeddings using dimensionality reduction</p>
    </div>
    
    <div class="info-section">
        <h2>About These Visualizations</h2>
        <p>These interactive plots show civic issues from the Járőkelő platform mapped to a 2D space based on their text content similarity. Points that are close together represent issues with similar content, while distant points represent very different types of issues.</p>
        <p>Each visualization colors the points by a different metadata field to help identify patterns and clusters in the data.</p>
    </div>
    
    <div class="visualization-grid">
"""
    
    descriptions = {
        "district": "See how issues cluster by geographic districts in Budapest",
        "status": "Explore the distribution of issue statuses (solved, pending, etc.)",
        "category": "Discover patterns in different types of civic issues",
        "institution": "Analyze how different responsible institutions handle various issues"
    }
    
    for color_by, display_name in color_schemes:
        index_content += f"""
        <a href="embeddings_{color_by}.html" class="visualization-card">
            <div class="card-title">{display_name}</div>
            <div class="card-description">{descriptions[color_by]}</div>
        </a>
"""
    
    index_content += """
    </div>
    
    <div class="tech-info">
        <p><strong>Technical Details:</strong> Embeddings generated using sentence-transformers, 
        dimensionality reduction via t-SNE, visualized with Plotly.</p>
        <p>Generated automatically by the Járőkelő Tracker embeddings visualization pipeline.</p>
    </div>
</body>
</html>
"""
    
    index_file = output_dir / "index.html"
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(index_content)
    
    print(f"  → Created index page: {index_file}")


def main():
    """Command line interface for embeddings visualization."""
    parser = argparse.ArgumentParser(
        description="Generate interactive 2D visualization of text embeddings"
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Generate comprehensive demo with all color schemes and index page"
    )
    
    parser.add_argument(
        "--vector-base-dir",
        default="data/vector_store",
        help="Base directory containing vector stores"
    )
    
    parser.add_argument(
        "--vector-backend",
        choices=["faiss", "chroma"],
        default="faiss",
        help="Vector store backend"
    )
    
    parser.add_argument(
        "--vector-path",
        help="Specific path to vector store (if not provided, uses latest)"
    )
    
    parser.add_argument(
        "--color-by",
        choices=["district", "status", "category", "institution"],
        default="district",
        help="Metadata field to color points by"
    )
    
    parser.add_argument(
        "--output-path",
        help="Path to save HTML visualization file"
    )
    
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Don't display the plot (useful for automated processing)"
    )
    
    # t-SNE dimensionality reduction parameters
    parser.add_argument("--perplexity", type=int, default=30, help="t-SNE perplexity parameter")
    parser.add_argument("--max-iter", type=int, default=1000, help="t-SNE maximum number of iterations")
    parser.add_argument("--random-state", type=int, default=42, help="Random state for reproducibility")
    parser.add_argument("--max-points", type=int, help="Maximum number of points to include (reduces file size)")
    
    args = parser.parse_args()
    
    # Handle demo mode
    if args.demo:
        generate_demo(max_points=args.max_points or 5000)
        return
    
    # Set up t-SNE parameters
    tsne_params = {
        'perplexity': args.perplexity,
        'max_iter': args.max_iter,
        'random_state': args.random_state
    }
    
    # Create visualizer
    visualizer = EmbeddingsVisualizer(
        vector_base_dir=args.vector_base_dir,
        vector_backend=args.vector_backend,
        vector_path=args.vector_path,
        tsne_params=tsne_params
    )
    
    # Generate default output path if not provided
    output_path = args.output_path
    if not output_path:
        output_path = "docs/embeddings_visualization.html"
    
    try:
        # Generate visualization
        df, fig = visualizer.generate_visualization(
            color_by=args.color_by,
            output_path=output_path,
            show_plot=not args.no_show,
            max_points=args.max_points
        )
        
        print(f"\nVisualization completed successfully!")
        print(f"Data points: {len(df)}")
        print(f"Colored by: {args.color_by}")
        if output_path:
            print(f"Saved to: {output_path}")
        
    except Exception as e:
        print(f"Error generating visualization: {e}")
        raise


if __name__ == "__main__":
    main()