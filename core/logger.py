# js_runtime\core\logger.py

"""Centralised logging facility (singleton)."""

import logging
import sys
from typing import Optional

from .config import Config


class Logger:
    """Singleton logger wrapping Python's :mod:`logging`.

    The logger respects the ``debug`` flag from :class:`Config`: debug
    messages are only emitted when ``Config().debug`` is ``True``.

    Use the predefined convenience methods for standard severity levels:
    :meth:`debug`, :meth:`info`, :meth:`warning`, :meth:`error`.
    """

    _instance: Optional["Logger"] = None
    _initialized: bool = False

    def __new__(cls) -> "Logger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Configure the underlying logger (only once)."""
        if self._initialized:
            return

        # Internal logger object
        self._logger = logging.getLogger("js_runtime")
        self._logger.setLevel(
            logging.DEBUG if Config.get_instance().debug else logging.INFO
        )

        # Console handler (stdout) with a simple format
        if not self._logger.handlers:  # avoid duplicate handlers
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "[%(levelname)-5s] %(message)s"
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

        self._initialized = True

    def debug(self, msg: str) -> None:
        """Log a debug message (visible only when ``debug`` is enabled)."""
        self._logger.debug(msg)

    def info(self, msg: str) -> None:
        """Log an informational message."""
        self._logger.info(msg)

    def warning(self, msg: str) -> None:
        """Log a warning message."""
        self._logger.warning(msg)

    def error(self, msg: str) -> None:
        """Log an error message."""
        self._logger.error(msg)