[![Data scraper](https://github.com/leweex95/jarokelo_tracker/actions/workflows/scraper.yml/badge.svg)](https://github.com/leweex95/jarokelo_tracker/actions/workflows/scraper.yml) [![Run data pipeline](https://github.com/leweex95/jarokelo_tracker/actions/workflows/data_pipeline.yml/badge.svg)](https://github.com/leweex95/jarokelo_tracker/actions/workflows/data_pipeline.yml) [![Update Github page](https://github.com/leweex95/jarokelo_tracker/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/leweex95/jarokelo_tracker/actions/workflows/pages/pages-build-deployment)

# Járókelő.hu RAG Pipeline

**AI-powered civic insights for Budapest**  

This project is a personal hobby: as someone who regularly rides a bike around the city, I report issues to local authorities and gradually contribute to improving our urban environment. The system builds a Retrieval-Augmented Generation (RAG) pipeline that collects and analyzes all public reports from [Járókelő.hu](https://jarokelo.hu). Users can explore, summarize, and gain insights into civic issues—both resolved and unresolved—filtered by district, category, and status.  

It automates the full pipeline: data scraping, preprocessing, text chunking, embedding generation, and vector store creation, enabling fast and flexible queries over civic reports.

## 1. Scrape data

Run:

    python ./scripts/scrape_data.py --headless true --start-page 1 --until-date 2025-08-01

- `--headless`: run Chrome without opening a window (`true` or `false`)  
- `--start-page`: page number to start from (default `1`)  
- `--until-date`: a date in YYYY-MM-DD format until which we need to continue the scraping (default none)

## 2. Preprocess data

Run:

    poetry run python ./scripts/preprocess_data.py

- Loads all `data/raw/*.jsonl` files  
- Cleans and normalizes text, date, and district  
- Splits long descriptions into ~400-token chunks  
- Saves results to `data/processed/rag/issues_chunks.jsonl`  

## 3. Build vector store

With SentenceTransformers:

    poetry run python ./scripts/build_vector_store.py --backend faiss --embedding sentence-transformers/distiluse-base-multilingual-cased-v2

- `--backend`: `faiss` or `chroma`  
- `--embedding`: embedding model
- Saves vector store to `data/vector_store/<backend>_YYYYMMDDTHHMMSSZ`

## 4. Run the RAG pipeline

    poetry run python ./src/jarokelo_tracker/rag_pipeline.py --query "What issues are not yet resolved in district 8 in Budapest?" --vector-backend "faiss" --embedding-provider "local" --local-model "distiluse-base-multilingual-cased-v2" --headless true --top_k 20

## 5. Run the streamlit app

    poetry run streamlit run streamlit_app/app.py

## Automated workflows

Note: Due to Github Actions workflows having a max. 10 GB cache limit, it is not possible to cache the entire .venv and project dependencies for speedup. Therefore, I sticked with a less efficient workflow in which we are forced to reinstall all dependencies in each workflow job. A more resource efficient method in this case would certainly be to drop job separation and integrate everything into one huge job but I intentionally chose to gave preference to the principle of traceability, ensuring that all steps of a complex pipeline are transparently visible. In a real-world production setup, we would certainly not have such limitations on cache size, hence keeping the pipeline intact is the most production-ready way to set up this workflow. But the 10 GB limit still allowed me to cache only `~/.cache/pypoetry`, still speeding up installation of dependencies, as the wheel files are preserved in between workflow jobs.

