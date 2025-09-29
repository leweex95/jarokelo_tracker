"""
Interactive Budapest Map Generator for Járókelő Issues
=====================================================

This module creates interactive maps showing:
1. All issues clustered by location with size indicating issue density
2. Top contributors' issue locations with different colors
3. Advanced geographic analysis and hotspot detection
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.offline as pyo
import plotly.io as pio
from pathlib import Path
import json
from sklearn.cluster import DBSCAN
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import time
import requests
from collections import Counter

# Set dark theme as default
pio.templates.default = "plotly_dark"

class BudapestIssueMapper:
    """
    Interactive map generator for Budapest municipal issues.
    """
    
    def __init__(self, df, geo_df=None):
        """
        Initialize mapper with main DataFrame and optional geo data.
        
        Args:
            df: Main DataFrame with all issues
            geo_df: DataFrame with GPS coordinates (optional)
        """
        self.df = df
        self.geo_df = geo_df
        self.maps = {}
        self.geocoder = Nominatim(user_agent="jarokelo_mapper")
        
        # Budapest center coordinates
        self.budapest_center = {'lat': 47.4979, 'lon': 19.0402}
        
    def load_or_create_coordinates(self):
        """Load existing coordinates or geocode addresses."""
        print("Processing geographic data...")
        
        if self.geo_df is not None and len(self.geo_df) > 0:
            print(f"Found existing GPS data for {len(self.geo_df)} records")
            # Merge with main dataset
            merged_df = self.df.merge(
                self.geo_df[['url', 'latitude', 'longitude']], 
                on='url', 
                how='left'
            )
            coords_available = merged_df['latitude'].notna().sum()
            print(f"GPS coordinates available for {coords_available} out of {len(self.df)} total records")
        else:
            print("No existing GPS data found")
            merged_df = self.df.copy()
            merged_df['latitude'] = None
            merged_df['longitude'] = None
            coords_available = 0
        
        self.df_with_coords = merged_df
        return coords_available
    
    def geocode_missing_addresses(self, limit=500):
        """Geocode addresses that don't have coordinates yet."""
        print(f"Geocoding missing addresses (limit: {limit})...")
        
        missing_coords = self.df_with_coords[
            self.df_with_coords['latitude'].isna() & 
            self.df_with_coords['address'].notna()
        ].copy()
        
        print(f"Found {len(missing_coords)} records without coordinates")
        
        if len(missing_coords) == 0:
            return
        
        # Take a sample if too many
        if len(missing_coords) > limit:
            missing_coords = missing_coords.sample(n=limit, random_state=42)
            print(f"Processing sample of {limit} addresses")
        
        geocoded_count = 0
        
        for idx, row in missing_coords.iterrows():
            try:
                # Clean address for better geocoding
                address = row['address']
                if pd.isna(address):
                    continue
                
                # Add Hungary to improve geocoding accuracy
                full_address = f"{address}, Hungary"
                
                location = self.geocoder.geocode(full_address, timeout=10)
                
                if location:
                    self.df_with_coords.at[idx, 'latitude'] = location.latitude
                    self.df_with_coords.at[idx, 'longitude'] = location.longitude
                    geocoded_count += 1
                    
                    if geocoded_count % 10 == 0:
                        print(f"  Geocoded {geocoded_count} addresses...")
                
                # Rate limiting to be respectful to the service
                time.sleep(1)
                
            except Exception as e:
                print(f"  Error geocoding {address}: {e}")
                continue
        
        print(f"Successfully geocoded {geocoded_count} additional addresses")
    
    def cluster_nearby_issues(self, eps_km=0.1):
        """Cluster nearby issues to reduce map complexity."""
        print(f"Clustering issues within {eps_km}km of each other...")
        
        # Get records with coordinates
        coords_df = self.df_with_coords[
            self.df_with_coords['latitude'].notna() & 
            self.df_with_coords['longitude'].notna()
        ].copy()
        
        if len(coords_df) == 0:
            print("No coordinates available for clustering")
            return coords_df
        
        # Prepare coordinates for clustering
        coordinates = coords_df[['latitude', 'longitude']].values
        
        # DBSCAN clustering with distance in kilometers
        # eps is in radians, so convert km to radians (approximately)
        eps_radians = eps_km / 6371.0  # Earth radius in km
        
        clustering = DBSCAN(eps=eps_radians, min_samples=1, metric='haversine').fit(coordinates)
        
        coords_df['cluster_id'] = clustering.labels_
        
        # Create cluster summary
        cluster_summary = coords_df.groupby('cluster_id').agg({
            'latitude': 'mean',
            'longitude': 'mean',
            'url': 'count',
            'is_solved': 'mean',
            'category': lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else 'Mixed',
            'contains_urgency': 'mean'
        }).reset_index()
        
        cluster_summary.columns = ['cluster_id', 'lat', 'lon', 'issue_count', 'resolution_rate', 'dominant_category', 'urgency_rate']
        
        print(f"Created {len(cluster_summary)} clusters from {len(coords_df)} issues")
        
        self.clustered_data = cluster_summary
        self.detailed_coords = coords_df
        
        return cluster_summary
    
    def create_issue_density_map(self):
        """Create interactive map showing issue density across Budapest."""
        print("Creating issue density map...")
        
        if not hasattr(self, 'clustered_data'):
            print("No clustered data available. Run cluster_nearby_issues() first.")
            return None
        
        cluster_data = self.clustered_data.copy()
        
        # Create size mapping for bubbles (min 10, max 50)
        min_size, max_size = 10, 50
        cluster_data['bubble_size'] = np.interp(
            cluster_data['issue_count'],
            [cluster_data['issue_count'].min(), cluster_data['issue_count'].max()],
            [min_size, max_size]
        )
        
        # Create color mapping based on resolution rate
        cluster_data['resolution_pct'] = cluster_data['resolution_rate'] * 100
        
        # Create the map
        fig = px.scatter_mapbox(
            cluster_data,
            lat='lat',
            lon='lon',
            size='bubble_size',
            color='resolution_pct',
            hover_name='dominant_category',
            hover_data={
                'issue_count': ':,',
                'resolution_pct': ':.1f',
                'urgency_rate': ':.1%',
                'bubble_size': False,
                'lat': ':.4f',
                'lon': ':.4f'
            },
            color_continuous_scale='RdYlGn',
            size_max=50,
            zoom=11,
            center=dict(lat=self.budapest_center['lat'], lon=self.budapest_center['lon']),
            title="Budapest Municipal Issues - Geographic Density Map",
            labels={
                'resolution_pct': 'Resolution Rate (%)',
                'issue_count': 'Issues Count',
                'urgency_rate': 'Urgency Rate'
            }
        )
        
        # Update layout for better visualization
        fig.update_layout(
            mapbox_style="carto-darkmatter",
            height=700,
            font={'color': 'white'},
            title_font_size=16,
            coloraxis_colorbar=dict(
                title="Resolution Rate (%)",
                titlefont={'color': 'white'},
                tickfont={'color': 'white'}
            )
        )
        
        # Add annotations
        fig.add_annotation(
            text="<b>Bubble size:</b> Number of issues reported<br><b>Color:</b> Resolution rate (green=high, red=low)",
            xref="paper", yref="paper",
            x=0.02, y=0.98,
            showarrow=False,
            font=dict(size=12, color="white"),
            bgcolor="rgba(0,0,0,0.7)",
            bordercolor="white",
            borderwidth=1
        )
        
        self.maps['density_map'] = fig
        return fig
    
    def get_top_contributors(self, n=10):
        """Get top N non-anonymous contributors."""
        print(f"Identifying top {n} non-anonymous contributors...")
        
        # Filter non-anonymous users
        registered_users = self.df[
            (self.df['author'] != 'Anonim Járókelő') & 
            (self.df['author'].notna())
        ]
        
        if len(registered_users) == 0:
            print("No registered users found")
            return []
        
        # Count reports per user
        user_counts = registered_users['author'].value_counts().head(n)
        top_users = user_counts.index.tolist()
        
        print(f"Top {len(top_users)} contributors:")
        for i, (user, count) in enumerate(user_counts.items(), 1):
            print(f"  {i}. {user}: {count} reports")
        
        return top_users
    
    def create_contributors_map(self, top_n=10):
        """Create map showing issue locations of top contributors."""
        print("Creating top contributors map...")
        
        top_users = self.get_top_contributors(top_n)
        
        if not top_users:
            return None
        
        # Filter data for top contributors with coordinates
        contributors_data = self.df_with_coords[
            (self.df_with_coords['author'].isin(top_users)) &
            (self.df_with_coords['latitude'].notna()) &
            (self.df_with_coords['longitude'].notna())
        ].copy()
        
        if len(contributors_data) == 0:
            print("No geographic data available for top contributors")
            return None
        
        print(f"Found {len(contributors_data)} georeferenced issues from top contributors")
        
        # Create color palette for contributors
        colors = px.colors.qualitative.Set1[:len(top_users)]
        color_map = dict(zip(top_users, colors))
        
        contributors_data['contributor_color'] = contributors_data['author'].map(color_map)
        
        # Create the map
        fig = go.Figure()
        
        # Add traces for each contributor
        for user in top_users:
            user_data = contributors_data[contributors_data['author'] == user]
            
            if len(user_data) > 0:
                fig.add_trace(go.Scattermapbox(
                    lat=user_data['latitude'],
                    lon=user_data['longitude'],
                    mode='markers',
                    marker=dict(
                        size=8,
                        color=color_map[user],
                        opacity=0.8
                    ),
                    text=user_data.apply(lambda row: 
                        f"<b>{row['author']}</b><br>" +
                        f"Issue: {row['title']}<br>" +
                        f"Category: {row['category']}<br>" +
                        f"Status: {row['status']}<br>" +
                        f"Date: {row['date']}", axis=1),
                    hoverinfo='text',
                    name=f"{user} ({len(user_data)} issues)",
                    showlegend=True
                ))
        
        # Update layout
        fig.update_layout(
            mapbox=dict(
                style="carto-darkmatter",
                center=dict(lat=self.budapest_center['lat'], lon=self.budapest_center['lon']),
                zoom=11
            ),
            height=700,
            title=f"Budapest Issues by Top {len(top_users)} Contributors",
            font={'color': 'white'},
            title_font_size=16,
            legend=dict(
                bgcolor="rgba(0,0,0,0.7)",
                bordercolor="white",
                borderwidth=1,
                font={'color': 'white'}
            )
        )
        
        # Add annotation
        fig.add_annotation(
            text=f"<b>Geographic distribution of issues reported by top {len(top_users)} most active contributors</b><br>" +
                 "Each color represents a different contributor's reporting patterns",
            xref="paper", yref="paper",
            x=0.02, y=0.98,
            showarrow=False,
            font=dict(size=12, color="white"),
            bgcolor="rgba(0,0,0,0.7)",
            bordercolor="white",
            borderwidth=1
        )
        
        self.maps['contributors_map'] = fig
        return fig
    
    def create_category_heatmap(self):
        """Create heatmap showing distribution of issue categories."""
        print("Creating category distribution heatmap...")
        
        if not hasattr(self, 'detailed_coords'):
            print("No detailed coordinate data available")
            return None
        
        coords_data = self.detailed_coords.copy()
        
        # Create subplots for major categories
        major_categories = coords_data['category'].value_counts().head(6).index.tolist()
        
        fig = make_subplots(
            rows=2, cols=3,
            subplot_titles=major_categories,
            specs=[[{"type": "scattermapbox"} for _ in range(3)] for _ in range(2)],
            vertical_spacing=0.1
        )
        
        colors = px.colors.qualitative.Set2
        
        for i, category in enumerate(major_categories):
            row = (i // 3) + 1
            col = (i % 3) + 1
            
            category_data = coords_data[coords_data['category'] == category]
            
            fig.add_trace(
                go.Scattermapbox(
                    lat=category_data['latitude'],
                    lon=category_data['longitude'],
                    mode='markers',
                    marker=dict(
                        size=6,
                        color=colors[i % len(colors)],
                        opacity=0.7
                    ),
                    text=category_data['title'],
                    hoverinfo='text',
                    showlegend=False
                ),
                row=row, col=col
            )
        
        # Update layout for all subplots
        for i in range(len(major_categories)):
            row = (i // 3) + 1
            col = (i % 3) + 1
            
            fig.update_layout(**{
                f'mapbox{i+1 if i > 0 else ""}': dict(
                    style="carto-darkmatter",
                    center=dict(lat=self.budapest_center['lat'], lon=self.budapest_center['lon']),
                    zoom=10
                )
            })
        
        fig.update_layout(
            height=800,
            title="Budapest Issues by Category - Geographic Distribution",
            font={'color': 'white'},
            title_font_size=16
        )
        
        self.maps['category_heatmap'] = fig
        return fig
    
    def export_maps(self, output_dir: str = "docs/eda"):
        """Export all maps as HTML files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"Exporting interactive maps to {output_dir}...")
        
        map_descriptions = {
            'density_map': {
                'title': 'Budapest Issue Density Map',
                'description': '''
                <div class="map-explanation">
                    <h4>🗺️ Budapest Municipal Issues - Geographic Density Analysis</h4>
                    <p><strong>What you see:</strong> Interactive map showing clustered municipal issues across Budapest.</p>
                    <ul>
                        <li><strong>Bubble size:</strong> Number of issues reported in that area (larger = more issues)</li>
                        <li><strong>Color scale:</strong> Resolution rate (green = high resolution rate, red = low resolution rate)</li>
                        <li><strong>Clustering:</strong> Nearby issues are grouped together to reduce visual complexity</li>
                        <li><strong>Zoom & Pan:</strong> Interactive map with full zoom and pan capabilities</li>
                    </ul>
                    <p><strong>Key Insights:</strong></p>
                    <ul>
                        <li>Identify problem hotspots where many issues are concentrated</li>
                        <li>Spot areas with poor resolution rates (red bubbles)</li>
                        <li>Discover geographic patterns in municipal service delivery</li>
                        <li>Plan resource allocation based on issue density</li>
                    </ul>
                    <p><strong>Usage:</strong> Click and drag to pan, scroll to zoom, hover over bubbles for details.</p>
                </div>
                '''
            },
            'contributors_map': {
                'title': 'Top Contributors Geographic Distribution',
                'description': '''
                <div class="map-explanation">
                    <h4>👥 Top Contributors - Issue Reporting Patterns</h4>
                    <p><strong>What you see:</strong> Geographic distribution of issues reported by the most active registered users.</p>
                    <ul>
                        <li><strong>Different colors:</strong> Each color represents a different top contributor</li>
                        <li><strong>Dot locations:</strong> Exact locations where each contributor reported issues</li>
                        <li><strong>Legend:</strong> Shows contributor names and their total issue counts</li>
                        <li><strong>Hover details:</strong> Shows specific issue information for each report</li>
                    </ul>
                    <p><strong>Key Insights:</strong></p>
                    <ul>
                        <li>Discover which areas are "dominated" by specific active citizens</li>
                        <li>Identify contributors who focus on specific neighborhoods vs. city-wide reporters</li>
                        <li>Understand citizen engagement patterns across different districts</li>
                        <li>Spot potential coordination opportunities between active contributors</li>
                    </ul>
                    <p><strong>Civic Engagement Analysis:</strong> This map reveals how dedicated citizens contribute to municipal oversight across different areas of Budapest.</p>
                </div>
                '''
            },
            'category_heatmap': {
                'title': 'Issue Category Distribution Map',
                'description': '''
                <div class="map-explanation">
                    <h4>📊 Issue Categories - Geographic Distribution Patterns</h4>
                    <p><strong>What you see:</strong> Six separate maps showing the geographic distribution of major issue categories.</p>
                    <ul>
                        <li><strong>Category-specific views:</strong> Each subplot focuses on one major issue type</li>
                        <li><strong>Spatial patterns:</strong> Reveals where different types of issues cluster</li>
                        <li><strong>Comparative analysis:</strong> Compare distribution patterns across categories</li>
                        <li><strong>Infrastructure insights:</strong> Understand how different municipal systems perform geographically</li>
                    </ul>
                    <p><strong>Key Insights:</strong></p>
                    <ul>
                        <li>Parks & green spaces issues may cluster in residential areas</li>
                        <li>Traffic issues often concentrate along major roads</li>
                        <li>Utilities problems may follow infrastructure layouts</li>
                        <li>Public cleanliness issues might correlate with foot traffic areas</li>
                    </ul>
                    <p><strong>Strategic Value:</strong> Helps municipal planners understand systemic issues and plan targeted improvements.</p>
                </div>
                '''
            }
        }
        
        for map_name, fig in self.maps.items():
            if fig is not None:
                info = map_descriptions.get(map_name, {'title': map_name, 'description': ''})
                
                # Create HTML with map and explanation
                map_html = fig.to_html(include_plotlyjs='cdn')
                
                full_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Járókelő Analysis - {info['title']}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #1e1e1e;
            color: #ffffff;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .map-explanation {{
            background-color: #2d2d2d;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            border-left: 4px solid #00d4aa;
        }}
        .map-explanation h4 {{
            color: #00d4aa;
            margin-top: 0;
        }}
        .map-explanation ul {{
            line-height: 1.6;
        }}
        .back-link {{
            display: inline-block;
            margin: 20px 0;
            padding: 10px 20px;
            background-color: #007acc;
            color: white;
            text-decoration: none;
            border-radius: 5px;
        }}
        .back-link:hover {{
            background-color: #0056b3;
        }}
        .plotly-graph-div {{
            border-radius: 8px;
            overflow: hidden;
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="back-link">← Back to Dashboard</a>
        {map_html}
        {info['description']}
        <a href="index.html" class="back-link">← Back to Dashboard</a>
    </div>
</body>
</html>
"""
                
                html_file = output_path / f"{map_name}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(full_html)
                print(f"  ✓ Exported {map_name}.html")
        
        print(f"✅ Exported {len(self.maps)} interactive maps")
    
    def create_all_maps(self, geocode_limit=500):
        """Create all maps in sequence."""
        print("🗺️  Starting Budapest Interactive Map Generation")
        print("=" * 60)
        
        # Step 1: Load/create coordinates
        coords_count = self.load_or_create_coordinates()
        
        # Step 2: Geocode missing addresses if needed
        if coords_count < 1000:  # If we have few coordinates, try to geocode more
            self.geocode_missing_addresses(limit=geocode_limit)
        
        # Step 3: Cluster nearby issues
        self.cluster_nearby_issues(eps_km=0.1)
        
        # Step 4: Create maps
        print("\nCreating interactive maps...")
        self.create_issue_density_map()
        self.create_contributors_map(top_n=10)
        self.create_category_heatmap()
        
        print(f"\n✅ Created {len(self.maps)} interactive maps")
        return self.maps


def create_budapest_maps(df, geo_df=None, output_dir="docs/eda", geocode_limit=500):
    """
    Convenience function to create all Budapest maps.
    
    Args:
        df: Main DataFrame with issues
        geo_df: DataFrame with GPS coordinates (optional)
        output_dir: Output directory for HTML files
        geocode_limit: Maximum addresses to geocode
        
    Returns:
        BudapestIssueMapper instance with generated maps
    """
    mapper = BudapestIssueMapper(df, geo_df)
    maps = mapper.create_all_maps(geocode_limit=geocode_limit)
    mapper.export_maps(output_dir=output_dir)
    return mapper


if __name__ == "__main__":
    print("Budapest Issue Mapper loaded.")
    print("Use create_budapest_maps() function with your data.")