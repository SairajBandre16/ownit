"""Shared FastAPI dependencies: rate limiting, response cache, input limits."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any, TypeVar

import orjson
from cachetools import LRUCache
from fastapi import HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])

_cache: LRUCache[str, Any] = LRUCache(maxsize=settings.cache_size)
T = TypeVar("T")


def cache_key(namespace: str, payload: Any) -> str:
    raw = orjson.dumps(payload, option=orjson.OPT_SORT_KEYS | orjson.OPT_SERIALIZE_NUMPY)
    return namespace + ":" + hashlib.sha256(raw).hexdigest()


def cached(namespace: str, payload: Any, compute: Callable[[], T]) -> T:
    """LRU cache keyed on sha256(text + params). Results are kept in memory only."""
    key = cache_key(namespace, payload)
    if key in _cache:
        return _cache[key]  # type: ignore[no-any-return]
    value = compute()
    _cache[key] = value
    return value


def enforce_word_limit(text: str) -> None:
    words = len(text.split())
    if words > settings.max_words:
        raise HTTPException(
            status_code=413,
            detail=f"Text has {words} words; the limit is {settings.max_words} per request.",
        )
