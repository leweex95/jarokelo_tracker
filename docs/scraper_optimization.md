# Scraper Optimization for GitHub Actions Disk Space Issue

## Problem
The nightly scraper runs were failing on GitHub Actions with "No space left on device" errors. The GitHub Actions runners have limited disk space (around 14GB available), and our scraper was consuming too much during the comprehensive scraping process.

## Root Cause Analysis
1. **High buffer size**: Default buffer size was 100-200 records, keeping large amounts of data in memory
2. **Large record size**: Each scraped record contains full HTML content, descriptions, comments, etc.
3. **Inefficient file operations**: Full file rewrites when flushing buffers
4. **No resource monitoring**: No visibility into memory/disk usage during scraping
5. **No cleanup**: Temporary files and caches weren't being cleaned up

## Optimizations Implemented

### 1. Reduced Buffer Sizes
- **Default buffer size**: Reduced from 100 to 50 records
- **GitHub Actions**: Reduced from 200 to 50 records
- **Impact**: ~50% reduction in peak memory usage

### 2. Resource Monitoring
- Added real-time memory and disk space monitoring
- Automatic buffer flush when memory > 800MB or disk free < 2GB
- Resource usage logging every 30 seconds
- Uses `psutil` library for accurate system metrics

### 3. Memory Management
- Added garbage collection after buffer flushes
- Automatic resource checking during buffer operations
- Force flush on high resource usage

### 4. Cleanup Functionality
- Automatic cleanup of temporary files
- Removal of large cache files (>50MB)
- Cleanup runs on context manager exit

### 5. Enhanced Monitoring in CI
- Pre-scraping disk space check
- Post-scraping disk space report
- Data directory size reporting
- Early warning for low disk space

## Code Changes

### Modified Files
1. `scripts/scrape_data.py` - Reduced default buffer size
2. `src/jarokelo_tracker/scraper/data_manager.py` - Added monitoring and cleanup
3. `src/jarokelo_tracker/scraper/core.py` - Updated default buffer size
4. `.github/workflows/scraper.yml` - Disk monitoring and reduced buffer size
5. `pyproject.toml` - Added psutil dependency

### New Features
- `_check_resource_usage()` - Real-time resource monitoring
- `cleanup_temp_files()` - Automatic cleanup of temporary files
- Enhanced buffer flushing with resource checks
- Disk space validation in GitHub Actions

## Expected Impact
- **Memory usage**: 40-60% reduction in peak memory usage
- **Disk space**: Better cleanup and monitoring prevents space exhaustion
- **Stability**: Automatic resource management prevents crashes
- **Visibility**: Better logging and monitoring for debugging

## Usage
The optimizations are transparent to users:
- Existing command-line arguments work unchanged
- Default behavior is more conservative but stable
- Users can still customize buffer sizes if needed

## Testing
Run the validation script:
```bash
python test_optimizations.py
```

## Monitoring
The scraper now provides detailed resource usage information:
```
[RESOURCE] Memory: 245.3MB, Disk free: 8.2GB, Buffer: 45 records
[WARNING] High resource usage detected - forcing buffer flush
```

## Future Improvements
1. **Compression**: Add optional compression for data files
2. **Streaming**: Implement streaming writes for very large datasets
3. **Chunking**: Break large scraping jobs into smaller chunks
4. **Caching optimization**: More intelligent cache management