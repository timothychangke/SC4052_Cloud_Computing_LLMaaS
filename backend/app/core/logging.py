"""
Structured logging config.  Every log line comes out as JSON in prod
and pretty-printed during local dev, which makes searching through
orchestrator step latencies much easier.
"""

import logging
import structlog


def setup_logging(json_output: bool = False):
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # tone down noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)