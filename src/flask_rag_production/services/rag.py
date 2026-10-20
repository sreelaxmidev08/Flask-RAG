import datetime

import time

from dotenv import load_dotenv

from langfuse import get_client

from flask_rag_production.services.cache import (

    cache_result,

    get_cached_result,

)

from flask_rag_production.services.context import build_context

from flask_rag_production.services.llm import GeminiLLM

from flask_rag_production.services.search import hybrid_search_chunks

# Load environment variables from .env when running locally.

load_dotenv()

# Langfuse client

langfuse = get_client()

# LLM client

llm = GeminiLLM()

def create_prompt(

    query: str,

    context: str,

) -> str:

    """Create the RAG prompt."""

    return f"""Answer the user's question using ONLY the provided Flask documentation context.

Instructions:

- Use the context as the only source of factual information.

- Identify the parts of the context that directly answer the question.

- If any provided source contains information about the topic asked about, you MUST answer using that information.

- Do not say that the information was not found merely because the exact wording of the question does not appear in the context.

- For questions asking "how", "why", or "what is", combine the relevant statements from the provided sources into a direct answer.

- Prefer the most direct answer to the question over related or tangential information.

- Do not include examples from the context merely because they are nearby or related to the topic.

- If the documentation gives a direct command for the requested task, use that command as the primary answer.

- Ignore context that is unrelated to the question.

- If the context contains a direct answer, answer the question clearly and concisely.

- When the context provides a command or code example that directly answers the question, reproduce it exactly. Do not reorder, modify, or reconstruct commands or code.

- Do not invent information that is not supported by the context.

- Do not combine separate examples into a new command or example unless the context explicitly supports that combination.

- If multiple sources provide relevant information, combine them only when they are consistent and necessary to answer the question.

- Cite the source number for factual claims using [1], [2], etc.

- Only cite sources that actually support the claim.

- If a statement is supported by multiple sources, you may cite multiple sources, such as [1][2].

- Do not create or guess source numbers.

- Only say "I couldn't find that information in the Flask documentation." when NONE of the provided sources contain information relevant to the question.

Question:

{query}

Context:

{context}

Answer:

"""

