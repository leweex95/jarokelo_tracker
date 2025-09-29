#!/usr/bin/env python3
"""
PowerBI GPS Integration Script

This script regenerates all PowerBI CSV files with GPS coordinates from the latest raw3 data.
Adds latitude/longitude columns and enhances geographic analytics capabilities.
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

def load_raw3_data() -> pd.DataFrame:
    """Load all data from raw3 directory with GPS coordinates"""
    raw3_dir = Path("data/raw3")
    all_data = []
    
    print("Loading GPS-enhanced data from raw3...")
    
    for jsonl_file in raw3_dir.glob("*.jsonl"):
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
    return pd.DataFrame(all_data)

def clean_and_enhance_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean data and add calculated fields"""
    print("Cleaning and enhancing dataset...")
    
    # Convert dates
    df['date'] = pd.to_datetime(df['date'])
    df['resolution_date'] = pd.to_datetime(df['resolution_date'], errors='coerce')
    
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
    
    # Urgency score (simplified)
    urgency_keywords = ['sürgős', 'veszélyes', 'baleset', 'törött', 'dugulás', 'áramszünet']
    def calculate_urgency(title, description):
        text = f"{str(title)} {str(description)}".lower()
        score = sum(10 for keyword in urgency_keywords if keyword in text)
        return min(score, 100)
    
    df['UrgencyScore'] = df.apply(lambda row: calculate_urgency(row['title'], row['description']), axis=1)
    
    # Description length
    df['DescriptionLength'] = df['description'].str.len().fillna(0)
    
    # Date components
    df['Year'] = df['date'].dt.year
    df['Month'] = df['date'].dt.month
    df['DayOfWeek'] = df['date'].dt.day_name()
    
    print(f"  Enhanced {len(df)} records")
    print(f"  Records with valid GPS: {df['HasValidGPS'].sum()} ({df['HasValidGPS'].mean()*100:.1f}%)")
    
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
        'category': 'Category',
        'institution': 'ResponsibleInstitution',
        'District': 'District', 
        'status': 'CurrentStatus',
        'IsResolved': 'IsResolved',
        'DaysToResolution': 'DaysToResolution',
        'UrgencyScore': 'UrgencyScore',
        'DescriptionLength': 'DescriptionLength',
        'ReporterType': 'ReporterType',
        'address': 'Address',
        'description': 'Description',
        'InstitutionPerformanceCategory': 'InstitutionPerformanceCategory',
        'Year': 'Year',
        'Month': 'Month', 
        'DayOfWeek': 'DayOfWeek',
        'latitude_clean': 'Latitude',  # NEW GPS COLUMN
        'longitude_clean': 'Longitude',  # NEW GPS COLUMN
        'HasValidGPS': 'HasValidGPS'  # NEW GPS VALIDATION COLUMN
    }
    
    main_powerbi = main_df[list(powerbi_columns.keys())].rename(columns=powerbi_columns)
    
    # Format dates for PowerBI
    main_powerbi['ReportDate'] = main_powerbi['ReportDate'].dt.strftime('%Y-%m-%d')
    main_powerbi['ResolutionDate'] = main_powerbi['ResolutionDate'].dt.strftime('%Y-%m-%d')
    main_powerbi['ResolutionDate'] = main_powerbi['ResolutionDate'].replace('NaT', '')
    
    print(f"  Created main dataset: {len(main_powerbi)} records with {main_powerbi['HasValidGPS'].sum()} GPS coordinates")
    
    return main_powerbi

def create_district_analysis_with_gps(df: pd.DataFrame) -> pd.DataFrame:
    """Enhanced district analysis with geographic data"""
    print("Creating GPS-enhanced district analysis...")
    
    district_stats = df.groupby('District').agg({
        'url': 'count',
        'IsResolved': ['mean', 'sum'],
        'DaysToResolution': 'mean',
        'ReporterType': lambda x: (x == 'Anonymous').mean(),
        'latitude_clean': ['mean', 'count'],
        'longitude_clean': 'mean',
        'UrgencyScore': 'mean'
    }).round(3)
    
    # Flatten column names
    district_stats.columns = [
        'TotalReports', 'ResolutionRate', 'ResolvedCount',
        'AvgDaysToResolution', 'AnonymousRate', 
        'CenterLatitude', 'GPSRecordCount', 'CenterLongitude', 'AvgUrgencyScore'
    ]
    
    # Calculate engagement score
    district_stats['CitizenEngagementScore'] = (
        (district_stats['TotalReports'] / district_stats['TotalReports'].max() * 40) +
        (district_stats['ResolutionRate'] * 30) +
        ((1 - district_stats['AnonymousRate']) * 20) +
        (district_stats['AvgUrgencyScore'] / 100 * 10)
    ).round(1)
    
    # GPS coverage percentage
    district_stats['GPSCoverageRate'] = (district_stats['GPSRecordCount'] / district_stats['TotalReports']).round(3)
    
    district_analysis = district_stats.reset_index()
    district_analysis['DistrictName'] = district_analysis['District']
    
    # Calculate district area density (placeholder - would need real area data)
    district_analysis['IssuesPerKmSquared'] = (district_analysis['TotalReports'] / 10).round(1)  # Placeholder
    
    print(f"  Created district analysis: {len(district_analysis)} districts with GPS centers")
    
    return district_analysis[['DistrictName', 'TotalReports', 'ResolutionRate', 'AvgDaysToResolution',
                              'CitizenEngagementScore', 'AnonymousRate', 'CenterLatitude', 'CenterLongitude',
                              'GPSCoverageRate', 'IssuesPerKmSquared', 'AvgUrgencyScore']]

