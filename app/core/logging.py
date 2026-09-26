import logging
import sys
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | [%(name)s] %(message)s"


def setup_logging():
    """Configure standard structured console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    # Silence noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware attaching unique X-Request-ID to every incoming HTTP request and response."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
