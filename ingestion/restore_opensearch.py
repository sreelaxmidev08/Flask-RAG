import json

from opensearchpy import OpenSearch, helpers


OPENSEARCH_HOST = "localhost"
OPENSEARCH_PORT = 9200
INDEX_NAME = "flask_chunks"

client = OpenSearch(
    hosts=[
        {
            "host": OPENSEARCH_HOST,
            "port": OPENSEARCH_PORT,
        }
    ]
)


with open(
    "data/opensearch_backup.json",
    "r",
    encoding="utf-8",
) as file:
    documents = json.load(file)


actions = []

for document in documents:
    actions.append(
        {
            "_index": INDEX_NAME,
            "_id": document["chunk_id"],
            "_source": document,
        }
    )


print(f"Restoring {len(actions)} documents...")

helpers.bulk(client, actions)

print("Restore complete.")