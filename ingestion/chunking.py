"""
Chunker for Sphinx text-builder output of Flask documentation.

Strategy:
- Default documents:
    paragraph-aware token packing
- api.txt:
    split by API entry first, then token-pack large entries
- changes.txt:
    split by version first, then token-pack large versions

Chunk target:
- 350 tokens
- 60-token overlap

The output contains metadata needed later for PostgreSQL and OpenSearch.
"""

import json
import re
from pathlib import Path

import tiktoken


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

FLASK_VERSION = "3.1.3"

CHUNK_SIZE = 350
OVERLAP = 60

ENC = tiktoken.get_encoding("cl100k_base")


# ---------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------

def n_tokens(text: str) -> int:
    """Return the number of tokens in a piece of text."""

    return len(ENC.encode(text))


# ---------------------------------------------------------------------
# Paragraph handling
# ---------------------------------------------------------------------

def split_paragraphs(text: str) -> list[str]:
    """
    Split Sphinx text output into paragraphs/blocks.

    Sphinx separates most logical blocks with blank lines.
    """

    paragraphs = re.split(r"\n\s*\n", text)

    return [
        paragraph.strip()
        for paragraph in paragraphs
        if paragraph.strip()
    ]


def get_overlap_paragraphs(
    paragraphs: list[str],
    overlap: int,
) -> tuple[list[str], int]:
    """
    Keep trailing paragraphs from the previous chunk until the
    overlap token budget is reached.
    """

    overlap_paragraphs = []
    overlap_tokens = 0

    for paragraph in reversed(paragraphs):
        paragraph_tokens = n_tokens(paragraph)

        if overlap_tokens + paragraph_tokens > overlap:
            break

        overlap_paragraphs.insert(0, paragraph)
        overlap_tokens += paragraph_tokens

    return overlap_paragraphs, overlap_tokens


def pack_paragraphs(
    paragraphs: list[str],
    max_tokens: int = CHUNK_SIZE,
    overlap: int = OVERLAP,
) -> list[str]:
    """
    Pack paragraphs into chunks without exceeding the token budget
    whenever possible.

    Splitting happens between paragraphs rather than arbitrarily
    cutting through text.
    """

    chunks: list[str] = []

    current: list[str] = []
    current_tokens = 0

    for paragraph in paragraphs:

        paragraph_tokens = n_tokens(paragraph)

        # -------------------------------------------------------------
        # A single paragraph is larger than the target.
        # -------------------------------------------------------------

        if paragraph_tokens > max_tokens:

            if current:
                chunks.append("\n\n".join(current))
                current = []
                current_tokens = 0

            # Keep the oversized paragraph intact for now.
            # We can add sentence/code-aware splitting later.
            chunks.append(paragraph)

            continue

        # -------------------------------------------------------------
        # Adding this paragraph would exceed the chunk size.
        # -------------------------------------------------------------

        if (
            current
            and current_tokens + paragraph_tokens > max_tokens
        ):
            chunks.append("\n\n".join(current))

            # Preserve a small amount of context from the
            # previous chunk.
            current, current_tokens = get_overlap_paragraphs(
                current,
                overlap,
            )

        # -------------------------------------------------------------
        # Add the paragraph to the current chunk.
        # -------------------------------------------------------------

        current.append(paragraph)
        current_tokens += paragraph_tokens

    # -------------------------------------------------------------
    # Add final chunk.
    # -------------------------------------------------------------

    if current:
        chunks.append("\n\n".join(current))

    return chunks


# ---------------------------------------------------------------------
# API documentation
# ---------------------------------------------------------------------

API_ENTRY_PATTERN = re.compile(
    r"^(?:class\s+)?flask\.[A-Za-z_][\w.]*",
    re.MULTILINE,
)


def split_api_entries(text: str) -> list[str]:
    """
    Split api.txt into individual Flask API entries.

    Examples of entry markers in the Sphinx output:

        class flask.Flask(...)
        class flask.Blueprint(...)
        flask.request
        flask.current_app
        flask.url_for(...)
    """

    matches = list(API_ENTRY_PATTERN.finditer(text))

    if not matches:
        return [text.strip()] if text.strip() else []

    entries: list[str] = []

    # Keep the introductory content before the first API entry.
    first_start = matches[0].start()

    introduction = text[:first_start].strip()

    if introduction:
        entries.append(introduction)

    # Each API entry runs until the beginning of the next entry.
    for index, match in enumerate(matches):

        start = match.start()

        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = len(text)

        entry = text[start:end].strip()

        if entry:
            entries.append(entry)

    return entries