def answer_question(

    query: str,

    top_k: int = 5,

) -> dict:

    """

    Run the complete RAG pipeline for /ask.

    Creates one root Langfuse observation with nested

    observations for retrieval, context building,

    prompt creation, and LLM generation.

    """

    with langfuse.start_as_current_observation(

        as_type="span",

        name="rag-request",

        input={

            "query": query,

            "top_k": top_k,

        },

    ) as root_span:

        # --------------------------------------------------

        # 0. CHECK CACHE

        # --------------------------------------------------

        cached_result = get_cached_result(

            endpoint="ask",

            query=query,

            top_k=top_k,

        )

        if cached_result is not None:

            root_span.update(

                output=cached_result,

                metadata={

                    "cache_hit": True,

                },

            )

            return cached_result

        # Start total timer

        total_start = time.perf_counter()

        # --------------------------------------------------

        # 1. RETRIEVAL

        # --------------------------------------------------

        retrieval_start = time.perf_counter()

        with langfuse.start_as_current_observation(

            as_type="retriever",

            name="hybrid-retrieval",

            input={

                "query": query,

                "top_k": top_k,

                "candidate_size": 10,

            },

        ) as retrieval_span:

            results = hybrid_search_chunks(
                query,
                size=top_k,
                candidate_size=10,
                trace_parent=retrieval_span,
            )

            retrieval_span.update(

                output={

                    "source_count": len(results),

                    "chunk_ids": [

                        result["chunk_id"]

                        for result in results

                    ],

                },

            )

        retrieval_time = (

            time.perf_counter()

            - retrieval_start

        )

        # --------------------------------------------------

        # 2. CONTEXT BUILDING

        # --------------------------------------------------

        context_start = time.perf_counter()

        with langfuse.start_as_current_observation(

            as_type="span",

            name="context-building",

            input={

                "source_count": len(results),

            },

        ) as context_span:

            context = build_context(results)

            context_span.update(

                output={

                    "context_size_chars": len(context),

                },

            )

        context_time = (

            time.perf_counter()

            - context_start

        )

        # --------------------------------------------------

        # 3. PROMPT CREATION

        # --------------------------------------------------

        prompt_start = time.perf_counter()

        with langfuse.start_as_current_observation(

            as_type="span",

            name="prompt-creation",

            input={

                "query": query,

                "context_size_chars": len(context),

            },

        ) as prompt_span:

            prompt = create_prompt(

                query,

                context,

            )

            prompt_size_bytes = len(

                prompt.encode("utf-8")

            )

            prompt_size_kb = (

                prompt_size_bytes / 1024

            )

            prompt_span.update(

                output={

                    "prompt_size_bytes": prompt_size_bytes,

                    "prompt_size_kb": prompt_size_kb,

                },

            )

        prompt_time = (

            time.perf_counter()

            - prompt_start

        )

        # --------------------------------------------------

        # 4. LLM GENERATION

        # --------------------------------------------------

        llm_start = time.perf_counter()

        with langfuse.start_as_current_observation(

            as_type="generation",

            name="llm-generation",

            model=llm.model,

            input={

                "prompt": prompt,

            },

        ) as generation_span:

            answer = llm.generate(prompt)

            generation_span.update(

                output=answer,

            )

        llm_time = (

            time.perf_counter()

            - llm_start

        )

        # --------------------------------------------------

        # 5. POST-PROCESSING

        # --------------------------------------------------

        postprocessing_start = (

            time.perf_counter()

        )

        result = {

            "answer": answer,

            "sources": results,

        }

        postprocessing_time = (

            time.perf_counter()

            - postprocessing_start

        )

        # --------------------------------------------------

        # 6. SAVE TO CACHE

        # --------------------------------------------------

        cache_result(

            endpoint="ask",

            query=query,

            top_k=top_k,

            result=result,

        )

        # --------------------------------------------------

        # 7. TOTAL TIME

        # --------------------------------------------------

        total_time = (

            time.perf_counter()

            - total_start

        )

        # --------------------------------------------------

        # PERFORMANCE LOG

        # --------------------------------------------------

        print("\n===== RAG PERFORMANCE =====")

        print(

            f"Retrieval time:       "

            f"{retrieval_time:.2f}s"

        )

        print(

            f"Context build time:   "

            f"{context_time:.2f}s"

        )

        print(

            f"Prompt creation time: "

            f"{prompt_time:.4f}s"

        )

        print(

            f"Prompt size:          "

            f"{prompt_size_kb:.2f} KB"

        )

        print(

            f"LLM generation time:  "

            f"{llm_time:.2f}s"

        )

        print(

            f"Post-processing time: "

            f"{postprocessing_time:.4f}s"

        )

        print(

            f"Total response time:  "

            f"{total_time:.2f}s"

        )

        print("===========================\n")

        # --------------------------------------------------

        # 8. UPDATE LANGFUSE ROOT OBSERVATION

        # --------------------------------------------------

        root_span.update(

            output=result,

            metadata={

                "cache_hit": False,

                "retrieval_time": retrieval_time,

                "context_time": context_time,

                "prompt_time": prompt_time,

                "prompt_size_kb": prompt_size_kb,

                "llm_time": llm_time,

                "postprocessing_time": postprocessing_time,

                "total_time": total_time,

                "source_count": len(results),

            },

        )

        return result

def stream_text(

    text: str,

    chunk_size: int = 80,

):

    """

    Split a cached answer into chunks so that

    cached responses can still be streamed.

    """

    for start in range(

        0,

        len(text),

        chunk_size,

    ):

        yield text[

            start:start + chunk_size

        ]

