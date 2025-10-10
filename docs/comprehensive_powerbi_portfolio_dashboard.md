# 🚀 Budapest Municipal Issue Tracker - PowerBI Portfolio Dashboard

## Executive Summary

**Project Overview**: A comprehensive, interactive PowerBI dashboard analyzing Budapest's municipal issue tracking system (jarokelo.hu) with 21,263+ records spanning 12 months (2024-11 to 2025-10). This portfolio project demonstrates advanced PowerBI skills including complex data modeling, geospatial analytics, temporal analysis, and interactive storytelling.

**Key Features**:
- 📊 **21,263+ Issues** across 39 categories and 268 institutions
- 🗺️ **100% GPS Coverage** with spatial clustering and geographic insights
- ⏱️ **Temporal Analytics** with response time and resolution tracking
- 🎯 **Performance Metrics** for institutions and districts
- 📱 **Mobile-Responsive** design with accessibility features
- 🔄 **Real-time Interactivity** with cross-filtering and drill-through

---

## 📊 Data Architecture & Model

### Source Data Structure
```
Raw Data (JSONL files):
├── Issue Details: title, description, category, status, dates
├── Geographic: latitude, longitude, address, district
├── Institutional: institution, supporter, author info
├── Temporal: creation_date, first_response, resolution_date
└── Engagement: anonymous_rate, image_attachments, URLs

Processed Datasets (10 CSV files):
├── jarokelo_main_powerbi_gps.csv (21,263 records) - Fact Table
├── category_analysis_gps.csv - Category performance
├── institution_scorecard_gps.csv - Institutional metrics
├── district_analysis_gps.csv - Geographic insights
├── temporal_trends_gps.csv - Time-based analytics
├── location_clusters.csv - Spatial clustering (100 clusters)
├── geographic_insights.csv - Spatial analysis
├── budapest_districts_geo.csv - District metadata
├── institution_territories_detailed.csv - Service areas
└── district_boundaries.csv - Geographic boundaries
```

### PowerBI Data Model
```
┌─────────────────────────────────────────────────────────────┐
│                    FACT TABLE                               │
│  jarokelo_main_powerbi_gps (21,263 records)                 │
│  ├── IssueID, Title, Description, Category, Status         │
│  ├── Dates: Created, FirstResponse, Resolved               │
│  ├── Location: Lat, Lng, Address, District                 │
│  ├── Institution: Primary, Supporter                       │
│  └── Metrics: UrgencyScore, ResponseTime, ResolutionTime  │
└─────────────────────┬───────────────────────────────────────┘
                      │
           ┌──────────┴──────────┐
           │                     │
    ┌──────▼──────┐       ┌──────▼──────┐
    │DIMENSIONS   │       │DIMENSIONS   │
    │Categories   │       │Geography    │
    │(39 records) │       │(23 districts│
    │- CategoryID │       │+ clusters)  │
    │- Priority   │       │- DistrictID │
    │- Resolution │       │- Boundaries │
    │  Rate       │       │- Population │
    └─────────────┘       └─────────────┘
           │                     │
           └──────────┬──────────┘
                      │
               ┌──────▼──────┐
               │DIMENSIONS   │
               │Institutions │
               │(268 records)│
               │- InstID     │
               │- Type       │
               │- Territory  │
               │- Performance│
               └─────────────┘
```

---

## 🎨 Dashboard Structure (8 Pages)

### Page 1: Executive Overview
**Theme**: High-level KPIs and system health metrics

#### Layout: 3x3 KPI Dashboard
```
┌─────────────────┬─────────────────┬─────────────────┐
│   SYSTEM KPIs   │   TREND CHARTS  │ STATUS OVERVIEW │
│ • Total Issues  │ • Monthly Trend │ • Status Pie    │
│   21,263+       │ • Resolution %  │ • Open/Closed   │
│ • Avg Response  │ • Category Mix  │ • Priority Dist │
│   16.6 days     │                 │                 │
├─────────────────┴─────────────────┴─────────────────┤
│              GEOGRAPHIC HEAT MAP                    │
│     Issues by District (Choropleth Map)             │
├─────────────────┬─────────────────┬─────────────────┐
│ TOP CATEGORIES  │ RESPONSE TIME    │ EFFICIENCY     │
│ (Horizontal Bar)│ PERFORMANCE      │ METRICS        │
│ • Parking       │ (Gauge Charts)   │ (KPIs)         │
│ • Cleanliness   │ • <24h Response  │ • Resolution   │
│ • Road Damage   │ • <7d Resolution │   Rate         │
└─────────────────┴─────────────────┴─────────────────┘
```

