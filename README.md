# Járókelő.hu RAG Pipeline

**AI-powered civic insights for Budapest**  

This project is a personal hobby: as someone who regularly rides a bike around the city, I report issues to local authorities and gradually contribute to improving our urban environment. The system builds a Retrieval-Augmented Generation (RAG) pipeline that collects and analyzes all public reports from [Járókelő.hu](https://jarokelo.hu). Users can explore, summarize, and gain insights into civic issues—both resolved and unresolved—filtered by district, category, and status.  

It automates the full pipeline: data scraping, preprocessing, text chunking, embedding generation, and vector store creation, enabling fast and flexible queries over civic reports.

## 1. Scrape data

Run:

    python scrape_data.py --headless true --start-page 1

- `--headless`: run Chrome without opening a window (`true` or `false`)  
- `--start-page`: page number to start from (default `1`)  

## 2. Preprocess data

Run:

    python preprocess_data.py

- Loads all `data/raw/*.jsonl` files  
- Cleans and normalizes text, date, and district  
- Splits long descriptions into ~400-token chunks  
- Saves results to `data/processed/issues_chunks.jsonl`  

## 3. Build vector store

With SentenceTransformers:

    python build_vector_store.py --backend faiss --embedding sentence-transformers/all-MiniLM-L6-v2

Or with OpenAI embeddings:

    python build_vector_store.py --backend faiss --embedding text-embedding-ada-002 --api-key YOUR_OPENAI_KEY

- `--backend`: `faiss` or `chroma`  
- `--embedding`: embedding model  
- `--api-key`: required only for OpenAI embeddings  
- Saves vector store to `data/vector_store/<backend>_YYYYMMDDTHHMMSSZ`
