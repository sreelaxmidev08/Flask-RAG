import json

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from flask_rag_production.services.rag import (
    answer_question,
    stream_answer,
)


router = APIRouter()


@router.get("/ask")
def ask(
    q: str = Query(
        ...,
        description="Question to ask",
    ),
    top_k: int = Query(
        5,
        ge=1,
        le=20,
        description="Number of sources",
    ),
):

    result = answer_question(
        q,
        top_k=top_k,
    )

    return {
        "query": q,
        "answer": result["answer"],
        "sources": result["sources"],
    }


@router.get("/stream")
def stream(
    q: str = Query(
        ...,
        description="Question to ask",
    ),
    top_k: int = Query(
        5,
        ge=1,
        le=20,
        description="Number of sources",
    ),
):

    def event_generator():

        yield (
            "data: "
            + json.dumps(
                {
                    "type": "metadata",
                    "query": q,
                }
            )
            + "\n\n"
        )

        for chunk in stream_answer(
            q,
            top_k=top_k,
        ):

            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "chunk",
                        "content": chunk,
                    }
                )
                + "\n\n"
            )

        yield (
            "data: "
            + json.dumps(
                {
                    "type": "done",
                }
            )
            + "\n\n"
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )