# js_runtime\runtime\environment.py

"""
runtime/environment.py
Variable scoping environment for the JavaScript runtime.
"""

from typing import Any, Optional

class ReturnValue(Exception):
    """Exception raised to unwind the call stack when a ``return`` statement is executed."""

    def __init__(self, value: Any) -> None:
        self.value = value
        super().__init__(f"Return: {value}")


class Environment:
    """Represents a variable scope with optional enclosing environment.

    Supports variable definition with ``"let"``, ``"const"`` and ``"var"``
    semantics, assignment, lookup, and built-in definitions.  Nested scopes
    are created by passing an enclosing :class:`Environment` instance.

    The global scope should be created with ``enclosing=None``; all built‑ins
    are then added to it via :meth:`define_builtin`.
    """

    def __init__(self, enclosing: Optional['Environment'] = None) -> None:
        self._values: dict[str, Any] = {}   # variable values
        self._kinds: dict[str, str] = {}    # "let", "const", "var", "builtin"
        self.enclosing = enclosing          # outer (enclosing) scope

    def define(self, name: str, value: Any, kind: str = "let") -> None:
        """Define a new variable in the **current** scope.

        Args:
            name: Variable identifier.
            value: Initial value.
            kind: One of ``"let"``, ``"const"`` or ``"var"``.

        Raises:
            RuntimeError: If the variable already exists in the current scope.
        """
        if name in self._values:
            raise RuntimeError(f"Variable '{name}' already defined in this scope.")
        self._values[name] = value
        self._kinds[name] = kind

    def define_builtin(self, name: str, value: Any) -> None:
        """Define a read‑only built‑in variable in the current scope.

        Built‑ins are treated like constants and cannot be reassigned later.
        The *value* may be a Python callable that will later be wrapped by the
        interpreter (e.g., ``print``, ``len``).
        """
        self.define(name, value, kind="builtin")

    def assign(self, name: str, value: Any) -> Any:
        """Update the value of an existing variable, searching enclosing scopes.

        Args:
            name: Variable to update.
            value: New value.

        Returns:
            The assigned value.

        Raises:
            RuntimeError: If the variable is not defined or is a constant
                (``"const"`` or ``"builtin"``).
        """
        env = self._find_environment(name)
        if env is None:
            raise RuntimeError(f"Assignment to undefined variable '{name}'.")

        kind = env._kinds[name]
        if kind in ("const", "builtin"):
            raise RuntimeError(f"Cannot reassign constant '{name}'.")

        env._values[name] = value
        return value

    def lookup(self, name: str) -> Any:
        """Retrieve the value of a variable, searching enclosing scopes.

        Args:
            name: Variable to look up.

        Returns:
            The variable's value.

        Raises:
            RuntimeError: If the variable is not defined in any accessible scope.
        """
        env = self._find_environment(name)
        if env is None:
            raise RuntimeError(f"Variable '{name}' is not defined.")
        return env._values[name]

    def has(self, name: str) -> bool:
        """Check whether a variable exists in any accessible scope.

        Returns:
            ``True`` if the variable exists, ``False`` otherwise.
        """
        return self._find_environment(name) is not None

    def _find_environment(self, name: str) -> Optional['Environment']:
        """Walk the scope chain and return the environment that contains *name*.

        Returns:
            The :class:`Environment` where the variable is defined, or ``None``
            if it cannot be found.
        """
        if name in self._values:
            return self
        if self.enclosing is not None:
            return self.enclosing._find_environment(name)
        return None