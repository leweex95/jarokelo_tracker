#!/usr/bin/env python3
"""
District Correction Script for PowerBI GPS Data

This script corrects district mapping issues in the processed PowerBI datasets.
Fixes known district names and attempts to resolve Unknown districts using GPS coordinates.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Tuple
import requests
from time import sleep

def correct_known_districts(df: pd.DataFrame) -> pd.DataFrame:
    """Correct known district mapping issues"""
    print("Correcting known district mappings...")

    # For older reports sometimes district was not properly administered
    # only district or sub-district names are present. So we need the below
    # mapping to ensure we can analyze those entries on district level too
    district_corrections = {
        'Belváros-Lipótváros': 'V. kerület',
        'Terézváros': 'VI. kerület',
        'Erzsébetváros': 'VII. kerület',
        'Józsefváros': 'VIII. kerület',
        'Ferencváros': 'IX. kerület',
        'Kőbánya': 'X. kerület',
        'Zugló': 'XIV. kerület',
        'Rákospalota': 'XV. kerület',
        'Újpest': 'IV. kerület',
        'Angyalföld': 'XIII. kerület',
        'Kispest': 'XIX. kerület',
        'Pesterzsébet': 'XX. kerület',
        'Csepel': 'XXI. kerület',
        'Soroksár': 'XXIII. kerület',
        'Pestszentlőrinc': 'XVIII. kerület',
        'Pestszentimre': 'XVIII. kerület',
        'Rákosmente': 'XVII. kerület',
        'Mátyásföld': 'XVI. kerület',
        'Óbuda': 'III. kerület',
        'Békásmegyer': 'III. kerület',
        'Újbuda': 'XI. kerület',
        'Kelenföld': 'XI. kerület',
        'Gazdagrét': 'XI. kerület',
        'Budafok': 'XXII. kerület',
        'Tétény': 'XXII. kerület',
        'Budatétény': 'XXII. kerület',
        'Albertfalva': 'XI. kerület',
        'Lágymányos': 'XI. kerület',
        'Krisztinaváros': 'I. kerület',
        'Várnegyed': 'I. kerület',
        'Tabán': 'I. kerület',
        'Rózsadomb': 'II. kerület',
        'Pasarét': 'II. kerület',
        'Zugló': 'XIV. kerület',
        'Hűvösvölgy': 'II. kerület',
        'Budakeszi út környéke': 'II. kerület',
        'Sashegy': 'XII. kerület',
        'Svábhegy': 'XII. kerület',
        'Normafa': 'XII. kerület',
        'Krisztinaváros': 'I. kerület',
        'Kelenvölgy': 'XI. kerület',
        'Kőérberek': 'XI. kerület',
        'Budafok-Tétény': 'XXII. kerület'
    }

    df['District'] = df['District'].replace(district_corrections)

    corrected_count = sum(1 for old, new in district_corrections.items()
                         if old in df['District'].values)
    print(f"  Corrected {corrected_count} known district mappings")

    return df

def get_budapest_district_centers() -> Dict[str, Tuple[float, float]]:
    """Get approximate center coordinates for Budapest districts"""
    # These are approximate center coordinates for Budapest districts
    district_centers = {
        'I. kerület': (47.4979, 19.0402),    # Budavár
        'II. kerület': (47.5360, 19.0220),   # Rózsadomb
        'III. kerület': (47.5416, 19.0450),  # Óbuda
        'IV. kerület': (47.5625, 19.0892),   # Újpest
        'V. kerület': (47.4979, 19.0500),    # Belváros-Lipótváros
        'VI. kerület': (47.5072, 19.0658),   # Terézváros
        'VII. kerület': (47.5000, 19.0686),  # Erzsébetváros
        'VIII. kerület': (47.4894, 19.0700), # Józsefváros
        'IX. kerület': (47.4774, 19.0914),   # Ferencváros
        'X. kerület': (47.4797, 19.1584),    # Kőbánya
        'XI. kerület': (47.4760, 19.0360),   # Újbuda
        'XII. kerület': (47.4917, 19.0142),  # Hegyvidék
        'XIII. kerület': (47.5298, 19.0806), # Angyalföld
        'XIV. kerület': (47.5098, 19.1164),  # Zugló
        'XV. kerület': (47.5625, 19.1167),   # Rákospalota
        'XVI. kerület': (47.5147, 19.1700),  # Mátyásföld
        'XVII. kerület': (47.4797, 19.2647), # Rákosmente
        'XVIII. kerület': (47.4444, 19.1758), # Pestszentlőrinc
        'XIX. kerület': (47.4528, 19.1397),  # Kispest
        'XX. kerület': (47.4361, 19.1008),   # Pesterzsébet
        'XXI. kerület': (47.4308, 19.0708),  # Csepel
        'XXII. kerület': (47.4267, 19.0400), # Budafok-Tétény
        'XXIII. kerület': (47.3978, 19.1147) # Soroksár
    }
    return district_centers

def assign_district_by_gps(lat: float, lon: float, district_centers: Dict[str, Tuple[float, float]]) -> str:
    """Assign district based on closest center coordinate"""
    if pd.isna(lat) or pd.isna(lon):
        return 'Unknown'

    min_distance = float('inf')
    closest_district = 'Unknown'

    for district, (center_lat, center_lon) in district_centers.items():
        # Calculate Euclidean distance (simplified, not accounting for Earth's curvature)
        distance = np.sqrt((lat - center_lat)**2 + (lon - center_lon)**2)
        if distance < min_distance:
            min_distance = distance
            closest_district = district

    return closest_district

def resolve_unknown_districts(df: pd.DataFrame) -> pd.DataFrame:
    """Attempt to resolve Unknown districts using GPS coordinates"""
    print("Resolving Unknown districts using GPS coordinates...")

    district_centers = get_budapest_district_centers()
    unknown_mask = df['District'] == 'Unknown'

    if unknown_mask.sum() == 0:
        print("  No Unknown districts found")
        return df

    print(f"  Processing {unknown_mask.sum()} Unknown districts...")

    # Apply district assignment to Unknown records
    df.loc[unknown_mask, 'District'] = df.loc[unknown_mask].apply(
        lambda row: assign_district_by_gps(row['Latitude'], row['Longitude'], district_centers),
        axis=1
    )

    resolved_count = unknown_mask.sum() - (df['District'] == 'Unknown').sum()
    print(f"  Resolved {resolved_count} districts using GPS coordinates")

    return df

def main():
    """Main district correction process"""
    print("🗺️ Budapest District Correction Script Starting...")
    print("=" * 50)

    # Load the main dataset
    input_file = Path("data/processed/powerbi/jarokelo_main_powerbi_gps.csv")
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        return

    print(f"Loading data from {input_file}...")
    df = pd.read_csv(input_file, encoding='utf-8-sig')

    original_unknown = (df['District'] == 'Unknown').sum()
    print(f"Original dataset: {len(df)} records, {original_unknown} Unknown districts")

    # Apply corrections
    df = correct_known_districts(df)
    df = resolve_unknown_districts(df)

    # Save corrected dataset
    output_file = input_file
    df.to_csv(output_file, index=False, encoding='utf-8-sig')

    final_unknown = (df['District'] == 'Unknown').sum()
    print(f"Final dataset: {len(df)} records, {final_unknown} Unknown districts")
    print(f"Saved corrected data to {output_file}")

    # Update district analysis file as well
    district_file = Path("data/processed/powerbi/district_analysis_gps.csv")
    if district_file.exists():
        print("Updating district analysis file...")
        district_df = pd.read_csv(district_file, encoding='utf-8-sig')

        # Recalculate district statistics based on corrected main data
        district_stats = df.groupby('District').agg({
            'IssueID': 'count',
            'IsResolved': 'mean',
            'DaysToResolution': 'mean',
            'Latitude': 'mean',
            'Longitude': 'mean'
        }).round(3)

        district_stats.columns = ['TotalIssues', 'ResolutionRate', 'AvgResolutionTime', 'CenterLat', 'CenterLng']
        district_stats = district_stats.reset_index()

        district_stats.to_csv(district_file, index=False, encoding='utf-8-sig')
        print(f"Updated district analysis: {len(district_stats)} districts")

    print("✅ District correction completed!")

if __name__ == "__main__":
    main()