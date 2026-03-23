import logging
import json
import traceback
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """
    Custom log formatter that outputs structured JSON instead of plain text.

    This format is natively understood by GCP Cloud Logging, Datadog, and most
    log aggregation platforms — they can parse and index each field individually
    rather than treating the log as a raw string.

    Example output:
    {
        "timestamp": "2026-03-22T14:00:00Z",
        "severity": "INFO",
        "message": "POST /api/bookings 201",
        "logger": "app.routes.bookings",
        "request_id": "abc-123"
    }
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            # GCP Cloud Logging uses 'timestamp' and 'severity' as reserved fields
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Include exception info if present
        if record.exc_info:
            log_entry["exception"] = traceback.format_exception(*record.exc_info)

        # Include any extra fields passed via logger.info("msg", extra={"key": "val"})
        for key, value in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "id", "levelname", "levelno", "lineno", "module",
                "msecs", "message", "msg", "name", "pathname", "process",
                "processName", "relativeCreated", "stack_info", "thread", "threadName",
            ):
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


def configure_logging(app):
    """
    Replace Flask's default log handlers with a JSON formatter.
    Called from create_app() so all app logs are structured from startup.
    """
    # Remove existing handlers to avoid duplicate log output
    app.logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    # Also configure the root logger so SQLAlchemy, Werkzeug etc. output JSON
    logging.root.handlers.clear()
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.WARNING)  # Only warnings and above for third-party libs
