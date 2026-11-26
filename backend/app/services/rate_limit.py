import time
from collections import defaultdict, deque
from typing import Deque, Dict
from fastapi import HTTPException, status

# shortcut: per-process memory, so each Vercel instance counts on its own; move to Redis (INCR + EXPIRE) once it is wired.
_hits: Dict[str, Deque[float]] = defaultdict(deque)


def check(key: str, limit: int, window_seconds: int = 60) -> None:
    now = time.monotonic()
    hits = _hits[key]
    while hits and now - hits[0] > window_seconds:
        hits.popleft()
    if len(hits) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please wait a minute and try again.",
            headers={"Retry-After": str(window_seconds)},
        )
    hits.append(now)


def reset() -> None:
    _hits.clear()
