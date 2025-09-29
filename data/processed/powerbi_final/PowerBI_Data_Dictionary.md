
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

Generated: 2025-09-28 20:59:32
