import os
import httpx

class Reranker:
    def __init__(self):
        self.api_key = os.getenv("JINA_API_KEY")
        self.model = os.getenv(
            "JINA_RERANKER_MODEL",
            "jina-reranker-v3.5",
        )
        self.api_url = "https://api.jina.ai/v1/rerank"

        if not self.api_key:
            raise RuntimeError(
                "JINA_API_KEY is missing. Check your .env configuration."
            )

    def rerank(
        self,
        query: str,
        results: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """Rerank retrieved chunks using Jina's hosted API."""

        if not results or top_k <= 0:
            return []

        documents = [
            result["content"]
            for result in results
        ]

        payload = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "top_n": min(top_k, len(documents)),
        }

        try:
            response = httpx.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                "Jina reranking API returned HTTP "
                f"{exc.response.status_code}: {exc.response.text}"
            ) from exc

        except httpx.RequestError as exc:
            raise RuntimeError(
                f"Could not connect to the Jina reranking API: {exc}"
            ) from exc

        reranked = []

        for item in data.get("results", []):
            index = item["index"]

            if not isinstance(index, int) or not (
                0 <= index < len(results)
            ):
                continue

            result = results[index].copy()
            result["rerank_score"] = float(
                item["relevance_score"]
            )
            reranked.append(result)

        return reranked[:top_k]
