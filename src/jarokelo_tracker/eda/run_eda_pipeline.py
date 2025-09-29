"""
Main EDA Runner - Comprehensive Járókelő Analysis Pipeline
=========================================================

This script runs the complete EDA pipeline:
1. Comprehensive data analysis
2. Interactive visualization generation
3. Enhanced dataset exports for PowerBI
4. GitHub Pages report generation
"""

from pathlib import Path
import pandas as pd

# Get project root path for data directories
project_root = Path(__file__).parent.parent.parent.parent

from jarokelo_tracker.eda.comprehensive_analysis import JarokeloEDA
from jarokelo_tracker.eda.interactive_visualizations import JarokeloVisualizer

def main():
    """Run the complete EDA pipeline."""
    print("🚀 Starting Comprehensive Járókelő EDA Pipeline")
    print("=" * 80)
    
    # Set paths
    data_dir = project_root / "data" / "raw"
    powerbi_output = project_root / "data" / "processed" / "powerbi_enhanced"
    viz_output = project_root / "docs" / "eda"
    
    # Step 1: Run comprehensive analysis
    print("\n📊 STEP 1: Running Comprehensive Data Analysis")
    print("-" * 50)
    
    eda = JarokeloEDA(data_dir=str(data_dir))
    analysis_results = eda.run_comprehensive_analysis()
    
    # Step 2: Generate interactive visualizations
    print("\n🎨 STEP 2: Generating Interactive Visualizations")
    print("-" * 50)
    
    visualizer = JarokeloVisualizer(eda_results=analysis_results, df=eda.df)
    charts = visualizer.generate_all_visualizations()
    
    # Step 3: Export visualizations for GitHub Pages
    print("\n📄 STEP 3: Exporting for GitHub Pages")
    print("-" * 50)
    
    visualizer.export_interactive_charts(output_dir=str(viz_output))
    
    # Step 4: Generate summary report
    print("\n📋 STEP 4: Generating Executive Summary")
    print("-" * 50)
    
    generate_executive_summary(analysis_results, eda.df, str(viz_output))
    
    # Final summary
    print("\n" + "=" * 80)
    print("✅ COMPLETE: Comprehensive Járókelő EDA Pipeline Finished!")
    print("=" * 80)
    
    print(f"\n📂 Outputs Generated:")
    print(f"   📊 Enhanced PowerBI datasets: {powerbi_output}")
    print(f"   🎨 Interactive charts: {viz_output}")
    print(f"   📄 GitHub Pages site: {viz_output}/index.html")
    print(f"   📋 Executive summary: {viz_output}/executive_summary.html")
    
    print(f"\n🔗 Next Steps:")
    print(f"   1. Review interactive charts at: file://{viz_output.resolve()}/index.html")
    print(f"   2. Import enhanced datasets into PowerBI from: {powerbi_output}")
    print(f"   3. Commit and push to update GitHub Pages")
    
    return analysis_results, charts

