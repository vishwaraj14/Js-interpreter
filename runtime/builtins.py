# js_runtime\runtime\builtins.py

"""
builtins.py – Populate the global environment with standard JavaScript
objects and functions.

Defines :class:`Builtins` whose :meth:`register` class method injects all
required built‑ins into the supplied :class:`~runtime.environment.Environment`.
Console output is captured in a module‑level buffer retrievable via
:func:`get_console_output`.
"""

from __future__ import annotations

import datetime
import math
import re
import types
from typing import Any, Callable, List, Sequence, Union, Optional

from runtime.environment import Environment  # noqa: E402 (assuming runtime is importable)

# ---------------------------------------------------------------------------
# Console capture buffer
# ---------------------------------------------------------------------------
_console_buffer: List[str] = []


def get_console_output() -> str:
    """Return all console output captured so far, joined by newlines."""
    return "\n".join(_console_buffer)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def _unwrap_string(this: Union[str, Any]) -> str:
    """Return the underlying Python string whether *this* is a plain string
    or a wrapper object with a ``.value`` attribute.
    """
    if isinstance(this, str):
        return this
    # Assume it's a boxed String object.
    return this.value


# ---------------------------------------------------------------------------
# console.log(...)
# ---------------------------------------------------------------------------
def _console_log(*args: Any) -> None:
    """Print *args* separated by a space, append to the global buffer."""
    line = " ".join(str(arg) for arg in args)
    _console_buffer.append(line)
    # Also print immediately so interactive sessions see output.
    print(line)


# ---------------------------------------------------------------------------
# Math object
# ---------------------------------------------------------------------------
def _math_random() -> float:
    """Return a random float in [0, 1)."""
    import random
    return random.random()


def _math_floor(x: float) -> int:
    """Return the integer floor of *x*."""
    return math.floor(x)


def _math_pow(base: float, exp: float) -> float:
    """Return base ** exp."""
    return base ** exp


def _math_sqrt(x: float) -> float:
    """Return the square root of *x*."""
    return math.sqrt(x)


def _math_abs(x: float) -> float:
    """Return the absolute value of *x*."""
    return abs(x)


def _math_max(*args: float) -> float:
    """Return the largest argument (or -Infinity for no arguments)."""
    if not args:
        return float("-inf")
    return max(args)


def _math_min(*args: float) -> float:
    """Return the smallest argument (or Infinity for no arguments)."""
    if not args:
        return float("inf")
    return min(args)


# Assemble the Math namespace.
Math = types.SimpleNamespace(
    PI=3.141592653589793,
    random=_math_random,
    floor=_math_floor,
    pow=_math_pow,
    sqrt=_math_sqrt,
    abs=_math_abs,
    max=_math_max,
    min=_math_min,
)


# ---------------------------------------------------------------------------
# Date constructor
# ---------------------------------------------------------------------------
def _date_constructor() -> str:
    """Return the current date/time as an ISO‑8601 string."""
    return datetime.datetime.now().isoformat()


Date = _date_constructor  # The callable that acts as `Date` in the global env.


# ---------------------------------------------------------------------------
# Array constructor and prototype methods
# ---------------------------------------------------------------------------
def _array_constructor(*elements: Any) -> List[Any]:
    """Create a new array (Python list) from the given elements."""
    return list(elements)


# ---- Mutating methods ----------------------------------------------------
def _array_push(this: List[Any], element: Any) -> int:
    """Append *element* and return the new length."""
    this.append(element)
    return len(this)


def _array_pop(this: List[Any]) -> Any:
    """Remove and return the last element, or None if empty."""
    if this:
        return this.pop()
    return None  # undefined


def _array_shift(this: List[Any]) -> Any:
    """Remove and return the first element, or None if empty."""
    if this:
        return this.pop(0)
    return None


def _array_unshift(this: List[Any], element: Any) -> int:
    """Insert *element* at the beginning and return the new length."""
    this.insert(0, element)
    return len(this)


def _array_splice(
    this: List[Any], start: int, delete_count: int, *items: Any
) -> List[Any]:
    """Remove *delete_count* elements at *start*, insert *items*, return removed."""
    # Clamp delete_count to available elements.
    length = len(this)
    start = max(0, start if start >= 0 else length + start)
    start = min(start, length)
    delete_count = max(0, min(delete_count, length - start))

    removed = this[start : start + delete_count]
    this[start : start + delete_count] = items
    return removed


