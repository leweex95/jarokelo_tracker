"""
Budapest Interactive Maps Runner
===============================

This script creates interactive maps for the Járókelő municipal issue data:
1. Issue density map with clustering
2. Top contributors geographic distribution
3. Category-based distribution analysis
"""

from pathlib import Path
import pandas as pd

# Get project root path for data directories
project_root = Path(__file__).parent.parent.parent.parent

from jarokelo_tracker.eda.comprehensive_analysis import JarokeloEDA
from jarokelo_tracker.eda.budapest_mapper import create_budapest_maps

def main():
    """Run the Budapest mapping pipeline."""
    print("🗺️  Starting Budapest Interactive Maps Generation")
    print("=" * 80)
    
    # Set paths
    data_dir = project_root / "data" / "raw"
    geo_file = project_root / "data" / "processed" / "powerbi" / "reports_geo.csv"
    output_dir = project_root / "docs" / "eda"
    
    # Step 1: Load main data
    print("\n📊 STEP 1: Loading Járókelő Data")
    print("-" * 50)
    
    eda = JarokeloEDA(data_dir=str(data_dir))
    df = eda.load_data()
    
    # Step 2: Load existing GPS data
    print("\n🌍 STEP 2: Loading GPS Coordinates")
    print("-" * 50)
    
    try:
        geo_df = pd.read_csv(geo_file)
        print(f"Loaded GPS data for {len(geo_df)} issues")
    except FileNotFoundError:
        print("No existing GPS data found - will work with addresses only")
        geo_df = None
    
    # Step 3: Create interactive maps
    print("\n🗺️  STEP 3: Creating Interactive Maps")
    print("-" * 50)
    
    mapper = create_budapest_maps(
        df=df,
        geo_df=geo_df,
        output_dir=str(output_dir),
        geocode_limit=0  # Skip geocoding for now, use existing GPS data only
    )
    
    # Step 4: Update index page with maps
    print("\n📄 STEP 4: Updating Dashboard Index")
    print("-" * 50)
    
    update_dashboard_index(output_dir, mapper.maps.keys())
    
    # Final summary
    print("\n" + "=" * 80)
    print("✅ COMPLETE: Budapest Interactive Maps Generated!")
    print("=" * 80)
    
    print_mapping_summary(mapper, output_dir)
    
    return mapper

def update_dashboard_index(output_dir, map_names):
    """Update the main dashboard index to include map links."""
    index_file = Path(output_dir) / "index.html"
    
    if not index_file.exists():
        print("  ⚠ Dashboard index not found - skipping update")
        return
    
    # Read current index
    with open(index_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Map descriptions for the index
    map_cards = {
        'density_map': {
            'title': '🗺️ Budapest Issue Density Map',
            'description': 'Interactive map showing clustered issues across Budapest with density visualization'
        },
        'contributors_map': {
            'title': '👥 Top Contributors Map',
            'description': 'Geographic distribution of issues reported by the 10 most active contributors'
        },
        'category_heatmap': {
            'title': '📊 Category Distribution Maps',
            'description': 'Spatial analysis of different issue categories across Budapest districts'
        }
    }
    
    # Create map cards HTML
    map_cards_html = ""
    for map_name in map_names:
        if map_name in map_cards:
            card_info = map_cards[map_name]
            map_cards_html += f"""
            <div class="chart-card">
                <h3>{card_info['title']}</h3>
                <p>{card_info['description']}</p>
                <a href="{map_name}.html">🗺️ View Interactive Map</a>
            </div>
"""
    
    # Find the chart grid and add maps before the closing div
    if '</div>' in content and 'chart-grid' in content:
        # Insert before the last chart-grid closing div
        insertion_point = content.rfind('</div>', content.find('chart-grid'))
        if insertion_point > 0:
            updated_content = content[:insertion_point] + map_cards_html + content[insertion_point:]
            
            # Write updated content
            with open(index_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            print(f"  ✓ Updated dashboard index with {len(map_names)} map links")
        else:
            print("  ⚠ Could not find insertion point in index file")
    else:
        print("  ⚠ Could not locate chart grid in index file")

def print_mapping_summary(mapper, output_dir):
    """Print comprehensive summary of mapping results."""
    
    print(f"\n📂 **MAPS GENERATED:**")
    for map_name in mapper.maps.keys():
        print(f"   🗺️ {map_name}.html")
    
    print(f"\n🔍 **GEOGRAPHIC DATA SUMMARY:**")
    if hasattr(mapper, 'df_with_coords'):
        total_issues = len(mapper.df_with_coords)
        with_coords = mapper.df_with_coords['latitude'].notna().sum()
        coord_percentage = (with_coords / total_issues) * 100
        print(f"   📊 Total Issues: {total_issues:,}")
        print(f"   📍 With GPS Coordinates: {with_coords:,} ({coord_percentage:.1f}%)")
        
        if hasattr(mapper, 'clustered_data'):
            clusters = len(mapper.clustered_data)
            print(f"   🎯 Geographic Clusters: {clusters}")
            print(f"   📈 Average Issues per Cluster: {with_coords/clusters:.1f}")
    
    print(f"\n👥 **CONTRIBUTOR ANALYSIS:**")
    if hasattr(mapper, 'df_with_coords'):
        registered = mapper.df_with_coords[mapper.df_with_coords['author'] != 'Anonim Járókelő']
        if len(registered) > 0:
            top_users = registered['author'].value_counts().head(10)
            print(f"   🏆 Top Contributor: {top_users.index[0]} ({top_users.iloc[0]} reports)")
            print(f"   📊 Total Registered Users: {registered['author'].nunique()}")
            print(f"   📈 Avg Reports per Registered User: {len(registered)/registered['author'].nunique():.1f}")
    
    print(f"\n🚀 **IMMEDIATE NEXT STEPS:**")
    print(f"   1. 🌐 View density map: file://{Path(output_dir).resolve()}/density_map.html")
    print(f"   2. 👥 View contributors map: file://{Path(output_dir).resolve()}/contributors_map.html")
    print(f"   3. 📊 View category maps: file://{Path(output_dir).resolve()}/category_heatmap.html")
    print(f"   4. 🏠 Updated dashboard: file://{Path(output_dir).resolve()}/index.html")
    print(f"   5. 🔄 Commit changes: git add -A && git commit -m 'Add interactive Budapest maps'")
    
    print(f"\n📈 **BUSINESS VALUE:**")
    print(f"   🎯 Geographic hotspot identification enabled")
    print(f"   🗺️ Resource allocation optimization insights available")
    print(f"   👥 Citizen engagement pattern analysis ready")
    print(f"   📊 Spatial municipal service delivery assessment complete")

if __name__ == "__main__":
    main()