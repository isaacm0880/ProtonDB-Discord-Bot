"""Small in-memory TTL cache with a size cap."""
from __future__ import annotations

import time
from typing import Any

MISSING: Any = object()  # returned by get() on a miss, so cached ``None`` is possible


class TTLCache:
    def __init__(self, ttl: int = 900, max_entries: int = 1000):
        self.ttl = ttl
        self.max_entries = max_entries
        self._data: dict[str, tuple[float, float, Any]] = {}

    def get(self, key: str) -> Any:
        item = self._data.get(key)
        if item is None:
            return MISSING
        created, ttl, value = item
        if time.monotonic() - created > ttl:
            self._data.pop(key, None)
            return MISSING
        return value

    def put(self, key: str, value: Any, ttl: float | None = None) -> None:
        effective = self.ttl if ttl is None else min(ttl, self.ttl) if self.ttl else 0
        if effective <= 0:  # CACHE_SECONDS=0 disables caching
            return
        if len(self._data) >= self.max_entries and key not in self._data:
            self._evict()
        self._data[key] = (time.monotonic(), effective, value)

    def _evict(self) -> None:
        now = time.monotonic()
        for k in [k for k, (c, t, _) in self._data.items() if now - c > t]:
            self._data.pop(k, None)
        while len(self._data) >= self.max_entries:
            oldest = min(self._data, key=lambda k: self._data[k][0])
            self._data.pop(oldest, None)

    def __len__(self) -> int:
        return len(self._data)
