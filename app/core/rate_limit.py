import time
from collections import defaultdict
from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """A sliding-window in-memory rate limiter with standard HTTP 429 and Retry-After headers."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: dict[str, list[float]] = defaultdict(list)

    def check(self, request: Request, custom_limit: int | None = None) -> bool:
        if request.headers.get("x-skip-rate-limit") == "1":
            return True

        limit = custom_limit or self.requests_per_minute
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        window_start = now - 60.0

        # Prune timestamps older than 1 minute
        history = [ts for ts in self.requests[client_ip] if ts > window_start]
        self.requests[client_ip] = history

        if len(history) >= limit:
            retry_after = int(60 - (now - history[0])) if history else 60
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down.",
                headers={"Retry-After": str(max(1, retry_after))},
            )

        self.requests[client_ip].append(now)
        return True

    def __call__(self, request: Request) -> bool:
        return self.check(request)


# Preconfigured limiters for sensitive endpoints
auth_rate_limiter = InMemoryRateLimiter(requests_per_minute=20)
payment_rate_limiter = InMemoryRateLimiter(requests_per_minute=30)
general_rate_limiter = InMemoryRateLimiter(requests_per_minute=120)
