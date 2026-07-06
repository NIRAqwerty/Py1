import logging
import os
import sys
import structlog
from src.config import settings

def setup_logging() -> None:
    logging_level = logging.DEBUG if settings.app.debug else logging.INFO

    def add_category(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        if "category" not in event_dict:
            event_dict["category"] = "GENERAL"
        return event_dict

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        add_category,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Decide renderer based on environment
    if settings.app.env == "development":
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging_level),
        cache_logger_on_first_use=True,
    )

# Type annotations helper
from typing import Any, Dict
setup_logging()

def get_logger(category: str = "GENERAL") -> Any:
    return structlog.get_logger().bind(category=category)
