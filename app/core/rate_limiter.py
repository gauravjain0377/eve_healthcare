import time
from collections import defaultdict
from fastapi import Request, HTTPException, status
from app.core.config import settings

# In-memory IP tracking: ip -> list of timestamps
_request_records: dict[str, list[float]] = defaultdict(list)


def rate_limit(max_requests: int = 60, window_seconds: int = 60):
    """
    FastAPI dependency for sliding-window rate limiting per client IP.
    """
    async def dependency(request: Request):
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        cutoff = now - window_seconds
        
        # Filter out timestamps older than the window
        timestamps = [t for t in _request_records[client_ip] if t > cutoff]
        
        if len(timestamps) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds}s.",
                headers={"Retry-After": str(window_seconds)}
            )
            
        timestamps.append(now)
        _request_records[client_ip] = timestamps

    return dependency
