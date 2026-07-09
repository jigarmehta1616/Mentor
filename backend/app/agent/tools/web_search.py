"""web_search tool: fetch current resources for a concept, cached per concept
with a TTL so repeated teaching doesn't re-search.

Offline/mock mode returns deterministic resource stubs so citations work with no
network and no keys. A real search backend can be slotted in behind the same
interface without changing callers.
"""

from __future__ import annotations

from urllib.parse import quote_plus

from app.config import get_settings
from app.lib.cache import TTLCache
from app.lib.logger import get_logger
from app.llm.provider import Resource

logger = get_logger()

# Bounded LRU + TTL cache keyed by concept id. Space is bounded (maxsize) and
# entries expire, so this never grows without limit.
_cache: TTLCache[str, list[Resource]] = TTLCache(
    ttl_seconds=get_settings().resource_cache_ttl_seconds, maxsize=1024
)


def _generate(concept_id: str, concept_name: str) -> list[Resource]:
    """Deterministic offline resources. O(1)."""
    q = quote_plus(concept_name)
    return [
        Resource(
            title=f"{concept_name} — overview",
            url=f"https://en.wikipedia.org/wiki/Special:Search?search={q}",
            snippet=f"Reference overview of {concept_name}.",
        ),
        Resource(
            title=f"{concept_name} — tutorial",
            url=f"https://www.google.com/search?q={q}+tutorial",
            snippet=f"Hands-on tutorial for {concept_name}.",
        ),
    ]


def search(concept_id: str, concept_name: str) -> list[Resource]:
    """Return cached resources for a concept, searching only on a cache miss.

    Amortized O(1): a cache hit is a single lookup; only misses do work.
    """
    hit = _cache.get(concept_id)
    if hit is not None:
        return hit
    resources = _generate(concept_id, concept_name)
    _cache.set(concept_id, resources)
    logger.info("web_search miss for %s (cached %d resources)", concept_id, len(resources))
    return resources


def clear_cache() -> None:
    _cache.clear()
