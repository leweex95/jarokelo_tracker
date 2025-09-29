# Performance Benchmarks

This directory contains the performance benchmarking experiment for the Jarokelo scraper optimization project.

## Files

### Scripts
- **`performance_benchmark.py`** - Complete performance benchmark comparing sync, async, and threading approaches with 100 URLs for statistical significance

### Results
- **`benchmark_results.json`** - Benchmark results showing async approach delivers 8.59x speedup

## Key Findings

The benchmark with 100 URLs showed:
- **Async (10 concurrent)**: 8.59x speedup, 26.77s vs 229.98s sync
- **Perfect reliability**: 100% success rate
- **Memory efficient**: Actually reduces memory usage (-0.1MB vs +25.8MB sync)

## Usage

To run the performance benchmark:

```bash
cd experiments/performance_benchmarks
python performance_benchmark.py
```

## Analysis

Full analysis and recommendations are available in the [GitHub Pages documentation](../../docs/scraper_optimization_benchmark_analysis.html).

## Implementation Status

- ✅ Benchmarking completed
- ⏳ Async implementation pending
- ⏳ Production deployment pending