**Key Visualizations**:
- **KPI Cards**: Total Issues, Resolution Rate, Avg Response Time, GPS Coverage
- **Trend Line**: Issues over time with moving averages
- **Choropleth Map**: District-wise issue density
- **Status Donut**: Open vs Closed vs In Progress
- **Top Categories**: Horizontal bar chart with resolution rates
- **Performance Gauges**: Response time and efficiency metrics

**Interactive Controls**:
- Date Range Slicer (Last 30/90/365 days)
- District Multi-select
- Category Filter
- Status Toggle

---

### Page 2: Geographic Intelligence
**Theme**: Spatial patterns and location-based insights

#### Layout: Map-Centric Design
```
┌─────────────────────────────────────────────────────┐
│                INTERACTIVE MAP VIEW                 │
│     (Multi-layer: Heat/Density/Cluster/Choropleth) │
├─────────────────┬─────────────────┬─────────────────┐
│ DISTRICT        │ CLUSTER         │ LOCATION        │
│ ANALYSIS        │ ANALYSIS        │ ANALYSIS        │
│ (Ranked Table)  │ (Bubble Chart)  │ (Scatter Plot)  │
├─────────────────┴─────────────────┴─────────────────┤
│         SPATIAL PATTERN ANALYSIS                    │
│   (Heat Grid + Correlation Matrix + Trend Lines)    │
└─────────────────────────────────────────────────────┘
```

**Key Visualizations**:
- **Multi-layer Map**: Toggle between:
  - Heat Map (intensity)
  - Bubble Map (density)
  - Cluster Map (K-means groups)
  - District Boundaries
- **District Rankings**: Issues per district with performance metrics
- **Cluster Analysis**: 100 spatial clusters with centroids
- **Location Scatter**: GPS coordinate distribution
- **Spatial Correlations**: Issue types by location patterns

**Advanced Features**:
- **Map Layers Toggle**: Switch between visualization modes
- **Zoom Controls**: District-level to street-level detail
- **Tooltips**: Issue details on hover
- **Drill-through**: Click district → detailed breakdown

---

### Page 3: Temporal Dynamics
**Theme**: Time-based patterns and seasonal analysis

#### Layout: Time Series Focus
```
┌─────────────────┬─────────────────┬─────────────────┐
│   DAILY PATTERNS│  WEEKLY CYCLES  │ MONTHLY TRENDS  │
│   (Line Chart)   │  (Heat Map)     │ (Area Chart)    │
├─────────────────┴─────────────────┴─────────────────┤
│              CALENDAR HEAT MAP                      │
│         (Issues by Day/Hour Matrix)                 │
├─────────────────┬─────────────────┬─────────────────┐
│ SEASONAL        │ RESPONSE TIME    │ RESOLUTION      │
│ ANALYSIS        │ TRENDS           │ ANALYSIS        │
│ (Year-over-Year)│ (Box Plot)       │ (Histogram)     │
└─────────────────┴─────────────────┴─────────────────┘
```

**Key Visualizations**:
- **Daily Trends**: Issues per day with weekday patterns
- **Weekly Heat Map**: Day-of-week × hour matrix
- **Monthly Trends**: Seasonal patterns and growth
- **Calendar Heat Map**: GitHub-style contribution calendar
- **Seasonal Comparison**: Year-over-year analysis
- **Response Time Distribution**: Statistical analysis
- **Resolution Time Histogram**: Completion patterns

**Time Intelligence Features**:
- **Dynamic Date Calculations**: DAX measures for periods
- **Moving Averages**: 7-day, 30-day trends
- **Seasonal Decomposition**: Trend + seasonal + residual
- **Forecasting**: Linear trend projections

