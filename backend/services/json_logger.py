"""
PROMEOS — JSON Log Formatter + setup_logging()
Structured JSON logs for backend (request_id, method, path, status, duration_ms).
"""
import json
import logging
import datetime


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON."""

    def format(self, record):
        log_entry = {
            "ts": datetime.datetime.now(datetime.UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Inject extra fields from middleware / app code
        for key in ("request_id", "method", "path", "status", "duration_ms"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging():
    """Configure structured JSON logging for the promeos namespace."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("promeos")
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    # Also capture uvicorn access logs with our formatter
    uv_access = logging.getLogger("uvicorn.access")
    uv_access.handlers = [handler]
