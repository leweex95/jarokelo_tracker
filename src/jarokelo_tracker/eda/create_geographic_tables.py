#!/usr/bin/env python3
"""
Geographic Dimension Tables Generator

Creates budapest_districts_geo.csv and institution_territories.csv for PowerBI spatial analysis.
Includes district boundaries, service areas, and geographic metadata.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

# Budapest district mapping with approximate boundaries and metadata
BUDAPEST_DISTRICTS = {
    "I. kerület": {
        "name": "Budavár", 
        "center_lat": 47.4979, "center_lng": 19.0402,
        "area_km2": 5.33, "population": 25500,
        "type": "Central", "side": "Buda"
    },
    "II. kerület": {
        "name": "Víziváros", 
        "center_lat": 47.5158, "center_lng": 19.0244,
        "area_km2": 36.34, "population": 88200,
        "type": "Residential", "side": "Buda"
    },
    "III. kerület": {
        "name": "Óbuda-Békásmegyer", 
        "center_lat": 47.5674, "center_lng": 19.0555,
        "area_km2": 38.26, "population": 124000,
        "type": "Mixed", "side": "Buda"
    },
    "IV. kerület": {
        "name": "Újpest", 
        "center_lat": 47.5611, "center_lng": 19.0881,
        "area_km2": 18.92, "population": 103000,
        "type": "Residential", "side": "Pest"
    },
    "V. kerület": {
        "name": "Belváros-Lipótváros", 
        "center_lat": 47.4979, "center_lng": 19.0402,
        "area_km2": 2.59, "population": 25500,
        "type": "Central", "side": "Pest"
    },
    "VI. kerület": {
        "name": "Terézváros", 
        "center_lat": 47.5073, "center_lng": 19.0658,
        "area_km2": 2.73, "population": 40600,
        "type": "Central", "side": "Pest"
    },
    "VII. kerület": {
        "name": "Erzsébetváros", 
        "center_lat": 47.4979, "center_lng": 19.0658,
        "area_km2": 2.09, "population": 58300,
        "type": "Central", "side": "Pest"
    },
    "VIII. kerület": {
        "name": "Józsefváros", 
        "center_lat": 47.4845, "center_lng": 19.0751,
        "area_km2": 6.85, "population": 83700,
        "type": "Mixed", "side": "Pest"
    },
    "IX. kerület": {
        "name": "Ferencváros", 
        "center_lat": 47.4751, "center_lng": 19.0818,
        "area_km2": 12.75, "population": 61900,
        "type": "Mixed", "side": "Pest"
    },
    "X. kerület": {
        "name": "Kőbánya", 
        "center_lat": 47.4758, "center_lng": 19.1293,
        "area_km2": 32.38, "population": 78600,
        "type": "Industrial", "side": "Pest"
    },
    "XI. kerület": {
        "name": "Újbuda", 
        "center_lat": 47.4562, "center_lng": 19.0380,
        "area_km2": 33.42, "population": 138100,
        "type": "Residential", "side": "Buda"
    },
    "XII. kerület": {
        "name": "Hegyvidék", 
        "center_lat": 47.5128, "center_lng": 18.9897,
        "area_km2": 26.67, "population": 56500,
        "type": "Residential", "side": "Buda"
    },
    "XIII. kerület": {
        "name": "Angyalföld", 
        "center_lat": 47.5403, "center_lng": 19.0658,
        "area_km2": 14.69, "population": 114700,
        "type": "Mixed", "side": "Pest"
    },
    "XIV. kerület": {
        "name": "Zugló", 
        "center_lat": 47.5208, "center_lng": 19.1083,
        "area_km2": 15.49, "population": 118800,
        "type": "Residential", "side": "Pest"
    },
    "XV. kerület": {
        "name": "Rákospalota-Pestújhely-Újpalota", 
        "center_lat": 47.5628, "center_lng": 19.1214,
        "area_km2": 26.31, "population": 76200,
        "type": "Residential", "side": "Pest"
    },
    "XVI. kerület": {
        "name": "Rákosszentmihály-Sashalom", 
        "center_lat": 47.5158, "center_lng": 19.1744,
        "area_km2": 33.61, "population": 69100,
        "type": "Residential", "side": "Pest"
    },
    "XVII. kerület": {
        "name": "Rákosmente", 
        "center_lat": 47.4979, "center_lng": 19.2274,
        "area_km2": 54.62, "population": 79600,
        "type": "Suburban", "side": "Pest"
    },
    "XVIII. kerület": {
        "name": "Pestszentlőrinc-Pestszentimre", 
        "center_lat": 47.4442, "center_lng": 19.1743,
        "area_km2": 34.87, "population": 95700,
        "type": "Suburban", "side": "Pest"
    },
    "XIX. kerület": {
        "name": "Kispest", 
        "center_lat": 47.4442, "center_lng": 19.1293,
        "area_km2": 34.73, "population": 62300,
        "type": "Suburban", "side": "Pest"
    },
    "XX. kerület": {
        "name": "Pesterzsébet", 
        "center_lat": 47.4173, "center_lng": 19.1083,
        "area_km2": 36.78, "population": 68400,
        "type": "Suburban", "side": "Pest"
    },
    "XXI. kerület": {
        "name": "Csepel", 
        "center_lat": 47.4241, "center_lng": 19.0581,
        "area_km2": 34.51, "population": 75600,
        "type": "Industrial", "side": "Pest"
    },
    "XXII. kerület": {
        "name": "Budafok-Tétény", 
        "center_lat": 47.4307, "center_lng": 19.0081,
        "area_km2": 54.57, "population": 50500,
        "type": "Suburban", "side": "Buda"
    },
    "XXIII. kerület": {
        "name": "Soroksár", 
        "center_lat": 47.3961, "center_lng": 19.1234,
        "area_km2": 61.86, "population": 25500,
        "type": "Suburban", "side": "Pest"
    }
}

def load_gps_enhanced_data() -> pd.DataFrame:
    """Load the GPS-enhanced main dataset"""
    main_file = Path("data/processed/powerbi_gps_enhanced/jarokelo_main_powerbi_gps.csv")
    if not main_file.exists():
        raise FileNotFoundError("GPS-enhanced dataset not found. Run generate_powerbi_gps.py first.")
    
    df = pd.read_csv(main_file)
    print(f"Loaded {len(df)} records from GPS-enhanced dataset")
    return df

def create_district_geo_table() -> pd.DataFrame:
    """Create Budapest districts geographic dimension table"""
    print("Creating Budapest districts geographic dimension table...")
    
    districts_data = []
    for district_id, info in BUDAPEST_DISTRICTS.items():
        districts_data.append({
            'DistrictID': district_id,
            'DistrictName': info['name'],
            'DistrictFullName': f"{district_id}, {info['name']}",
            'CenterLatitude': info['center_lat'],
            'CenterLongitude': info['center_lng'],
            'AreaKmSquared': info['area_km2'],
            'Population': info['population'],
            'PopulationDensity': round(info['population'] / info['area_km2'], 1),
            'DistrictType': info['type'],
            'BudaPestSide': info['side'],
            'IsInnerCity': 1 if info['type'] == 'Central' else 0,
            'IsResidential': 1 if info['type'] == 'Residential' else 0,
            'IsIndustrial': 1 if info['type'] == 'Industrial' else 0,
        })
    
    districts_df = pd.DataFrame(districts_data)
    print(f"  Created {len(districts_df)} district records")
    
    return districts_df

def create_institution_territories_table(main_df: pd.DataFrame) -> pd.DataFrame:
    """Create institution territories table with service areas"""
    print("Creating institution territories table...")
    
    # Calculate service territories for each institution
    institution_territories = []
    
    institutions = main_df.groupby('ResponsibleInstitution').agg({
        'Latitude': ['mean', 'min', 'max', 'count'],
        'Longitude': ['mean', 'min', 'max'],
        'District': ['nunique', lambda x: list(x.unique())]
    }).round(6)
    
    institutions.columns = [
        'ServiceCenterLat', 'MinLat', 'MaxLat', 'RecordCount',
        'ServiceCenterLng', 'MinLng', 'MaxLng',
        'DistrictsServedCount', 'DistrictsServedList'
    ]
    
    for institution_name, row in institutions.iterrows():
        # Calculate service area bounds (simplified rectangular area)
        lat_range = row['MaxLat'] - row['MinLat']
        lng_range = row['MaxLng'] - row['MinLng']
        service_area_km2 = lat_range * lng_range * 12100  # Rough approximation
        
        # Categorize institution type based on name
        institution_type = categorize_institution_type(institution_name)
        
        institution_territories.append({
            'InstitutionName': institution_name,
            'ServiceCenterLatitude': row['ServiceCenterLat'],
            'ServiceCenterLongitude': row['ServiceCenterLng'],
            'ServiceAreaMinLatitude': row['MinLat'],
            'ServiceAreaMaxLatitude': row['MaxLat'],
            'ServiceAreaMinLongitude': row['MinLng'],
            'ServiceAreaMaxLongitude': row['MaxLng'],
            'ServiceAreaKmSquared': round(service_area_km2, 2),
            'DistrictsServed': row['DistrictsServedCount'],
            'DistrictsServedList': ', '.join(row['DistrictsServedList'][:5]),  # Top 5 districts
            'TotalRecords': row['RecordCount'],
            'InstitutionType': institution_type,
            'IsDistrictLevel': 1 if 'kerület' in institution_name.lower() else 0,
            'IsCityWide': 1 if any(keyword in institution_name.lower() for keyword in ['budapest', 'fővárosi', 'bkv', 'főváros']) else 0,
            'IsUtilityCompany': 1 if any(keyword in institution_name.lower() for keyword in ['kft', 'zrt', 'bt', 'kht']) else 0
        })
    
    territories_df = pd.DataFrame(institution_territories)
    print(f"  Created {len(territories_df)} institution territory records")
    
    return territories_df

def categorize_institution_type(name: str) -> str:
    """Categorize institution based on name"""
    name_lower = name.lower()
    
    if any(keyword in name_lower for keyword in ['rendőr', 'rendészet']):
        return 'Law Enforcement'
    elif any(keyword in name_lower for keyword in ['közút', 'út', 'forgalom']):
        return 'Roads & Traffic'
    elif any(keyword in name_lower for keyword in ['park', 'zöld', 'kert']):
        return 'Parks & Environment'
    elif any(keyword in name_lower for keyword in ['víz', 'csatorna', 'hulladék']):
        return 'Utilities'
    elif any(keyword in name_lower for keyword in ['bkv', 'közlekedés', 'vasút']):
        return 'Public Transport'
    elif any(keyword in name_lower for keyword in ['kerület', 'önkormányzat']):
        return 'Local Government'
    elif any(keyword in name_lower for keyword in ['közvilágítás', 'villany', 'lámpa']):
        return 'Public Lighting'
    else:
        return 'Other Municipal'

def create_geographic_insights_table(main_df: pd.DataFrame, districts_df: pd.DataFrame) -> pd.DataFrame:
    """Create geographic insights for heat map visualizations"""
    print("Creating geographic insights for heat maps...")
    
    # Grid-based analysis for heat map
    lat_min, lat_max = main_df['Latitude'].min(), main_df['Latitude'].max()
    lng_min, lng_max = main_df['Longitude'].min(), main_df['Longitude'].max()
    
    # Create 50x50 grid for heat map
    grid_size = 50
    lat_bins = np.linspace(lat_min, lat_max, grid_size)
    lng_bins = np.linspace(lng_min, lng_max, grid_size)
    
    geographic_insights = []
    
    for i in range(len(lat_bins)-1):
        for j in range(len(lng_bins)-1):
            lat_center = (lat_bins[i] + lat_bins[i+1]) / 2
            lng_center = (lng_bins[j] + lng_bins[j+1]) / 2
            
            # Count issues in this grid cell
            issues_in_cell = main_df[
                (main_df['Latitude'] >= lat_bins[i]) & 
                (main_df['Latitude'] < lat_bins[i+1]) &
                (main_df['Longitude'] >= lng_bins[j]) & 
                (main_df['Longitude'] < lng_bins[j+1])
            ]
            
            if len(issues_in_cell) > 0:
                geographic_insights.append({
                    'GridID': f"G_{i:02d}_{j:02d}",
                    'CenterLatitude': round(lat_center, 6),
                    'CenterLongitude': round(lng_center, 6),
                    'IssueCount': len(issues_in_cell),
                    'IssueDensity': round(len(issues_in_cell) / 0.01, 1),  # Per km²
                    'AvgResolutionTime': round(issues_in_cell['DaysToResolution'].mean(), 1),
                    'ResolutionRate': round(issues_in_cell['IsResolved'].mean() * 100, 1),
                    'AvgUrgencyScore': round(issues_in_cell['UrgencyScore'].mean(), 1),
                    'TopCategory': issues_in_cell['Category'].mode().iloc[0] if not issues_in_cell['Category'].mode().empty else 'Other',
                    'AnonymousRate': round((issues_in_cell['ReporterType'] == 'Anonymous').mean() * 100, 1)
                })
    
    insights_df = pd.DataFrame(geographic_insights)
    print(f"  Created {len(insights_df)} geographic grid cells for heat mapping")
    
    return insights_df

def create_location_clusters_table(main_df: pd.DataFrame) -> pd.DataFrame:
    """Create location clusters for advanced spatial analysis"""
    print("Creating location clusters for spatial analysis...")
    
    # Simple clustering based on geographic proximity
    from sklearn.cluster import KMeans
    
    # Use coordinates for clustering
    coords = main_df[['Latitude', 'Longitude']].dropna()
    
    # Create 50 clusters for Budapest
    n_clusters = 50
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(coords)
    
    # Add cluster labels back to main dataframe
    main_df_with_coords = main_df.dropna(subset=['Latitude', 'Longitude']).copy()
    main_df_with_coords['ClusterID'] = cluster_labels
    
    # Calculate cluster statistics
    cluster_stats = main_df_with_coords.groupby('ClusterID').agg({
        'Latitude': 'mean',
        'Longitude': 'mean',
        'IssueID': 'count',
        'IsResolved': 'mean',
        'DaysToResolution': 'mean',
        'UrgencyScore': 'mean',
        'Category': lambda x: x.mode().iloc[0] if not x.mode().empty else 'Other',
        'ResponsibleInstitution': lambda x: x.mode().iloc[0] if not x.mode().empty else 'Other'
    }).round(3)
    
    cluster_stats.columns = [
        'ClusterCenterLat', 'ClusterCenterLng', 'IssueCount',
        'ResolutionRate', 'AvgResolutionTime', 'AvgUrgencyScore',
        'DominantCategory', 'PrimaryInstitution'
    ]
    
    # Add cluster metadata
    cluster_stats['ClusterSize'] = cluster_stats['IssueCount']
    cluster_stats['ClusterType'] = cluster_stats['ClusterSize'].apply(
        lambda x: 'Major Hotspot' if x >= 50 else 'Medium Hotspot' if x >= 20 else 'Minor Cluster'
    )
    cluster_stats['ClusterPriority'] = cluster_stats['AvgUrgencyScore'].apply(
        lambda x: 'High' if x >= 30 else 'Medium' if x >= 15 else 'Low'
    )
    
    clusters_df = cluster_stats.reset_index()
    print(f"  Created {len(clusters_df)} location clusters")
    
    return clusters_df

def main():
    """Main execution function"""
    print("🗺️ Geographic Dimension Tables Generator Starting...")
    print("=" * 60)
    
    # Load GPS-enhanced data
    main_df = load_gps_enhanced_data()
    
    # Create dimension tables
    print("\n📊 Creating Geographic Dimension Tables...")
    
    # Districts geographic table
    districts_geo = create_district_geo_table()
    
    # Institution territories
    institution_territories = create_institution_territories_table(main_df)
    
    # Geographic insights for heat maps  
    geographic_insights = create_geographic_insights_table(main_df, districts_geo)
    
    # Location clusters
    try:
        location_clusters = create_location_clusters_table(main_df)
    except ImportError:
        print("  Skipping location clusters (scikit-learn not available)")
        location_clusters = pd.DataFrame()
    
    # Save dimension tables
    output_dir = Path("data/processed/powerbi_gps_enhanced")
    
    print(f"\n💾 Saving Geographic Dimension Tables...")
    
    districts_geo.to_csv(output_dir / "budapest_districts_geo.csv", index=False, encoding='utf-8-sig')
    institution_territories.to_csv(output_dir / "institution_territories.csv", index=False, encoding='utf-8-sig')
    geographic_insights.to_csv(output_dir / "geographic_insights.csv", index=False, encoding='utf-8-sig')
    
    if not location_clusters.empty:
        location_clusters.to_csv(output_dir / "location_clusters.csv", index=False, encoding='utf-8-sig')
    
    # Summary report
    print("\n✅ Geographic Dimension Tables Complete!")
    print("=" * 60)
    print(f"🏢 Budapest Districts: {len(districts_geo)}")
    print(f"🌍 Institution Territories: {len(institution_territories)}")
    print(f"🔥 Heat Map Grid Cells: {len(geographic_insights)}")
    if not location_clusters.empty:
        print(f"📍 Location Clusters: {len(location_clusters)}")
    
    print(f"\n📂 Files Created:")
    for file in output_dir.glob("*.csv"):
        size_kb = file.stat().st_size / 1024
        print(f"  • {file.name} ({size_kb:.1f} KB)")
    
    print("\n🚀 Geographic Tables Ready for PowerBI!")

if __name__ == "__main__":
    main()