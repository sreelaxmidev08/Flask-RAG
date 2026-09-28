from opensearchpy import OpenSearch
import os
import time

from flask_rag_production.services.embeddings import JinaEmbeddings
from flask_rag_production.services.reranker import Reranker


OPENSEARCH_HOST = os.getenv(
    "OPENSEARCH_HOST",
    "localhost",
)

OPENSEARCH_PORT = int(
    os.getenv(
        "OPENSEARCH_PORT",
        "9200",
    )
)

INDEX_NAME = "flask_chunks"


client = OpenSearch(
    hosts=[
        {
            "host": OPENSEARCH_HOST,
            "port": OPENSEARCH_PORT,
        }
    ]
)

embedding_model = JinaEmbeddings()
reranker = Reranker()


def search_chunks(
    query: str,
    size: int = 5,
) -> list[dict]:

    search_body = {
        "size": size,
        "query": {
            "match": {
                "content": query
            }
        },
    }

    response = client.search(
        index=INDEX_NAME,
        body=search_body,
    )

    results = []

    for hit in response["hits"]["hits"]:
        results.append(
            {
                "score": hit["_score"],
                "chunk_id": hit["_source"]["chunk_id"],
                "document_id": hit["_source"]["document_id"],
                "title": hit["_source"]["title"],
                "source_file": hit["_source"]["source_file"],
                "content": hit["_source"]["content"],
            }
        )

    return results


def vector_search_chunks(
    query: str,
    size: int = 5,
) -> list[dict]:

    # --------------------------------------------------
    # 1. Query embedding
    # --------------------------------------------------

    start = time.perf_counter()

    query_embedding = embedding_model.generate(
        [query],
        task="retrieval.query",
    )[0]

    embedding_time = time.perf_counter() - start

    # --------------------------------------------------
    # 2. OpenSearch vector retrieval
    # --------------------------------------------------

    search_body = {
        "size": size,
        "query": {
            "knn": {
                "embedding": {
                    "vector": query_embedding,
                    "k": size,
                }
            }
        },
    }

    start = time.perf_counter()

    response = client.search(
        index=INDEX_NAME,
        body=search_body,
    )

    vector_retrieval_time = time.perf_counter() - start

    # --------------------------------------------------
    # 3. Build results
    # --------------------------------------------------

    results = []

    for hit in response["hits"]["hits"]:
        results.append(
            {
                "score": hit["_score"],
                "chunk_id": hit["_source"]["chunk_id"],
                "document_id": hit["_source"]["document_id"],
                "title": hit["_source"]["title"],
                "source_file": hit["_source"]["source_file"],
                "content": hit["_source"]["content"],
            }
        )

    # --------------------------------------------------
    # 4. Performance report
    # --------------------------------------------------

    print("\n===== VECTOR SEARCH PERFORMANCE =====")
    print(f"Query embedding:    {embedding_time:.2f}s")
    print(f"OpenSearch kNN:     {vector_retrieval_time:.2f}s")
    print(
        f"Total vector stage: "
        f"{embedding_time + vector_retrieval_time:.2f}s"
    )
    print("======================================\n")

    return results


def reciprocal_rank_fusion(
    bm25_results: list[dict],
    vector_results: list[dict],
    k: int = 60,
) -> list[dict]:

    scores = {}
    results_by_chunk_id = {}

    # --------------------------------------------------
    # Add BM25 rankings
    # --------------------------------------------------

    for rank, result in enumerate(
        bm25_results,
        start=1,
    ):

        chunk_id = result["chunk_id"]

        scores[chunk_id] = (
            scores.get(chunk_id, 0)
            + 1 / (k + rank)
        )

        results_by_chunk_id[chunk_id] = result

    # --------------------------------------------------
    # Add vector rankings
    # --------------------------------------------------

    for rank, result in enumerate(
        vector_results,
        start=1,
    ):

        chunk_id = result["chunk_id"]

        scores[chunk_id] = (
            scores.get(chunk_id, 0)
            + 1 / (k + rank)
        )

        results_by_chunk_id[chunk_id] = result

    # --------------------------------------------------
    # Sort by RRF score
    # --------------------------------------------------

    ranked_chunk_ids = sorted(
        scores,
        key=scores.get,
        reverse=True,
    )

    results = []

    for chunk_id in ranked_chunk_ids:

        result = results_by_chunk_id[
            chunk_id
        ].copy()

        result["rrf_score"] = scores[
            chunk_id
        ]

        results.append(result)

    return results


def hybrid_search_chunks(
    query: str,
    size: int = 5,
    candidate_size: int = 10,
) -> list[dict]:

    # --------------------------------------------------
    # 1. BM25
    # --------------------------------------------------

    start = time.perf_counter()

    bm25_results = search_chunks(
        query,
        size=candidate_size,
    )

    bm25_time = time.perf_counter() - start

    # --------------------------------------------------
    # 2. Vector search
    # --------------------------------------------------

    start = time.perf_counter()

    vector_results = vector_search_chunks(
        query,
        size=candidate_size,
    )

    vector_time = time.perf_counter() - start

    # --------------------------------------------------
    # 3. RRF
    # --------------------------------------------------

    start = time.perf_counter()

    fused_results = reciprocal_rank_fusion(
        bm25_results,
        vector_results,
    )

    rrf_time = time.perf_counter() - start

    print(
        f"RRF candidates: {len(fused_results)}"
    )

    # --------------------------------------------------
    # 4. Reranking
    # --------------------------------------------------

    start = time.perf_counter()

    reranked_results = reranker.rerank(
        query,
        fused_results,
        top_k=size,
    )

    reranker_time = time.perf_counter() - start

    # --------------------------------------------------
    # 5. Total retrieval time
    # --------------------------------------------------

    total_time = (
        bm25_time
        + vector_time
        + rrf_time
        + reranker_time
    )

    # --------------------------------------------------
    # 6. Performance report
    # --------------------------------------------------

    print("\n===== RETRIEVAL PERFORMANCE =====")
    print(f"BM25 time:       {bm25_time:.2f}s")
    print(f"Vector time:     {vector_time:.2f}s")
    print(f"RRF time:        {rrf_time:.4f}s")
    print(f"Reranker time:   {reranker_time:.2f}s")
    print(f"Total retrieval: {total_time:.2f}s")
    print("=================================\n")

    return reranked_results