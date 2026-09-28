import json
from pathlib import Path


chunks_path = Path(
    "data/flask_docs/flask-3.1.3/chunks.jsonl"
)

chunks = []

with chunks_path.open(encoding="utf-8") as file:
    for line in file:
        chunk = json.loads(line)

        if chunk["source_file"] == "api.txt":
            chunks.append(chunk)


print(f"API chunks: {len(chunks)}")

print("\nFirst 20 chunks:")
for chunk in chunks[:20]:
    preview = chunk["text"][:100].replace("\n", " ")

    print(
        f"{chunk['chunk_index']}: "
        f"{chunk['n_tokens']} tokens | "
        f"{preview}"
    )


large_chunks = [
    chunk
    for chunk in chunks
    if chunk["n_tokens"] > 350
]

print(
    f"\nOversized API chunks: {len(large_chunks)}"
)

for chunk in large_chunks:
    preview = chunk["text"][:120].replace("\n", " ")

    print(
        f"{chunk['chunk_index']}: "
        f"{chunk['n_tokens']} tokens | "
        f"{preview}"
    )