"""
Logging pipeline: formatter output, the dictConfig shape, and the listener's
lifetime. No database.
"""

import io
import json
import logging
import logging.handlers

from basic_api.logging_config import (
    QUEUE_HANDLER_NAME,
    ContextQueueHandler,
    JsonFormatter,
    build_config,
    configure_logging,
    request_id_var,
)


def _record(message="hello %s", args=("world",), exc_info=None):
    return logging.LogRecord(
        name="basic_api.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=args,
        exc_info=exc_info,
    )


def test_json_formatter_emits_one_object_with_the_expected_fields():
    record = _record()
    record.request_id = "req-1"
    entry = json.loads(JsonFormatter().format(record))
    assert entry["message"] == "hello world"
    assert entry["level"] == "INFO"
    assert entry["logger"] == "basic_api.test"
    assert entry["request_id"] == "req-1"
    # Aware UTC timestamp: ends with the zone offset.
    assert entry["timestamp"].endswith("+00:00")
    assert "exception" not in entry


def test_json_formatter_includes_the_exception_text():
    try:
        raise ValueError("boom")
    except ValueError as e:
        record = _record(exc_info=(type(e), e, e.__traceback__))
    entry = json.loads(JsonFormatter().format(record))
    assert "ValueError: boom" in entry["exception"]


def test_queue_handler_stamps_the_request_id_and_keeps_the_record():
    handler = ContextQueueHandler(queue=None)
    record = _record()
    token = request_id_var.set("req-2")
    try:
        prepared = handler.prepare(record)
    finally:
        request_id_var.reset(token)
    assert prepared is record
    assert record.request_id == "req-2"
    assert request_id_var.get() is None
    assert handler.prepare(_record()).request_id == ""


def test_build_config_routes_the_root_logger_through_the_queue():
    config = build_config("DEBUG", "json")
    assert config["disable_existing_loggers"] is False
    queue = config["handlers"][QUEUE_HANDLER_NAME]
    assert queue["handlers"] == ["console"]
    assert queue["respect_handler_level"] is True
    assert config["root"] == {"level": "DEBUG", "handlers": [QUEUE_HANDLER_NAME]}
    assert config["handlers"]["console"]["formatter"] == "json"


def test_listener_runs_for_the_block_and_delivers_lines_with_the_request_id():
    listener = configure_logging("INFO", "text")
    assert isinstance(listener, logging.handlers.QueueListener)
    captured = io.StringIO()
    # The console handler is the listener's only target; point it at a buffer.
    (console,) = listener.handlers
    assert isinstance(console, logging.StreamHandler)
    console.setStream(captured)
    assert listener._thread is None
    with listener:
        assert listener._thread is not None
        token = request_id_var.set("req-3")
        try:
            logging.getLogger("basic_api.test").info("inside the block")
        finally:
            request_id_var.reset(token)
    # Stopped and drained: the line reached the stream in the listener thread.
    assert listener._thread is None
    assert "basic_api.test [req-3] inside the block" in captured.getvalue()
    # Leave the test process with a configuration that writes nowhere exotic.
    logging.getLogger().handlers.clear()
