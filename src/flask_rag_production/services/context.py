def build_context(results: list[dict]) -> str:
    context_parts = []

    for i, result in enumerate(results, start=1):
        context_parts.append(
            f"[Source {i}]\n"
            f"Title: {result['title']}\n"
            f"File: {result['source_file']}\n"
            f"Content:\n{result['content']}"
        )

    return "\n\n".join(context_parts)