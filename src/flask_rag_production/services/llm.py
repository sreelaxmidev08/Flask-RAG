import os

from google import genai


class GeminiLLM:
    def __init__(self, model: str | None = None):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is missing. Check your .env configuration."
            )

        self.model = model or os.getenv(
            "GEMINI_MODEL",
            "gemini-3.8-flash",
        )

        self.client = genai.Client(api_key=api_key)

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        if response.text is None:
            raise RuntimeError("Gemini returned an empty response.")

        return response.text

    def generate_stream(self, prompt: str):
        for chunk in self.client.models.generate_content_stream(
            model=self.model,
            contents=prompt,
        ):
            if chunk.text:
                yield chunk.text


# Backward compatibility for code that imports OllamaLLM.
OllamaLLM = GeminiLLM