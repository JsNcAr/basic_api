"""
Logging: level, format and a queue so that writing a line never blocks the
event loop.

Modules log through `logging.getLogger(__name__)` and nothing else; this module
is the only place that configures logging, and the lifespan in main.py is the
only caller. uvicorn's own loggers (`uvicorn`, `uvicorn.access`) keep their
handlers and do not propagate, so they are untouched here.

The pipeline is the standard-library one from the logging cookbook: the root
logger has a single QueueHandler; a QueueListener thread takes records off the
queue and writes them to stderr. A blocking `write` to a slow terminal, a pipe
or a file therefore never stalls a request. `logging.config.dictConfig` builds
the handler and its listener (Python 3.12+); the listener is started and
stopped as a context manager (Python 3.14) around the application's lifetime.

Every line carries the request id set by request_id.py, in a `request_id`
field (JSON) or in brackets (text).
"""

import json
import logging
import logging.config
import logging.handlers
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from .config import LOG_FORMAT, LOG_LEVEL

# The id of the request being handled on this task, or None outside a request.
# Set by RequestIdMiddleware; read when a record enters the queue.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

QUEUE_HANDLER_NAME = "queue"
TEXT_FORMAT = "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"


class ContextQueueHandler(logging.handlers.QueueHandler):
    """
    QueueHandler that stamps the request id and queues the record as it is.

    The base `prepare` renders the message and drops `exc_info` so that the
    record can be pickled for another process. The listener here runs in a
    thread of the same process, so the record goes through untouched and the
    formatter on the other side still sees the exception. The request id is
    read here, on the task that logged, because the listener thread has no
    request context.
    """

    def prepare(self, record: logging.LogRecord) -> logging.LogRecord:
        record.request_id = request_id_var.get() or ""
        return record


class JsonFormatter(logging.Formatter):
    """
    One JSON object per line, for log collectors.

    Fields: `timestamp` (UTC, ISO 8601, milliseconds), `level`, `logger`,
    `message`, `request_id`, plus `exception` and `stack` when the record has
    them. Values that are not JSON types are rendered with `str`.
    """

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", ""),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            entry["stack"] = self.formatStack(record.stack_info)
        return json.dumps(entry, default=str)


def build_config(level: str, fmt: str) -> dict[str, Any]:
    """
    The dictConfig dictionary for the given level and format.

    Args:
        level: A logging level name, e.g. "INFO" (validated in config.py).
        fmt: "json" or "text" (validated in config.py).

    Returns:
        A dictionary for `logging.config.dictConfig`: a `console` handler on
        stderr behind a `queue` handler on the root logger. Existing loggers
        are left enabled, so uvicorn's keep working.
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {"()": JsonFormatter},
            "text": {"format": TEXT_FORMAT},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
                "formatter": fmt,
            },
            QUEUE_HANDLER_NAME: {
                # "class", not "()": only the class path builds the listener from
                # "handlers" (dictConfig's QueueHandler special case).
                "class": ContextQueueHandler,
                "handlers": ["console"],
                "respect_handler_level": True,
            },
        },
        "root": {"level": level, "handlers": [QUEUE_HANDLER_NAME]},
    }


def configure_logging(
    level: str = LOG_LEVEL, fmt: str = LOG_FORMAT
) -> logging.handlers.QueueListener:
    """
    Apply the configuration and return the listener to run it.

    The listener is not started here: use the returned object as a context
    manager (`with configure_logging(): ...`), which starts its thread on
    entry and stops it, draining the queue, on exit.

    Args:
        level: Logging level name; defaults to LOG_LEVEL.
        fmt: "json" or "text"; defaults to LOG_FORMAT.

    Returns:
        The QueueListener that dictConfig created for the queue handler.

    Example:
        with configure_logging():
            logging.getLogger(__name__).info("ready")
    """
    logging.config.dictConfig(build_config(level, fmt))
    handler = logging.getHandlerByName(QUEUE_HANDLER_NAME)
    if (
        not isinstance(handler, logging.handlers.QueueHandler)
        or handler.listener is None
    ):
        raise RuntimeError("logging configuration did not produce a queue listener")
    return handler.listener
