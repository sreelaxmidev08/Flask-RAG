
import json
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from flask_rag_production.services.rag import (
    answer_question,
    stream_answer,
)


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/ask")
def ask(
    q: str = Query(
        ...,
        min_length=1,
        description="Question to ask",
    ),
    top_k: int = Query(
        5,
        ge=1,
        le=20,
        description="Number of sources",
    ),
):
    if not q.strip():
        raise HTTPException(
            status_code=422,
            detail="Question must not be empty or whitespace.",
        )

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
        min_length=1,
        description="Question to ask",
    ),
    top_k: int = Query(
        5,
        ge=1,
        le=20,
        description="Number of sources",
    ),
):
    if not q.strip():
        raise HTTPException(
            status_code=422,
            detail="Question must not be empty or whitespace.",
        )

    def event_generator():
        retrieved_sources = []
        retrieval_finished = False
        sources_sent = False

        def capture_sources(sources):
            nonlocal retrieval_finished
            retrieved_sources.extend(sources)
            retrieval_finished = True

        def sources_event():
            return (
                "data: "
                + json.dumps({
                    "type": "sources",
                    "sources": retrieved_sources,
                })
                + "\n\n"
            )

        # Send query metadata first.
        yield (
            "data: "
            + json.dumps({
                "type": "metadata",
                "query": q,
            })
            + "\n\n"
        )

        try:
            # Stream the answer in chunks.
            for chunk in stream_answer(
                q,
                top_k=top_k,
                on_sources=capture_sources,
            ):
                if retrieval_finished and not sources_sent:
                    yield sources_event()
                    sources_sent = True
                yield (
                    "data: "
                    + json.dumps({
                        "type": "chunk",
                        "content": chunk,
                    })
                    + "\n\n"
                )

            if retrieval_finished and not sources_sent:
                yield sources_event()

            # Send completion only if generation succeeds.
            yield (
                "data: "
                + json.dumps({
                    "type": "done",
                })
                + "\n\n"
            )

        except Exception:
            if retrieval_finished and not sources_sent:
                yield sources_event()

            # Keep technical details in server logs.
            logger.exception(
                "Error while streaming RAG response"
            )

            # Send a safe error event to the client.
            yield (
                "data: "
                + json.dumps({
                    "type": "error",
                    "message": (
                        "An error occurred while "
                        "generating the response."
                    ),
                })
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
