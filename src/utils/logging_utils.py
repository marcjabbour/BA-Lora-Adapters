"""
Logging Configuration Utilities
"""

import logging
import sys
from typing import Optional


def setup_logging(verbose: bool = False, name: str = "pipeline") -> logging.Logger:
    """
    Configure logging with console output.

    Args:
        verbose: Enable debug logging if True
        name: Logger name

    Returns:
        Configured logger instance
    """
    level = logging.DEBUG if verbose else logging.INFO

    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
