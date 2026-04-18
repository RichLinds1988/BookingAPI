import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.requests")

_SKIP_PATHS = {"/openapi.json", "/redoc"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        if (
            request.method != "OPTIONS"
            and not request.url.path.startswith("/docs")
            and request.url.path not in _SKIP_PATHS
        ):
            logger.info(
                f"{request.method} {request.url.path} {response.status_code}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "ip": request.client.host if request.client else None,
                },
            )

        return response