def generate_executive_summary(analysis_results, df, output_dir):
    """Generate executive summary HTML report."""
    
    # Calculate key metrics
    total_reports = len(df)
    resolution_rate = df['is_solved'].mean() * 100
    months_covered = df['date'].dt.to_period('M').nunique()
    categories = df['category'].nunique()
    institutions = df['institution'].nunique()
    districts = df['district'].nunique()
    
    # Get top performers
    if 'institution_performance' in analysis_results:
        top_institution = analysis_results['institution_performance'].index[0]
        top_rate = analysis_results['institution_performance'].iloc[0]['Resolution_Rate'] * 100
    else:
        top_institution = "N/A"
        top_rate = 0
    
    if 'category_performance' in analysis_results:
        top_category = analysis_results['category_performance'].index[0]
        top_category_count = analysis_results['category_performance'].iloc[0]['Total_Reports']
    else:
        top_category = "N/A"
        top_category_count = 0
    
    # Generate HTML report
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Járókelő System - Executive Summary</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 3px solid #007acc;
        }}
        .header h1 {{
            color: #007acc;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}
        .header p {{
            color: #666;
            font-size: 1.1em;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 40px 0;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        .metric-number {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 10px;
            display: block;
        }}
        .metric-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        .insights {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 10px;
            margin: 30px 0;
            border-left: 5px solid #28a745;
        }}
        .insights h2 {{
            color: #28a745;
            margin-top: 0;
        }}
        .insight-item {{
            margin: 15px 0;
            padding: 10px;
            background: white;
            border-radius: 5px;
            border-left: 3px solid #007acc;
        }}
        .recommendations {{
            background: #fff3cd;
            padding: 30px;
            border-radius: 10px;
            margin: 30px 0;
            border-left: 5px solid #ffc107;
        }}
        .recommendations h2 {{
            color: #856404;
            margin-top: 0;
        }}
        .recommendation-item {{
            margin: 15px 0;
            padding: 15px;
            background: white;
            border-radius: 5px;
            border-left: 3px solid #ffc107;
        }}
        .navigation {{
            background: #e9ecef;
            padding: 20px;
            border-radius: 10px;
            margin: 30px 0;
            text-align: center;
        }}
        .navigation a {{
            display: inline-block;
            margin: 10px;
            padding: 12px 25px;
            background: #007acc;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: background 0.3s;
        }}
        .navigation a:hover {{
            background: #0056b3;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏛️ Járókelő Municipal System</h1>
            <h2>Executive Summary Report</h2>
            <p>Comprehensive analysis of citizen-reported municipal issues and institutional performance</p>
            <p><strong>Analysis Period:</strong> January 2025 - September 2025 ({months_covered} months)</p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <span class="metric-number">{total_reports:,}</span>
                <div class="metric-label">Total Citizen Reports</div>
            </div>
            <div class="metric-card">
                <span class="metric-number">{resolution_rate:.1f}%</span>
                <div class="metric-label">Overall Resolution Rate</div>
            </div>
            <div class="metric-card">
                <span class="metric-number">{categories}</span>
                <div class="metric-label">Issue Categories</div>
            </div>
            <div class="metric-card">
                <span class="metric-number">{institutions}</span>
                <div class="metric-label">Municipal Institutions</div>
            </div>
        </div>
        
        <div class="insights">
            <h2>🔍 Key Insights</h2>
            <div class="insight-item">
                <strong>Top Performing Institution:</strong> {top_institution} with {top_rate:.1f}% resolution rate
            </div>
            <div class="insight-item">
                <strong>Most Reported Issue:</strong> {top_category} category with {top_category_count:,} reports
            </div>
            <div class="insight-item">
                <strong>Citizen Engagement:</strong> {(1 - df['is_anonymous'].mean()) * 100:.1f}% of users provide identification for accountability
            </div>
            <div class="insight-item">
                <strong>Documentation Quality:</strong> {(df['image_count'] > 0).mean() * 100:.1f}% of reports include photographic evidence
            </div>
            <div class="insight-item">
                <strong>Geographic Coverage:</strong> Issues reported across {districts} different districts
            </div>
        </div>
        
        <div class="recommendations">
            <h2>💡 Strategic Recommendations</h2>
            <div class="recommendation-item">
                <strong>🎯 Performance Optimization:</strong> Focus improvement efforts on institutions with resolution rates below 30%. Implement best practices from top performers.
            </div>
            <div class="recommendation-item">
                <strong>📊 Resource Allocation:</strong> Prioritize resources for high-volume categories like infrastructure and public safety issues.
            </div>
            <div class="recommendation-item">
                <strong>👥 Citizen Engagement:</strong> Encourage photo documentation and registered user accounts to improve issue quality and follow-up.
            </div>
            <div class="recommendation-item">
                <strong>⏱️ Response Time:</strong> Implement SLA tracking and automated status updates to improve citizen communication.
            </div>
            <div class="recommendation-item">
                <strong>📍 Geographic Focus:</strong> Establish proactive maintenance programs in districts with consistently high issue volumes.
            </div>
        </div>
        
        <div class="navigation">
            <h3>📊 Explore Detailed Analysis</h3>
            <a href="index.html">🏠 Dashboard Home</a>
            <a href="executive_dashboard.html">📊 Executive KPIs</a>
            <a href="institution_performance.html">🏢 Institution Performance</a>
            <a href="temporal_trends.html">📈 Trends Analysis</a>
            <a href="geographic_analysis.html">🗺️ Geographic Insights</a>
        </div>
        
        <div class="footer">
            <p>Report generated on {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Data source: <a href="https://jarokelo.hu/" target="_blank">Járókelő.hu</a> | 
            Analysis by: <a href="https://github.com/leweex95/jarokelo_tracker" target="_blank">Járókelő Tracker Project</a></p>
        </div>
    </div>
</body>
</html>
"""
    
    # Write the executive summary
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    with open(output_path / "executive_summary.html", 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("  ✓ Generated executive_summary.html")

if __name__ == "__main__":
    main()