from typing import Literal

from fastapi import APIRouter, Query

from flask_rag_production.services.search import (
    hybrid_search_chunks,
    search_chunks,
    vector_search_chunks,
)


router = APIRouter()


@router.get("/search")
def search(
    q: str = Query(..., description="Search query"),
    size: int = Query(
        5,
        ge=1,
        le=20,
        description="Number of results",
    ),
    mode: Literal["bm25", "vector", "hybrid"] = Query(
        "bm25",
        description="Search mode",
    ),
):
    if mode == "bm25":
        results = search_chunks(q, size)

    elif mode == "vector":
        results = vector_search_chunks(q, size)

    else:
        results = hybrid_search_chunks(
            q,
            size=size,
            candidate_size=20,
        )

    return {
        "query": q,
        "mode": mode,
        "results": results,
    }