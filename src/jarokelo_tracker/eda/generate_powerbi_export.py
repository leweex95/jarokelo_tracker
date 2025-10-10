#!/usr/bin/env python3
"""
PowerBI GPS Integration Script - Complete Dataset

This script creates comprehensive GPS-enhanced PowerBI datasets from all raw data.
Includes geographic analytics, spatial clustering, and territorial analysis.
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

def load_all_raw_data() -> pd.DataFrame:
    """Load all data from raw directory with GPS coordinates"""
    raw_dir = Path("data/raw")
    all_data = []

    print("Loading complete GPS-enhanced dataset from raw...")

    for jsonl_file in sorted(raw_dir.glob("*.jsonl")):
        print(f"  Processing {jsonl_file.name}...")
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    record = json.loads(line.strip())
                    all_data.append(record)
                except json.JSONDecodeError as e:
                    print(f"    Warning: Skipping malformed JSON at line {line_num}: {e}")
                    continue

    print(f"Loaded {len(all_data)} records with GPS coordinates")
    df = pd.DataFrame(all_data)
    
    # Fix encoding issues for all text columns
    text_columns = ['title', 'author', 'category', 'institution', 'supporter', 'description', 'status', 'address']
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].astype(str).apply(lambda x: x.encode('utf-8').decode('utf-8') if x else x)
    
    print(f"Fixed encoding for {len(text_columns)} text columns")
    return df

def clean_and_enhance_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean data and add calculated fields"""
    print("Cleaning and enhancing complete dataset...")

    # Convert dates
    df['date'] = pd.to_datetime(df['date'])
    df['resolution_date'] = pd.to_datetime(df['resolution_date'], errors='coerce')
    df['first_authority_response_date'] = pd.to_datetime(df['first_authority_response_date'], errors='coerce')

    # Extract district from address
    def extract_district(address):
        if pd.isna(address):
            return "Unknown"
        # Pattern for Roman numerals I-XXIII (Budapest districts)
        district_match = re.search(r'\b([IXV]+\.?\s*kerület)', str(address), re.IGNORECASE)
        if district_match:
            return district_match.group(1).replace('kerület', 'kerület').strip()
        # Fallback to named districts
        district_names = [
            'Budavár', 'Víziváros', 'Óbuda-Békásmegyer', 'Újpest', 'Belváros-Lipótváros',
            'Terézváros', 'Erzsébetváros', 'Józsefváros', 'Ferencváros', 'Kőbánya',
            'Újbuda', 'Hegyvidék', 'Zugló', 'Pestszentlőrinc-Pestszentimre', 'Rákospalota',
            'Szentendre', 'Soroksár', 'Pestszenterzsébet', 'Kispest', 'Pesterzsébet',
            'Csepel', 'Budafok-Tétény', 'Dunakeszi'
        ]
        for district in district_names:
            if district.lower() in str(address).lower():
                return district
        return "Unknown"

    df['District'] = df['address'].apply(extract_district)

    # Calculate resolution metrics
    df['IsResolved'] = df['status'].str.upper().isin(['MEGOLDOTT', 'MEGOLDVA'])
    df['DaysToResolution'] = (df['resolution_date'] - df['date']).dt.days
    df['DaysToFirstResponse'] = (df['first_authority_response_date'] - df['date']).dt.days

    # GPS coordinate validation and cleaning
    def validate_gps_coord(coord, coord_type='lat'):
        if pd.isna(coord):
            return None
        try:
            coord_float = float(coord)
            if coord_type == 'lat':
                return coord_float if 47.35 <= coord_float <= 47.65 else None
            else:  # longitude
                return coord_float if 18.9 <= coord_float <= 19.4 else None
        except (ValueError, TypeError):
            return None

    df['latitude_clean'] = df['latitude'].apply(lambda x: validate_gps_coord(x, 'lat'))
    df['longitude_clean'] = df['longitude'].apply(lambda x: validate_gps_coord(x, 'lng'))
    df['HasValidGPS'] = (df['latitude_clean'].notna()) & (df['longitude_clean'].notna())

    # Reporter type
    df['ReporterType'] = df['author'].apply(lambda x: 'Anonymous' if pd.isna(x) or 'Anonim' in str(x) else 'Registered')

    # Description length and engagement metrics
    df['DescriptionLength'] = df['description'].str.len().fillna(0)
    df['HasImage'] = df['description'].str.contains(r'\.jpg|\.png|\.jpeg', case=False, na=False)

    # Date components
    df['Year'] = df['date'].dt.year
    df['Month'] = df['date'].dt.month
    df['DayOfWeek'] = df['date'].dt.day_name()
    df['HourOfDay'] = df['date'].dt.hour
    df['IsWeekend'] = df['date'].dt.dayofweek >= 5

    # Response time categories
    df['ResponseTimeCategory'] = pd.cut(df['DaysToFirstResponse'],
                                       bins=[-1, 1, 3, 7, 14, float('inf')],
                                       labels=['Same Day', '2-3 Days', '1 Week', '2 Weeks', 'Over 2 Weeks'])

    print(f"  Enhanced {len(df)} records")
    print(f"  Records with valid GPS: {df['HasValidGPS'].sum()} ({df['HasValidGPS'].mean()*100:.1f}%)")
    print(f"  Date range: {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")

    return df

def create_main_powerbi_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Create the main PowerBI fact table with GPS coordinates"""
    print("Creating main PowerBI dataset with GPS integration...")

    main_df = df.copy()

    # Create sequential IssueID
    main_df = main_df.reset_index(drop=True)
    main_df['IssueID'] = main_df.index + 1

    # Institution performance categorization
    resolution_rates = df.groupby('institution')['IsResolved'].mean()
    def categorize_institution(institution):
        if pd.isna(institution):
            return 'Unknown'
        rate = resolution_rates.get(institution, 0)
        if rate >= 0.8:
            return 'High Performance'
        elif rate >= 0.6:
            return 'Medium Performance'
        else:
            return 'Low Performance'

    main_df['InstitutionPerformanceCategory'] = main_df['institution'].apply(categorize_institution)

    # Select and rename columns for PowerBI
    powerbi_columns = {
        'IssueID': 'IssueID',
        'url': 'SourceURL',
        'title': 'IssueTitle',
        'date': 'ReportDate',
        'resolution_date': 'ResolutionDate',
        'first_authority_response_date': 'FirstResponseDate',
        'category': 'Category',
        'institution': 'ResponsibleInstitution',
        'District': 'District',
        'status': 'CurrentStatus',
        'IsResolved': 'IsResolved',
        'DaysToResolution': 'DaysToResolution',
        'DaysToFirstResponse': 'DaysToFirstResponse',
        'ResponseTimeCategory': 'ResponseTimeCategory',
        'DescriptionLength': 'DescriptionLength',
        'HasImage': 'HasImage',
        'ReporterType': 'ReporterType',
        'address': 'Address',
        'description': 'Description',
        'InstitutionPerformanceCategory': 'InstitutionPerformanceCategory',
        'Year': 'Year',
        'Month': 'Month',
        'DayOfWeek': 'DayOfWeek',
        'HourOfDay': 'HourOfDay',
        'IsWeekend': 'IsWeekend',
        'latitude_clean': 'Latitude',  # GPS COLUMN
        'longitude_clean': 'Longitude',  # GPS COLUMN
        'HasValidGPS': 'HasValidGPS'  # GPS VALIDATION COLUMN
    }

    main_powerbi = main_df[list(powerbi_columns.keys())].rename(columns=powerbi_columns)

    # Format dates for PowerBI
    date_columns = ['ReportDate', 'ResolutionDate', 'FirstResponseDate']
    for col in date_columns:
        main_powerbi[col] = main_powerbi[col].dt.strftime('%Y-%m-%d')
        main_powerbi[col] = main_powerbi[col].replace('NaT', '')

    print(f"  Created main dataset: {len(main_powerbi)} records with {main_powerbi['HasValidGPS'].sum()} GPS coordinates")

    return main_powerbi

def create_district_analysis_with_gps(df: pd.DataFrame) -> pd.DataFrame:
    """Enhanced district analysis with GPS centroids"""
    print("Creating GPS-enhanced district analysis...")

    district_stats = df.groupby('District').agg({
        'url': 'count',
        'IsResolved': ['mean', 'sum'],
        'DaysToResolution': ['mean', 'median'],
        'DaysToFirstResponse': ['mean', 'median'],
        'ReporterType': lambda x: (x == 'Anonymous').mean(),
        'latitude_clean': ['mean', 'min', 'max', 'count'],
        'longitude_clean': ['mean', 'min', 'max'],
        'HasImage': 'mean',
        'IsWeekend': 'mean'
    }).round(3)

    # Flatten column names
    district_stats.columns = [
        'TotalReports', 'ResolutionRate', 'ResolvedCount',
        'AvgDaysToResolution', 'MedianDaysToResolution',
        'AvgDaysToFirstResponse', 'MedianDaysToFirstResponse',
        'AnonymousRate', 'CenterLatitude', 'MinLat', 'MaxLat', 'GPSRecordCount',
        'CenterLongitude', 'MinLng', 'MaxLng',
        'ImageAttachmentRate', 'WeekendReportingRate'
    ]

    # Calculate engagement score (enhanced)
    district_stats['CitizenEngagementScore'] = (
        (district_stats['TotalReports'] / district_stats['TotalReports'].max() * 40) +
        (district_stats['ResolutionRate'] * 30) +
        ((1 - district_stats['AnonymousRate']) * 20) +
        (district_stats['ImageAttachmentRate'] * 10)
    ).round(1)

    # GPS coverage and geographic metrics
    district_stats['GPSCoverageRate'] = (district_stats['GPSRecordCount'] / district_stats['TotalReports']).round(3)
    district_stats['GeographicSpanLat'] = (district_stats['MaxLat'] - district_stats['MinLat']).round(4)
    district_stats['GeographicSpanLng'] = (district_stats['MaxLng'] - district_stats['MinLng']).round(4)

    # Performance categories
    district_stats['PerformanceCategory'] = pd.cut(district_stats['ResolutionRate'],
                                                  bins=[0, 0.5, 0.7, 0.85, 1.0],
                                                  labels=['Critical', 'Needs Attention', 'Good', 'Excellent'])

    district_analysis = district_stats.reset_index()
    district_analysis['DistrictName'] = district_analysis['District']

    print(f"  Created district analysis: {len(district_analysis)} districts with GPS centers")

    return district_analysis

def create_institution_scorecard_with_territories(df: pd.DataFrame) -> pd.DataFrame:
    """Enhanced institution analysis with territorial data"""
    print("Creating institution scorecard with territorial analysis...")

    institution_stats = df.groupby('institution').agg({
        'url': 'count',
        'IsResolved': ['mean', 'sum'],
        'DaysToResolution': ['mean', 'median'],
        'DaysToFirstResponse': ['mean', 'median'],
        'latitude_clean': ['mean', 'min', 'max', 'count'],
        'longitude_clean': ['mean', 'min', 'max'],
        'District': ['nunique', lambda x: list(x.unique())],
        'HasImage': 'mean',
        'ReporterType': lambda x: (x == 'Anonymous').mean()
    }).round(3)

    institution_stats.columns = [
        'TotalIssuesAssigned', 'ResolutionRate', 'ResolvedCount',
        'AvgDaysToResolution', 'MedianDaysToResolution',
        'AvgDaysToFirstResponse', 'MedianDaysToFirstResponse',
        'ServiceCenterLat', 'MinLat', 'MaxLat', 'GPSRecordCount',
        'ServiceCenterLng', 'MinLng', 'MaxLng',
        'DistrictsServedCount', 'DistrictsServedList',
        'ImageResponseRate', 'AnonymousReportingRate'
    ]

    # Calculate efficiency score (enhanced)
    institution_stats['EfficiencyScore'] = (
        (institution_stats['ResolutionRate'] * 50) +
        (np.maximum(0, 30 - institution_stats['AvgDaysToResolution']) / 30 * 30) +
        (np.maximum(0, 7 - institution_stats['AvgDaysToFirstResponse']) / 7 * 20)
    ).round(1)

    # Performance ranking
    institution_stats['PerformanceRanking'] = institution_stats['EfficiencyScore'].rank(ascending=False, method='min')
    institution_stats['PerformanceRanking'] = institution_stats['PerformanceRanking'].fillna(999).astype(int)

    # Workload category
    def categorize_workload(count):
        if count >= 500:
            return 'Very High'
        elif count >= 200:
            return 'High'
        elif count >= 50:
            return 'Medium'
        else:
            return 'Low'

    institution_stats['WorkloadCategory'] = institution_stats['TotalIssuesAssigned'].apply(categorize_workload)

    # Service area coverage
    institution_stats['ServiceAreaCoverage'] = (institution_stats['GPSRecordCount'] / institution_stats['TotalIssuesAssigned']).round(3)

    # Geographic span
    institution_stats['ServiceAreaSpanLat'] = (institution_stats['MaxLat'] - institution_stats['MinLat']).round(4)
    institution_stats['ServiceAreaSpanLng'] = (institution_stats['MaxLng'] - institution_stats['MinLng']).round(4)

    institution_scorecard = institution_stats.reset_index()
    institution_scorecard['InstitutionName'] = institution_scorecard['institution']

    print(f"  Created institution scorecard: {len(institution_scorecard)} institutions with service territories")

    return institution_scorecard

def create_temporal_trends(df: pd.DataFrame) -> pd.DataFrame:
    """Create temporal trends dataset for time series analysis"""
    print("Creating temporal trends analysis...")

    # Daily trends
    daily_stats = df.groupby(df['date'].dt.date).agg({
        'url': 'count',
        'IsResolved': 'mean',
        'DaysToResolution': 'mean',
        'DaysToFirstResponse': 'mean',
        'ReporterType': lambda x: (x == 'Anonymous').mean(),
        'HasImage': 'mean',
        'latitude_clean': 'count'
    }).round(3)

    daily_stats.columns = [
        'TotalReports', 'ResolutionRate', 'AvgDaysToResolution',
        'AvgDaysToFirstResponse', 'AnonymousRate',
        'ImageAttachmentRate', 'GPSCoverageCount'
    ]

    # Add date components
    daily_stats = daily_stats.reset_index()
    daily_stats['Date'] = pd.to_datetime(daily_stats['date'])
    daily_stats['Year'] = daily_stats['Date'].dt.year
    daily_stats['Month'] = daily_stats['Date'].dt.month
    daily_stats['DayOfWeek'] = daily_stats['Date'].dt.day_name()
    daily_stats['IsWeekend'] = daily_stats['Date'].dt.dayofweek >= 5
    daily_stats['WeekOfYear'] = daily_stats['Date'].dt.isocalendar().week

    # Calculate 7-day moving averages
    daily_stats = daily_stats.sort_values('Date')
    daily_stats['Reports_7Day_MA'] = daily_stats['TotalReports'].rolling(7).mean().round(1)
    daily_stats['ResolutionRate_7Day_MA'] = daily_stats['ResolutionRate'].rolling(7).mean().round(3)

    print(f"  Created temporal trends: {len(daily_stats)} daily records")

    return daily_stats[['Date', 'Year', 'Month', 'DayOfWeek', 'IsWeekend', 'WeekOfYear',
                       'TotalReports', 'ResolutionRate', 'AvgDaysToResolution',
                       'AvgDaysToFirstResponse', 'AnonymousRate',
                       'ImageAttachmentRate', 'GPSCoverageCount',
                       'Reports_7Day_MA', 'ResolutionRate_7Day_MA']]

def create_category_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Create category analysis dataset"""
    print("Creating category analysis...")

    category_stats = df.groupby('category').agg({
        'url': 'count',
        'IsResolved': ['mean', 'sum'],
        'DaysToResolution': ['mean', 'median'],
        'DaysToFirstResponse': ['mean', 'median'],
        'ReporterType': lambda x: (x == 'Anonymous').mean(),
        'HasImage': 'mean',
        'institution': 'nunique'
    }).round(3)

    category_stats.columns = [
        'TotalReports', 'ResolutionRate', 'ResolvedCount',
        'AvgDaysToResolution', 'MedianDaysToResolution',
        'AvgDaysToFirstResponse', 'MedianDaysToFirstResponse',
        'AnonymousRate', 'ImageAttachmentRate', 'InstitutionsInvolved'
    ]

    # Calculate category priority score
    category_stats['CategoryPriorityScore'] = (
        (category_stats['TotalReports'] / category_stats['TotalReports'].max() * 50) +
        ((1 - category_stats['ResolutionRate']) * 50)  # Higher weight for unresolved
    ).round(1)

    category_analysis = category_stats.reset_index()
    category_analysis['CategoryName'] = category_analysis['category']

    print(f"  Created category analysis: {len(category_analysis)} categories")

    return category_analysis

def create_geographic_insights(df: pd.DataFrame) -> pd.DataFrame:
    """Create geographic insights for heat map visualizations"""
    print("Creating geographic insights for heat maps...")

    # Filter to GPS-valid records
    gps_df = df.dropna(subset=['latitude_clean', 'longitude_clean']).copy()

    if len(gps_df) == 0:
        print("  No GPS data available for geographic insights")
        return pd.DataFrame()

    # Create 100x100 grid for heat map (more detailed)
    lat_min, lat_max = gps_df['latitude_clean'].min(), gps_df['latitude_clean'].max()
    lng_min, lng_max = gps_df['longitude_clean'].min(), gps_df['longitude_clean'].max()

    grid_size = 100
    lat_bins = np.linspace(lat_min, lat_max, grid_size)
    lng_bins = np.linspace(lng_min, lng_max, grid_size)

    geographic_insights = []

    for i in range(len(lat_bins)-1):
        for j in range(len(lng_bins)-1):
            lat_center = (lat_bins[i] + lat_bins[i+1]) / 2
            lng_center = (lng_bins[j] + lng_bins[j+1]) / 2

            # Count issues in this grid cell
            issues_in_cell = gps_df[
                (gps_df['latitude_clean'] >= lat_bins[i]) &
                (gps_df['latitude_clean'] < lat_bins[i+1]) &
                (gps_df['longitude_clean'] >= lng_bins[j]) &
                (gps_df['longitude_clean'] < lng_bins[j+1])
            ]

            if len(issues_in_cell) > 0:
                geographic_insights.append({
                    'GridID': f"G_{i:03d}_{j:03d}",
                    'CenterLatitude': round(lat_center, 6),
                    'CenterLongitude': round(lng_center, 6),
                    'IssueCount': len(issues_in_cell),
                    'IssueDensity': round(len(issues_in_cell) / 0.0001, 1),  # Per 0.01° cell
                    'AvgResolutionTime': round(issues_in_cell['DaysToResolution'].mean(), 1),
                    'ResolutionRate': round(issues_in_cell['IsResolved'].mean() * 100, 1),
                    'TopCategory': issues_in_cell['category'].mode().iloc[0] if not issues_in_cell['category'].mode().empty else 'Other',
                    'AnonymousRate': round((issues_in_cell['ReporterType'] == 'Anonymous').mean() * 100, 1),
                    'AvgDescriptionLength': round(issues_in_cell['DescriptionLength'].mean(), 1)
                })

    insights_df = pd.DataFrame(geographic_insights)
    print(f"  Created {len(insights_df)} geographic grid cells for heat mapping")

    return insights_df

