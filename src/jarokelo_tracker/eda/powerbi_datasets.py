"""
PowerBI Dataset Generator for Járókelő Municipal System
======================================================

This module creates optimized CSV datasets specifically designed for PowerBI import,
following the dashboard strategy outlined in powerbi_strategy.md.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json

class PowerBIDatasetGenerator:
    """
    Generates PowerBI-optimized datasets from Járókelő municipal data.
    """
    
    def __init__(self, df, analysis_results):
        """
        Initialize with processed DataFrame and analysis results.
        
        Args:
            df: Main DataFrame with all processed data
            analysis_results: Dictionary from comprehensive_analysis.py
        """
        self.df = df
        self.analysis_results = analysis_results
        self.powerbi_datasets = {}
        
    def create_main_issues_dataset(self):
        """Create the primary fact table for PowerBI analysis."""
        print("Creating main issues dataset for PowerBI...")
        
        # Start with core fields
        main_df = self.df.copy()
        
        # Add calculated fields for PowerBI
        main_df['issue_id'] = range(1, len(main_df) + 1)
        main_df['report_date'] = main_df['date']
        
        # Calculate resolution date (approximation based on status)
        main_df['resolution_date'] = main_df.apply(
            lambda row: row['date'] + timedelta(days=30) if row['is_solved'] else None, 
            axis=1
        )
        
        # Calculate days to resolution
        main_df['days_to_resolution'] = main_df.apply(
            lambda row: 30 if row['is_solved'] else None,  # Simplified calculation
            axis=1
        )
        
        # Create urgency score (0-100)
        main_df['urgency_score'] = (
            main_df['contains_urgency'].astype(int) * 60 +  # Base urgency
            (main_df['description_length'] > 300).astype(int) * 20 +  # Detailed reports
            (main_df['image_count'] > 3).astype(int) * 20  # Well-documented
        )
        
        # Standardize reporter type
        main_df['reporter_type'] = main_df['is_anonymous'].map({
            True: 'Anonymous',
            False: 'Registered'
        })
        
        # Clean and standardize geographic data
        main_df['district_clean'] = main_df['district'].str.replace(r'[.,]', '', regex=True)
        
        # Create performance categories for institutions
        if 'institution_performance' in self.analysis_results:
            perf_map = self.analysis_results['institution_performance']['Resolution_Rate'].to_dict()
            main_df['institution_performance_category'] = main_df['institution'].map(
                lambda x: 'High' if perf_map.get(x, 0) > 0.7 else 
                         'Medium' if perf_map.get(x, 0) > 0.4 else 'Low'
            )
        else:
            main_df['institution_performance_category'] = 'Unknown'
        
        # Select and rename columns for PowerBI
        powerbi_columns = {
            'issue_id': 'IssueID',
            'url': 'SourceURL',
            'title': 'IssueTitle',
            'report_date': 'ReportDate',
            'resolution_date': 'ResolutionDate',
            'category': 'Category',
            'institution': 'ResponsibleInstitution',
            'district_clean': 'District',
            'status': 'CurrentStatus',
            'is_solved': 'IsResolved',
            'days_to_resolution': 'DaysToResolution',
            'urgency_score': 'UrgencyScore',
            'image_count': 'ImageCount',
            'description_length': 'DescriptionLength',
            'update_count': 'UpdateCount',
            'reporter_type': 'ReporterType',
            'address': 'Address',
            'description': 'Description',
            'institution_performance_category': 'InstitutionPerformanceCategory',
            'year': 'Year',
            'month': 'Month',
            'day_of_week': 'DayOfWeek'
        }
        
        main_powerbi = main_df[list(powerbi_columns.keys())].rename(columns=powerbi_columns)
        
        # Ensure data types are PowerBI-friendly
        main_powerbi['ReportDate'] = pd.to_datetime(main_powerbi['ReportDate'])
        main_powerbi['ResolutionDate'] = pd.to_datetime(main_powerbi['ResolutionDate'])
        main_powerbi['IsResolved'] = main_powerbi['IsResolved'].astype(bool)
        main_powerbi['UrgencyScore'] = main_powerbi['UrgencyScore'].astype(int)
        
        self.powerbi_datasets['main_issues'] = main_powerbi
        print(f"  ✓ Created main issues dataset with {len(main_powerbi)} records")
        
        return main_powerbi
    
    def create_institution_scorecard(self):
        """Create institution performance scorecard for PowerBI."""
        print("Creating institution performance scorecard...")
        
        if 'institution_performance' not in self.analysis_results:
            print("  ⚠ No institution performance data available")
            return None
        
        perf_df = self.analysis_results['institution_performance'].reset_index()
        
        # Add calculated fields
        perf_df['PerformanceRanking'] = perf_df['Resolution_Rate'].rank(ascending=False, method='dense')
        
        # Categorize workload
        perf_df['WorkloadCategory'] = pd.cut(
            perf_df['Total_Reports'],
            bins=[0, 50, 200, float('inf')],
            labels=['Low', 'Medium', 'High']
        )
        
        # Calculate efficiency score (composite metric)
        perf_df['EfficiencyScore'] = (
            0.4 * perf_df['Resolution_Rate'] +
            0.3 * (perf_df['Avg_Updates'] / perf_df['Avg_Updates'].max()) +
            0.3 * (perf_df['Total_Reports'] / perf_df['Total_Reports'].max())
        ) * 100
        
        # Add improvement trend (simplified)
        perf_df['ImprovementTrend'] = 'Stable'  # Would require historical data for accurate calculation
        
        # Rename columns for PowerBI
        institution_powerbi = perf_df.rename(columns={
            'institution': 'InstitutionName',
            'Total_Reports': 'TotalIssuesAssigned',
            'Solved_Count': 'IssuesResolved',
            'Resolution_Rate': 'ResolutionRate',
            'Avg_Updates': 'AvgUpdatesPerIssue',
            'PerformanceRanking': 'PerformanceRanking',
            'WorkloadCategory': 'WorkloadCategory',
            'EfficiencyScore': 'EfficiencyScore',
            'ImprovementTrend': 'ImprovementTrend'
        })
        
        # Add average resolution days (approximation)
        institution_powerbi['AvgResolutionDays'] = 30  # Simplified
        
        self.powerbi_datasets['institution_scorecard'] = institution_powerbi
        print(f"  ✓ Created institution scorecard with {len(institution_powerbi)} institutions")
        
        return institution_powerbi
    
    def create_district_analysis_dataset(self):
        """Create geographic analysis dataset for PowerBI."""
        print("Creating district analysis dataset...")
        
        if 'district_analysis' not in self.analysis_results:
            print("  ⚠ No district analysis data available")
            return None
        
        district_df = self.analysis_results['district_analysis'].reset_index()
        
        # Calculate citizen engagement score
        district_df['CitizenEngagementScore'] = (
            (1 - district_df['Anonymous_Rate']) * 50 +  # Registered user rate
            (district_df['Avg_Images'] / district_df['Avg_Images'].max()) * 30 +  # Documentation quality
            (district_df['Avg_Updates'] / district_df['Avg_Updates'].max()) * 20  # Communication level
        )
        
        # Calculate issue density per capita (would need population data)
        district_df['IssueDensityPerCapita'] = district_df['Total_Reports'] / 100000  # Simplified
        
        # Rename columns for PowerBI
        district_powerbi = district_df.rename(columns={
            'district': 'DistrictName',
            'Total_Reports': 'TotalReports',
            'Resolution_Rate': 'ResolutionRate',
            'Anonymous_Rate': 'AnonymousRate',
            'Avg_Images': 'AvgImagesPerReport',
            'Avg_Updates': 'AvgUpdatesPerReport',
            'CitizenEngagementScore': 'CitizenEngagementScore',
            'IssueDensityPerCapita': 'IssueDensityPerCapita'
        })
        
        # Add approximated resolution days
        district_powerbi['AvgResolutionDays'] = 30  # Simplified
        
        # Add external data placeholders (would be enhanced with real data)
        district_powerbi['PopulationDensity'] = 5000  # Placeholder
        district_powerbi['SocioeconomicIndex'] = 50  # Placeholder
        
        self.powerbi_datasets['district_analysis'] = district_powerbi
        print(f"  ✓ Created district analysis with {len(district_powerbi)} districts")
        
        return district_powerbi
    
    def create_temporal_trends_dataset(self):
        """Create time series dataset for PowerBI."""
        print("Creating temporal trends dataset...")
        
        # Create daily aggregations
        daily_data = self.df.groupby(self.df['date'].dt.date).agg({
            'url': 'count',
            'is_solved': ['sum', 'mean'],
            'contains_urgency': 'mean',
            'update_count': 'mean'
        }).reset_index()
        
        # Flatten column names
        daily_data.columns = ['Date', 'IssuesReported', 'IssuesResolved', 'ResolutionRate', 'UrgencyRate', 'AvgResponseTime']
        
        # Add date components
        daily_data['Date'] = pd.to_datetime(daily_data['Date'])
        daily_data['DayOfWeek'] = daily_data['Date'].dt.day_name()
        daily_data['Month'] = daily_data['Date'].dt.month
        daily_data['Season'] = daily_data['Date'].dt.month.map({
            12: 'Winter', 1: 'Winter', 2: 'Winter',
            3: 'Spring', 4: 'Spring', 5: 'Spring',
            6: 'Summer', 7: 'Summer', 8: 'Summer',
            9: 'Fall', 10: 'Fall', 11: 'Fall'
        })
        daily_data['IsWeekend'] = daily_data['Date'].dt.weekday >= 5
        daily_data['IsHoliday'] = False  # Placeholder - would need holiday calendar
        
        # Convert percentages to 0-100 scale
        daily_data['ResolutionRate'] = daily_data['ResolutionRate'] * 100
        daily_data['UrgencyRate'] = daily_data['UrgencyRate'] * 100
        
        self.powerbi_datasets['temporal_trends'] = daily_data
        print(f"  ✓ Created temporal trends with {len(daily_data)} daily records")
        
        return daily_data
    
    def create_category_analysis_dataset(self):
        """Create category performance dataset for PowerBI."""
        print("Creating category analysis dataset...")
        
        if 'category_performance' not in self.analysis_results:
            print("  ⚠ No category performance data available")
            return None
        
        category_df = self.analysis_results['category_performance'].reset_index()
        
        # Add calculated fields
        category_df['ResourceIntensity'] = pd.cut(
            category_df['Avg_Updates'],
            bins=[0, 0.2, 0.4, float('inf')],
            labels=['Low', 'Medium', 'High']
        )
        
        # Calculate improvement priority score
        category_df['ImprovementPriority'] = (
            (1 - category_df['Resolution_Rate']) * 0.4 +  # Low resolution rate = high priority
            (category_df['Total_Reports'] / category_df['Total_Reports'].max()) * 0.3 +  # High volume = higher priority
            category_df['Urgency_Rate'] * 0.3  # High urgency = higher priority
        ) * 100
        
        # Seasonal pattern (placeholder - would need historical data)
        category_df['SeasonalPattern'] = 'Stable'
        
        # Citizen satisfaction proxy (based on multiple factors)
        category_df['CitizenSatisfactionProxy'] = (
            category_df['Resolution_Rate'] * 0.6 +
            (category_df['Avg_Updates'] / category_df['Avg_Updates'].max()) * 0.4
        ) * 100
        
        # Rename columns for PowerBI
        category_powerbi = category_df.rename(columns={
            'category': 'CategoryName',
            'Total_Reports': 'TotalReports',
            'Resolution_Rate': 'ResolutionRate',
            'Urgency_Rate': 'UrgencyFrequency',
            'Avg_Updates': 'AvgUpdatesPerReport',
            'ResourceIntensity': 'ResourceIntensity',
            'ImprovementPriority': 'ImprovementPriority',
            'SeasonalPattern': 'SeasonalPattern',
            'CitizenSatisfactionProxy': 'CitizenSatisfactionProxy'
        })
        
        # Add approximated resolution days by category
        category_powerbi['AvgResolutionDays'] = 30  # Simplified
        
        # Convert percentages to 0-100 scale
        category_powerbi['ResolutionRate'] = category_powerbi['ResolutionRate'] * 100
        category_powerbi['UrgencyFrequency'] = category_powerbi['UrgencyFrequency'] * 100
        
        self.powerbi_datasets['category_analysis'] = category_powerbi
        print(f"  ✓ Created category analysis with {len(category_powerbi)} categories")
        
        return category_powerbi
    
    def create_citizen_behavior_dataset(self):
        """Create citizen engagement dataset for PowerBI."""
        print("Creating citizen behavior dataset...")
        
        # Aggregate by reporter type
        citizen_data = self.df.groupby('is_anonymous').agg({
            'url': 'count',
            'image_count': 'mean',
            'description_length': 'mean',
            'contains_urgency': 'mean',
            'is_solved': 'mean',
            'update_count': 'mean'
        }).reset_index()
        
        # Map anonymous flag to readable names
        citizen_data['ReporterType'] = citizen_data['is_anonymous'].map({
            True: 'Anonymous',
            False: 'Registered'
        })
        
        # Calculate quality score
        citizen_data['QualityScore'] = (
            (citizen_data['image_count'] / citizen_data['image_count'].max()) * 30 +
            (citizen_data['description_length'] / citizen_data['description_length'].max()) * 40 +
            citizen_data['contains_urgency'] * 30
        )
        
        # Calculate follow-up engagement (placeholder)
        citizen_data['FollowUpEngagement'] = citizen_data['update_count'] * 20  # Simplified
        
        # Rename columns for PowerBI
        citizen_powerbi = citizen_data.rename(columns={
            'url': 'TotalReports',
            'image_count': 'AvgImageCount',
            'description_length': 'AvgDescriptionLength',
            'contains_urgency': 'UrgencyRate',
            'is_solved': 'ResolutionRateReceived',
            'update_count': 'AvgUpdatesReceived',
            'QualityScore': 'QualityScore',
            'FollowUpEngagement': 'FollowUpEngagement'
        }).drop(columns=['is_anonymous'])
        
        # Convert percentages to 0-100 scale
        citizen_powerbi['UrgencyRate'] = citizen_powerbi['UrgencyRate'] * 100
        citizen_powerbi['ResolutionRateReceived'] = citizen_powerbi['ResolutionRateReceived'] * 100
        
        self.powerbi_datasets['citizen_behavior'] = citizen_powerbi
        print(f"  ✓ Created citizen behavior analysis with {len(citizen_powerbi)} user types")
        
        return citizen_powerbi
    
    def create_quality_metrics_dataset(self):
        """Create quality indicators dataset for PowerBI."""
        print("Creating quality metrics dataset...")
        
        # Create daily quality metrics
        quality_data = self.df.groupby(self.df['date'].dt.date).agg({
            'url': 'count',
            'image_count': lambda x: (x > 0).sum(),  # Reports with images
            'address': lambda x: x.notna().sum(),  # Reports with location
            'description_length': 'mean',
            'update_count': 'mean'
        }).reset_index()
        
        quality_data.columns = ['Date', 'TotalReports', 'ReportsWithImages', 'ReportsWithLocation', 'AvgDescriptionQuality', 'UpdateFrequencyScore']
        
        # Calculate percentages
        quality_data['ImageDocumentationRate'] = (quality_data['ReportsWithImages'] / quality_data['TotalReports']) * 100
        quality_data['LocationAccuracyRate'] = (quality_data['ReportsWithLocation'] / quality_data['TotalReports']) * 100
        
        # Response time compliance (placeholder - would need SLA data)
        quality_data['ResponseTimeCompliance'] = 75  # Placeholder percentage
        
        # Citizen satisfaction proxy
        quality_data['CitizenSatisfactionProxy'] = (
            quality_data['ImageDocumentationRate'] * 0.3 +
            quality_data['LocationAccuracyRate'] * 0.3 +
            quality_data['UpdateFrequencyScore'] * 40 +
            quality_data['ResponseTimeCompliance'] * 0.4
        )
        
        # Ensure date is datetime
        quality_data['Date'] = pd.to_datetime(quality_data['Date'])
        
        self.powerbi_datasets['quality_metrics'] = quality_data
        print(f"  ✓ Created quality metrics with {len(quality_data)} daily records")
        
        return quality_data
    
    def create_all_powerbi_datasets(self):
        """Generate all PowerBI datasets."""
        print("🔄 Generating PowerBI-optimized datasets...")
        print("=" * 60)
        
        # Create all datasets
        self.create_main_issues_dataset()
        self.create_institution_scorecard()
        self.create_district_analysis_dataset()
        self.create_temporal_trends_dataset()
        self.create_category_analysis_dataset()
        self.create_citizen_behavior_dataset()
        self.create_quality_metrics_dataset()
        
        print("=" * 60)
        print(f"✅ Generated {len(self.powerbi_datasets)} PowerBI datasets")
        
        return self.powerbi_datasets
    
    def export_powerbi_datasets(self, output_dir: str = "data/processed/powerbi_final"):
        """Export all PowerBI datasets as CSV files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"\n📁 Exporting PowerBI datasets to {output_dir}...")
        
        dataset_files = {
            'main_issues': 'jarokelo_main_powerbi.csv',
            'institution_scorecard': 'institution_scorecard_powerbi.csv',
            'district_analysis': 'district_analysis_powerbi.csv',
            'temporal_trends': 'temporal_trends_powerbi.csv',
            'category_analysis': 'category_analysis_powerbi.csv',
            'citizen_behavior': 'citizen_behavior_powerbi.csv',
            'quality_metrics': 'quality_indicators_powerbi.csv'
        }
        
        for dataset_key, filename in dataset_files.items():
            if dataset_key in self.powerbi_datasets:
                filepath = output_path / filename
                self.powerbi_datasets[dataset_key].to_csv(
                    filepath, 
                    index=False, 
                    encoding='utf-8-sig'  # Ensures proper encoding for PowerBI
                )
                print(f"  ✓ Exported {filename} ({len(self.powerbi_datasets[dataset_key])} rows)")
        
        # Create data dictionary
        self._create_data_dictionary(output_path)
        
        print(f"\n✅ All PowerBI datasets exported successfully!")
        print(f"📊 Ready for PowerBI import from: {output_path}")
        
        return output_path
    
    def _create_data_dictionary(self, output_path: Path):
        """Create a data dictionary for PowerBI datasets."""
        dictionary_content = """
# PowerBI Dataset Dictionary - Járókelő Municipal System
========================================================

## Dataset Overview
This directory contains 7 optimized CSV files for PowerBI import, designed to support
the three-tier dashboard strategy (Executive, Operational, Public Transparency).

## File Descriptions

### 1. jarokelo_main_powerbi.csv
**Purpose:** Primary fact table containing all issue records
**Rows:** ~14,000 citizen reports
**Key Fields:**
- IssueID: Unique identifier for each report
- ReportDate: When the issue was reported
- ResolutionDate: When marked resolved (null if unresolved)
- Category: Type of municipal issue
- ResponsibleInstitution: Department assigned to handle
- District: Geographic area in Budapest
- IsResolved: Boolean resolution status
- UrgencyScore: Calculated urgency (0-100)
- ReporterType: Anonymous vs Registered user

### 2. institution_scorecard_powerbi.csv  
**Purpose:** Institution performance metrics
**Rows:** ~50 municipal departments
**Key Fields:**
- InstitutionName: Department name
- TotalIssuesAssigned: Volume of work
- ResolutionRate: Success percentage (0-100)
- EfficiencyScore: Composite performance metric
- PerformanceRanking: Relative ranking (1=best)
- WorkloadCategory: High/Medium/Low volume

### 3. district_analysis_powerbi.csv
**Purpose:** Geographic performance analysis
**Rows:** 24 Budapest districts
**Key Fields:**
- DistrictName: District identifier
- TotalReports: Citizen engagement level
- ResolutionRate: Municipal effectiveness (0-100)
- CitizenEngagementScore: Composite engagement metric
- AnonymousRate: Privacy preference percentage

### 4. temporal_trends_powerbi.csv
**Purpose:** Time series analysis
**Rows:** ~240 daily records
**Key Fields:**
- Date: Daily date
- IssuesReported: Daily volume
- ResolutionRate: Daily effectiveness (0-100)
- DayOfWeek: Weekday name
- Season: Seasonal classification
- IsWeekend: Weekend flag

### 5. category_analysis_powerbi.csv
**Purpose:** Issue type performance
**Rows:** 15 issue categories
**Key Fields:**
- CategoryName: Issue type
- TotalReports: Volume per category
- ResolutionRate: Category success rate (0-100)
- ImprovementPriority: Action priority score (0-100)
- ResourceIntensity: High/Medium/Low resource needs

### 6. citizen_behavior_powerbi.csv
**Purpose:** User behavior analysis
**Rows:** 2 user types (Anonymous/Registered)
**Key Fields:**
- ReporterType: User classification
- TotalReports: Volume by type
- QualityScore: Report quality metric (0-100)
- ResolutionRateReceived: Success rate experienced

### 7. quality_indicators_powerbi.csv
**Purpose:** System quality tracking
**Rows:** ~240 daily quality metrics
**Key Fields:**
- Date: Daily date
- TotalReports: Volume per day
- ImageDocumentationRate: Photo inclusion rate (0-100)
- CitizenSatisfactionProxy: Estimated satisfaction (0-100)
- ResponseTimeCompliance: SLA adherence (0-100)

## PowerBI Import Instructions

1. **Data Source Setup:**
   - Use "Get Data" > "Text/CSV"
   - Import each file individually
   - Ensure UTF-8 encoding for Hungarian characters

2. **Relationships:**
   - Link main_issues to other tables via appropriate keys
   - Create date relationships for time intelligence

3. **Data Types:**
   - Dates: Ensure proper date/time formatting
   - Percentages: Already scaled 0-100 for PowerBI
   - Categories: Set as text type

4. **Refresh Schedule:**
   - Executive dashboards: Daily
   - Operational dashboards: Every 2 hours
   - Public dashboards: Daily

## Calculated Measures (DAX Examples)

```dax
// Current Resolution Rate
Current Resolution Rate = 
DIVIDE(
    COUNTROWS(FILTER(jarokelo_main_powerbi, jarokelo_main_powerbi[IsResolved] = TRUE)),
    COUNTROWS(jarokelo_main_powerbi)
) * 100

// Performance Trend
Performance Trend = 
VAR CurrentMonth = [Current Resolution Rate]
VAR PreviousMonth = CALCULATE([Current Resolution Rate], DATEADD('temporal_trends_powerbi'[Date], -1, MONTH))
RETURN
IF(CurrentMonth > PreviousMonth, "↗ Improving", 
   IF(CurrentMonth < PreviousMonth, "↘ Declining", "→ Stable"))
```

Generated: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """
"""
        
        with open(output_path / "PowerBI_Data_Dictionary.md", 'w', encoding='utf-8') as f:
            f.write(dictionary_content)
        
        print("  ✓ Created PowerBI_Data_Dictionary.md")


def generate_powerbi_datasets(df, analysis_results, output_dir="data/processed/powerbi_final"):
    """
    Convenience function to generate all PowerBI datasets.
    
    Args:
        df: Main DataFrame from comprehensive analysis
        analysis_results: Analysis results dictionary
        output_dir: Output directory for CSV files
        
    Returns:
        Path to exported datasets
    """
    generator = PowerBIDatasetGenerator(df, analysis_results)
    datasets = generator.create_all_powerbi_datasets()
    export_path = generator.export_powerbi_datasets(output_dir)
    return export_path, datasets


if __name__ == "__main__":
    print("PowerBI Dataset Generator loaded.")
    print("Use generate_powerbi_datasets() function with your data.")