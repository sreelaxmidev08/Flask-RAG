from flask_rag_production.services.search import hybrid_search_chunks
from flask_rag_production.services.reranker import Reranker


query = "How do I enable debug mode in Flask?"

results = hybrid_search_chunks(
    query,
    size=20,
    candidate_size=20,
)

reranker = Reranker()

reranked_results = reranker.rerank(
    query,
    results,
    top_k=5,
)

print("\nRERANKED RESULTS\n")

for i, result in enumerate(reranked_results, start=1):
    print(f"--- Result {i} ---")
    print("Rerank Score:", result["rerank_score"])
    print("RRF Score:", result["rrf_score"])
    print("Chunk ID:", result["chunk_id"])
    print("Title:", result["title"])
    print("Content:")
    print(result["content"][:500])
    print()