"""Structured JSON logging configuration."""
import sys
import logging
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["service"] = getattr(record, "service", "unknown")
        log_record["request_id"] = getattr(record, "request_id", None)


def configure_logging(service_name: str, level: str = "INFO"):
    log_handler = logging.StreamHandler(sys.stdout)
    formatter = CustomJsonFormatter(
        "%(timestamp)s %(level)s %(name)s %(message)s %(service)s %(request_id)s"
    )
    log_handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.handlers = []
    logger.addHandler(log_handler)
    logger.setLevel(getattr(logging, level.upper()))

    # Inject service name into LogRecord factory
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.service = service_name
        record.request_id = None
        return record

    logging.setLogRecordFactory(record_factory)
    return logger