def create_location_clusters(df: pd.DataFrame) -> pd.DataFrame:
    """Create location clusters for advanced spatial analysis"""
    print("Creating location clusters for spatial analysis...")

    # Filter to GPS-valid records
    gps_df = df.dropna(subset=['latitude_clean', 'longitude_clean']).copy()

    if len(gps_df) < 50:
        print("  Insufficient GPS data for clustering")
        return pd.DataFrame()

    # Use coordinates for clustering
    coords = gps_df[['latitude_clean', 'longitude_clean']].values

    # Standardize coordinates for better clustering
    scaler = StandardScaler()
    coords_scaled = scaler.fit_transform(coords)

    # Create 100 clusters for detailed Budapest analysis
    n_clusters = min(100, len(gps_df) // 10)  # At least 10 points per cluster
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(coords_scaled)

    # Add cluster labels back to dataframe
    gps_df['ClusterID'] = cluster_labels

    # Calculate cluster statistics
    cluster_stats = gps_df.groupby('ClusterID').agg({
        'latitude_clean': 'mean',
        'longitude_clean': 'mean',
        'url': 'count',
        'IsResolved': 'mean',
        'DaysToResolution': 'mean',
        'category': lambda x: x.mode().iloc[0] if not x.mode().empty else 'Other',
        'institution': lambda x: x.mode().iloc[0] if not x.mode().empty else 'Other',
        'District': lambda x: x.mode().iloc[0] if not x.mode().empty else 'Other'
    }).round(3)

    cluster_stats.columns = [
        'ClusterCenterLat', 'ClusterCenterLng', 'IssueCount',
        'ResolutionRate', 'AvgResolutionTime',
        'DominantCategory', 'PrimaryInstitution', 'DominantDistrict'
    ]

    # Add cluster metadata
    cluster_stats['ClusterSize'] = cluster_stats['IssueCount']
    cluster_stats['ClusterType'] = cluster_stats['ClusterSize'].apply(
        lambda x: 'Major Hotspot' if x >= 50 else 'Medium Hotspot' if x >= 20 else 'Minor Cluster'
    )

    clusters_df = cluster_stats.reset_index()
    print(f"  Created {len(clusters_df)} location clusters")

    return clusters_df

def main():
    """Main execution function"""
    print("🗺️ Complete PowerBI GPS Integration Pipeline Starting...")
    print("=" * 70)

    # Load complete GPS-enhanced data
    raw_df = load_all_raw_data()

    # Clean and enhance
    enhanced_df = clean_and_enhance_data(raw_df)

    # Create PowerBI datasets
    print("\n📊 Generating Complete GPS-Enhanced PowerBI Datasets...")

    # Main fact table with GPS
    main_powerbi = create_main_powerbi_dataset(enhanced_df)

    # District analysis with GPS
    district_analysis = create_district_analysis_with_gps(enhanced_df)

    # Institution scorecard with territories
    institution_scorecard = create_institution_scorecard_with_territories(enhanced_df)

    # Temporal trends
    temporal_trends = create_temporal_trends(enhanced_df)

    # Category analysis
    category_analysis = create_category_analysis(enhanced_df)

    # Geographic insights for heat maps
    geographic_insights = create_geographic_insights(enhanced_df)

    # Location clusters
    location_clusters = create_location_clusters(enhanced_df)

    # Save enhanced datasets
    output_dir = Path("data/processed/powerbi")
    output_dir.mkdir(exist_ok=True, parents=True)

    print(f"\n💾 Saving Complete GPS-Enhanced PowerBI Files...")

    main_powerbi.to_csv(output_dir / "jarokelo_main_powerbi_gps.csv", index=False, encoding='utf-8-sig')
    district_analysis.to_csv(output_dir / "district_analysis_gps.csv", index=False, encoding='utf-8-sig')
    institution_scorecard.to_csv(output_dir / "institution_scorecard_gps.csv", index=False, encoding='utf-8-sig')
    temporal_trends.to_csv(output_dir / "temporal_trends_gps.csv", index=False, encoding='utf-8-sig')
    category_analysis.to_csv(output_dir / "category_analysis_gps.csv", index=False, encoding='utf-8-sig')
    geographic_insights.to_csv(output_dir / "geographic_insights.csv", index=False, encoding='utf-8-sig')
    location_clusters.to_csv(output_dir / "location_clusters.csv", index=False, encoding='utf-8-sig')

    # Summary report
    print("\n✅ Complete GPS Integration Pipeline Finished!")
    print("=" * 70)
    print(f"📈 Total Records: {len(main_powerbi):,}")
    print(f"🗺️ GPS Coverage: {main_powerbi['HasValidGPS'].sum():,} records ({main_powerbi['HasValidGPS'].mean()*100:.1f}%)")
    print(f"🏢 Institutions: {len(institution_scorecard)}")
    print(f"🌍 Districts: {len(district_analysis)}")
    print(f"📅 Date Range: {enhanced_df['date'].min().strftime('%Y-%m-%d')} to {enhanced_df['date'].max().strftime('%Y-%m-%d')}")
    print(f"📊 Categories: {len(category_analysis)}")
    print(f"🔥 Heat Map Cells: {len(geographic_insights)}")
    print(f"📍 Location Clusters: {len(location_clusters)}")

    print(f"\n📂 Files Created in {output_dir}:")
    for file in sorted(output_dir.glob("*.csv")):
        size_mb = file.stat().st_size / (1024*1024)
        print(f"  • {file.name}: {size_mb:.2f} MB")

    print("\n🚀 Complete PowerBI GPS Dataset Ready for Dashboard Development!")

if __name__ == "__main__":
    main()