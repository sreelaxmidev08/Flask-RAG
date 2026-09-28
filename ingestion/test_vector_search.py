from flask_rag_production.services.search import vector_search_chunks


query = "How do I enable debug mode in Flask?"

results = vector_search_chunks(query, size=5)

print("\nVECTOR SEARCH RESULTS\n")

for i, result in enumerate(results, start=1):
    print(f"--- Result {i} ---")
    print("Score:", result["score"])
    print("Chunk ID:", result["chunk_id"])
    print("Title:", result["title"])
    print("Source:", result["source_file"])
    print("Content:")
    print(result["content"][:500])
    print()