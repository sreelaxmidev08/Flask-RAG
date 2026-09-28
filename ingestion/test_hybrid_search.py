from flask_rag_production.services.search import hybrid_search_chunks

query = "How do I enable debug mode in Flask?"

results = hybrid_search_chunks(
    query,
    size=5,
    candidate_size=20,
)

print("\nHYBRID SEARCH RESULTS\n")

for i, result in enumerate(results, start=1):
    print(f"--- Result {i} ---")
    print("RRF Score:", result["rrf_score"])
    print("Rerank Score:", result["rerank_score"])
    print("Chunk ID:", result["chunk_id"])
    print("Title:", result["title"])
    print("Source:", result["source_file"])
    print("Content:")
    print(result["content"][:500])
    print()