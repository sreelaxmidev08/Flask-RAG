from flask_rag_production.services.rag import answer_question


query = "How do I enable debug mode in Flask?"

result = answer_question(query, top_k=5)

print("\nANSWER\n")
print(result["answer"])

print("\nSOURCES\n")

for i, source in enumerate(result["sources"], start=1):
    print(f"--- Source {i} ---")
    print("Chunk ID:", source["chunk_id"])
    print("Title:", source["title"])
    print("File:", source["source_file"])
    print("Rerank Score:", source["rerank_score"])
    print()