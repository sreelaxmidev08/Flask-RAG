from sentence_transformers import CrossEncoder


class Reranker:
    def __init__(self):
        self.model = None

    def _load_model(self):
        """Load the reranker model only when it is first needed."""

        if self.model is None:
            print("Loading reranker model: BAAI/bge-reranker-v2-m3")

            self.model = CrossEncoder(
                "BAAI/bge-reranker-v2-m3"
            )

        return self.model

    def rerank(
        self,
        query: str,
        results: list[dict],
        top_k: int = 5,
    ) -> list[dict]:

        model = self._load_model()

        pairs = [
            (query, result["content"])
            for result in results
        ]

        scores = model.predict(pairs)

        reranked = []

        for result, score in zip(results, scores):
            result = result.copy()
            result["rerank_score"] = float(score)
            reranked.append(result)

        reranked.sort(
            key=lambda result: result["rerank_score"],
            reverse=True,
        )

        return reranked[:top_k]