def chunk_api_txt(text: str) -> list[str]:
    """
    Chunk API documentation.

    First split into individual API entries.

    If an entry fits within the token budget, keep it together.

    If it is too large, split it using paragraph-aware token packing.
    """

    entries = split_api_entries(text)

    chunks: list[str] = []

    for entry in entries:

        if n_tokens(entry) <= CHUNK_SIZE:
            chunks.append(entry)
            continue

        paragraphs = split_paragraphs(entry)

        chunks.extend(
            pack_paragraphs(
                paragraphs,
                max_tokens=CHUNK_SIZE,
                overlap=OVERLAP,
            )
        )

    return chunks


# ---------------------------------------------------------------------
# Changelog
# ---------------------------------------------------------------------

VERSION_PATTERN = re.compile(
    r"^Version\s+\d+(?:\.\d+)+(?:[^\n]*)$",
    re.MULTILINE,
)


def split_versions(text: str) -> list[str]:
    """
    Split changes.txt into version blocks.

    Example:

        Version 3.1.3
        =============

        Released ...

        * change

        Version 3.1.2
        =============
        ...
    """

    matches = list(VERSION_PATTERN.finditer(text))

    if not matches:
        return [text.strip()] if text.strip() else []

    blocks: list[str] = []

    # Content before the first version header.
    introduction = text[:matches[0].start()].strip()

    if introduction:
        blocks.append(introduction)

    for index, match in enumerate(matches):

        start = match.start()

        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = len(text)

        block = text[start:end].strip()

        if block:
            blocks.append(block)

    return blocks


def chunk_changes_txt(text: str) -> list[str]:
    """
    Chunk the changelog.

    First split by Flask version.

    Large version blocks are then packed using paragraph boundaries.
    """

    versions = split_versions(text)

    chunks: list[str] = []

    for version_block in versions:

        if n_tokens(version_block) <= CHUNK_SIZE:
            chunks.append(version_block)
            continue

        paragraphs = split_paragraphs(version_block)

        chunks.extend(
            pack_paragraphs(
                paragraphs,
                max_tokens=CHUNK_SIZE,
                overlap=OVERLAP,
            )
        )

    return chunks


# ---------------------------------------------------------------------
# Generic document chunking
# ---------------------------------------------------------------------

def chunk_generic_txt(text: str) -> list[str]:
    """
    Chunk a normal Flask documentation page.

    Paragraph boundaries are preferred before token limits.
    """

    paragraphs = split_paragraphs(text)

    return pack_paragraphs(
        paragraphs,
        max_tokens=CHUNK_SIZE,
        overlap=OVERLAP,
    )


# ---------------------------------------------------------------------
# File processing
# ---------------------------------------------------------------------

def chunk_file(
    path: Path,
    source_root: Path,
) -> list[dict]:
    """
    Chunk a single Sphinx-generated text file.
    """

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    ).strip()

    if not text:
        return []

    if path.name == "api.txt":
        chunks = chunk_api_txt(text)

    elif path.name == "changes.txt":
        chunks = chunk_changes_txt(text)

    else:
        chunks = chunk_generic_txt(text)

    relative_source = path.relative_to(source_root)

    return [
        {
            "source_file": relative_source.as_posix(),
            "chunk_index": index,
            "n_tokens": n_tokens(chunk),
            "flask_version": FLASK_VERSION,
            "text": chunk,
        }
        for index, chunk in enumerate(chunks)
    ]


# ---------------------------------------------------------------------
# Directory processing
# ---------------------------------------------------------------------

def chunk_directory(
    source_dir: Path,
) -> list[dict]:
    """
    Recursively chunk all Sphinx-generated text files.
    """

    all_chunks: list[dict] = []

    for path in sorted(source_dir.rglob("*.txt")):

        # Sphinx's internal build files are not documentation.
        if ".doctrees" in path.parts:
            continue

        file_chunks = chunk_file(
            path=path,
            source_root=source_dir,
        )

        all_chunks.extend(file_chunks)

    return all_chunks


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

if __name__ == "__main__":

    import sys

    source_dir = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(
            "data/flask_docs/flask-3.1.3/build/text"
        )
    )

    output_path = (
        Path(sys.argv[2])
        if len(sys.argv) > 2
        else Path(
            "data/flask_docs/flask-3.1.3/chunks.jsonl"
        )
    )

    if not source_dir.exists():
        raise FileNotFoundError(
            f"Source directory not found: {source_dir}"
        )

    chunks = chunk_directory(source_dir)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as output_file:

        for chunk in chunks:
            output_file.write(
                json.dumps(
                    chunk,
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(f"Documents processed: {len(list(source_dir.rglob('*.txt')))}")
    print(f"Chunks created: {len(chunks)}")
    print(f"Output: {output_path}")