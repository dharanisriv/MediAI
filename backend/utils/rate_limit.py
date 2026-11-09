"""
A tiny in-memory rate limiter so one visitor cannot use up your free Gemini quota.
(It resets when the server restarts - fine for a learning project.)
"""
import threading
import time
from collections import defaultdict, deque
from functools import wraps

from flask import request

from backend.config import Config
from backend.utils.errors import RateLimitError

_hits = defaultdict(deque)
_lock = threading.Lock()


def client_ip() -> str:
    # Behind hosting / ngrok / Colab the real IP arrives in X-Forwarded-For.
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def rate_limited(view):
    """Decorator: allow at most RATE_LIMIT_PER_MINUTE AI requests per visitor per minute."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        now = time.time()
        ip = client_ip()
        with _lock:
            q = _hits[ip]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= Config.RATE_LIMIT_PER_MINUTE:
                raise RateLimitError("You are sending requests too quickly. Please wait a minute and try again.")
            q.append(now)
            if len(_hits) > 5000:  # keep memory small
                for key in [k for k, v in _hits.items() if not v]:
                    del _hits[key]
        return view(*args, **kwargs)

    return wrapper
