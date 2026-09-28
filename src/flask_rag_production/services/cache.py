import hashlib
import json
import os

import redis


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0",
)

try:
    CACHE_TTL = int(
        os.getenv(
            "REDIS_CACHE_TTL",
            "3600",
        )
    )
except ValueError:
    CACHE_TTL = 3600


client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
)


def normalize_query(query: str) -> str:
    """Normalize whitespace and case for exact cache matching."""

    return " ".join(
        query.strip().lower().split()
    )


def make_cache_key(
    endpoint: str,
    query: str,
    top_k: int,
) -> str:
    """
    Create a parameter-aware cache key.

    The cache key depends on:
    - endpoint
    - normalized query
    - top_k
    """

    cache_data = {
        "endpoint": endpoint,
        "query": normalize_query(query),
        "top_k": top_k,
    }

    serialized = json.dumps(
        cache_data,
        sort_keys=True,
    )

    query_hash = hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()

    return f"rag:{endpoint}:{query_hash}"


def get_cached_result(
    endpoint: str,
    query: str,
    top_k: int,
) -> dict | None:

    key = make_cache_key(
        endpoint,
        query,
        top_k,
    )

    try:
        cached = client.get(key)

    except redis.RedisError:
        print("Redis unavailable. Skipping cache.")
        return None

    if cached is None:
        print("CACHE MISS")
        return None

    print("CACHE HIT")

    return json.loads(cached)


def cache_result(
    endpoint: str,
    query: str,
    top_k: int,
    result: dict,
) -> None:

    key = make_cache_key(
        endpoint,
        query,
        top_k,
    )

    try:
        client.setex(
            key,
            CACHE_TTL,
            json.dumps(result),
        )

        print(
            f"CACHE SET "
            f"(TTL: {CACHE_TTL}s)"
        )

    except redis.RedisError:
        print(
            "Redis unavailable. "
            "Could not cache result."
        )