import json
import os

import httpx


class OllamaLLM:
    def __init__(
        self,
        base_url: str | None = None,
        model: str = "llama3.2:3b",
    ):
        self.base_url = base_url or os.getenv(
            "OLLAMA_BASE_URL",
            "http://localhost:11434",
        )
        self.model = model

    def generate(self, prompt: str) -> str:
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=300,
        )

        response.raise_for_status()

        data = response.json()

        return data["response"]

    def generate_stream(self, prompt: str):
        with httpx.stream(
            "POST",
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": True,
            },
            timeout=300,
        ) as response:
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    data = json.loads(line)

                    if "response" in data:
                        yield data["response"]

                    if data.get("done"):
                        break