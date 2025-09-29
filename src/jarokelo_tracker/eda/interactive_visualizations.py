"""
Interactive Visualization Module for Járókelő EDA
================================================

This module creates interactive charts and visualizations using Plotly
for GitHub Pages publication and PowerBI complement.
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

# Set default template
pio.templates.default = "plotly_white"

class JarokeloVisualizer:
    """
    Interactive visualization generator for Járókelő municipal data.
    """
    
    def __init__(self, eda_results=None, df=None):
        """
        Initialize visualizer with EDA results and DataFrame.
        
        Args:
            eda_results: Dictionary of analysis results from comprehensive_analysis
            df: Main DataFrame with all data
        """
        self.eda_results = eda_results or {}
        self.df = df
        self.charts = {}
        
    def create_executive_dashboard(self):
        """Create executive-level dashboard with key metrics."""
        if self.eda_results is None or self.df is None:
            print("No data available for visualization")
            return
            
        # Key metrics cards
        total_reports = len(self.df)
        resolution_rate = self.df['is_solved'].mean() * 100
        avg_updates = self.df['update_count'].mean()
        urgency_rate = self.df['contains_urgency'].mean() * 100
        
        # Create metrics cards using indicators
        fig_metrics = make_subplots(
            rows=2, cols=2,
            specs=[[{"type": "indicator"}, {"type": "indicator"}],
                   [{"type": "indicator"}, {"type": "indicator"}]],
            subplot_titles=("Total Reports", "Resolution Rate", "Avg Updates", "Urgency Rate")
        )
        
        # Total Reports
        fig_metrics.add_trace(go.Indicator(
            mode="number",
            value=total_reports,
            title={"text": "Total Reports"},
            number={'font': {'size': 40, 'color': 'darkblue'}},
        ), row=1, col=1)
        
        # Resolution Rate
        fig_metrics.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=resolution_rate,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Resolution Rate (%)"},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkgreen"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 80], 'color': "yellow"},
                    {'range': [80, 100], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ), row=1, col=2)
        
        # Average Updates
        fig_metrics.add_trace(go.Indicator(
            mode="number",
            value=avg_updates,
            title={"text": "Avg Updates per Report"},
            number={'font': {'size': 40, 'color': 'darkgreen'}},
        ), row=2, col=1)
        
        # Urgency Rate
        fig_metrics.add_trace(go.Indicator(
            mode="number+gauge",
            value=urgency_rate,
            title={"text": "Urgency Rate (%)"},
            number={'suffix': "%"},
            gauge={
                'axis': {'range': [None, 20]},
                'bar': {'color': "red"},
                'steps': [{'range': [0, 20], 'color': "lightgray"}],
            }
        ), row=2, col=2)
        
        fig_metrics.update_layout(
            title="Járókelő Municipal System - Executive Dashboard",
            font={'size': 12},
            height=600
        )
        
        self.charts['executive_dashboard'] = fig_metrics
        return fig_metrics
    
    def create_institution_performance_chart(self):
        """Create institution performance comparison chart."""
        if 'institution_performance' not in self.eda_results:
            return None
            
        perf_df = self.eda_results['institution_performance'].reset_index()
        
        # Filter top 15 institutions by report count for readability
        top_institutions = perf_df.nlargest(15, 'Total_Reports')
        
        # Create scatter plot: Resolution Rate vs Total Reports
        fig = px.scatter(
            top_institutions,
            x='Total_Reports',
            y='Resolution_Rate',
            size='Avg_Updates',
            color='Resolution_Rate',
            hover_name='institution',
            hover_data=['Total_Reports', 'Solved_Count', 'Avg_Updates'],
            title="Institution Performance: Resolution Rate vs Report Volume",
            labels={
                'Total_Reports': 'Total Reports Handled',
                'Resolution_Rate': 'Resolution Rate',
                'Avg_Updates': 'Average Updates per Report'
            },
            color_continuous_scale='RdYlGn'
        )
        
        fig.update_layout(
            xaxis_title="Total Reports Handled",
            yaxis_title="Resolution Rate",
            yaxis=dict(tickformat='.1%'),
            height=600
        )
        
        self.charts['institution_performance'] = fig
        return fig
    
    def create_temporal_trends_chart(self):
        """Create temporal trends analysis chart."""
        if self.df is None:
            return None
            
        # Monthly trends
        monthly_data = self.df.groupby([self.df['date'].dt.to_period('M')]).agg({
            'url': 'count',
            'is_solved': 'mean'
        }).reset_index()
        
        monthly_data['date'] = monthly_data['date'].dt.to_timestamp()
        monthly_data['is_solved'] = monthly_data['is_solved'] * 100
        
        # Create dual-axis chart
        fig = make_subplots(
            specs=[[{"secondary_y": True}]],
            subplot_titles=("Monthly Reporting Trends and Resolution Rates",)
        )
        
        # Reports count (bar chart)
        fig.add_trace(
            go.Bar(
                x=monthly_data['date'],
                y=monthly_data['url'],
                name='Reports Count',
                marker_color='lightblue',
                opacity=0.7
            ),
            secondary_y=False,
        )
        
        # Resolution rate (line chart)
        fig.add_trace(
            go.Scatter(
                x=monthly_data['date'],
                y=monthly_data['is_solved'],
                mode='lines+markers',
                name='Resolution Rate (%)',
                line=dict(color='red', width=3),
                marker=dict(size=8)
            ),
            secondary_y=True,
        )
        
        fig.update_xaxes(title_text="Month")
        fig.update_yaxes(title_text="Number of Reports", secondary_y=False)
        fig.update_yaxes(title_text="Resolution Rate (%)", secondary_y=True)
        
        fig.update_layout(
            title="Municipal Issue Reporting: Volume vs Resolution Trends",
            height=500
        )
        
        self.charts['temporal_trends'] = fig
        return fig
    
    def create_category_analysis_chart(self):
        """Create category analysis with treemap and bar charts."""
        if self.df is None:
            return None
            
        # Category analysis data
        category_stats = self.df.groupby('category').agg({
            'url': 'count',
            'is_solved': 'mean',
            'contains_urgency': 'mean',
            'update_count': 'mean'
        }).round(3)
        
        category_stats.columns = ['Total_Reports', 'Resolution_Rate', 'Urgency_Rate', 'Avg_Updates']
        category_stats = category_stats.sort_values('Total_Reports', ascending=False)
        
        # Create treemap
        fig_treemap = px.treemap(
            category_stats.reset_index(),
            path=['category'],
            values='Total_Reports',
            color='Resolution_Rate',
            hover_data=['Urgency_Rate', 'Avg_Updates'],
            title="Issue Categories: Report Volume and Resolution Performance",
            color_continuous_scale='RdYlGn',
            labels={'Resolution_Rate': 'Resolution Rate'}
        )
        
        fig_treemap.update_layout(height=500)
        
        # Create horizontal bar chart for top categories
        top_categories = category_stats.head(10).reset_index()
        
        fig_bar = px.bar(
            top_categories,
            x='Total_Reports',
            y='category',
            color='Resolution_Rate',
            title="Top 10 Issue Categories by Volume",
            labels={'Total_Reports': 'Number of Reports', 'category': 'Issue Category'},
            color_continuous_scale='RdYlGn',
            orientation='h'
        )
        
        fig_bar.update_layout(
            height=500,
            yaxis={'categoryorder': 'total ascending'}
        )
        
        self.charts['category_treemap'] = fig_treemap
        self.charts['category_bars'] = fig_bar
        
        return fig_treemap, fig_bar
    
    def create_geographic_analysis_chart(self):
        """Create geographic analysis chart."""
        if 'district_analysis' not in self.eda_results:
            return None
            
        district_df = self.eda_results['district_analysis'].reset_index()
        district_df = district_df[district_df['district'] != 'Unknown'].head(15)
        
        # Create bubble chart: District performance
        fig = px.scatter(
            district_df,
            x='Total_Reports',
            y='Resolution_Rate',
            size='Avg_Updates',
            color='Anonymous_Rate',
            hover_name='district',
            hover_data=['Total_Reports', 'Resolution_Rate', 'Anonymous_Rate'],
            title="District Performance Analysis",
            labels={
                'Total_Reports': 'Total Reports',
                'Resolution_Rate': 'Resolution Rate',
                'Anonymous_Rate': 'Anonymous Reporting Rate',
                'Avg_Updates': 'Average Updates'
            },
            color_continuous_scale='Viridis'
        )
        
        fig.update_layout(
            xaxis_title="Total Reports",
            yaxis_title="Resolution Rate",
            yaxis=dict(tickformat='.1%'),
            height=600
        )
        
        self.charts['geographic_analysis'] = fig
        return fig
    
    def create_citizen_engagement_chart(self):
        """Create citizen engagement analysis charts."""
        if self.df is None:
            return None
            
        # Anonymous vs Registered comparison
        engagement_data = self.df.groupby('is_anonymous').agg({
            'url': 'count',
            'is_solved': 'mean',
            'image_count': 'mean',
            'description_length': 'mean',
            'contains_urgency': 'mean'
        })
        
        engagement_data.index = ['Registered Users', 'Anonymous Users']
        engagement_data = engagement_data.reset_index()
        
        # Create radar chart for engagement comparison
        categories = ['Resolution Rate', 'Avg Images', 'Description Length', 'Urgency Rate']
        
        fig = go.Figure()
        
        # Normalize data for radar chart (0-1 scale)
        reg_values = [
            engagement_data.loc[0, 'is_solved'],
            engagement_data.loc[0, 'image_count'] / engagement_data['image_count'].max(),
            engagement_data.loc[0, 'description_length'] / engagement_data['description_length'].max(),
            engagement_data.loc[0, 'contains_urgency']
        ]
        
        anon_values = [
            engagement_data.loc[1, 'is_solved'],
            engagement_data.loc[1, 'image_count'] / engagement_data['image_count'].max(),
            engagement_data.loc[1, 'description_length'] / engagement_data['description_length'].max(),
            engagement_data.loc[1, 'contains_urgency']
        ]
        
        fig.add_trace(go.Scatterpolar(
            r=reg_values,
            theta=categories,
            fill='toself',
            name='Registered Users',
            line_color='blue'
        ))
        
        fig.add_trace(go.Scatterpolar(
            r=anon_values,
            theta=categories,
            fill='toself',
            name='Anonymous Users',
            line_color='red'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1]
                )),
            showlegend=True,
            title="Citizen Engagement: Anonymous vs Registered Users",
            height=500
        )
        
        self.charts['citizen_engagement'] = fig
        return fig
    
    def create_status_progression_chart(self):
        """Create status progression and resolution pipeline chart."""
        if self.df is None:
            return None
            
        # Status distribution
        status_counts = self.df['status'].value_counts()
        
        # Create funnel chart
        fig = go.Figure(go.Funnel(
            y=status_counts.index,
            x=status_counts.values,
            textinfo="value+percent initial",
            marker_color=px.colors.qualitative.Set3[:len(status_counts)]
        ))
        
        fig.update_layout(
            title="Issue Resolution Pipeline - Status Distribution",
            height=500
        )
        
        self.charts['status_progression'] = fig
        return fig
    
    def export_interactive_charts(self, output_dir: str = "docs/eda"):
        """Export all interactive charts as HTML files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"Exporting interactive charts to {output_dir}...")
        
        # Export each chart
        for chart_name, fig in self.charts.items():
            if fig is not None:
                html_file = output_path / f"{chart_name}.html"
                fig.write_html(str(html_file))
                print(f"  ✓ Exported {chart_name}.html")
        
        # Create index page
        self._create_chart_index(output_path)
        
        print(f"✅ Exported {len(self.charts)} interactive charts")
    
    def _create_chart_index(self, output_path: Path):
        """Create an index HTML page linking all charts."""
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Járókelő Municipal System - EDA Dashboard</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            border-bottom: 3px solid #007acc;
            padding-bottom: 20px;
        }}
        .header h1 {{
            color: #007acc;
            margin-bottom: 10px;
        }}
        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }}
        .chart-card {{
            background: #f9f9f9;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #007acc;
            transition: transform 0.2s;
        }}
        .chart-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .chart-card h3 {{
            margin-top: 0;
            color: #333;
        }}
        .chart-card a {{
            color: #007acc;
            text-decoration: none;
            font-weight: bold;
        }}
        .chart-card a:hover {{
            text-decoration: underline;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .stat-box {{
            background: linear-gradient(135deg, #007acc, #0099ff);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
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
            <h2>Exploratory Data Analysis Dashboard</h2>
            <p>Interactive insights into citizen-reported municipal issues and institutional performance</p>
        </div>
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-number">14K+</div>
                <div>Total Reports</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">20%</div>
                <div>Resolution Rate</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">16</div>
                <div>Issue Categories</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">50+</div>
                <div>Institutions</div>
            </div>
        </div>
        
        <div class="chart-grid">
"""
        
        # Chart descriptions
        chart_descriptions = {
            'executive_dashboard': {
                'title': '📊 Executive Dashboard',
                'description': 'High-level KPIs and performance metrics for municipal leadership'
            },
            'institution_performance': {
                'title': '🏢 Institution Performance',
                'description': 'Comparative analysis of municipal institution effectiveness and efficiency'
            },
            'temporal_trends': {
                'title': '📈 Temporal Trends',
                'description': 'Monthly reporting patterns and resolution rate trends over time'
            },
            'category_treemap': {
                'title': '🗂️ Issue Categories (Treemap)',
                'description': 'Visual breakdown of issue types by volume and resolution performance'
            },
            'category_bars': {
                'title': '📊 Top Issue Categories',
                'description': 'Most frequently reported municipal issues ranked by volume'
            },
            'geographic_analysis': {
                'title': '🗺️ Geographic Analysis',
                'description': 'District-level performance and citizen engagement patterns'
            },
            'citizen_engagement': {
                'title': '👥 Citizen Engagement',
                'description': 'Comparison of anonymous vs registered user reporting behavior'
            },
            'status_progression': {
                'title': '⚡ Resolution Pipeline',
                'description': 'Issue status distribution and resolution funnel analysis'
            }
        }
        
        # Add chart cards
        for chart_name in self.charts.keys():
            if chart_name in chart_descriptions:
                info = chart_descriptions[chart_name]
                html_content += f"""
            <div class="chart-card">
                <h3>{info['title']}</h3>
                <p>{info['description']}</p>
                <a href="{chart_name}.html" target="_blank">📊 View Interactive Chart</a>
            </div>
"""
        
        html_content += f"""
        </div>
        
        <div class="footer">
            <p>Generated on {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')} | 
            <a href="https://github.com/leweex95/jarokelo_tracker">🔗 View Source Code</a></p>
            <p>Data source: <a href="https://jarokelo.hu/">Járókelő.hu</a> - Hungarian municipal issue reporting platform</p>
        </div>
    </div>
</body>
</html>
"""
        
        with open(output_path / "index.html", 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print("  ✓ Created index.html")
    
    def generate_all_visualizations(self):
        """Generate all visualization charts."""
        print("🎨 Generating interactive visualizations...")
        
        # Create all charts
        self.create_executive_dashboard()
        self.create_institution_performance_chart()
        self.create_temporal_trends_chart()
        self.create_category_analysis_chart()
        self.create_geographic_analysis_chart()
        self.create_citizen_engagement_chart()
        self.create_status_progression_chart()
        
        print(f"✅ Generated {len(self.charts)} interactive charts")
        return self.charts


if __name__ == "__main__":
    # This would typically be run after the comprehensive analysis
    print("Interactive visualization module loaded.")
    print("Use in conjunction with comprehensive_analysis.py")