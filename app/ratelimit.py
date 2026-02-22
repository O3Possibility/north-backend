from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException

from app.config import settings

@dataclass
class RateState:
    # timestamps (epoch seconds) of recent requests for per-minute limiting
    recent: deque
    # day key (YYYY-MM-DD) in UTC for daily counters
    day: str
    count: int

# In-memory store (IP -> RateState). Resets on restart.
_STATE: dict[str, RateState] = {}

def _utc_day_key(now: float | None = None) -> str:
    if now is None:
        now = time.time()
    return datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%d")

def check_rate_limit(client_ip: str, *, byok: bool) -> None:
    """Basic per-IP rate limiting.

    - RATE_PER_MIN: rolling 60s window per IP
    - DAILY_LIMIT_PER_IP / DAILY_LIMIT_BYOK: reset at UTC midnight
    """
    if not client_ip:
        # If we can't identify the client, fail closed with a conservative limit bucket.
        client_ip = "unknown"

    now = time.time()
    day = _utc_day_key(now)

    st = _STATE.get(client_ip)
    if st is None or st.day != day:
        st = RateState(recent=deque(), day=day, count=0)
        _STATE[client_ip] = st

    # Per-minute: drop old entries
    window_start = now - 60.0
    while st.recent and st.recent[0] < window_start:
        st.recent.popleft()

    if len(st.recent) >= settings.RATE_PER_MIN:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "message": "Too many requests. Please slow down and try again.",
                "limit": {"per_min": settings.RATE_PER_MIN},
            },
        )

    # Daily caps
    daily_cap = settings.DAILY_LIMIT_BYOK if byok else settings.DAILY_LIMIT_PER_IP
    if st.count >= daily_cap:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_limit_reached",
                "message": "Daily limit reached for this IP. Try again tomorrow or use BYOK (your own API key).",
                "limit": {"per_day": daily_cap, "utc_day": st.day},
            },
        )

    # Consume
    st.recent.append(now)
    st.count += 1