---

### Page 4: Category Deep Dive
**Theme**: Issue type analysis and category performance

#### Layout: Category-Centric Analysis
```
┌─────────────────┬─────────────────┬─────────────────┐
│ CATEGORY        │ SUB-CATEGORY    │ PRIORITY        │
│ DISTRIBUTION    │ BREAKDOWN       │ ANALYSIS        │
│ (Treemap)       │ (Sunburst)      │ (Stacked Bar)   │
├─────────────────┴─────────────────┴─────────────────┤
│         CATEGORY PERFORMANCE MATRIX                │
│     (Heat Map: Category × Institution × District)  │
├─────────────────┬─────────────────┬─────────────────┐
│ RESOLUTION      │ ESCALATION      │ RECURRING       │
│ PATTERNS        │ ANALYSIS        │ ISSUES          │
│ (Funnel Chart)  │ (Sankey)        │ (Network)       │
└─────────────────┴─────────────────┴─────────────────┘
```

**Key Visualizations**:
- **Category Treemap**: Issue volume by category (size) and resolution rate (color)
- **Sunburst Chart**: Category → Sub-category → Status hierarchy
- **Priority Stacked Bar**: Urgency levels across categories
- **Performance Heat Map**: Category performance by district/institution
- **Resolution Funnel**: Issue flow from submission to resolution
- **Escalation Sankey**: Status transitions over time
- **Recurring Issues Network**: Connected problem patterns

**Category Intelligence**:
- **Resolution Rate by Category**: Success metrics
- **Average Response Times**: Category-specific SLAs
- **Geographic Distribution**: Where issues occur by type
- **Institutional Specialization**: Which agencies handle what

---

### Page 5: Institutional Performance
**Theme**: Service provider accountability and efficiency

#### Layout: Performance Dashboard
```
┌─────────────────┬─────────────────┬─────────────────┐
│ INSTITUTION     │ WORKLOAD        │ EFFICIENCY      │
│ OVERVIEW        │ DISTRIBUTION    │ METRICS         │
│ (Scorecard)     │ (Treemap)       │ (Radar Chart)   │
├─────────────────┴─────────────────┴─────────────────┤
│         SERVICE AREA PERFORMANCE MAP               │
│     (Institution territories with KPIs overlay)    │
├─────────────────┬─────────────────┬─────────────────┐
│ RESPONSE TIME   │ SUCCESS RATE    │ CATEGORY        │
│ ANALYSIS        │ BY INSTITUTION  │ SPECIALIZATION  │
│ (Box Plot)      │ (Bar Chart)     │ (Heat Map)      │
└─────────────────┴─────────────────┴─────────────────┘
```

**Key Visualizations**:
- **Institution Scorecard**: Performance metrics table
- **Workload Treemap**: Issue volume by institution
- **Efficiency Radar**: Multi-dimensional performance
- **Territory Map**: Service areas with performance overlay
- **Response Time Box Plot**: Statistical distribution
- **Success Rate Ranking**: Performance comparison
- **Category Specialization**: Institution expertise matrix

**Performance Metrics**:
- **Response Time Quartiles**: P25, P50, P75, P95
- **Resolution Success Rate**: Completed vs total
- **Workload Capacity**: Issues per day/week
- **Geographic Coverage**: Service area analysis
- **Category Expertise**: Specialization scores

---

### Page 6: User Engagement & Behavior
**Theme**: Citizen participation and platform usage patterns

#### Layout: User-Centric Analytics
```
┌─────────────────┬─────────────────┬─────────────────┐
│   USER TYPES    │ ANONYMOUS VS    │ ENGAGEMENT      │
│   ANALYSIS      │ REGISTERED      │ METRICS         │
│   (Pie Chart)   │ (Comparison)    │ (KPIs)          │
├─────────────────┴─────────────────┴─────────────────┤
│         USER BEHAVIOR PATTERNS                     │
│   (Cohort Analysis + Engagement Funnel)            │
├─────────────────┬─────────────────┬─────────────────┐
│ ISSUE QUALITY   │ ATTACHMENT      │ FOLLOW-UP       │
│ ANALYSIS        │ USAGE           │ PATTERNS        │
│ (Text Analytics)│ (Rates)         │ (Network)       │
└─────────────────┴─────────────────┴─────────────────┘
```

