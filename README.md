![Python Version](https://img.shields.io/badge/python-3.11%2B-blue) ![License](https://img.shields.io/github/license/leweex95/jarokelo_tracker) [![Data scraper](https://github.com/leweex95/jarokelo_tracker/actions/workflows/scraper.yml/badge.svg)](https://github.com/leweex95/jarokelo_tracker/actions/workflows/scraper.yml) [![Run data pipeline](https://github.com/leweex95/jarokelo_tracker/actions/workflows/data_pipeline.yml/badge.svg)](https://github.com/leweex95/jarokelo_tracker/actions/workflows/data_pipeline.yml) [![Full data pipeline](https://github.com/leweex95/jarokelo_tracker/actions/workflows/full_data_pipeline.yml/badge.svg)](https://github.com/leweex95/jarokelo_tracker/actions/workflows/full_data_pipeline.yml) [![Automated RAG Evaluation Pipeline](https://github.com/leweex95/jarokelo_tracker/actions/workflows/eval_pipeline.yml/badge.svg)](https://github.com/leweex95/jarokelo_tracker/actions/workflows/eval_pipeline.yml) [![Update Github page](https://github.com/leweex95/jarokelo_tracker/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/leweex95/jarokelo_tracker/actions/workflows/pages/pages-build-deployment)

---

# Járókelő.hu RAG Pipeline

**Using RAG to evaluate the state of civic issues across Budapest**  

---

## Overview

This project builds a full **Retrieval-Augmented Generation (RAG)** pipeline for the data of [Járókelő.hu](https://jarokelo.hu), a Hungarian civic platform for reporting and tracking public issues across Budapest and other Hungarian cities.

It automates data scraping, preprocessing, chunking, embedding, vector store creation, and provides a Streamlit UI for interactive querying and debugging. I am currently working on exploratory data analysis and building an informative PowerBI dashboard for further insights on the type of civic insights and their state of resolution — by district, issue type, and many more.

> _This project came as a personal hobby. I regularly ride a bike around Budapest, and have been noticing disrepair, vandalism, and lack of care of our public spaces. Instead of just complaining or falling into apathy, I began using the Járókelő platform and found a new hope that even in a hostile political climate and a financially suffocated Budapest, issues can and will be resolved -- at least most of them, if reported to and tracked at the authorities._

## Features

- **Data scraping**: Automated collection of public reports from Járókelő.hu using Selenium, triggered on a daily basis. 
- **Preprocessing**: Cleans, normalizes, and chunks text for efficient retrieval, as well as for exploratory data analysis and Power BI reporting. Automated to run daily and on the arrival of any new scraped data.
- **Vector store**: Embeds and indexes the corpus using either FAISS or Chroma for fast semantic search.
- **RAG pipeline**: The core of the system, responsible for answering user queries by retrieving relevant issues and generating responses via LLM (currently OpenAI's ChatGPT).
- **Streamlit app**: User-friendly interface for interacting with the RAG pipeline.
- **Embeddings visualization**: Interactive 2D visualizations of text embeddings using UMAP/t-SNE to explore patterns and clusters in civic issues.
- **Experiments**: More applied research focused section for comparing embedding models, vector stores, using state-of-the-art RAG evaluation techniques.
- **PowerBI dashboard**: A comprehensive interactive dashboard to understand the state of civic issues in a visual manner.

---

### Quickstart

1. Install dependencies

    poetry install

2. Scrape data

The scraper supports two backends:
- **BeautifulSoup** (default): Faster, more reliable, no browser needed
- **Selenium**: Uses a headless Chrome browser (useful for dynamic content)

_From scratch with BeautifulSoup (recommended):_

    poetry run python ./scripts/scrape_data.py --backend beautifulsoup --start-page 1 --until-date 2025-08-01

_From scratch with Selenium:_

    poetry run python ./scripts/scrape_data.py --backend selenium --headless true --start-page 1 --until-date 2025-08-01

_Or if there is already an amount of scraped data under `data/raw`, the scraper can continue from the last-scraped entry:_

    poetry run python ./scripts/scrape_data.py --backend beautifulsoup --continue-scraping

_You can also use the shorthand `bs` for `beautifulsoup`:_

    poetry run python ./scripts/scrape_data.py --backend bs --continue-scraping

_To update the status of existing records (e.g., when "Válaszra vár" changes to "MEGOLDOTT"):_

    poetry run python ./scripts/scrape_data.py --backend bs --update-existing-status

This efficiently checks and updates the status of already-scraped records without performing full re-scraping. When a status changes to "MEGOLDOTT" (resolved), the scraper automatically performs a full re-scrape to capture the `resolution_date`.

### ⚡ Optimized Status Update Pipeline

The status update process has been revolutionized with a **24x performance improvement**, solving the previous 6-hour timeout issue:

- **🚀 Speed**: From 6+ hours down to **10-15 minutes total**
- **🎯 Smart Processing**: Only scrapes URLs that actually changed
- **📊 4-Job Architecture**: Parallel processing with clear dependencies
- **⚙️ Configurable**: Tunable cutoff period (default: 3 months)

**New optimized commands:**

```bash
# Fast detection of recently changed URLs
poetry run python scripts/scrape_data.py --fetch-changed-urls --cutoff-months 3

# Load old pending URLs for checking
poetry run python scripts/scrape_data.py --load-old-pending --cutoff-months 3

# Scrape specific URLs from file
poetry run python scripts/scrape_data.py --scrape-urls-file recent_changed_urls.txt
```

The GitHub Actions workflow now runs 4 parallel jobs instead of 1 monolithic process, providing detailed tracking and 100% reliability. See [docs/optimized_status_pipeline.html](https://leweex95.github.io/jarokelo_tracker/optimized_status_pipeline.html) for complete technical details.

### Quick Commands with Makefile

For convenience, common scraping tasks are available as short commands.

**Prerequisites:**
- **Windows:** Use the included `jarokelo.bat` file (no installation needed!) or optionally install Make via: `winget install GnuWin32.Make`
- **macOS/Linux:** Make is usually pre-installed

**View all available commands:**

```bash
# Windows (using batch file - recommended)
jarokelo.bat help

# macOS/Linux (using Makefile)
make help
```

**Most commonly used commands:**

```bash
# Windows
jarokelo.bat continue-scraping
jarokelo.bat update-status

# macOS/Linux  
make continue-scraping
make update-status
```

**Scrape until a specific date:**

```bash
# Windows
set DATE=2025-01-01 && jarokelo.bat scrape-until-date

# macOS/Linux
make scrape-until-date DATE=2025-01-01
```

**Other useful commands:**

```bash
# Show resume point
jarokelo.bat show-scraping-resume-date    # Windows
make show-scraping-resume-date           # macOS/Linux

# Data pipeline
jarokelo.bat run-pipeline        # Windows  
make run-pipeline               # macOS/Linux
```

**Alternative: Direct Poetry Commands**

If you prefer to use poetry commands directly:

```bash
# Continue scraping
poetry run python scripts/scrape_data.py --backend bs --continue-scraping --data-dir "data/raw"

# Update status
poetry run python scripts/scrape_data.py --backend bs --update-existing-status --data-dir "data/raw"

# Scrape until date
poetry run python scripts/scrape_data.py --backend bs --start-page 1 --until-date 2025-01-01 --data-dir "data/raw"
```

**Yes, you can now use short commands instead of the longer poetry commands!** 🎉
- **Windows users:** Use `jarokelo.bat` (no installation required)
- **macOS/Linux users:** Use `make` commands

3. Preprocess data

I implemented two types of preprocessing. One is specifically for the vector store and RAG functionality (`preprocess_rag.py`) while the other is for exploratory data analysis and extracting insights from data via Power BI dashboarding (`preprocess_eda.py`).

    poetry run python ./src/jarokelo_tracker/preprocess/preprocess_rag.py 

This loads raw jsonl files, cleans and normalizes their content, splits issue descriptions that are longer than 400 tokens to chunks, and saves the output to `data/processed/rag`.

    poetry run python ./src/jarokelo_tracker/preprocess/preprocess_eda.py 

This loads raw jsonl files, cleans and normalizes their content, and prepares a set of csv files for the Power BI dashboarding at `data/processed/powerbi`.

4.  Build vector store

    poetry run python ./scripts/build_vector_store.py --backend faiss --embedding sentence-transformers/distiluse-base-multilingual-cased-v2

This saves the vector store to `data/vector_store/<backend>_YYYYMMDDTHHMMSSZ` and **automatically generates interactive embeddings visualizations** saved to `docs/`.

5. (Optional) Generate embeddings visualizations

The vector store building automatically creates visualizations, but you can also generate them manually:

    # Generate visualization with default settings (colored by district)
    poetry run python ./scripts/visualize_embeddings.py
    
    # Create comprehensive demo with multiple color schemes
    poetry run python ./scripts/demo_embeddings_visualization.py
    
    # Color by different metadata fields
    poetry run python ./scripts/visualize_embeddings.py --color-by status
    poetry run python ./scripts/visualize_embeddings.py --color-by category

See [docs/embeddings_visualization.md](docs/embeddings_visualization.md) for detailed usage instructions.

6. Run the RAG pipeline

    poetry run python ./src/jarokelo_tracker/rag/pipeline.py --query "What issues are not yet resolved in district 8 in Budapest?" --vector-backend "faiss" --headless true --top_k 5

Encodes the input query, fetches the top 5 closest matches from the vector store and feeds it to an LLM for answer generation.

7. (Optional) Run RAG evaluation

    poetry run python -m jarokelo_tracker.rag.evaluation.evaluate \
        --eval-set-path data/eval/eval_set.json \
        --vector-backend faiss \
        --embedding-provider local \
        --local-model distiluse-base-multilingual-cased-v2 \
        --topk "1,5,10" \
        --lang en

This evaluates retrieval performance and saves results to `experiments/results/retrieval_eval/`. You can then generate an HTML report:

    poetry run python ./src/jarokelo_tracker/rag/evaluation/assemble_retrieval_reports.py \
        --results-dir experiments/results/retrieval_eval

8. Launch the streamlit app

    poetry run streamlit run streamlit_app/app.py

---

## Streamlit UI

The streamlit UI allows users to interact with my RAG service. For convenience, I added an optional debug checkbox which prints out the entire debug trace from the RAG pipeline. In case the RAG pipeline crashes, this comes very handy to pinpoint where the problem lies.

Main components and functionalities:

- **Query input**: Ask questions about civic issues.
- **Debug checkbox** and **debug logs**: If the checkbox is checked, detailed logs will be shown from the RAG pipeline. I added this for my convenience to pinpoint potential issues easier.
- **Result box**: Displays the final answer with completion time.

![Streamlit UI](assets/streamlit_ui_dark_mode.png)*The streamlit UI in dark mode*

## Automated workflows and MLOps

The repository leverages GitHub Actions for a robust, fully automated data and ML pipeline, incorporating MLOps best practices to this personal project.

- **Automated scraper**:
    - Runs nightly or on-demand via the [scraper.yml](./.github/workflows/scraper.yml) workflow
    - Scrapes new civic issue data from Járókelő.hu using BeautifulSoup (faster and more reliable than the previous Selenium approach).
    - Commits and pushes new raw data files to the repository automatically.

- **Automated data pipeline**:
    - Triggered by new data arrival (commit and push) or on-demand via [data_pipeline.yml](./.github/workflows/data_pipeline.yml).
    - Handles preprocessing (cleaning, normalization, chunking), vector store building, EDA report generation, and CSV file export for Power BI dashboarding.
    - Includes automated cleanup of old vector stores and cache management to stay within GitHub’s 10 GB cache limit (now only caching Poetry folders: ~/.cache/pypoetry/cache and ~/.cache/pypoetry/artifacts, ensuring we are around ~8 GB total cache).

- **Automated RAG evaluation**:
    - Runs nightly at 23:00 UTC or on-demand via [eval_pipeline.yml](./.github/workflows/eval_pipeline.yml)
    - Evaluates retrieval performance using standard IR metrics (hit rate, recall@k, precision@k)
    - Supports configurable parameters: embedding models, vector backends, top-k values, and languages
    - Generates automated HTML reports with interactive Plotly charts showing performance trends
    - Results automatically committed and deployed to [GitHub Pages dashboard](https://leweex95.github.io/jarokelo_tracker/experiments/retrieval_eval_report.html)

- **Experiment results aggregation**:
    - Triggered automatically by new reports arrival (commit and push) or on-demand via [aggregate_embedding_results.yml](.github/workflows/aggregate_embedding_results.yml) to collect and aggregate experiment results from [embedding comparison](./experiments/embeddings_comparison.py)
    - **Todo**: This still has to be combined with an automated build and deploy step to immediately reflect on our Github page. 

## Experiments

This is a continuously evolving, applied research focused section aiming at presenting a state-of-the-art RAG system evaluation. 

1. **Embedding model comparison**:

The current [embeddings_comparison.py](./experiments/embeddings_comparison.py) script benchmarks multiple Hungarian, English, and multilingual sentence embedding models on real civic data.

2. **RAG evaluation**:

A comprehensive automated RAG evaluation pipeline that measures retrieval performance using standard information retrieval metrics:

- **Hit rate**: Proportion of queries where at least one relevant document is retrieved
- **Recall@k**: Average proportion of relevant documents retrieved in top-k results  
- **Precision@k**: Average proportion of retrieved documents that are relevant

The evaluation supports:
- Multiple top-k values (configurable, e.g., 1,5,10) for comprehensive analysis
- Both Hungarian and English query evaluation
- Multiple vector backends (FAISS, Chroma) and embedding models
- Automated report generation with interactive plots and historical tracking
- Integration with GitHub Pages for live dashboard viewing

Results are automatically tracked and visualized at [experiments/retrieval_eval_report.html](https://leweex95.github.io/jarokelo_tracker/experiments/retrieval_eval_report.html).

---

## Github Pages

The project's [Github Pages site](https://leweex95.github.io/jarokelo_tracker/) is automatically updated with experiment results and (future) evaluation reports.
