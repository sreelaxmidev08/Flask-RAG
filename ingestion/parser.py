from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedDocument:
    title: str
    content: str
    source: str


def extract_title(content: str, fallback: str) -> str:
    """Extract the document title from Sphinx text output."""

    lines = content.splitlines()

    for index, line in enumerate(lines[:-1]):
        if line.strip() and set(lines[index + 1].strip()) <= {"*", "=" , "-", "~", "^"}:
            return line.strip()

    return fallback


def parse_file(file_path: Path) -> ParsedDocument:
    """Parse a single Sphinx-generated text file."""

    content = file_path.read_text(
        encoding="utf-8",
        errors="replace",
    ).strip()

    title = extract_title(
        content,
        fallback=file_path.stem.replace("-", " ").title(),
    )

    return ParsedDocument(
        title=title,
        content=content,
        source=str(file_path),
    )


def parse_directory(directory: Path) -> list[ParsedDocument]:
    """Parse all text files in a directory recursively."""

    documents = []

    for file_path in sorted(directory.rglob("*.txt")):
        # Ignore Sphinx's internal build directory.
        if ".doctrees" in file_path.parts:
            continue

        documents.append(parse_file(file_path))

    return documents


if __name__ == "__main__":
    build_dir = Path(
        "data/flask_docs/flask-3.1.3/build/text"
    )

    documents = parse_directory(build_dir)

    print(f"Documents parsed: {len(documents)}")

    for document in documents[:5]:
        print(f"\nTitle: {document.title}")
        print(f"Source: {document.source}")
        print(f"Characters: {len(document.content)}")