**Key Visualizations**:
- **User Type Distribution**: Anonymous vs Registered users
- **Engagement Comparison**: Behavior differences
- **Cohort Analysis**: User retention and activity
- **Engagement Funnel**: Issue submission to resolution
- **Text Quality Metrics**: Description length, detail level
- **Attachment Rates**: Image/document usage patterns
- **Follow-up Network**: Related issue connections

**Behavioral Insights**:
- **User Segmentation**: Power users vs occasional reporters
- **Geographic Participation**: Civic engagement by district
- **Category Preferences**: What issues different users report
- **Response Satisfaction**: Based on resolution outcomes

---

### Page 7: Predictive Analytics & Forecasting
**Theme**: Data-driven insights and future predictions

#### Layout: Advanced Analytics
```
┌─────────────────┬─────────────────┬─────────────────┐
│   TREND         │ CORRELATION     │ PREDICTIVE      │
│   ANALYSIS      │ MATRIX          │ MODELS          │
│   (Line Charts)  │ (Scatter)       │ (Forecast)      │
├─────────────────┴─────────────────┴─────────────────┤
│         ANOMALY DETECTION & ALERTS                 │
│   (Control Charts + Statistical Process Control)   │
├─────────────────┬─────────────────┬─────────────────┐
│ CLUSTER         │ BENCHMARKING    │ SCENARIO        │
│ ANALYSIS        │ ANALYSIS        │ PLANNING        │
│ (Segmentation)  │ (Radar)         │ (What-if)       │
└─────────────────┴─────────────────┴─────────────────┘
```

**Key Visualizations**:
- **Trend Forecasting**: Time series predictions
- **Correlation Matrix**: Variable relationships
- **Predictive Models**: Issue volume forecasting
- **Anomaly Detection**: Statistical process control charts
- **Cluster Segmentation**: Issue pattern grouping
- **Benchmarking Radar**: Performance comparisons
- **What-if Analysis**: Scenario planning tools

**Advanced Features**:
- **Machine Learning Integration**: Clustering algorithms
- **Statistical Forecasting**: ARIMA/ETS models
- **Anomaly Detection**: Control limits and alerts
- **Scenario Analysis**: What-if parameter testing

---

### Page 8: Administrative Dashboard
**Theme**: System monitoring and administrative insights

#### Layout: Operational Dashboard
```
┌─────────────────┬─────────────────┬─────────────────┐
│   SYSTEM        │ DATA QUALITY    │ PERFORMANCE     │
│   HEALTH        │ METRICS         │ MONITORING      │
│   (KPIs)        │ (Quality Gates) │ (Response Times)│
├─────────────────┴─────────────────┴─────────────────┤
│         ADMINISTRATIVE CONTROLS                    │
│   (Management Tools + Configuration Panel)         │
├─────────────────┬─────────────────┬─────────────────┐
│ AUDIT TRAIL    │ EXPORT &        │ SYSTEM          │
│ & LOGS         │ REPORTING       │ CONFIGURATION   │
│ (Activity Log) │ (Automated)     │ (Settings)      │
└─────────────────┴─────────────────┴─────────────────┘
```

**Key Visualizations**:
- **System Health KPIs**: Uptime, data freshness, error rates
- **Data Quality Metrics**: Completeness, accuracy, consistency
- **Performance Monitoring**: Query response times, refresh duration
- **Administrative Controls**: Management tools and settings
- **Audit Trail**: Activity logs and change tracking
- **Automated Reporting**: Scheduled exports and alerts
- **System Configuration**: Parameter settings and thresholds

---

## 🔄 Interactive Features & Navigation

### Cross-Page Navigation
```
Navigation Bar (Top):
├── Home (Page 1) - Executive Overview
├── 📍 Geography (Page 2) - Spatial Analysis
├── ⏰ Time (Page 3) - Temporal Patterns
├── 📊 Categories (Page 4) - Issue Types
├── 🏢 Institutions (Page 5) - Performance
├── 👥 Users (Page 6) - Engagement
├── 🔮 Analytics (Page 7) - Predictions
└── ⚙️ Admin (Page 8) - System Management
```

