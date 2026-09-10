"""Small bounded caches for Streamlit message media."""

from __future__ import annotations

from collections.abc import MutableMapping


MediaValue = bytes | None


def media_cache_bytes(cache: MutableMapping[str, MediaValue]) -> int:
    """Return the number of binary payload bytes retained by a cache."""
    return sum(len(value) for value in cache.values() if isinstance(value, bytes))


def store_bounded_media(
    cache: MutableMapping[str, MediaValue],
    key: str,
    value: MediaValue,
    *,
    max_bytes: int,
    max_items: int,
) -> bool:
    """Store one payload and evict the oldest entries until limits are met."""
    if max_bytes < 1 or max_items < 1:
        raise ValueError("Media cache limits must be positive.")

    cache.pop(key, None)
    if isinstance(value, bytes) and len(value) > max_bytes:
        return False
    cache[key] = value

    while len(cache) > max_items or media_cache_bytes(cache) > max_bytes:
        oldest_key = next(iter(cache))
        del cache[oldest_key]
    return key in cache
