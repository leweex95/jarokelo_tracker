# Járokelő Tracker - Simplified Pipeline

## Overview

A single nightly workflow that runs comprehensive scraping and status updates in parallel every night at 10 PM UTC. No complex scheduling or conditional logic - just two jobs running simultaneously for maximum efficiency.

## Schedule

- **10 PM UTC (Daily)**: Both comprehensive scraping AND status updates run in parallel
- **Manual trigger**: Can be triggered anytime with custom parameters

## Job Architecture

### 1. **comprehensive-scraping** (Parallel)
- Scrapes new entries from Járokelő website
- Commits new data with detailed statistics
- Always runs (no conditions)

### 2. **status-updates** (Parallel) 
- Updates status of existing records efficiently
- Only commits if changes detected
- Always runs (no conditions)

### 3. **pipeline-summary**
- Always runs last (even if other jobs fail)
- Provides comprehensive report of pipeline execution
- Shows record counts, job results, and timing

## Key Features

### Simple Scheduling
```yaml
# Nightly run - both jobs in parallel
- cron: "0 22 * * *"
```

### True Parallel Execution
- Comprehensive scraping and status updates run **simultaneously**
- No dependencies or conditional logic
- Maximum efficiency with parallel processing

### Smart Commits
- Only commits when actual changes detected
- Detailed commit messages with statistics
- Separate commits for different job types
- Uses `[skip ci]` to prevent recursive triggers

### Robust Error Handling
- Jobs run independently (failure in one doesn't stop others)
- Retry logic for git push operations
- Summary job always runs to report status

## Usage Examples

### Manual Triggers

```bash
# Run full pipeline (both jobs in parallel)
gh workflow run scraper.yml

# Run with specific backend
gh workflow run scraper.yml \
  --field backend="beautifulsoup" \
  --field until_date="2025-01-01"

# Run with continue scraping
gh workflow run scraper.yml \
  --field continue_scraping="true" \
  --field start_page="50"
```

### Scheduled Behavior

| Time (UTC) | Jobs Running | Purpose |
|------------|--------------|---------|
| 22:00 | Comprehensive + Status (Parallel) | Nightly full update |

## 📊 Pipeline Output

### Comprehensive Scraping
```
🚀 [Auto-commit] Comprehensive scraping: 1,247 new records

⏰ Scraped at: 2025-09-28 22:15:33 UTC
🤖 Backend: beautifulsoup
📊 Total records: 25,891
🆕 New records: 1,247
```

### Status Updates
```
🔄 [Auto-commit] Status updates: 3 files updated

⏰ Updated at: 2025-09-28 12:08:15 UTC
🤖 Backend: beautifulsoup
📊 Records checked: 25,891
🔄 Files modified: 3
```

## 🔧 Configuration

### Environment Variables
- `PAT_TOKEN`: GitHub Personal Access Token (required)

### Input Parameters
- `backend`: Scraper backend (`beautifulsoup`)
- `data_dir`: Target data directory (`data/raw`)
- `start_page`: Starting page for comprehensive scraping
- `until_date`: Scrape/update until this date
- `headless`: Run browser in headless mode
- `continue_scraping`: Continue from last saved state

## Benefits

1. **Simplicity**: No complex conditional logic or scheduling decisions
2. **Efficiency**: True parallel execution reduces total pipeline time
3. **Reliability**: Independent jobs with robust error handling
4. **Transparency**: Detailed logging and commit messages
5. **Predictability**: Always runs both jobs - no surprises
6. **Manual Control**: Can be triggered anytime with custom parameters

This simplified pipeline provides maximum efficiency and reliability for maintaining fresh Járokelő data with parallel processing every night.