def _array_reverse(this: List[Any]) -> List[Any]:
    """Reverse the array in place and return it."""
    this.reverse()
    return this


def _array_sort(this: List[Any]) -> List[Any]:
    """Sort the array in place (default: string ordering) and return it."""
    # JS default sort converts elements to strings.
    this.sort(key=lambda x: str(x))
    return this


# ---- Non‑mutating methods ------------------------------------------------
def _array_slice(this: List[Any], start: int, end: Optional[int] = None) -> List[Any]:
    """Return a shallow copy of a portion of the array."""
    if end is None:
        end = len(this)
    return this[start:end]


def _array_concat(this: List[Any], *arrays: Any) -> List[Any]:
    """Return a new array with *arrays* concatenated (one level flatten)."""
    result = list(this)
    for arr in arrays:
        if isinstance(arr, list):
            result.extend(arr)
        else:
            result.append(arr)
    return result


def _array_includes(this: List[Any], element: Any) -> bool:
    """Return whether *element* is present."""
    return element in this


def _array_index_of(this: List[Any], element: Any) -> int:
    """Return the first index of *element*, or -1 if not found."""
    try:
        return this.index(element)
    except ValueError:
        return -1


# ---- Higher‑order methods ------------------------------------------------
# Assume that the callback `fn` has a `.call(thisArg, ...args)` method.

def _array_map(this: List[Any], fn: Any) -> List[Any]:
    """Return a new array with the result of calling *fn* on each element."""
    result: List[Any] = []
    for idx, el in enumerate(this):
        result.append(fn.call(None, el, idx, this))
    return result


def _array_filter(this: List[Any], fn: Any) -> List[Any]:
    """Return a new array with elements for which *fn* returns truthy."""
    result: List[Any] = []
    for idx, el in enumerate(this):
        if fn.call(None, el, idx, this):
            result.append(el)
    return result


def _array_reduce(
    this: List[Any], fn: Any, initial_value: Any = None
) -> Any:
    """Apply *fn* against an accumulator and each element."""
    if not this and initial_value is None:
        raise TypeError("Reduce of empty array with no initial value")
    start_idx = 0
    if initial_value is None:
        accumulator = this[0]
        start_idx = 1
    else:
        accumulator = initial_value
    for idx in range(start_idx, len(this)):
        accumulator = fn.call(None, accumulator, this[idx], idx, this)
    return accumulator


def _array_find(this: List[Any], fn: Any) -> Any:
    """Return the first element for which *fn* returns truthy, or None."""
    for idx, el in enumerate(this):
        if fn.call(None, el, idx, this):
            return el
    return None


def _array_some(this: List[Any], fn: Any) -> bool:
    """Return True if *fn* returns truthy for at least one element."""
    for idx, el in enumerate(this):
        if fn.call(None, el, idx, this):
            return True
    return False


def _array_every(this: List[Any], fn: Any) -> bool:
    """Return True if *fn* returns truthy for every element."""
    for idx, el in enumerate(this):
        if not fn.call(None, el, idx, this):
            return False
    return True


# Build the Array.prototype object.
ArrayPrototype = types.SimpleNamespace(
    push=_array_push,
    pop=_array_pop,
    shift=_array_shift,
    unshift=_array_unshift,
    splice=_array_splice,
    reverse=_array_reverse,
    sort=_array_sort,
    slice=_array_slice,
    concat=_array_concat,
    includes=_array_includes,
    indexOf=_array_index_of,
    map=_array_map,
    filter=_array_filter,
    reduce=_array_reduce,
    find=_array_find,
    some=_array_some,
    every=_array_every,
)

# Attach prototype to the constructor.
_array_constructor.prototype = ArrayPrototype # type: ignore


# ---------------------------------------------------------------------------
# String constructor and prototype methods
# ---------------------------------------------------------------------------
def _string_constructor(value: Any = "") -> str:
    """Return a new string (automatically boxed when needed)."""
    return str(value)


# ---- Mutating methods (strings are immutable, so they return new strings) --
def _string_replace(this: Any, search: str, replace: str) -> str:
    """Replace the first occurrence of *search* with *replace*."""
    return _unwrap_string(this).replace(search, replace, 1)


def _string_replace_all(this: Any, search: str, replace: str) -> str:
    """Replace all occurrences of *search* with *replace*."""
    return _unwrap_string(this).replace(search, replace)


