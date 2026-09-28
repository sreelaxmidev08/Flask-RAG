from flask_rag_production.services.search import search_chunks


query = "how do I enable debug mode"

results = search_chunks(query, size=5)

for result in results:
    print("=" * 80)
    print(f"Score: {result['score']}")
    print(f"Title: {result['title']}")
    print(f"Source: {result['source_file']}")
    print()
    print(result["content"][:500])