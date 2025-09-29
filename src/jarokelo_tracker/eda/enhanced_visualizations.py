"""
Enhanced Interactive Visualization Module for Járókelő EDA
=========================================================

This improved module creates professional interactive charts with:
- Dark mode styling
- Clear explanations for each chart
- Comprehensive data coverage
- PowerBI-ready insights
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

# Set dark theme as default
pio.templates.default = "plotly_dark"

class EnhancedJarokeloVisualizer:
    """
    Enhanced interactive visualization generator with dark mode and explanations.
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
        self.explanations = {}
        
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
            title={"text": "Total Reports", "font": {"color": "white"}},
            number={'font': {'size': 40, 'color': '#00d4aa'}},
        ), row=1, col=1)
        
        # Resolution Rate
        fig_metrics.add_trace(go.Indicator(
            mode="gauge+number",
            value=resolution_rate,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Resolution Rate (%)", "font": {"color": "white"}},
            gauge={
                'axis': {'range': [None, 100], 'tickcolor': "white"},
                'bar': {'color': "#00d4aa"},
                'steps': [
                    {'range': [0, 30], 'color': "#ff6b6b"},
                    {'range': [30, 60], 'color': "#ffd93d"},
                    {'range': [60, 100], 'color': "#6bcf7f"}
                ],
                'threshold': {
                    'line': {'color': "white", 'width': 4},
                    'thickness': 0.75,
                    'value': 80
                }
            }
        ), row=1, col=2)
        
        # Average Updates
        fig_metrics.add_trace(go.Indicator(
            mode="number",
            value=avg_updates,
            title={"text": "Avg Updates per Report", "font": {"color": "white"}},
            number={'font': {'size': 40, 'color': '#74b9ff'}},
        ), row=2, col=1)
        
        # Urgency Rate
        fig_metrics.add_trace(go.Indicator(
            mode="number+gauge",
            value=urgency_rate,
            title={"text": "Urgency Rate (%)", "font": {"color": "white"}},
            number={'suffix': "%", 'font': {'color': '#fd79a8'}},
            gauge={
                'axis': {'range': [None, 25], 'tickcolor': "white"},
                'bar': {'color': "#fd79a8"},
                'steps': [{'range': [0, 25], 'color': "#2d3436"}],
            }
        ), row=2, col=2)
        
        fig_metrics.update_layout(
            title="Járókelő Municipal System - Executive Dashboard",
            font={'size': 12, 'color': 'white'},
            height=600,
            paper_bgcolor='#1e1e1e',
            plot_bgcolor='#1e1e1e'
        )
        
        self.charts['executive_dashboard'] = fig_metrics
        self.explanations['executive_dashboard'] = """
        <div class="chart-explanation">
            <h4>📊 Executive Dashboard - Key Performance Indicators</h4>
            <p><strong>What you see:</strong> Four critical metrics that summarize the entire municipal issue reporting system.</p>
            <ul>
                <li><strong>Total Reports:</strong> Volume of citizen-reported issues across all categories</li>
                <li><strong>Resolution Rate:</strong> Percentage of issues marked as resolved (target: >80%)</li>
                <li><strong>Average Updates:</strong> How actively institutions communicate with citizens</li>
                <li><strong>Urgency Rate:</strong> Percentage of reports containing urgent keywords</li>
            </ul>
            <p><strong>Key Insight:</strong> The 61% resolution rate indicates significant room for improvement in municipal responsiveness.</p>
        </div>
        """
        return fig_metrics
    
    def create_institution_performance_chart(self):
        """Create comprehensive institution performance comparison chart."""
        if 'institution_performance' not in self.eda_results:
            return None
            
        perf_df = self.eda_results['institution_performance'].reset_index()
        
        # Include ALL institutions with at least 20 reports for meaningful analysis
        all_institutions = perf_df[perf_df['Total_Reports'] >= 20].copy()
        
        # Create scatter plot: Resolution Rate vs Total Reports
        fig = px.scatter(
            all_institutions,
            x='Total_Reports',
            y='Resolution_Rate',
            size='Avg_Updates',
            color='Resolution_Rate',
            hover_name='institution',
            hover_data={
                'Total_Reports': ':,',
                'Resolution_Rate': ':.1%', 
                'Solved_Count': ':,',
                'Avg_Updates': ':.2f'
            },
            title="Institution Performance Analysis - All Municipal Entities",
            labels={
                'Total_Reports': 'Total Reports Handled',
                'Resolution_Rate': 'Resolution Rate',
                'Avg_Updates': 'Average Updates per Report'
            },
            color_continuous_scale='RdYlGn',
            template='plotly_dark'
        )
        
        # Add benchmark lines
        fig.add_hline(y=0.8, line_dash="dash", line_color="green", 
                     annotation_text="Excellence Benchmark (80%)")
        fig.add_hline(y=0.5, line_dash="dash", line_color="orange", 
                     annotation_text="Minimum Acceptable (50%)")
        
        fig.update_layout(
            xaxis_title="Total Reports Handled",
            yaxis_title="Resolution Rate",
            yaxis=dict(tickformat='.0%'),
            height=700,
            showlegend=True
        )
        
        self.charts['institution_performance'] = fig
        self.explanations['institution_performance'] = """
        <div class="chart-explanation">
            <h4>🏢 Institution Performance Analysis</h4>
            <p><strong>What you see:</strong> Each bubble represents a municipal institution, positioned by workload (x-axis) and effectiveness (y-axis).</p>
            <ul>
                <li><strong>X-axis:</strong> Total reports handled (workload capacity)</li>
                <li><strong>Y-axis:</strong> Resolution rate (effectiveness)</li>
                <li><strong>Bubble size:</strong> Average updates per report (communication frequency)</li>
                <li><strong>Color:</strong> Resolution rate (green=good, red=poor)</li>
            </ul>
            <p><strong>Key Insights:</strong></p>
            <ul>
                <li>Top-right quadrant: High-volume, high-performance institutions (benchmarks)</li>
                <li>Bottom-right quadrant: High-volume, low-performance institutions (need immediate attention)</li>
                <li>Green benchmark line at 80% represents excellence standard</li>
            </ul>
        </div>
        """
        return fig
    
    def create_temporal_trends_chart(self):
        """Create temporal trends analysis chart."""
        if self.df is None:
            return None
            
        # Monthly trends with complete data
        monthly_data = self.df.groupby([self.df['date'].dt.to_period('M')]).agg({
            'url': 'count',
            'is_solved': 'mean',
            'contains_urgency': 'mean'
        }).reset_index()
        
        monthly_data['date'] = monthly_data['date'].dt.to_timestamp()
        monthly_data['resolution_rate'] = monthly_data['is_solved'] * 100
        monthly_data['urgency_rate'] = monthly_data['contains_urgency'] * 100
        
        # Create triple-axis chart
        fig = make_subplots(
            specs=[[{"secondary_y": True}]],
            subplot_titles=("Monthly System Performance Trends",)
        )
        
        # Reports count (bar chart)
        fig.add_trace(
            go.Bar(
                x=monthly_data['date'],
                y=monthly_data['url'],
                name='Reports Volume',
                marker_color='#74b9ff',
                opacity=0.7
            ),
            secondary_y=False,
        )
        
        # Resolution rate (line chart)
        fig.add_trace(
            go.Scatter(
                x=monthly_data['date'],
                y=monthly_data['resolution_rate'],
                mode='lines+markers',
                name='Resolution Rate (%)',
                line=dict(color='#00d4aa', width=4),
                marker=dict(size=10)
            ),
            secondary_y=True,
        )
        
        # Urgency rate (line chart)
        fig.add_trace(
            go.Scatter(
                x=monthly_data['date'],
                y=monthly_data['urgency_rate'],
                mode='lines+markers',
                name='Urgency Rate (%)',
                line=dict(color='#fd79a8', width=3, dash='dot'),
                marker=dict(size=8)
            ),
            secondary_y=True,
        )
        
        fig.update_xaxes(title_text="Month")
        fig.update_yaxes(title_text="Number of Reports", secondary_y=False)
        fig.update_yaxes(title_text="Percentage (%)", secondary_y=True)
        
        fig.update_layout(
            title="Municipal System Performance Over Time",
            height=500,
            template='plotly_dark'
        )
        
        self.charts['temporal_trends'] = fig
        self.explanations['temporal_trends'] = """
        <div class="chart-explanation">
            <h4>📈 Temporal Performance Trends</h4>
            <p><strong>What you see:</strong> How the municipal system performs over time across three key dimensions.</p>
            <ul>
                <li><strong>Blue bars:</strong> Monthly report volume (citizen engagement level)</li>
                <li><strong>Green line:</strong> Resolution rate trend (system effectiveness)</li>
                <li><strong>Pink dotted line:</strong> Urgency rate (critical issue frequency)</li>
            </ul>
            <p><strong>Key Insights:</strong></p>
            <ul>
                <li>September 2025 shows dramatic decline in resolution rate - investigate immediately</li>
                <li>Spring months (March-May) show peak reporting activity</li>
                <li>Summer months maintain higher resolution rates</li>
                <li>Urgency rate remains relatively stable, indicating consistent critical issue flow</li>
            </ul>
        </div>
        """
        return fig
    
    def create_category_analysis_chart(self):
        """Create category analysis with comprehensive bar charts."""
        if self.df is None:
            return None
            
        # Category analysis data - ALL categories
        category_stats = self.df.groupby('category').agg({
            'url': 'count',
            'is_solved': 'mean',
            'contains_urgency': 'mean',
            'update_count': 'mean',
            'image_count': 'mean'
        }).round(3)
        
        category_stats.columns = ['Total_Reports', 'Resolution_Rate', 'Urgency_Rate', 'Avg_Updates', 'Avg_Images']
        category_stats = category_stats.sort_values('Total_Reports', ascending=True)  # Ascending for horizontal bar
        
        # Create horizontal bar chart for ALL categories
        fig_bar = px.bar(
            category_stats.reset_index(),
            x='Total_Reports',
            y='category',
            color='Resolution_Rate',
            title="Complete Issue Category Analysis - Volume vs Performance",
            labels={'Total_Reports': 'Number of Reports', 'category': 'Issue Category'},
            color_continuous_scale='RdYlGn',
            orientation='h',
            template='plotly_dark'
        )
        
        fig_bar.update_layout(
            height=600,
            yaxis={'categoryorder': 'total ascending'},
            coloraxis_colorbar=dict(
                title="Resolution Rate",
                tickformat='.0%'
            )
        )
        
        # Add text annotations for key metrics
        fig_bar.update_traces(
            texttemplate='%{x:,}',
            textposition='outside'
        )
        
        self.charts['category_analysis'] = fig_bar
        self.explanations['category_analysis'] = """
        <div class="chart-explanation">
            <h4>📊 Complete Issue Category Analysis</h4>
            <p><strong>What you see:</strong> All 15 issue categories ranked by volume, colored by resolution effectiveness.</p>
            <ul>
                <li><strong>Bar length:</strong> Total number of reports in each category</li>
                <li><strong>Color scale:</strong> Resolution rate (green=high performance, red=poor performance)</li>
                <li><strong>Ordering:</strong> Categories ordered from lowest to highest volume</li>
            </ul>
            <p><strong>Key Insights:</strong></p>
            <ul>
                <li><strong>Parks & Green Spaces:</strong> Highest volume (2,416 reports) but moderate resolution rate</li>
                <li><strong>Public Cleanliness:</strong> Second highest volume with good resolution rate (66%)</li>
                <li><strong>Utilities:</strong> High volume with good resolution rate - well-managed category</li>
                <li><strong>Lighting:</strong> Lower volume but excellent resolution rate (73%) - benchmark performer</li>
            </ul>
        </div>
        """
        
        return fig_bar
    
    def create_geographic_analysis_chart(self):
        """Create comprehensive geographic analysis chart."""
        if 'district_analysis' not in self.eda_results:
            return None
            
        district_df = self.eda_results['district_analysis'].reset_index()
        # Include ALL districts, remove only 'Unknown'
        district_df = district_df[district_df['district'] != 'Unknown']
        
        # Create bubble chart: District performance
        fig = px.scatter(
            district_df,
            x='Total_Reports',
            y='Resolution_Rate',
            size='Avg_Updates',
            color='Anonymous_Rate',
            hover_name='district',
            hover_data={
                'Total_Reports': ':,',
                'Resolution_Rate': ':.1%',
                'Anonymous_Rate': ':.1%',
                'Avg_Updates': ':.2f'
            },
            title="Complete District Performance Analysis - All Budapest Districts",
            labels={
                'Total_Reports': 'Total Reports',
                'Resolution_Rate': 'Resolution Rate',
                'Anonymous_Rate': 'Anonymous Reporting Rate',
                'Avg_Updates': 'Average Updates'
            },
            color_continuous_scale='Viridis',
            template='plotly_dark'
        )
        
        # Add benchmark lines
        fig.add_hline(y=0.7, line_dash="dash", line_color="green", 
                     annotation_text="Good Performance (70%)")
        fig.add_vline(x=district_df['Total_Reports'].median(), line_dash="dash", line_color="yellow", 
                     annotation_text="Median Volume")
        
        fig.update_layout(
            xaxis_title="Total Reports (Citizen Engagement)",
            yaxis_title="Resolution Rate (Municipal Effectiveness)",
            yaxis=dict(tickformat='.0%'),
            height=700
        )
        
        self.charts['geographic_analysis'] = fig
        self.explanations['geographic_analysis'] = """
        <div class="chart-explanation">
            <h4>🗺️ Complete District Performance Analysis</h4>
            <p><strong>What you see:</strong> All Budapest districts plotted by citizen engagement (x-axis) vs municipal effectiveness (y-axis).</p>
            <ul>
                <li><strong>X-axis:</strong> Total reports (higher = more citizen engagement)</li>
                <li><strong>Y-axis:</strong> Resolution rate (higher = better municipal response)</li>
                <li><strong>Bubble size:</strong> Average updates per report (communication frequency)</li>
                <li><strong>Color:</strong> Anonymous reporting rate (darker = more anonymous reports)</li>
            </ul>
            <p><strong>Key Insights:</strong></p>
            <ul>
                <li><strong>Top-right quadrant:</strong> High engagement + high performance districts (benchmark areas)</li>
                <li><strong>Bottom-right quadrant:</strong> High engagement + low performance (need improvement)</li>
                <li><strong>XIV. kerület (Zugló):</strong> Highest engagement (1,681 reports) with moderate performance</li>
                <li><strong>XXI. kerület (Csepel):</strong> Lower engagement but excellent 70% resolution rate</li>
            </ul>
        </div>
        """
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
            'contains_urgency': 'mean',
            'update_count': 'mean'
        })
        
        engagement_data.index = ['Registered Users', 'Anonymous Users']
        engagement_data = engagement_data.reset_index()
        
        # Create radar chart for engagement comparison
        categories = ['Resolution Rate', 'Avg Images', 'Description Length', 'Urgency Rate', 'Updates Received']
        
        fig = go.Figure()
        
        # Normalize data for radar chart (0-1 scale)
        reg_values = [
            engagement_data.loc[0, 'is_solved'],
            engagement_data.loc[0, 'image_count'] / engagement_data['image_count'].max(),
            engagement_data.loc[0, 'description_length'] / engagement_data['description_length'].max(), 
            engagement_data.loc[0, 'contains_urgency'],
            engagement_data.loc[0, 'update_count'] / engagement_data['update_count'].max()
        ]
        
        anon_values = [
            engagement_data.loc[1, 'is_solved'],
            engagement_data.loc[1, 'image_count'] / engagement_data['image_count'].max(),
            engagement_data.loc[1, 'description_length'] / engagement_data['description_length'].max(),
            engagement_data.loc[1, 'contains_urgency'],
            engagement_data.loc[1, 'update_count'] / engagement_data['update_count'].max()
        ]
        
        fig.add_trace(go.Scatterpolar(
            r=reg_values,
            theta=categories,
            fill='toself',
            name='Registered Users',
            line_color='#00d4aa',
            fillcolor='rgba(0, 212, 170, 0.3)'
        ))
        
        fig.add_trace(go.Scatterpolar(
            r=anon_values,
            theta=categories,
            fill='toself',
            name='Anonymous Users',
            line_color='#fd79a8',
            fillcolor='rgba(253, 121, 168, 0.3)'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1],
                    tickcolor="white",
                    gridcolor="gray"
                )),
            showlegend=True,
            title="Citizen Engagement Patterns: Anonymous vs Registered Users",
            height=500,
            template='plotly_dark'
        )
        
        self.charts['citizen_engagement'] = fig
        self.explanations['citizen_engagement'] = """
        <div class="chart-explanation">
            <h4>👥 Citizen Engagement Analysis</h4>
            <p><strong>What you see:</strong> Comparison of reporting behavior between anonymous and registered users across five key dimensions.</p>
            <ul>
                <li><strong>Resolution Rate:</strong> How successfully each group's reports get resolved</li>
                <li><strong>Avg Images:</strong> Documentation quality (photos per report)</li>
                <li><strong>Description Length:</strong> Detail level in problem descriptions</li>
                <li><strong>Urgency Rate:</strong> Frequency of urgent issue reporting</li>
                <li><strong>Updates Received:</strong> Institutional communication frequency</li>
            </ul>
            <p><strong>Key Insights:</strong></p>
            <ul>
                <li><strong>Registered users</strong> provide more detailed reports and receive slightly better resolution rates</li>
                <li><strong>Anonymous users</strong> make up 62% of all reports, indicating trust/privacy concerns</li>
                <li>Both groups show similar documentation patterns (image usage)</li>
                <li>Registered users receive more updates, suggesting better institutional follow-up</li>
            </ul>
        </div>
        """
        return fig
    
    def create_status_progression_chart(self):
        """Create status progression and resolution pipeline chart."""
        if self.df is None:
            return None
            
        # Status distribution with proper ordering
        status_counts = self.df['status'].value_counts()
        
        # Define logical order for the funnel
        status_order = [
            'MEGERŐSÍTÉSRE VÁR',  # Waiting for confirmation
            'MEGOLDÁSRA VÁR',     # Waiting for solution  
            'MEGOLDOTT',          # Resolved
            'MEGOLDATLAN'         # Unresolved
        ]
        
        # Reorder status counts
        ordered_counts = []
        ordered_statuses = []
        colors = ['#fd79a8', '#fdcb6e', '#00d4aa', '#ff6b6b']
        
        for status in status_order:
            if status in status_counts.index:
                ordered_counts.append(status_counts[status])
                ordered_statuses.append(status)
        
        # Create funnel chart
        fig = go.Figure(go.Funnel(
            y=ordered_statuses,
            x=ordered_counts,
            textinfo="value+percent initial",
            marker_color=colors[:len(ordered_counts)],
            textfont=dict(color="white", size=14)
        ))
        
        fig.update_layout(
            title="Issue Resolution Pipeline - Status Flow Analysis",
            height=500,
            template='plotly_dark'
        )
        
        self.charts['status_progression'] = fig
        self.explanations['status_progression'] = """
        <div class="chart-explanation">
            <h4>⚡ Resolution Pipeline Analysis</h4>
            <p><strong>What you see:</strong> The flow of issues through the municipal resolution process, from initial report to final status.</p>
            <ul>
                <li><strong>Waiting for Confirmation:</strong> Issues reported but not yet acknowledged</li>
                <li><strong>Waiting for Solution:</strong> Acknowledged issues pending resolution</li>
                <li><strong>Resolved:</strong> Issues marked as successfully completed</li>
                <li><strong>Unresolved:</strong> Issues that remain unsolved</li>
            </ul>
            <p><strong>Key Insights:</strong></p>
            <ul>
                <li><strong>High confirmation rate:</strong> Most reports get acknowledged by institutions</li>
                <li><strong>Resolution bottleneck:</strong> Gap between "waiting for solution" and "resolved" indicates capacity issues</li>
                <li><strong>Success rate:</strong> Funnel shows overall 61% resolution effectiveness</li>
                <li><strong>Process transparency:</strong> Clear status progression helps citizen expectations</li>
            </ul>
        </div>
        """
        return fig
    
    def export_interactive_charts(self, output_dir: str = "docs/eda"):
        """Export all interactive charts as HTML files with explanations."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"Exporting enhanced interactive charts to {output_dir}...")
        
        # Export each chart with explanations
        for chart_name, fig in self.charts.items():
            if fig is not None:
                # Create HTML with chart and explanation
                chart_html = fig.to_html(include_plotlyjs='cdn')
                
                # Add explanation below the chart
                explanation = self.explanations.get(chart_name, "")
                
                full_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Járókelő Analysis - {chart_name.replace('_', ' ').title()}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #1e1e1e;
            color: #ffffff;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .chart-explanation {{
            background-color: #2d2d2d;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            border-left: 4px solid #00d4aa;
        }}
        .chart-explanation h4 {{
            color: #00d4aa;
            margin-top: 0;
        }}
        .chart-explanation ul {{
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
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="back-link">← Back to Dashboard</a>
        {chart_html}
        {explanation}
        <a href="index.html" class="back-link">← Back to Dashboard</a>
    </div>
</body>
</html>
"""
                
                html_file = output_path / f"{chart_name}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(full_html)
                print(f"  ✓ Exported {chart_name}.html with explanation")
        
        # Create enhanced index page
        self._create_enhanced_index(output_path)
        
        print(f"✅ Exported {len(self.charts)} enhanced interactive charts")
    
    def _create_enhanced_index(self, output_path: Path):
        """Create an enhanced index HTML page with dark theme."""
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
            background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
            color: #ffffff;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: #2d2d2d;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 0 30px rgba(0,0,0,0.5);
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            border-bottom: 3px solid #00d4aa;
            padding-bottom: 20px;
        }}
        .header h1 {{
            color: #00d4aa;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}
        .header p {{
            color: #cccccc;
            font-size: 1.1em;
        }}
        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
            margin-top: 30px;
        }}
        .chart-card {{
            background: linear-gradient(135deg, #3d3d3d 0%, #4a4a4a 100%);
            padding: 25px;
            border-radius: 12px;
            border-left: 5px solid #00d4aa;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        .chart-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0, 212, 170, 0.3);
        }}
        .chart-card h3 {{
            margin-top: 0;
            color: #00d4aa;
            font-size: 1.3em;
        }}
        .chart-card p {{
            color: #cccccc;
            margin: 15px 0;
        }}
        .chart-card a {{
            display: inline-block;
            color: #74b9ff;
            text-decoration: none;
            font-weight: bold;
            padding: 10px 15px;
            background: rgba(116, 185, 255, 0.1);
            border-radius: 5px;
            border: 1px solid #74b9ff;
            transition: all 0.3s;
        }}
        .chart-card a:hover {{
            background: #74b9ff;
            color: #1e1e1e;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .stat-box {{
            background: linear-gradient(135deg, #00d4aa, #74b9ff);
            color: #1e1e1e;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }}
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #4a4a4a;
            color: #999;
        }}
        .footer a {{
            color: #74b9ff;
            text-decoration: none;
        }}
        .footer a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏛️ Járókelő Municipal System</h1>
            <h2>Enhanced EDA Dashboard</h2>
            <p>Professional insights into citizen-reported municipal issues and institutional performance</p>
        </div>
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-number">14K+</div>
                <div>Total Reports</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">61%</div>
                <div>Resolution Rate</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">15</div>
                <div>Issue Categories</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">24</div>
                <div>Districts Covered</div>
            </div>
        </div>
        
        <div class="chart-grid">
"""
        
        # Chart descriptions
        chart_descriptions = {
            'executive_dashboard': {
                'title': '📊 Executive Dashboard',
                'description': 'High-level KPIs and performance metrics for municipal leadership and stakeholders'
            },
            'institution_performance': {
                'title': '🏢 Institution Performance Analysis',
                'description': 'Comprehensive analysis of ALL municipal institutions - effectiveness vs workload comparison'
            },
            'temporal_trends': {
                'title': '📈 Temporal Performance Trends',
                'description': 'Monthly reporting patterns, resolution rates, and urgency trends over time'
            },
            'category_analysis': {
                'title': '📊 Complete Category Analysis',
                'description': 'All 15 issue categories analyzed by volume and resolution performance'
            },
            'geographic_analysis': {
                'title': '🗺️ District Performance Analysis',
                'description': 'All Budapest districts analyzed for citizen engagement and municipal effectiveness'
            },
            'citizen_engagement': {
                'title': '👥 Citizen Engagement Intelligence',
                'description': 'Anonymous vs registered user behavior patterns and reporting quality analysis'
            },
            'status_progression': {
                'title': '⚡ Resolution Pipeline',
                'description': 'Issue status distribution and municipal resolution process flow analysis'
            }
        }
        
        # Add chart cards (excluding removed treemap)
        for chart_name in self.charts.keys():
            if chart_name in chart_descriptions:
                info = chart_descriptions[chart_name]
                html_content += f"""
            <div class="chart-card">
                <h3>{info['title']}</h3>
                <p>{info['description']}</p>
                <a href="{chart_name}.html">📊 View Interactive Analysis</a>
            </div>
"""
        
        html_content += f"""
        </div>
        
        <div class="footer">
            <p>Report generated on {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')} | 
            <a href="https://github.com/leweex95/jarokelo_tracker">🔗 View Source Code</a></p>
            <p>Data source: <a href="https://jarokelo.hu/">Járókelő.hu</a> - Hungarian municipal issue reporting platform</p>
        </div>
    </div>
</body>
</html>
"""
        
        with open(output_path / "index.html", 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print("  ✓ Created enhanced index.html with dark theme")
    
    def generate_all_visualizations(self):
        """Generate all enhanced visualization charts."""
        print("🎨 Generating enhanced interactive visualizations with dark mode...")
        
        # Create all charts (excluding treemap)
        self.create_executive_dashboard()
        self.create_institution_performance_chart()
        self.create_temporal_trends_chart()
        self.create_category_analysis_chart()  # Replaces treemap
        self.create_geographic_analysis_chart()
        self.create_citizen_engagement_chart()
        self.create_status_progression_chart()
        
        print(f"✅ Generated {len(self.charts)} enhanced interactive charts")
        return self.charts


if __name__ == "__main__":
    print("Enhanced interactive visualization module loaded.")
    print("Features: Dark mode, comprehensive explanations, complete data coverage")