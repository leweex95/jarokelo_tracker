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
- Saves results to `data/processed/issues_chunks.jsonl`  

## 3. Build vector store

With SentenceTransformers:

    poetry run python ./scripts/build_vector_store.py --backend faiss --embedding sentence-transformers/distiluse-base-multilingual-cased-v2

Or with OpenAI embeddings:

    poetry run python ./scripts/build_vector_store.py --backend faiss --embedding sentence-transformers/distiluse-base-multilingual-cased-v2

- `--backend`: `faiss` or `chroma`  
- `--embedding`: embedding model  
- `--api-key`: required only for OpenAI embeddings  
- Saves vector store to `data/vector_store/<backend>_YYYYMMDDTHHMMSSZ`

## 4. Run the RAG pipeline

    poetry run python ./src/jarokelo_tracker/rag_pipeline.py --query="What are the unresolved issues in Tömő street in District VIII?" --vector_backend=faiss --embedding_provider=local
