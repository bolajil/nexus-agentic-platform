"""
NEXUS Platform — Structured Logging Configuration
Uses Python structlog for structured, JSON-formatted logging.
"""
from __future__ import annotations

import logging
import sys
from typing import Any

try:
    import structlog

    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False


def configure_logging(log_level: str = "INFO", json_logs: bool = False) -> None:
    """Configure application-wide logging."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    if STRUCTLOG_AVAILABLE:
        shared_processors: list[Any] = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
        ]

        if json_logs:
            shared_processors.append(structlog.processors.JSONRenderer())
        else:
            shared_processors.append(structlog.dev.ConsoleRenderer(colors=True))

        structlog.configure(
            processors=shared_processors,
            wrapper_class=structlog.make_filtering_bound_logger(level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        logging.basicConfig(
            level=level,
            stream=sys.stdout,
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )


def get_logger(name: str) -> Any:
    """Get a configured logger by name."""
    if STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    return logging.getLogger(name)
