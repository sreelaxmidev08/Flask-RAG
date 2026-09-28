from opensearchpy import OpenSearch, helpers
from sqlalchemy import select
from sqlalchemy.orm import Session

from flask_rag_production.database import engine
from flask_rag_production.models.chunk import Chunk
from flask_rag_production.models.document import Document
from flask_rag_production.services.embeddings import JinaEmbeddings


OPENSEARCH_HOST = "localhost"
OPENSEARCH_PORT = 9200
INDEX_NAME = "flask_chunks"

BATCH_SIZE = 10


client = OpenSearch(
    hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}]
)

embedding_model = JinaEmbeddings()


def get_existing_chunk_ids():
    response = client.search(
        index=INDEX_NAME,
        body={
            "size": 1000,
            "_source": ["chunk_id"],
            "query": {"match_all": {}},
        },
    )

    return {
        hit["_source"]["chunk_id"]
        for hit in response["hits"]["hits"]
    }


def index_chunks():
    existing_ids = get_existing_chunk_ids()

    print(f"Already indexed: {len(existing_ids)} chunks.")

    with Session(engine) as session:
        statement = (
            select(Chunk, Document)
            .join(Document, Chunk.document_id == Document.id)
            .order_by(Chunk.id)
        )

        rows = session.execute(statement).all()

        remaining_rows = [
            (chunk, document)
            for chunk, document in rows
            if chunk.id not in existing_ids
        ]

        print(f"Remaining: {len(remaining_rows)} chunks.")

        for start in range(0, len(remaining_rows), BATCH_SIZE):
            batch = remaining_rows[start:start + BATCH_SIZE]

            texts = [chunk.content for chunk, document in batch]

            print(
                f"Generating embeddings for "
                f"{start + 1}-{start + len(batch)}..."
            )

            embeddings = embedding_model.generate(texts)

            actions = []

            for (chunk, document), embedding in zip(batch, embeddings):
                actions.append(
                    {
                        "_index": INDEX_NAME,
                        "_id": chunk.id,
                        "_source": {
                            "chunk_id": chunk.id,
                            "document_id": document.id,
                            "title": document.title,
                            "source_file": document.source_file,
                            "content": chunk.content,
                            "flask_version": document.version,
                            "n_tokens": chunk.n_tokens,
                            "embedding": embedding,
                        },
                    }
                )

            helpers.bulk(client, actions)

            print(
                f"Indexed {start + len(batch)}/{len(remaining_rows)} "
                f"remaining chunks."
            )


if __name__ == "__main__":
    index_chunks()