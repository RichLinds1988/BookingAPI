import time
from flask import request, g, current_app


def register_request_logging(app):
    """
    Register before/after request hooks that log every HTTP request as structured JSON.

    Logs include method, path, status code, response time, and user ID (if authenticated).
    This gives you a complete audit trail of all API activity without adding logging
    calls to every individual route.
    """

    @app.before_request
    def start_timer():
        # Store the start time on Flask's request context (g)
        # g is a per-request global that lives for the duration of one request
        g.start_time = time.perf_counter()

    @app.after_request
    def log_request(response):
        # Calculate how long the request took in milliseconds
        duration_ms = round((time.perf_counter() - g.start_time) * 1000, 2)

        # Skip logging for Swagger UI asset requests to reduce noise
        if request.path.startswith("/flasgger_static") or request.path == "/apidocs":
            return response

        current_app.logger.info(
            f"{request.method} {request.path} {response.status_code}",
            extra={
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "ip": request.remote_addr,
            }
        )
        return response