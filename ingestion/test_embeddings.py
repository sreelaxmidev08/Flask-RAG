from flask_rag_production.services.embeddings import JinaEmbeddings


embedding_model = JinaEmbeddings()

text = """
To enable debug mode, use the --debug option.
"""

embedding = embedding_model.generate([text])[0]

print("Embedding generated successfully.")
print("Dimension:", len(embedding))
print("First 5 values:", embedding[:5])