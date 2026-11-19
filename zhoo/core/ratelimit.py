"""محدد معدل بسيط (نافذة منزلقة) لمنع إغراق البوت بالأوامر أو الأزرار."""
from __future__ import annotations

import time
from collections import deque


class RateLimiter:
    def __init__(self, max_hits: int, per_seconds: float, max_keys: int = 20_000):
        self.max_hits = max_hits
        self.per = per_seconds
        self.max_keys = max_keys
        self._hits: dict[object, deque[float]] = {}
        self._warned: dict[object, float] = {}

    def hit(self, key: object) -> bool:
        """يرجع True إذا مسموح، False إذا تجاوز الحد."""
        t = time.monotonic()
        if len(self._hits) > self.max_keys:
            self._hits.clear()
            self._warned.clear()
        q = self._hits.setdefault(key, deque())
        while q and t - q[0] > self.per:
            q.popleft()
        if len(q) >= self.max_hits:
            return False
        q.append(t)
        return True

    def should_warn(self, key: object) -> bool:
        """تحذير مرة واحدة لكل نافذة، حتى البوت نفسه ما يصير سبام."""
        t = time.monotonic()
        last = self._warned.get(key, 0.0)
        if t - last > self.per:
            self._warned[key] = t
            return True
        return False