### Global Controls (Persistent)
- **Date Range Slicer**: Timeline control (affects all pages)
- **District Filter**: Geographic scope (multi-select)
- **Category Filter**: Issue type scope (multi-select)
- **Institution Filter**: Service provider scope
- **Status Filter**: Issue status scope
- **Priority Filter**: Urgency level scope

### Drill-Through Capabilities
- **Map → District Details**: Click district → detailed breakdown
- **Category → Issue Details**: Click category → individual issues
- **Institution → Performance**: Click institution → detailed metrics
- **Time → Daily Details**: Click time period → daily breakdown
- **User → Issue History**: Click user → their issue history

### Tooltips & Contextual Information
- **Rich Tooltips**: Detailed information on hover
- **Contextual Actions**: Right-click menus for export/print
- **Related Insights**: "See also" suggestions
- **Performance Indicators**: Color-coded status indicators

---

## 🎨 Design System & UX

### Color Palette
```
Primary Theme: Municipal/Civic
├── Background: #F8F9FA (Light Gray)
├── Primary: #005CA9 (Budapest Blue)
├── Secondary: #28A745 (Success Green)
├── Warning: #FFC107 (Amber)
├── Danger: #DC3545 (Alert Red)
├── Neutral: #6C757D (Gray)
└── Accent: #17A2B8 (Info Blue)
```

### Typography Hierarchy
- **Headers**: Segoe UI Bold, 16-24pt
- **KPIs**: Segoe UI Semibold, 24-48pt
- **Body**: Segoe UI Regular, 10-14pt
- **Captions**: Segoe UI Light, 8-10pt

### Responsive Design
- **Desktop**: Full layout (1920x1080+)
- **Tablet**: Stacked layout (1024x768)
- **Mobile**: Single column (375x667)
- **Touch Targets**: Minimum 44px for mobile interaction

### Accessibility Features
- **WCAG 2.1 AA Compliance**: Color contrast, keyboard navigation
- **Screen Reader Support**: Alt text, semantic markup
- **Keyboard Navigation**: Tab order, shortcuts
- **Color Blind Friendly**: Pattern differentiation, high contrast
- **Reduced Motion**: Animation preferences respected

---

## ⚡ Performance Optimization

### Data Model Optimizations
- **Star Schema**: Optimized relationships and cardinalities
- **Calculated Columns**: Pre-computed where possible
- **Aggregations**: Summary tables for large datasets
- **Indexing**: Optimized for common filter patterns

### DAX Optimizations
```dax
// Efficient measures with variables
Total Issues = VAR BaseTable = 'jarokelo_main_powerbi_gps'
             RETURN COUNTROWS(BaseTable)

// Time intelligence with proper context
Monthly Trend = CALCULATE([Total Issues],
                          DATESINPERIOD('Calendar'[Date],
                                       MAX('Calendar'[Date]), -30, DAY))

// Filtered measures for performance
District Issues = CALCULATE([Total Issues],
                           KEEPFILTERS('Districts'[DistrictID]))
```

### Query Optimizations
- **Query Diagnostics**: Performance analyzer usage
- **DAX Studio**: Query plan analysis and optimization
- **VertiPaq Analyzer**: Column compression and cardinality
- **Incremental Refresh**: For large datasets

### Loading Performance
- **Initial Load**: < 30 seconds for full dataset
- **Page Switching**: < 5 seconds between pages
- **Filter Application**: < 2 seconds for common filters
- **Drill-through**: < 3 seconds for detailed views

---

## 📱 Mobile & Tablet Optimization

### Mobile Layout (375px width)
```
┌─────────────────────────────────┐
│         NAVIGATION BAR          │
│     (Collapsible hamburger)     │
├─────────────────────────────────┤
│         GLOBAL FILTERS          │
│     (Horizontal scroll)         │
├─────────────────────────────────┤
│         PRIMARY KPI             │
│       (Large, prominent)        │
├─────────────────────────────────┤
│       TREND CHART               │
│     (Full width, touchable)     │
├─────────────────────────────────┤
│       TOP CATEGORIES            │
│     (Vertical list)             │
├─────────────────────────────────┤
│       MAP VIEW                  │
│   (Full screen on tap)          │
└─────────────────────────────────┘
```