def _string_substring(this: Any, start: int, end: Optional[int] = None) -> str:
    """Return the substring between *start* and *end* (JS semantics)."""
    s = _unwrap_string(this)
    length = len(s)
    if end is None:
        end = length
    # JS substring: if start > end, swap; clamp negatives to 0.
    if start > end:
        start, end = end, start
    start = max(0, start)
    end = max(0, min(end, length))
    return s[start:end]


def _string_slice(this: Any, start: int, end: Optional[int] = None) -> str:
    """Return a slice of the string (Python‑like negative indices)."""
    s = _unwrap_string(this)
    if end is None:
        end = len(s)
    return s[start:end]


def _string_split(this: Any, separator: str) -> List[str]:
    """Split the string by *separator*."""
    return _unwrap_string(this).split(separator)


def _string_trim(this: Any) -> str:
    """Remove whitespace from both ends."""
    return _unwrap_string(this).strip()


def _string_to_upper(this: Any) -> str:
    """Return the uppercase version."""
    return _unwrap_string(this).upper()


def _string_to_lower(this: Any) -> str:
    """Return the lowercase version."""
    return _unwrap_string(this).lower()


def _string_includes(this: Any, substr: str) -> bool:
    """Return whether *substr* exists in the string."""
    return substr in _unwrap_string(this)


def _string_starts_with(this: Any, substr: str) -> bool:
    """Return whether the string starts with *substr*."""
    return _unwrap_string(this).startswith(substr)


def _string_ends_with(this: Any, substr: str) -> bool:
    """Return whether the string ends with *substr*."""
    return _unwrap_string(this).endswith(substr)


def _string_index_of(this: Any, substr: str) -> int:
    """Return the first index of *substr*, or -1."""
    return _unwrap_string(this).find(substr)


# Build the String.prototype object.
StringPrototype = types.SimpleNamespace(
    replace=_string_replace,
    replaceAll=_string_replace_all,
    substring=_string_substring,
    slice=_string_slice,
    split=_string_split,
    trim=_string_trim,
    toUpperCase=_string_to_upper,
    toLowerCase=_string_to_lower,
    includes=_string_includes,
    startsWith=_string_starts_with,
    endsWith=_string_ends_with,
    indexOf=_string_index_of,
)

_string_constructor.prototype = StringPrototype # type: ignore


# ---------------------------------------------------------------------------
# Object constructor and methods
# ---------------------------------------------------------------------------
def _object_constructor() -> dict:
    """Return a new empty object."""
    return {}


def _object_keys(obj: dict) -> List[str]:
    """Return the keys of *obj* as a list."""
    return list(obj.keys())


# Attach keys as a property of the constructor.
_object_constructor.keys = _object_keys # type: ignore (allow attaching arbitrary attributes)


# ---------------------------------------------------------------------------
# Global functions
# ---------------------------------------------------------------------------
def _parse_int(string: str) -> Union[int, float]:
    """Parse an integer prefix of *string*; return NaN on failure."""
    s = str(string).strip()
    # Try to match an optional sign and digits.
    m = re.match(r"[-+]?\d+", s)
    if m:
        return int(m.group())
    return float("nan")


def _parse_float(string: str) -> float:
    """Parse a floating‑point prefix of *string*; return NaN on failure."""
    s = str(string).strip()
    # Matches an optional sign, integer/fraction, optional exponent.
    m = re.match(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", s)
    if m:
        return float(m.group())
    return float("nan")


def _is_nan(value: Any) -> bool:
    """Return True if *value* is NaN."""
    # NaN is the only value not equal to itself.
    try:
        return value != value
    except Exception:
        return False


def _number(value: Any) -> float:
    """Coerce *value* to a number, or return NaN."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return float("nan")


# ---------------------------------------------------------------------------
# Builtins registration
# ---------------------------------------------------------------------------
class Builtins:
    """Inject all standard built‑ins into the global environment."""

    @classmethod
    def register(cls, env: Environment) -> None:
        """Add every built‑in object, constructor, and function to *env*.

        Args:
            env: The global :class:`Environment` instance.
        """
        env.define("console", types.SimpleNamespace(log=_console_log))
        env.define("Math", Math)
        env.define("Date", Date)
        env.define("Array", _array_constructor)
        env.define("String", _string_constructor)
        env.define("Object", _object_constructor)
        env.define("parseInt", _parse_int)
        env.define("parseFloat", _parse_float)
        env.define("isNaN", _is_nan)
        env.define("Number", _number)