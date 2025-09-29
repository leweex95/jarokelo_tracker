"""
Comprehensive EDA for Járókelő Municipal Issue Tracking System
============================================================

This module performs advanced exploratory data analysis on citizen-reported
municipal issues to generate insights for municipal management and public transparency.

Key Analysis Areas:
- Municipal Performance Analytics
- Citizen Engagement Intelligence  
- Urban Infrastructure Intelligence
- Operational Excellence Metrics
"""

import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
from datetime import datetime, timedelta
import re
from collections import defaultdict, Counter
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Set plotting style
plt.style.use('default')
sns.set_palette("husl")
pio.templates.default = "plotly_white"

class JarokeloEDA:
    """
    Comprehensive EDA class for Járókelő municipal issue data analysis.
    """
    
    def __init__(self, data_dir: str = "data/raw"):
        """
        Initialize the EDA class with data directory path.
        
        Args:
            data_dir: Path to directory containing JSONL files
        """
        self.data_dir = Path(data_dir)
        self.df = None
        self.analysis_results = {}
        
    def load_data(self):
        """Load all JSONL files and combine into a single DataFrame."""
        print("Loading Járókelő data from JSONL files...")
        
        all_data = []
        jsonl_files = list(self.data_dir.glob("*.jsonl"))
        
        for file_path in sorted(jsonl_files):
            print(f"Loading {file_path.name}...")
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        all_data.append(data)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing line in {file_path}: {e}")
                        continue
        
        self.df = pd.DataFrame(all_data)
        print(f"Loaded {len(self.df)} records from {len(jsonl_files)} files")
        
        # Data preprocessing
        self._preprocess_data()
        return self.df
    
    def _preprocess_data(self):
        """Perform data cleaning and feature engineering."""
        print("Preprocessing data...")
        
        # Convert date to datetime
        self.df['date'] = pd.to_datetime(self.df['date'])
        
        # Extract date components
        self.df['year'] = self.df['date'].dt.year
        self.df['month'] = self.df['date'].dt.month
        self.df['day_of_week'] = self.df['date'].dt.day_name()
        self.df['week_of_year'] = self.df['date'].dt.isocalendar().week
        
        # Create solved status binary variable
        solved_statuses = ['MEGOLDOTT', 'MEGOLDÁSRA VÁR']
        self.df['is_solved'] = self.df['status'].isin(solved_statuses)
        
        # Extract district information from address
        self.df['district'] = self.df['address'].str.extract(r'(\w+\.\s*[Kk]erület)', expand=False)
        self.df['district'] = self.df['district'].fillna('Unknown')
        
        # Clean and standardize category names
        self.df['category'] = self.df['category'].fillna('Egyéb')
        
        # Clean institution names
        self.df['institution'] = self.df['institution'].fillna('Ismeretlen intézmény')
        
        # Create author type (anonymous vs named)
        self.df['is_anonymous'] = self.df['author'] == 'Anonim Járókelő'
        
        # Count images per report
        self.df['image_count'] = self.df['images'].apply(lambda x: len(x) if isinstance(x, list) else 0)
        
        # Calculate description length
        self.df['description_length'] = self.df['description'].str.len()
        
        # Extract update information from description
        self.df['update_count'] = self.df['description'].str.count('FRISSÍTÉS')
        
        # Create urgency score based on keywords in title and description
        urgency_keywords = ['sürgős', 'veszélyes', 'akut', 'azonnali', 'kritikus', 'baleset']
        urgency_pattern = '|'.join(urgency_keywords)
        self.df['contains_urgency'] = (
            self.df['title'].str.contains(urgency_pattern, case=False, na=False) |
            self.df['description'].str.contains(urgency_pattern, case=False, na=False)
        )
        
        print("Data preprocessing completed.")
    
    def generate_data_overview(self):
        """Generate comprehensive data overview and quality assessment."""
        print("\n" + "="*60)
        print("DATA OVERVIEW & QUALITY ASSESSMENT")
        print("="*60)
        
        overview = {
            'total_records': len(self.df),
            'date_range': f"{self.df['date'].min()} to {self.df['date'].max()}",
            'unique_categories': self.df['category'].nunique(),
            'unique_institutions': self.df['institution'].nunique(),
            'unique_districts': self.df['district'].nunique(),
            'solved_rate': self.df['is_solved'].mean(),
            'anonymous_rate': self.df['is_anonymous'].mean(),
            'avg_images_per_report': self.df['image_count'].mean(),
            'avg_description_length': self.df['description_length'].mean(),
        }
        
        self.analysis_results['data_overview'] = overview
        
        # Print overview
        print(f"Total Records: {overview['total_records']:,}")
        print(f"Date Range: {overview['date_range']}")
        print(f"Unique Categories: {overview['unique_categories']}")
        print(f"Unique Institutions: {overview['unique_institutions']}")
        print(f"Unique Districts: {overview['unique_districts']}")
        print(f"Overall Resolution Rate: {overview['solved_rate']:.1%}")
        print(f"Anonymous Reports: {overview['anonymous_rate']:.1%}")
        print(f"Average Images per Report: {overview['avg_images_per_report']:.1f}")
        print(f"Average Description Length: {overview['avg_description_length']:.0f} characters")
        
        # Missing data analysis
        print("\nMISSING DATA ANALYSIS:")
        missing_data = self.df.isnull().sum()
        missing_pct = (missing_data / len(self.df) * 100).round(1)
        missing_df = pd.DataFrame({
            'Missing Count': missing_data,
            'Missing %': missing_pct
        })
        print(missing_df[missing_df['Missing Count'] > 0])
    
    def analyze_municipal_performance(self):
        """Analyze municipal institution performance metrics."""
        print("\n" + "="*60)
        print("MUNICIPAL PERFORMANCE ANALYTICS")
        print("="*60)
        
        # Institution performance analysis
        inst_performance = self.df.groupby('institution').agg({
            'is_solved': ['count', 'sum', 'mean'],
            'update_count': 'mean',
            'image_count': 'mean',
            'description_length': 'mean'
        }).round(3)
        
        inst_performance.columns = ['Total_Reports', 'Solved_Count', 'Resolution_Rate', 
                                  'Avg_Updates', 'Avg_Images', 'Avg_Description_Length']
        
        # Filter institutions with at least 50 reports for meaningful analysis
        inst_performance = inst_performance[inst_performance['Total_Reports'] >= 50]
        inst_performance = inst_performance.sort_values('Resolution_Rate', ascending=False)
        
        self.analysis_results['institution_performance'] = inst_performance
        
        print("TOP PERFORMING INSTITUTIONS (Resolution Rate):")
        print(inst_performance.head(10)[['Total_Reports', 'Resolution_Rate', 'Avg_Updates']])
        
        print("\nBOTTOM PERFORMING INSTITUTIONS:")
        print(inst_performance.tail(5)[['Total_Reports', 'Resolution_Rate', 'Avg_Updates']])
        
        # Category performance analysis
        cat_performance = self.df.groupby('category').agg({
            'is_solved': ['count', 'mean'],
            'update_count': 'mean',
            'contains_urgency': 'mean'
        }).round(3)
        
        cat_performance.columns = ['Total_Reports', 'Resolution_Rate', 'Avg_Updates', 'Urgency_Rate']
        cat_performance = cat_performance.sort_values('Total_Reports', ascending=False)
        
        self.analysis_results['category_performance'] = cat_performance
        
        print("\nCATEGORY PERFORMANCE ANALYSIS:")
        print(cat_performance.head(10))
    
    def analyze_temporal_patterns(self):
        """Analyze temporal patterns in issue reporting and resolution."""
        print("\n" + "="*60)
        print("TEMPORAL PATTERN ANALYSIS")
        print("="*60)
        
        # Monthly reporting trends
        monthly_trends = self.df.groupby(['year', 'month']).agg({
            'url': 'count',
            'is_solved': 'mean',
            'update_count': 'mean'
        }).round(3)
        monthly_trends.columns = ['Reports_Count', 'Resolution_Rate', 'Avg_Updates']
        
        self.analysis_results['monthly_trends'] = monthly_trends
        
        print("MONTHLY REPORTING TRENDS:")
        print(monthly_trends)
        
        # Day of week patterns
        dow_patterns = self.df.groupby('day_of_week').agg({
            'url': 'count',
            'is_solved': 'mean'
        }).round(3)
        dow_patterns.columns = ['Reports_Count', 'Resolution_Rate']
        
        # Reorder by weekday
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        dow_patterns = dow_patterns.reindex(day_order)
        
        self.analysis_results['day_of_week_patterns'] = dow_patterns
        
        print("\nDAY OF WEEK PATTERNS:")
        print(dow_patterns)
    
    def analyze_geographic_patterns(self):
        """Analyze geographic patterns and district-level insights."""
        print("\n" + "="*60)
        print("GEOGRAPHIC PATTERN ANALYSIS")
        print("="*60)
        
        # District analysis
        district_analysis = self.df.groupby('district').agg({
            'url': 'count',
            'is_solved': 'mean',
            'is_anonymous': 'mean',
            'image_count': 'mean',
            'update_count': 'mean'
        }).round(3)
        
        district_analysis.columns = ['Total_Reports', 'Resolution_Rate', 'Anonymous_Rate', 
                                   'Avg_Images', 'Avg_Updates']
        district_analysis = district_analysis.sort_values('Total_Reports', ascending=False)
        
        self.analysis_results['district_analysis'] = district_analysis
        
        print("DISTRICT PERFORMANCE ANALYSIS:")
        print(district_analysis.head(15))
        
        # Category by district heatmap data
        category_district = pd.crosstab(self.df['category'], self.df['district'])
        self.analysis_results['category_district_matrix'] = category_district
    
    def analyze_citizen_engagement(self):
        """Analyze citizen engagement patterns and behavior."""
        print("\n" + "="*60)
        print("CITIZEN ENGAGEMENT INTELLIGENCE")
        print("="*60)
        
        # Anonymous vs registered user analysis
        engagement_analysis = self.df.groupby('is_anonymous').agg({
            'url': 'count',
            'is_solved': 'mean',
            'image_count': 'mean',
            'description_length': 'mean',
            'contains_urgency': 'mean'
        }).round(3)
        
        engagement_analysis.columns = ['Report_Count', 'Resolution_Rate', 'Avg_Images', 
                                     'Avg_Description_Length', 'Urgency_Rate']
        engagement_analysis.index = ['Registered Users', 'Anonymous Users']
        
        self.analysis_results['user_engagement'] = engagement_analysis
        
        print("USER ENGAGEMENT COMPARISON:")
        print(engagement_analysis)
        
        # Image usage patterns
        image_usage = self.df['image_count'].value_counts().sort_index()
        self.analysis_results['image_usage_distribution'] = image_usage
        
        print(f"\nIMAGE USAGE PATTERNS:")
        print(f"Reports with 0 images: {image_usage.get(0, 0)} ({image_usage.get(0, 0)/len(self.df):.1%})")
        print(f"Reports with 1+ images: {image_usage[image_usage.index > 0].sum()} ({image_usage[image_usage.index > 0].sum()/len(self.df):.1%})")
        print(f"Max images in single report: {self.df['image_count'].max()}")
    
    def generate_insights_summary(self):
        """Generate executive summary of key insights."""
        print("\n" + "="*60)
        print("EXECUTIVE INSIGHTS SUMMARY")
        print("="*60)
        
        insights = []
        
        # Key performance insights
        overall_resolution = self.df['is_solved'].mean()
        insights.append(f"Overall municipal resolution rate: {overall_resolution:.1%}")
        
        # Best/worst performers
        if 'institution_performance' in self.analysis_results:
            best_inst = self.analysis_results['institution_performance'].index[0]
            best_rate = self.analysis_results['institution_performance'].iloc[0]['Resolution_Rate']
            insights.append(f"Top performing institution: {best_inst} ({best_rate:.1%} resolution rate)")
            
            worst_inst = self.analysis_results['institution_performance'].index[-1]
            worst_rate = self.analysis_results['institution_performance'].iloc[-1]['Resolution_Rate']
            insights.append(f"Lowest performing institution: {worst_inst} ({worst_rate:.1%} resolution rate)")
        
        # Temporal insights
        if 'monthly_trends' in self.analysis_results:
            latest_month = self.analysis_results['monthly_trends'].index[-1]
            latest_reports = self.analysis_results['monthly_trends'].iloc[-1]['Reports_Count']
            insights.append(f"Latest month ({latest_month[1]}/{latest_month[0]}) had {latest_reports} reports")
        
        # Category insights
        if 'category_performance' in self.analysis_results:
            top_category = self.analysis_results['category_performance'].index[0]
            top_count = self.analysis_results['category_performance'].iloc[0]['Total_Reports']
            insights.append(f"Most reported issue category: {top_category} ({top_count} reports)")
        
        # Engagement insights
        anonymous_rate = self.df['is_anonymous'].mean()
        insights.append(f"Citizen anonymity rate: {anonymous_rate:.1%}")
        
        # Urgency insights
        urgency_rate = self.df['contains_urgency'].mean()
        insights.append(f"Reports containing urgency indicators: {urgency_rate:.1%}")
        
        self.analysis_results['key_insights'] = insights
        
        print("\nKEY INSIGHTS:")
        for i, insight in enumerate(insights, 1):
            print(f"{i}. {insight}")
    
    def export_enhanced_datasets(self, output_dir: str = "data/processed/powerbi_enhanced"):
        """Export enhanced datasets for PowerBI with derived metrics."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"\nExporting enhanced datasets to {output_dir}...")
        
        # 1. Enhanced main dataset with all derived features
        main_export = self.df.copy()
        main_export.to_csv(output_path / "jarokelo_enhanced_main.csv", index=False, encoding='utf-8-sig')
        
        # 2. Institution performance scorecard
        if 'institution_performance' in self.analysis_results:
            self.analysis_results['institution_performance'].to_csv(
                output_path / "institution_performance_scorecard.csv", encoding='utf-8-sig'
            )
        
        # 3. Category performance analysis
        if 'category_performance' in self.analysis_results:
            self.analysis_results['category_performance'].to_csv(
                output_path / "category_performance_analysis.csv", encoding='utf-8-sig'
            )
        
        # 4. District analysis
        if 'district_analysis' in self.analysis_results:
            self.analysis_results['district_analysis'].to_csv(
                output_path / "district_performance_analysis.csv", encoding='utf-8-sig'
            )
        
        # 5. Monthly trends
        if 'monthly_trends' in self.analysis_results:
            monthly_df = self.analysis_results['monthly_trends'].reset_index()
            monthly_df.to_csv(output_path / "monthly_trends_analysis.csv", index=False, encoding='utf-8-sig')
        
        # 6. User engagement metrics
        if 'user_engagement' in self.analysis_results:
            self.analysis_results['user_engagement'].to_csv(
                output_path / "user_engagement_analysis.csv", encoding='utf-8-sig'
            )
        
        # 7. Category-District matrix for heatmaps
        if 'category_district_matrix' in self.analysis_results:
            self.analysis_results['category_district_matrix'].to_csv(
                output_path / "category_district_heatmap.csv", encoding='utf-8-sig'
            )
        
        print(f"Exported {len(list(output_path.glob('*.csv')))} enhanced datasets")
    
    def run_comprehensive_analysis(self):
        """Run the complete EDA pipeline."""
        print("🚀 Starting Comprehensive Járókelő EDA Analysis")
        print("="*80)
        
        # Load and preprocess data
        self.load_data()
        
        # Run all analysis modules
        self.generate_data_overview()
        self.analyze_municipal_performance()
        self.analyze_temporal_patterns()
        self.analyze_geographic_patterns()
        self.analyze_citizen_engagement()
        self.generate_insights_summary()
        
        # Export enhanced datasets
        self.export_enhanced_datasets()
        
        print("\n" + "="*80)
        print("✅ Comprehensive EDA Analysis Complete!")
        print("📊 Check 'data/processed/powerbi_enhanced/' for enhanced datasets")
        print("📈 Analysis results stored in self.analysis_results")
        
        return self.analysis_results


if __name__ == "__main__":
    # Run the comprehensive analysis
    eda = JarokeloEDA()
    results = eda.run_comprehensive_analysis()