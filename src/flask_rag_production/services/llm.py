
import os

from groq import Groq


class GroqLLM:
    def __init__(self, model: str | None = None):
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is missing. Check your .env configuration."
            )

        self.model = model or os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-20b",
        )

        self.client = Groq(api_key=api_key)

    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_completion_tokens=1024,
        )

        content = response.choices[0].message.content

        if not content:
            raise RuntimeError("Groq returned an empty response.")

        return content

    def generate_stream(self, prompt: str):
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_completion_tokens=1024,
            stream=True,
        )

        for chunk in stream:
            if not chunk.choices:
                continue

            content = chunk.choices[0].delta.content

            if content:
                yield content


# Compatibility with existing imports in the RAG pipeline.
GeminiLLM = GroqLLM
OllamaLLM = GroqLLM
