# js_runtime\core\config.py

"""Global runtime configuration (singleton)."""

import os
from typing import Optional


class Config:
    """Singleton that holds all runtime settings.

    Settings are read from environment variables (with fallback defaults)
    and can be accessed through the unique instance returned by
    :meth:`get_instance` or by calling ``Config()`` directly.

    Attributes:
        debug: Whether debug mode is enabled.
        max_call_stack: Maximum size of the interpreter call stack.
    """

    _instance: Optional["Config"] = None
    _initialized: bool = False

    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialise the instance (only once)."""
        if self._initialized:
            return

        # -- debug flag --
        raw_debug = os.environ.get("JS_RUNTIME_DEBUG", "").strip().lower()
        self.debug: bool = raw_debug in ("1", "true", "yes")

        # -- max call stack --
        try:
            self.max_call_stack: int = int(
                os.environ.get("JS_RUNTIME_MAX_CALL_STACK", "1000")
            )
        except ValueError:
            self.max_call_stack = 1000

        self._initialized = True

    @classmethod
    def get_instance(cls) -> "Config":
        """Return the unique ``Config`` instance, creating it if necessary."""
        return cls()