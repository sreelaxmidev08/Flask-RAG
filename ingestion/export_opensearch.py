from opensearchpy import OpenSearch

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


response = client.search(
    index=INDEX_NAME,
    body={
        "size": 1000,
        "query": {
            "match_all": {}
        }
    }
)

documents = [
    hit["_source"]
    for hit in response["hits"]["hits"]
]

print(f"Found {len(documents)} documents.")

import json

with open("data/opensearch_backup.json", "w", encoding="utf-8") as file:
    json.dump(documents, file)

print("Backup saved to data/opensearch_backup.json")