def stream_answer(
    query: str,
    top_k: int = 5,
    on_sources=None,
):
    """Run the streaming RAG pipeline with safe Langfuse tracing."""

    total_start = time.perf_counter()

    # Do not keep a current-observation context manager open across yield.
    root_span = langfuse.start_observation(
        as_type="span",
        name="rag-stream-request",
        input={"query": query, "top_k": top_k},
    )

    try:
        # 0. CHECK CACHE
        cached_result = get_cached_result(
            endpoint="stream",
            query=query,
            top_k=top_k,
        )

        if cached_result is not None:
            print("Streaming cached answer.")
            if on_sources is not None:
                on_sources(cached_result.get("sources", []))
            root_span.update(
                output=cached_result,
                metadata={
                    "cache_hit": True,
                    "total_time": time.perf_counter() - total_start,
                },
            )

            for chunk in stream_text(cached_result["answer"]):
                yield chunk
            return

        # 1. RETRIEVAL
        retrieval_start = time.perf_counter()
        retrieval_span = root_span.start_observation(
            as_type="retriever",
            name="hybrid-retrieval",
            input={
                "query": query,
                "top_k": top_k,
                "candidate_size": 10,
            },
        )

        try:
            results = hybrid_search_chunks(
                query,
                size=top_k,
                candidate_size=10,
                trace_parent=retrieval_span,
            )
            retrieval_span.update(
                output={
                    "source_count": len(results),
                    "chunk_ids": [result["chunk_id"] for result in results],
                },
            )
        finally:
            retrieval_span.end()

        retrieval_time = time.perf_counter() - retrieval_start

        if on_sources is not None:
            on_sources(results)

        # 2. CONTEXT BUILDING
        context_start = time.perf_counter()

        context_span = root_span.start_observation(
            as_type="span",
            name="context-building",
            input={"source_count": len(results)},
        )

        try:
            context = build_context(results)
            context_span.update(
                output={"context_size_chars": len(context)},
            )
        finally:
            context_span.end()

        context_time = time.perf_counter() - context_start

        # 3. PROMPT CREATION
        prompt_start = time.perf_counter()

        prompt_span = root_span.start_observation(
            as_type="span",
            name="prompt-creation",
            input={
                "query": query,
                "context_size_chars": len(context),
            },
        )

        try:
            prompt = create_prompt(query, context)
            prompt_size_bytes = len(prompt.encode("utf-8"))
            prompt_size_kb = prompt_size_bytes / 1024

            prompt_span.update(
                output={
                    "prompt_size_bytes": prompt_size_bytes,
                    "prompt_size_kb": prompt_size_kb,
                },
            )
        finally:
            prompt_span.end()

        prompt_time = time.perf_counter() - prompt_start

        # 4. STREAM LLM RESPONSE
        llm_start = time.perf_counter()
        first_chunk_time = None
        answer_parts = []

        generation_span = root_span.start_observation(
            as_type="generation",
            name="llm-generation",
            model=llm.model,
            input={"prompt": prompt},
        )

        try:
            for chunk in llm.generate_stream(prompt):
                if first_chunk_time is None:
                    first_chunk_time = time.perf_counter() - total_start
                    generation_span.update(
                        completion_start_time=datetime.datetime.now(),
                    )

                    print("\n===== STREAMING PERFORMANCE =====")
                    print(f"Retrieval time:       {retrieval_time:.2f}s")
                    print(f"Context build time:   {context_time:.2f}s")
                    print(f"Prompt creation time: {prompt_time:.4f}s")
                    print(f"Prompt size:          {prompt_size_kb:.2f} KB")
                    print(f"Time to first chunk:  {first_chunk_time:.2f}s")
                    print("=================================\n")

                answer_parts.append(chunk)
                # No Langfuse current-observation context manager spans this yield.
                yield chunk

            complete_answer = "".join(answer_parts)
            generation_span.update(output=complete_answer)
        finally:
            generation_span.end()

        llm_time = time.perf_counter() - llm_start

        # 5. CREATE RESULT
        result = {
            "answer": complete_answer,
            "sources": results,
        }

        # 6. SAVE TO CACHE
        cache_result(
            endpoint="stream",
            query=query,
            top_k=top_k,
            result=result,
        )

        # 7. POST-PROCESSING
        postprocessing_start = time.perf_counter()
        postprocessing_time = time.perf_counter() - postprocessing_start

        # 8. TOTAL TIME
        total_time = time.perf_counter() - total_start

        print("\n===== STREAM COMPLETE =====")
        print(f"LLM streaming time:   {llm_time:.2f}s")
        print(f"Post-processing time: {postprocessing_time:.4f}s")
        print(f"Total response time:  {total_time:.2f}s")
        print("===========================\n")

        # 9. UPDATE ROOT OBSERVATION
        root_span.update(
            output=result,
            metadata={
                "cache_hit": False,
                "retrieval_time": retrieval_time,
                "context_time": context_time,
                "prompt_time": prompt_time,
                "prompt_size_kb": prompt_size_kb,
                "time_to_first_chunk": first_chunk_time,
                "llm_time": llm_time,
                "postprocessing_time": postprocessing_time,
                "total_time": total_time,
                "source_count": len(results),
            },
        )
    finally:
        root_span.end()



