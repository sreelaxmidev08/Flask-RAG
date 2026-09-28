FROM python:3.13-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync

CMD ["uv", "run", "uvicorn", "flask_rag_production.main:app", "--host", "0.0.0.0", "--port", "8000"]