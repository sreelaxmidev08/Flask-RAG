# Flask Documentation RAG Assistant

A Retrieval-Augmented Generation (RAG) application that answers questions about Flask documentation using hybrid search, reranking, and LLM-powered response generation.

## Features

- Hybrid retrieval using BM25 and vector search
- Reciprocal Rank Fusion (RRF) for combining search results
- Jina reranker for improving retrieval relevance
- Gemini API for answer generation
- Redis caching for repeated queries
- Streaming responses using Server-Sent Events (SSE)
- Langfuse for tracing and observability
- Responsive frontend built with HTML, CSS, and JavaScript

## Tech Stack

**Backend:** Python, FastAPI, OpenSearch

**AI/LLM:** Gemini API, Jina Reranker

**Infrastructure:** Redis, PostgreSQL, Docker Compose

**Observability:** Langfuse

**Frontend:** HTML5, CSS3, Vanilla JavaScript

## Getting Started

### 1. Configure environment variables

Create a `.env` file in the project root and configure the API credentials and service settings required by the application.

### 2. Start the backend

```bash
docker compose -f compose.yml up -d --build
```

Check the API:

```bash
curl http://localhost:8000/health
```

### 3. Start the frontend

```bash
cd frontend
python -m http.server 5500
```

Open [http://localhost:5500](http://localhost:5500).

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Health check |
| `GET /search` | Retrieve relevant documentation |
| `GET /ask` | Generate an answer with sources |
| `GET /stream` | Stream an answer progressively |

Interactive API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

## Project Goal

Build a practical documentation assistant that retrieves relevant Flask documentation and generates useful, context-grounded answers with low latency and reliable source references.
