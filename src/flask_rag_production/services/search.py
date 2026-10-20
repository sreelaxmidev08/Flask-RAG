import os
import time
from contextlib import contextmanager

from opensearchpy import OpenSearch

from flask_rag_production.services.embeddings import JinaEmbeddings
from flask_rag_production.services.reranker import Reranker


OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.getenv("OPENSEARCH_PORT", "9200"))
INDEX_NAME = "flask_chunks"

client = OpenSearch(
    hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}]
)
embedding_model = JinaEmbeddings()
reranker = Reranker()


@contextmanager
def _traced_span(parent, name: str, input_data: dict):
    """Create and safely close a Langfuse child span when a parent is supplied."""
    if parent is None:
        yield None
        return

    span = parent.start_observation(
        as_type="span",
        name=name,
        input=input_data,
    )
    try:
        yield span
    except Exception as exc:
        span.update(
            level="ERROR",
            status_message=str(exc),
        )
        raise
    finally:
        span.end()


def search_chunks(query: str, size: int = 5) -> list[dict]:
    """Retrieve documents using OpenSearch BM25."""
    search_body = {
        "size": size,
        "query": {"match": {"content": query}},
    }
    response = client.search(index=INDEX_NAME, body=search_body)

    return [
        {
            "score": hit["_score"],
            "chunk_id": hit["_source"]["chunk_id"],
            "document_id": hit["_source"]["document_id"],
            "title": hit["_source"]["title"],
            "source_file": hit["_source"]["source_file"],
            "content": hit["_source"]["content"],
        }
        for hit in response["hits"]["hits"]
    ]


def vector_search_chunks(
    query: str,
    size: int = 5,
    trace_parent=None,
) -> list[dict]:
    """Embed the query and retrieve nearest chunks from OpenSearch."""
    with _traced_span(
        trace_parent,
        "query-embedding",
        {"query": query, "task": "retrieval.query"},
    ) as embedding_span:
        start = time.perf_counter()
        query_embedding = embedding_model.generate(
            [query], task="retrieval.query"
        )[0]
        embedding_time = time.perf_counter() - start
        if embedding_span is not None:
            embedding_span.update(
                output={"embedding_dimensions": len(query_embedding)},
                metadata={"duration_seconds": round(embedding_time, 4)},
            )

    search_body = {
        "size": size,
        "query": {
            "knn": {
                "embedding": {"vector": query_embedding, "k": size}
            }
        },
    }

    with _traced_span(
        trace_parent,
        "opensearch-vector-search",
        {"index": INDEX_NAME, "requested_size": size},
    ) as vector_span:
        start = time.perf_counter()
        response = client.search(index=INDEX_NAME, body=search_body)
        vector_retrieval_time = time.perf_counter() - start
        hits = response["hits"]["hits"]
        if vector_span is not None:
            vector_span.update(
                output={"result_count": len(hits)},
                metadata={"duration_seconds": round(vector_retrieval_time, 4)},
            )

    results = [
        {
            "score": hit["_score"],
            "chunk_id": hit["_source"]["chunk_id"],
            "document_id": hit["_source"]["document_id"],
            "title": hit["_source"]["title"],
            "source_file": hit["_source"]["source_file"],
            "content": hit["_source"]["content"],
        }
        for hit in hits
    ]

    print("\n===== VECTOR SEARCH PERFORMANCE =====")
    print(f"Query embedding:    {embedding_time:.2f}s")
    print(f"OpenSearch kNN:     {vector_retrieval_time:.2f}s")
    print(f"Total vector stage: {embedding_time + vector_retrieval_time:.2f}s")
    print("======================================\n")
    return results


def reciprocal_rank_fusion(
    bm25_results: list[dict],
    vector_results: list[dict],
    k: int = 60,
) -> list[dict]:
    """Combine BM25 and vector rankings using reciprocal rank fusion."""
    scores = {}
    results_by_chunk_id = {}

    for rank, result in enumerate(bm25_results, start=1):
        chunk_id = result["chunk_id"]
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank)
        results_by_chunk_id[chunk_id] = result

    for rank, result in enumerate(vector_results, start=1):
        chunk_id = result["chunk_id"]
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank)
        results_by_chunk_id[chunk_id] = result

    ranked_chunk_ids = sorted(scores, key=scores.get, reverse=True)
    results = []
    for chunk_id in ranked_chunk_ids:
        result = results_by_chunk_id[chunk_id].copy()
        result["rrf_score"] = scores[chunk_id]
        results.append(result)
    return results


def hybrid_search_chunks(
    query: str,
    size: int = 5,
    candidate_size: int = 10,
    trace_parent=None,
) -> list[dict]:
    """Run BM25, vector retrieval, RRF, and reranking with child traces."""
    total_start = time.perf_counter()

    # 1. BM25 retrieval
    with _traced_span(
        trace_parent,
        "bm25-search",
        {"query": query, "index": INDEX_NAME, "requested_size": candidate_size},
    ) as bm25_span:
        start = time.perf_counter()
        bm25_results = search_chunks(query, size=candidate_size)
        bm25_time = time.perf_counter() - start
        if bm25_span is not None:
            bm25_span.update(
                output={"result_count": len(bm25_results)},
                metadata={"duration_seconds": round(bm25_time, 4)},
            )

    # 2. Query embedding and vector retrieval
    vector_results = vector_search_chunks(
        query,
        size=candidate_size,
        trace_parent=trace_parent,
    )

    # 3. Reciprocal rank fusion
    with _traced_span(
        trace_parent,
        "rrf-fusion",
        {
            "bm25_result_count": len(bm25_results),
            "vector_result_count": len(vector_results),
            "rrf_k": 60,
        },
    ) as rrf_span:
        start = time.perf_counter()
        fused_results = reciprocal_rank_fusion(bm25_results, vector_results)
        rrf_time = time.perf_counter() - start
        if rrf_span is not None:
            rrf_span.update(
                output={"fused_result_count": len(fused_results)},
                metadata={"duration_seconds": round(rrf_time, 4)},
            )

    print(f"RRF candidates: {len(fused_results)}")

    # 4. Jina reranking — measure the external API call separately.
    rerank_start = time.perf_counter()
    with _traced_span(
        trace_parent,
        "jina-reranking",
        {
            "model": reranker.model,
            "candidate_count": len(fused_results),
            "requested_top_k": size,
        },
    ) as rerank_span:
        reranked_results = reranker.rerank(
            query,
            fused_results,
            top_k=size,
        )
        reranker_time = time.perf_counter() - rerank_start
        if rerank_span is not None:
            rerank_span.update(
                output={
                    "result_count": len(reranked_results),
                    "reranked_chunk_ids": [
                        result["chunk_id"] for result in reranked_results
                    ],
                },
                metadata={
                    "duration_seconds": round(reranker_time, 4),
                    "candidate_count": len(fused_results),
                },
            )

    total_time = time.perf_counter() - total_start
    print("\n===== RETRIEVAL PERFORMANCE =====")
    print(f"BM25 time:       {bm25_time:.2f}s")
    print(f"Vector time:     (see embedding and vector spans)")
    print(f"RRF time:        {rrf_time:.4f}s")
    print(f"Reranker time:   {reranker_time:.2f}s")
    print(f"Total retrieval: {total_time:.2f}s")
    print("=================================\n")
    return reranked_results