### Touch Interactions
- **Swipe Navigation**: Between pages
- **Pinch-to-Zoom**: Map interactions
- **Long Press**: Context menus
- **Tap to Drill**: Interactive elements
- **Pull to Refresh**: Data updates

---

## 🚀 Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
1. **Data Import & Model**: Set up PowerBI file, import CSVs, create relationships
2. **Basic Visualizations**: Create core charts and KPIs
3. **Navigation Setup**: Implement page navigation and basic filters

### Phase 2: Core Dashboard (Week 3-4)
1. **Page Development**: Build Pages 1-4 with full layouts
2. **Interactive Features**: Implement slicers, drill-through, tooltips
3. **Performance Tuning**: Optimize DAX measures and data model

### Phase 3: Advanced Features (Week 5-6)
1. **Pages 5-8**: Complete remaining pages
2. **Advanced Analytics**: Forecasting, clustering, anomaly detection
3. **Mobile Optimization**: Responsive design and touch interactions

### Phase 4: Polish & Deployment (Week 7-8)
1. **Design System**: Consistent styling and branding
2. **Testing & QA**: Cross-device testing and performance validation
3. **Documentation**: User guide and technical documentation
4. **Deployment**: Publish to PowerBI Service with scheduled refresh

---

## 🛠️ Technical Requirements

### PowerBI Version
- **PowerBI Desktop**: Latest version (February 2024+)
- **PowerBI Service**: Pro license for sharing and scheduling
- **Gateway**: For scheduled data refresh (if needed)

### System Requirements
- **RAM**: 16GB+ recommended for large datasets
- **Storage**: 10GB+ free space for PBIX file and cache
- **CPU**: Multi-core processor for complex calculations

### Data Refresh Strategy
- **Manual Refresh**: For development and testing
- **Scheduled Refresh**: Daily at 6 AM (production)
- **Incremental Refresh**: For historical data optimization
- **Real-time**: DirectQuery for live data (future enhancement)

---

## 📈 Success Metrics & KPIs

### Dashboard Performance
- **Load Time**: < 30 seconds initial load
- **Interaction Speed**: < 2 seconds for filters
- **Data Freshness**: < 24 hours old
- **Uptime**: 99.9% availability

### User Engagement
- **Page Views**: Average session duration > 5 minutes
- **Interaction Rate**: > 70% of visitors interact with filters
- **Mobile Usage**: > 40% of sessions from mobile devices
- **Feature Adoption**: > 60% use advanced features (drill-through, etc.)

### Business Impact
- **Insights Generated**: Track key findings and decisions
- **Time Saved**: Hours saved vs manual reporting
- **User Satisfaction**: Survey scores > 4.5/5
- **Portfolio Value**: Measurable improvement in job prospects

---

## 🎯 Portfolio Impact

### Recruiter-Focused Features
- **Advanced DAX**: Complex measures and time intelligence
- **Data Modeling**: Star schema with 10+ tables and relationships
- **Geospatial Analytics**: Maps, clustering, spatial analysis
- **Predictive Analytics**: Forecasting and statistical modeling
- **Performance Optimization**: Query diagnostics and optimization
- **Mobile-First Design**: Responsive layouts and touch interactions
- **Accessibility**: WCAG compliance and inclusive design

### Demonstration Scenarios
1. **"Show me issue patterns"**: Geographic clustering and heat maps
2. **"Performance analysis"**: Institutional efficiency and benchmarking
3. **"Predictive insights"**: Forecasting and trend analysis
4. **"Mobile experience"**: Responsive design demonstration
5. **"Technical depth"**: DAX optimization and data model complexity

This comprehensive dashboard represents the pinnacle of PowerBI development, showcasing enterprise-level skills in data visualization, analytics, and user experience design. It's specifically crafted to impress recruiters and demonstrate mastery of modern business intelligence tools.