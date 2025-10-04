@echo off
REM Járókelő Tracker - Windows Batch Commands
REM ========================================

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="continue-scraping" goto continue-scraping
if "%1"=="update-status" goto update-status
if "%1"=="detect-recent-changes" goto detect-recent-changes
if "%1"=="load-old-pending" goto load-old-pending
if "%1"=="scrape-urls-file" goto scrape-urls-file
if "%1"=="scrape-until-date" goto scrape-until-date
if "%1"=="show-scraping-resume-date" goto show-scraping-resume-date
if "%1"=="preprocess-all" goto preprocess-all
if "%1"=="build-vector-store" goto build-vector-store
if "%1"=="run-pipeline" goto run-pipeline
goto invalid

:help
echo Járókelő Tracker - Common Scraping Commands
echo ===========================================
echo.
echo Core scraping tasks:
echo   continue-scraping     Continue scraping from last scraped date onwards (no upper limit)
echo   update-status         Scrape newest entries and update status of existing records
echo.
echo Additional tasks:
echo   scrape-until-date     Scrape until specific date (set DATE env var: set DATE=2025-01-01)
echo   preprocess-all        Run both RAG and EDA preprocessing
echo   build-vector-store    Build FAISS vector store with default embedding model
echo   run-pipeline          Run full data pipeline (preprocess + vector store)
echo.
echo Utility tasks:
echo   show-scraping-resume-date  Show where scraping would resume from
echo.
echo Examples:
echo   jarokelo.bat continue-scraping
echo   jarokelo.bat update-status
echo   set DATE=2025-01-01 ^&^& jarokelo.bat scrape-until-date
goto end

:continue-scraping
echo Continuing scraping from last scraped date onwards...
poetry run python scripts/scrape_data.py --continue-scraping --data-dir "data/raw"
goto end

:update-status
echo Updating status of existing records and scraping new entries...
poetry run python scripts/scrape_data.py --update-existing-status --data-dir "data/raw"
goto end

:scrape-until-date
if "%DATE%"=="" (
    echo Error: Please set DATE environment variable. Example: set DATE=2025-01-01 ^&^& jarokelo.bat scrape-until-date
    goto end
)
echo Scraping until date: %DATE%
poetry run python scripts/scrape_data.py --start-page 1 --until-date %DATE% --data-dir "data/raw"
goto end

:show-scraping-resume-date
echo Checking resume date where scraping would continue from...
poetry run python -c "from src.jarokelo_tracker.scraper.data_manager import DataManager; dm = DataManager('data/raw'); resume_date, page = dm.get_scraping_resume_point(); print(f'Would resume from: {resume_date} (page {page})' if resume_date else 'No existing data - would start from page 1')"
goto end

:preprocess-all
echo Running RAG preprocessing...
poetry run python src/jarokelo_tracker/preprocess/preprocess_rag.py
echo Running EDA preprocessing...
poetry run python src/jarokelo_tracker/preprocess/preprocess_eda.py
goto end

:build-vector-store
echo Building FAISS vector store...
poetry run python scripts/build_vector_store.py --backend faiss --embedding sentence-transformers/distiluse-base-multilingual-cased-v2
goto end

:run-pipeline
echo Running RAG preprocessing...
poetry run python src/jarokelo_tracker/preprocess/preprocess_rag.py
echo Running EDA preprocessing...
poetry run python src/jarokelo_tracker/preprocess/preprocess_eda.py
echo Building FAISS vector store...
poetry run python scripts/build_vector_store.py --backend faiss --embedding sentence-transformers/distiluse-base-multilingual-cased-v2
echo Full data pipeline completed!
goto end

:invalid
echo Invalid command: %1
echo Run "jarokelo.bat help" to see available commands
goto end

:end