def create_institution_scorecard_with_territories(df: pd.DataFrame) -> pd.DataFrame:
    """Enhanced institution analysis with territorial data"""
    print("Creating institution scorecard with territorial analysis...")
    
    institution_stats = df.groupby('institution').agg({
        'url': 'count',
        'IsResolved': ['mean', 'sum'],
        'DaysToResolution': 'mean',
        'UrgencyScore': 'mean',
        'latitude_clean': ['mean', 'count'],
        'longitude_clean': 'mean',
        'District': lambda x: x.nunique()
    }).round(3)
    
    institution_stats.columns = [
        'TotalIssuesAssigned', 'ResolutionRate', 'ResolvedCount',
        'AvgDaysToResolution', 'AvgUrgencyScore',
        'ServiceCenterLatitude', 'GPSRecordCount', 'ServiceCenterLongitude',
        'DistrictsServed'
    ]
    
    # Calculate efficiency score (handle NaN values)
    institution_stats['EfficiencyScore'] = (
        (institution_stats['ResolutionRate'].fillna(0) * 50) +
        (np.maximum(0, 30 - institution_stats['AvgDaysToResolution'].fillna(30)) / 30 * 30) +
        (institution_stats['AvgUrgencyScore'].fillna(0) / 100 * 20)
    ).round(1)
    
    # Performance ranking (handle NaN values)
    institution_stats['PerformanceRanking'] = institution_stats['EfficiencyScore'].rank(ascending=False, method='min')
    institution_stats['PerformanceRanking'] = institution_stats['PerformanceRanking'].fillna(999).astype(int)
    
    # Workload category
    def categorize_workload(count):
        if count >= 100:
            return 'High'
        elif count >= 30:
            return 'Medium'
        else:
            return 'Low'
    
    institution_stats['WorkloadCategory'] = institution_stats['TotalIssuesAssigned'].apply(categorize_workload)
    
    # Service area coverage
    institution_stats['ServiceAreaCoverage'] = (institution_stats['GPSRecordCount'] / institution_stats['TotalIssuesAssigned']).round(3)
    
    institution_scorecard = institution_stats.reset_index()
    institution_scorecard['InstitutionName'] = institution_scorecard['institution']
    
    print(f"  Created institution scorecard: {len(institution_scorecard)} institutions with service territories")
    
    return institution_scorecard[['InstitutionName', 'TotalIssuesAssigned', 'ResolutionRate', 'EfficiencyScore',
                                  'PerformanceRanking', 'WorkloadCategory', 'AvgDaysToResolution',
                                  'ServiceCenterLatitude', 'ServiceCenterLongitude', 'DistrictsServed',
                                  'ServiceAreaCoverage', 'AvgUrgencyScore']]

def main():
    """Main execution function"""
    print("🗺️ PowerBI GPS Integration Pipeline Starting...")
    print("=" * 60)
    
    # Load GPS-enhanced data
    raw_df = load_raw3_data()
    
    # Clean and enhance
    enhanced_df = clean_and_enhance_data(raw_df)
    
    # Create PowerBI datasets
    print("\n📊 Generating GPS-Enhanced PowerBI Datasets...")
    
    # Main fact table with GPS
    main_powerbi = create_main_powerbi_dataset(enhanced_df)
    
    # District analysis with GPS
    district_analysis = create_district_analysis_with_gps(enhanced_df)
    
    # Institution scorecard with territories  
    institution_scorecard = create_institution_scorecard_with_territories(enhanced_df)
    
    # Save enhanced datasets
    output_dir = Path("data/processed/powerbi_gps_enhanced")
    output_dir.mkdir(exist_ok=True)
    
    print(f"\n💾 Saving GPS-Enhanced PowerBI Files to {output_dir}...")
    
    main_powerbi.to_csv(output_dir / "jarokelo_main_powerbi_gps.csv", index=False, encoding='utf-8-sig')
    district_analysis.to_csv(output_dir / "district_analysis_gps.csv", index=False, encoding='utf-8-sig')  
    institution_scorecard.to_csv(output_dir / "institution_scorecard_gps.csv", index=False, encoding='utf-8-sig')
    
    # Summary report
    print("\n✅ GPS Integration Complete!")
    print("=" * 60)
    print(f"📈 Total Records: {len(main_powerbi):,}")
    print(f"🗺️ GPS Coverage: {main_powerbi['HasValidGPS'].sum():,} records ({main_powerbi['HasValidGPS'].mean()*100:.1f}%)")
    print(f"🏢 Institutions: {len(institution_scorecard)}")
    print(f"🌍 Districts: {len(district_analysis)}")
    print(f"📅 Date Range: {enhanced_df['date'].min().strftime('%Y-%m-%d')} to {enhanced_df['date'].max().strftime('%Y-%m-%d')}")
    
    print(f"\n📂 Files Created:")
    for file in output_dir.glob("*.csv"):
        size_mb = file.stat().st_size / (1024*1024)
        print(f"  • {file.name} ({size_mb:.1f} MB)")
    
    print("\n🚀 Ready for PowerBI Import!")

if __name__ == "__main__":
    main()