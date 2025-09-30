# Járókelő Tracker - Common Scraping Tasks
# =====================================

# Default target
.PHONY: help
help:
	@echo "Járókelő Tracker - Common Scraping Commands"
	@echo "==========================================="
	@echo ""
	@echo "Core scraping tasks:"
	@echo "  continue-scraping     Continue scraping from last scraped date onwards (no upper limit)"
	@echo "  update-status         Scrape newest entries and update status of existing records"
	@echo ""
	@echo "Additional tasks:"
	@echo "  scrape-until-date     Scrape until specific date (set DATE=YYYY-MM-DD)"
	@echo "  preprocess-all        Run both RAG and EDA preprocessing"
	@echo "  build-vector-store    Build FAISS vector store with default embedding model"
	@echo "  run-pipeline          Run full data pipeline (preprocess + vector store)"
	@echo ""
	@echo "Utility tasks:"
	@echo "  show-scraping-resume-date  Show where scraping would resume from"
	@echo ""
	@echo "Examples:"
	@echo "  make continue-scraping"
	@echo "  make update-status"
	@echo "  make scrape-until-date DATE=2025-01-01"

# =============================================================================
# CORE SCRAPING TASKS (Your 2 main use cases)
# =============================================================================

# Task 1: Continue scraping from the last scraped date onwards without an upper limit
.PHONY: continue-scraping
continue-scraping:
	@echo "🚀 Continuing scraping from last scraped date onwards..."
	poetry run python scripts/scrape_data.py \
		--backend bs \
		--continue-scraping \
		--data-dir "data/raw3"

# Task 2: Scrape newest entries and update status of existing records
.PHONY: update-status
update-status:
	@echo "🔄 Updating status of existing records and scraping new entries..."
	poetry run python scripts/scrape_data.py \
		--backend bs \
		--update-existing-status \
		--data-dir "data/raw3"

# =============================================================================
# ADDITIONAL SCRAPING TASKS
# =============================================================================

# Scrape until a specific date (usage: make scrape-until-date DATE=2025-01-01)
.PHONY: scrape-until-date
scrape-until-date:
	@if [ -z "$(DATE)" ]; then \
		echo "❌ Error: Please specify DATE. Usage: make scrape-until-date DATE=YYYY-MM-DD"; \
		exit 1; \
	fi
	@echo "📅 Scraping until date: $(DATE)"
	poetry run python scripts/scrape_data.py \
		--backend bs \
		--start-page 1 \
		--until-date $(DATE) \
		--data-dir "data/raw3"

# =============================================================================
# DATA PIPELINE TASKS
# =============================================================================

# Run both RAG and EDA preprocessing
.PHONY: preprocess-all
preprocess-all:
	@echo "🔧 Running RAG preprocessing..."
	poetry run python src/jarokelo_tracker/preprocess/preprocess_rag.py
	@echo "📊 Running EDA preprocessing..."
	poetry run python src/jarokelo_tracker/preprocess/preprocess_eda.py

# Build FAISS vector store with default multilingual model
.PHONY: build-vector-store
build-vector-store:
	@echo "🏗️ Building FAISS vector store..."
	poetry run python scripts/build_vector_store.py \
		--backend faiss \
		--embedding sentence-transformers/distiluse-base-multilingual-cased-v2

# Run full data pipeline (preprocess + vector store)
.PHONY: run-pipeline
run-pipeline: preprocess-all build-vector-store
	@echo "✅ Full data pipeline completed!"

# =============================================================================
# UTILITY TASKS
# =============================================================================

# Show where scraping would resume from
.PHONY: show-scraping-resume-date
show-scraping-resume-date:
	@echo "📍 Checking resume date where scraping would continue from..."
	poetry run python -c "from src.jarokelo_tracker.scraper.data_manager import DataManager; dm = DataManager('data/raw3'); resume_date, page = dm.get_scraping_resume_point(); print(f'Would resume from: {resume_date} (page {page})' if resume_date else 'No existing data - would start from page 1')"
