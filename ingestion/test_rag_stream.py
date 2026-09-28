from flask_rag_production.services.search import hybrid_search_chunks

query = "How do I enable debug mode in Flask?"

results = hybrid_search_chunks(
    query,
    size=5,
    candidate_size=20,
)

for i, result in enumerate(results, start=1):
    print(f"\n===== SOURCE {i} =====")
    print("chunk_id:", result["chunk_id"])
    print("title:", result["title"])
    print("score:", result.get("rerank_score"))
    print(result["content"])