# Flask Documentation RAG Assistant

A Retrieval-Augmented Generation (RAG) application that answers questions about Flask documentation using hybrid search, reranking, and LLM-powered response generation.

## Features

- Hybrid retrieval combining BM25 keyword search and vector search
- Reciprocal Rank Fusion (RRF) to combine retrieval results
- Jina reranker to improve retrieval relevance
- Groq API with `openai/gpt-oss-20b` for answer generation
- Redis caching for repeated queries
- Streaming responses using Server-Sent Events (SSE)
- Langfuse tracing and observability for monitoring retrieval and generation latency
- Responsive frontend built with HTML, CSS, and JavaScript
- Docker Compose-based application deployment

## Tech Stack

**Backend:** Python, FastAPI, OpenSearch

**AI/LLM:** Groq API (`openai/gpt-oss-20b`), Jina Reranker

**Retrieval:** BM25, vector search, Reciprocal Rank Fusion (RRF)

**Infrastructure:** Redis, PostgreSQL, Docker Compose

**Observability:** Langfuse

**Frontend:** HTML5, CSS3, Vanilla JavaScript

## Performance

- Reduced observed end-to-end request latency from **42.57 seconds to 3.42 seconds**, approximately a **92% reduction**, after switching LLM providers.
- Uses Langfuse to trace retrieval stages, reranking, and LLM generation.

*Performance figures are based on an observed request and may vary with query complexity, caching, network conditions, and provider load.*

## Getting Started

### 1. Configure environment variables

Create a `.env` file in the project root and configure the API credentials and service settings required by the application.

For Groq generation, configure your Groq API key and model:

```dotenv
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-20b
```

Configure any additional credentials required by your retrieval, reranking, and observability services. Never commit your `.env` file or API keys.

### 2. Start the backend and supporting services

```bash
docker compose -f compose.yml up -d --build
```

Check the API health endpoint:

```bash
curl http://localhost:8000/health
```

### 3. Start the frontend

Open a separate terminal and run:

```bash
cd frontend
python -m http.server 5500
```

Open [http://localhost:5500](http://localhost:5500).

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Check API health |
| `GET /search` | Retrieve relevant Flask documentation |
| `GET /ask` | Generate an answer with sources |
| `GET /stream` | Stream an answer progressively |

Interactive API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

## Observability

Langfuse is used to inspect request traces and measure the performance of retrieval and generation stages. This helps identify latency bottlenecks and evaluate the impact of optimization changes.

## Project Goal

Build a practical documentation assistant that retrieves relevant Flask documentation and generates useful, context-grounded answers with source references and low latency.
