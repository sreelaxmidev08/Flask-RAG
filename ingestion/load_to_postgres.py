import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from flask_rag_production.database import engine
from flask_rag_production.models.chunk import Chunk
from flask_rag_production.models.document import Document


CHUNKS_FILE = Path(
    "data/flask_docs/flask-3.1.3/chunks.jsonl"
)

TEXT_DIR = Path(
    "data/flask_docs/flask-3.1.3/build/text"
)

FLASK_VERSION = "3.1.3"
SOURCE = "Flask"


def get_document_title(source_file: str) -> str:
    """Get the title from the Sphinx-generated text file."""

    file_path = TEXT_DIR / source_file

    with file_path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if line:
                return line

    raise ValueError(
        f"Could not find title for {source_file}"
    )


def load_chunks() -> None:
    with CHUNKS_FILE.open(
        encoding="utf-8"
    ) as file:
        chunks = [
            json.loads(line)
            for line in file
        ]

    print(f"Loaded {len(chunks)} chunks from JSONL.")

    source_files = sorted(
        {
            chunk["source_file"]
            for chunk in chunks
        }
    )

    print(
        f"Found {len(source_files)} documents."
    )

    with Session(engine) as session:

        with session.begin():

            document_map = {}

            for source_file in source_files:

                title = get_document_title(
                    source_file
                )

                existing_document = session.scalar(
                    select(Document).where(
                        Document.source_file
                        == source_file,
                        Document.version
                        == FLASK_VERSION,
                    )
                )

                if existing_document:
                    document = existing_document

                    print(
                        f"Document already exists: "
                        f"{source_file}"
                    )

                else:
                    document = Document(
                        source=SOURCE,
                        version=FLASK_VERSION,
                        title=title,
                        source_file=source_file,
                    )

                    session.add(document)
                    session.flush()

                    print(
                        f"Created document: "
                        f"{source_file}"
                    )

                document_map[source_file] = document.id

            for chunk_data in chunks:

                document_id = document_map[
                    chunk_data["source_file"]
                ]

                existing_chunk = session.scalar(
                    select(Chunk).where(
                        Chunk.document_id
                        == document_id,
                        Chunk.chunk_index
                        == chunk_data["chunk_index"],
                    )
                )

                if existing_chunk:
                    continue

                chunk = Chunk(
                    document_id=document_id,
                    chunk_index=chunk_data[
                        "chunk_index"
                    ],
                    content=chunk_data["text"],
                    n_tokens=chunk_data["n_tokens"],
                )

                session.add(chunk)

    print("PostgreSQL ingestion completed.")


if __name__ == "__main__":
    load_chunks()