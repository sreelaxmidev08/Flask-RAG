import os
import time

import httpx
from dotenv import load_dotenv


load_dotenv()


class JinaEmbeddings:
    def __init__(self):
        self.api_key = os.getenv("JINA_API_KEY")
        self.model = "jina-embeddings-v3"
        self.base_url = "https://api.jina.ai/v1/embeddings"
        self.dimension = 1024

        if not self.api_key:
            raise ValueError("JINA_API_KEY is not set")

    def generate(
        self,
        texts: list[str],
        task: str = "retrieval.passage",
    ) -> list[list[float]]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model,
            "input": texts,
            "task": task,
        }

        max_attempts = 5

        for attempt in range(max_attempts):
            try:
                response = httpx.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=30,
                )

                # Jina rate limit
                if response.status_code == 429:
                    wait_time = 10 * (attempt + 1)

                    print(
                        f"Jina rate limit reached. "
                        f"Waiting {wait_time} seconds..."
                    )

                    time.sleep(wait_time)
                    continue

                # Temporary Jina server errors
                if response.status_code >= 500:
                    wait_time = 2 ** attempt

                    print(
                        f"Jina server error "
                        f"({response.status_code}). "
                        f"Retrying in {wait_time} seconds..."
                    )

                    time.sleep(wait_time)
                    continue

                response.raise_for_status()

                data = response.json()

                return [
                    item["embedding"]
                    for item in data["data"]
                ]

            except httpx.RequestError as exc:
                wait_time = 2 ** attempt

                print(
                    f"Jina network error: {exc}. "
                    f"Retrying in {wait_time} seconds..."
                )

                time.sleep(wait_time)

        raise RuntimeError(
            f"Jina embedding request failed "
            f"after {max_attempts} attempts."
        )