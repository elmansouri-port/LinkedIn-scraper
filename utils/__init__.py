"""
Utilities package for LinkedIn Scraper.
"""

from .logger import (
    get_logger,
    init_logging,
    close_logger,
    SessionState,
)

# Backward compatibility aliases
ActionLogger = get_logger
init_logger = get_logger

__all__ = [
    "get_logger",
    "init_logging",
    "close_logger",
    "SessionState",
    "ActionLogger",
    "init_logger",
]
