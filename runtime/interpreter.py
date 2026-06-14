# js_runtime\runtime\interpreter.py

"""
Tree-walking interpreter for the JavaScript runtime.

The interpreter traverses the AST produced by the parser and evaluates it
using the visitor pattern.  It maintains a runtime :class:`Environment` for
variable scoping and relies on the helper classes :class:`JSFunction`,
:class:`JSArray`, and various type-coercion utilities.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Union

from core.logger import Logger

from .ast_nodes import (
    ArrayLiteral,
    AssignmentExpression,
    BinaryExpression,
    BlockStatement,
    CallExpression,
    ExpressionStatement,
    ForStatement,
    FunctionDeclaration,
    Identifier,
    IfStatement,
    Literal,
    MemberExpression,
    Program,
    ReturnStatement,
    UnaryExpression,
    VariableDeclaration,
    VariableDeclarator,
    Visitor,
    WhileStatement,
    LogicalExpression,
    ConditionalExpression,
    ArrayExpression,
    ObjectExpression,
    Property,
    UpdateExpression,
    ThisExpression,
    NewExpression,
    FunctionExpression,
    ThrowStatement,
    TryStatement,
    CatchClause,
    SpreadElement
)
from .environment import Environment, ReturnValue

logger = Logger()

# ---------------------------------------------------------------------------
# Sentinel values for JavaScript `undefined` and `null`
# ---------------------------------------------------------------------------



class UndefinedType:
    """Singleton representing JavaScript ``undefined``."""
    _instance: Optional[UndefinedType] = None

    def __new__(cls) -> UndefinedType:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "undefined"

    def __str__(self) -> str:
        return "undefined"


class NullType:
    """Singleton representing JavaScript ``null``."""
    _instance: Optional[NullType] = None

    def __new__(cls) -> NullType:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "null"

    def __str__(self) -> str:
        return "null"


UNDEFINED = UndefinedType()
NULL = NullType()

# ---------------------------------------------------------------------------
# Type coercion helpers
# ---------------------------------------------------------------------------

def is_truthy(value: Any) -> bool:
    """Return ``True`` if *value* is truthy in JavaScript semantics."""
    if value is UNDEFINED or value is NULL:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0 and not math.isnan(value)
    if isinstance(value, str):
        return value != ""
    # objects, arrays, functions are truthy
    return True


def to_number(value: Any) -> float:
    """Convert *value* to a JavaScript number (``NaN`` for unsupported)."""
    if value is UNDEFINED:
        return float("nan")
    if value is NULL:
        return 0.0
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return float("nan")
    return float("nan")


def to_string(value: Any) -> str:
    """Convert *value* to a JavaScript string."""
    if value is UNDEFINED:
        return "undefined"
    if value is NULL:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        s = str(value)
        if s.endswith(".0"):   # JavaScript prints integers without decimal
            s = s[:-2]
        return s
    if isinstance(value, str):
        return value
    # For objects / arrays default to a placeholder
    return str(value)


def strict_equal(a: Any, b: Any) -> bool:
    """JavaScript strict equality (``===``)."""
    if a is b:
        return True
    if a is UNDEFINED and b is UNDEFINED:
        return True
    if a is NULL and b is NULL:
        return True
    # NaN !== NaN
    if isinstance(a, float) and math.isnan(a):
        return False
    if isinstance(b, float) and math.isnan(b):
        return False
    return type(a) == type(b) and a == b


def loose_equal(a: Any, b: Any) -> bool:
    """Simplified JavaScript abstract equality (``==``)."""
    if type(a) == type(b):
        return strict_equal(a, b)
    if a is UNDEFINED and b is NULL:
        return True
    if a is NULL and b is UNDEFINED:
        return True
    if isinstance(a, str) and isinstance(b, (int, float)):
        return loose_equal(to_number(a), b)
    if isinstance(b, str) and isinstance(a, (int, float)):
        return loose_equal(a, to_number(b))
    if isinstance(a, bool):
        return loose_equal(1 if a else 0, b)
    if isinstance(b, bool):
        return loose_equal(a, 1 if b else 0)
    return False


# ---------------------------------------------------------------------------
# JavaScript array wrapper
# ---------------------------------------------------------------------------

class JSArray:
    """Wraps a Python list to behave like a JavaScript array.

    Supports integer indexing, a ``length`` property, and built‑in methods
    dispatched through :mod:`runtime.builtins` when available, otherwise
    falling back to pure‑Python implementations.
    """

    def __init__(self, elements: Optional[List[Any]] = None) -> None:
        self._elements: List[Any] = list(elements) if elements is not None else []
        self._extra: Dict[str, Any] = {}

    def __getitem__(self, idx: int) -> Any:
        return self._elements[idx]

    def __setitem__(self, idx: int, value: Any) -> None:
        if 0 <= idx < len(self._elements):
            self._elements[idx] = value
        elif idx >= 0:
            # extend if necessary
            while len(self._elements) <= idx:
                self._elements.append(UNDEFINED)
            self._elements[idx] = value

    def __len__(self) -> int:
        return len(self._elements)

    def __iter__(self):
        return iter(self._elements)
    
    @property
    def length(self) -> int:
        """Return the JavaScript ``length`` property."""
        return len(self._elements)

    @length.setter
    def length(self, value: int) -> None:
        if value < 0:
            return
        if value < len(self._elements):
            del self._elements[value:]
        else:
            self._elements.extend([UNDEFINED] * (value - len(self._elements)))

    # --- built-in method stubs (to be replaced by actual builtins) ---

    def push(self, *args: Any) -> int:
        """Append elements and return new length."""
        self._elements.extend(args)
        return len(self._elements)

    def pop(self) -> Any:
        """Remove and return the last element."""
        if self._elements:
            return self._elements.pop()
        return UNDEFINED

    def shift(self) -> Any:
        """Remove and return the first element."""
        if self._elements:
            return self._elements.pop(0)
        return UNDEFINED

    def unshift(self, *args: Any) -> int:
        """Prepend elements and return new length."""
        for item in reversed(args):
            self._elements.insert(0, item)
        return len(self._elements)

    def index_of(self, search_element: Any, from_index: int = 0) -> int:
        """Return the first index of *search_element*, or -1."""
        try:
            return self._elements.index(search_element, from_index)
        except ValueError:
            return -1

    def join(self, separator: str = ",") -> str:
        """Join all elements into a string."""
        return separator.join(to_string(e) for e in self._elements)

    def slice(self, start: int = 0, end: Optional[int] = None) -> JSArray:
        """Return a shallow copy of a portion of the array."""
        end = len(self._elements) if end is None else end
        return JSArray(self._elements[start:end])

    def map(self, callback: Callable, this_arg: Any = UNDEFINED) -> JSArray:
        """Create a new array with the results of calling *callback*."""
        return JSArray([callback(element, i, self) for i, element in enumerate(self._elements)])

    def filter(self, callback: Callable, this_arg: Any = UNDEFINED) -> JSArray:
        """Create a new array with elements that pass the test."""
        return JSArray([element for element in self._elements if is_truthy(callback(element))])


# ---------------------------------------------------------------------------
# JavaScript function object
# ---------------------------------------------------------------------------

class JSFunction:
    """Captures a function declaration AST node and its closure.

    When called, it sets up a new environment with the closure as enclosing
    scope, binds arguments, executes the body, and catches
    :class:`ReturnValue` exceptions.
    """

    def __init__(self,
                 node:  FunctionDeclaration | FunctionExpression,
                 closure: Environment,
                 interpreter: Interpreter) -> None:
        self.node = node
        self.closure = closure
        self.interpreter = interpreter

    def __call__(self, *args: Any) -> Any:
        logger.debug(f"Calling JSFunction '{self.node.id.name if self.node.id else 'anonymous'}'")
        old_env = self.interpreter.env
        new_env = Environment(enclosing=self.closure)
        # Bind parameters
        params = self.node.params
        for i, param in enumerate(params):
            val = args[i] if i < len(args) else UNDEFINED
            new_env.define(param.name, val)
        self.interpreter.env = new_env
        try:
            self.interpreter.visit(self.node.body)   # BlockStatement
            return UNDEFINED
        except ReturnValue as ret:
            return ret.value
        finally:
            self.interpreter.env = old_env

    def __repr__(self) -> str:
        name = self.node.id.name if self.node.id else "<anonymous>"
        return f"<JSFunction {name}>"


# ---------------------------------------------------------------------------
# Interpreter
# ---------------------------------------------------------------------------

class Interpreter(Visitor):
    """Tree‑walking interpreter for the JavaScript AST.

    The interpreter evaluates nodes by visiting them and returns the
    resulting runtime value.  It uses an :class:`Environment` for scoping
    and relies on the :class:`Visitor` base class for dispatching.

    Parameters:
        env: The initial (global) environment.
    """

    def __init__(self, env: Environment) -> None:
        self.env = env
        # Cache method tables for built‑in objects (filled lazily)
        self._array_methods: Optional[Dict[str, Callable]] = None
        self._string_methods: Optional[Dict[str, Callable]] = None

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def interpret(self, program: Program) -> None:
        """Evaluate all statements in *program.body*.

        Args:
            program: The AST ``Program`` node.
        """
        logger.info("Starting interpretation")
        for stmt in program.body:
            self.visit(stmt)
        logger.info("Interpretation finished")

    # ------------------------------------------------------------------
    # Visitor methods for statements
    # ------------------------------------------------------------------

    def visit_Program(self, node: Program) -> Any:
        for stmt in node.body:
            self.visit(stmt)
        return None

    def visit_SpreadElement(self, node: SpreadElement) -> Any:
        """Normally handled inside array/object literals.  If called standalone, evaluate the argument."""
        return self.visit(node.argument)
    
    def visit_VariableDeclaration(self, node: VariableDeclaration) -> None:
        """Process variable declarations (``var``, ``let``, ``const``).

        Each declarator is evaluated and the resulting value is bound in the
        current environment.
        """
        for decl in node.declarations:
            value = self.visit(decl)
            self.env.define(decl.id.name, value)

    def visit_VariableDeclarator(self, node: VariableDeclarator) -> Any:
        """Evaluate the initialiser (if any) and return its value."""
        if node.init is not None:
            return self.visit(node.init)
        return UNDEFINED

    def visit_FunctionDeclaration(self, node: FunctionDeclaration) -> None:
        """Create a :class:`JSFunction` and bind it in the current scope."""
        func = JSFunction(node, self.env, self)
        self.env.define(node.id.name, func)

    def visit_BlockStatement(self, node: BlockStatement) -> None:
        """Execute a block in a new nested environment."""
        previous = self.env
        self.env = Environment(enclosing=previous)
        try:
            for stmt in node.body:
                self.visit(stmt)
        finally:
            self.env = previous

    def visit_IfStatement(self, node: IfStatement) -> None:
        """Conditionally execute ``consequent`` or ``alternate``."""
        if is_truthy(self.visit(node.test)):
            self.visit(node.consequent)
        elif node.alternate is not None:
            self.visit(node.alternate)

    def visit_ForStatement(self, node: ForStatement) -> None:
        """Standard ``for`` loop."""
        if node.init is not None:
            self.visit(node.init)
        while True:
            if node.test is not None and not is_truthy(self.visit(node.test)):
                break
            self.visit(node.body)
            if node.update is not None:
                self.visit(node.update)

    def visit_WhileStatement(self, node: WhileStatement) -> None:
        """Standard ``while`` loop."""
        while is_truthy(self.visit(node.test)):
            self.visit(node.body)

    def visit_ReturnStatement(self, node: ReturnStatement) -> None:
        """Raise :class:`ReturnValue` to unwind the call stack."""
        value = self.visit(node.argument) if node.argument else UNDEFINED
        raise ReturnValue(value)

    def visit_ExpressionStatement(self, node: ExpressionStatement) -> Any:
        """Evaluate a statement‑level expression and discard the result."""
        return self.visit(node.expression)

    def visit_LogicalExpression(self, node: LogicalExpression) -> Any:
        left = self.visit(node.left)
        if node.operator == "&&":
            # Short circuit: if left is falsy, return left; else right
            if not is_truthy(left):
                return left
            return self.visit(node.right)
        elif node.operator == "||":
            # Short circuit: if left is truthy, return left; else right
            if is_truthy(left):
                return left
            return self.visit(node.right)
        else:
            raise RuntimeError(f"Unknown logical operator {node.operator}")

    def visit_ConditionalExpression(self, node: ConditionalExpression) -> Any:
        test = self.visit(node.test)
        if is_truthy(test):
            return self.visit(node.consequent)
        return self.visit(node.alternate)

    def visit_ArrayExpression(self, node: ArrayExpression) -> JSArray:
        arr = JSArray()
        for element in node.elements:
            if isinstance(element, SpreadElement):
                # The spread argument should evaluate to an array
                iterable = self.visit(element.argument)
                if isinstance(iterable, JSArray):
                    # Push each item individually
                    # JSArray stores elements in an internal list; use `iterable.elements` if public
                    # or create a temporary list. Assuming _elements is accessible.
                    for item in iterable._elements:
                        arr.push(item)
                else:
                    raise RuntimeError("Spread of non-array is not supported yet")
            else:
                arr.push(self.visit(element))
        return arr
    
    def visit_ObjectExpression(self, node: ObjectExpression) -> Any:
        obj = {}  # or JSObject()
        for prop in node.properties:
            key, value = self.visit(prop)
            obj[key] = value
        return obj

    def visit_Property(self, node: Property) -> tuple:
        if isinstance(node.key, Identifier):
            key = node.key.name
        elif hasattr(node.key, "value"):
            # getattr dynamically fetches the attribute, which stops the type checker warning
            key = getattr(node.key, "value")
        else:
            raise RuntimeError("Object property key must be an Identifier or Literal")
            
        value = self.visit(node.value)
        return (key, value)



    def visit_UpdateExpression(self, node: UpdateExpression) -> Any:
        assert isinstance(node.argument, Identifier)
        var_name = node.argument.name
        current = self.env.lookup(var_name)
        if not isinstance(current, (int, float)):
            raise RuntimeError("UpdateExpression requires a number")
        if node.operator == "++":
            new_value = current + 1
        elif node.operator == "--":
            new_value = current - 1
        else:
            raise RuntimeError(f"Unknown update operator {node.operator}")
        self.env.assign(var_name, new_value)   # or self.env.assign(var_name, new_value)
        return new_value if node.prefix else current   # prefix vs postfix

    def visit_ThisExpression(self, node: ThisExpression) -> Any:
        # In a simple global‑only interpreter, 'this' could be the global object.
        # For now, just return a special value or the environment itself.
        return self.env  # or a dedicated global object

    def visit_NewExpression(self, node: NewExpression) -> Any:
        callee = self.visit(node.callee)
        args = [self.visit(arg) for arg in node.arguments]

        # If the callee is a built‑in constructor (Date, etc.)
        if hasattr(callee, 'construct'):
            return callee.construct(*args)

        # If it's a user‑defined constructor (function)
        if isinstance(callee, JSFunction):
            # Create a new object, set its prototype, call the function with this = newObj
            obj = {}  # or a proper JSObject
            # … set up prototype etc. (simplified)
            callee(obj, *args)
            return obj

        raise RuntimeError(f"{callee} is not a constructor")

    def visit_FunctionExpression(self, node: FunctionExpression) -> JSFunction:
        """Create a new JSFunction object capturing the current lexical scope."""
        func = JSFunction(
            node=node,           # Pass the function AST node
            closure=self.env,    # Pass the current environment scope 
            interpreter=self     # Pass the interpreter instance
        )
        return func


    def visit_ThrowStatement(self, node: ThrowStatement) -> None:
        exception = self.visit(node.argument)
        raise RuntimeError(exception)   # or a custom exception class

    def visit_TryStatement(self, node: TryStatement) -> Any:
        raise NotImplementedError("try/catch is not implemented yet")

    def visit_CatchClause(self, node: CatchClause) -> None:
        raise NotImplementedError("catch clause not implemented")
    # ------------------------------------------------------------------
    # Visitor methods for expressions
    # ------------------------------------------------------------------

    def visit_Literal(self, node: Literal) -> Any:
        """Return the literal value stored in the node."""
        return node.value

    def visit_Identifier(self, node: Identifier) -> Any:
        """Look up the identifier in the environment chain."""
        return self.env.lookup(node.name)

    def visit_AssignmentExpression(self, node: AssignmentExpression) -> Any:
        """Handle ``=``, ``+=``, ``-=`` and similar operators."""
        op = node.operator
        left = node.left

        # Evaluate right-hand side once
        right = self.visit(node.right)

        if isinstance(left, Identifier):
            name = left.name
            if op == "=":
                self.env.assign(name, right)
                return right
            # Compound assignment
            current = self.env.lookup(name)
            new_val = self._apply_compound(op, current, right)
            self.env.assign(name, new_val)
            return new_val

        elif isinstance(left, MemberExpression):
            obj, prop = self._evaluate_member_parts(left)
            if op == "=":
                self._set_property(obj, prop, right)
                return right
            # Compound assignment
            current = self._get_property(obj, prop)
            new_val = self._apply_compound(op, current, right)
            self._set_property(obj, prop, new_val)
            return new_val

        logger.error(f"Unsupported assignment left-hand side: {type(left)}")
        return UNDEFINED

    def visit_BinaryExpression(self, node: BinaryExpression) -> Any:
        """Evaluate a binary expression with JavaScript‑style coercion."""
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = node.operator

        if op == "+":
            # String concatenation if either operand is a string
            if isinstance(left, str) or isinstance(right, str):
                return to_string(left) + to_string(right)
            return to_number(left) + to_number(right)

        if op == "-":
            return to_number(left) - to_number(right)
        if op == "*":
            return to_number(left) * to_number(right)
        if op == "/":
            l_num, r_num = to_number(left), to_number(right)
            if r_num == 0:
                return float("inf") if l_num >= 0 else float("-inf")
            return l_num / r_num
        if op == "%":
            return to_number(left) % to_number(right)

        if op == "==":
            return loose_equal(left, right)
        if op == "!=":
            return not loose_equal(left, right)
        if op == "===":
            return strict_equal(left, right)
        if op == "!==":
            return not strict_equal(left, right)

        if op == "<":
            # If both are strings → lexicographic comparison
            if isinstance(left, str) and isinstance(right, str):
                return left < right
            return to_number(left) < to_number(right)
        if op == "<=":
            if isinstance(left, str) and isinstance(right, str):
                return left <= right
            return to_number(left) <= to_number(right)
        if op == ">":
            if isinstance(left, str) and isinstance(right, str):
                return left > right
            return to_number(left) > to_number(right)
        if op == ">=":
            if isinstance(left, str) and isinstance(right, str):
                return left >= right
            return to_number(left) >= to_number(right)

        logger.error(f"Unknown binary operator '{op}'")
        return UNDEFINED

    def visit_UnaryExpression(self, node: UnaryExpression) -> Any:
        """Evaluate a unary expression (``!``, ``-``, ``+``)."""
        arg = self.visit(node.argument)
        op = node.operator

        if op == "!":
            return not is_truthy(arg)
        if op == "-":
            return -to_number(arg)
        if op == "+":
            return to_number(arg)

        logger.error(f"Unknown unary operator '{op}'")
        return UNDEFINED

    def visit_CallExpression(self, node: CallExpression) -> Any:
        """Evaluate a function/method call."""
        callee = self.visit(node.callee)
        args = [self.visit(a) for a in node.arguments]

        if isinstance(callee, JSFunction):
            return callee(*args)

        if callable(callee):
            return callee(*args)

        logger.error(f"{callee} is not callable")
        return UNDEFINED

    def visit_MemberExpression(self, node: MemberExpression) -> Any:
        """Evaluate property access (``obj.prop`` or ``obj[expr]``)."""
        obj, prop = self._evaluate_member_parts(node)
        return self._get_property(obj, prop)

    def visit_ArrayLiteral(self, node: ArrayLiteral) -> JSArray:
        """Create a :class:`JSArray` from an array literal."""
        elements = [self.visit(el) for el in node.elements]
        return JSArray(elements)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_compound(self, op: str, current: Any, right: Any) -> Any:
        """Apply a compound assignment operator."""
        op = op[0]  # strip the '=' -> '+', '-', '*', etc.
        # Use the same logic as BinaryExpression for the operator
        # Re‑using BinaryExpression would require a node; we do it inline.
        if op == "+":
            if isinstance(current, str) or isinstance(right, str):
                return to_string(current) + to_string(right)
            return to_number(current) + to_number(right)
        if op == "-":
            return to_number(current) - to_number(right)
        if op == "*":
            return to_number(current) * to_number(right)
        if op == "/":
            return to_number(current) / to_number(right)
        if op == "%":
            return to_number(current) % to_number(right)
        return right

    def _evaluate_member_parts(self, node: MemberExpression) -> tuple[Any, Any]:
        """Return the (object, property‑key) pair for a member expression."""
        obj = self.visit(node.object)
        if node.computed:
            prop = self.visit(node.property)
        else:
            # Assert to the type checker that this must be an Identifier node
            assert isinstance(node.property, Identifier)
            prop = node.property.name   # Identifier
        return obj, prop

    def _get_property(self, obj: Any, key: Any) -> Any:
        """Retrieve a property from *obj* using JavaScript semantics."""
        # Handle JSArray specially
        if isinstance(obj, JSArray):
            if key == "length":
                return len(obj)
            if isinstance(key, int):
                try:
                    return obj._elements[key]
                except IndexError:
                    return UNDEFINED
            if isinstance(key, str):
                if key.isdigit():
                    idx = int(key)
                    try:
                        return obj._elements[idx]
                    except IndexError:
                        return UNDEFINED
                # Look up a built‑in method
                method = self._lookup_array_method(key)
                if method is not None:
                    def bound(*args: Any) -> Any:
                        return method(obj, *args)
                    return bound
                # Check extra properties
                if key in obj._extra:
                    return obj._extra[key]
            return UNDEFINED

        # Handle strings (auto‑boxing for method access)
        if isinstance(obj, str):
            if key == "length":
                return len(obj)
            method = self._lookup_string_method(key)
            if method is not None:
                def bound(*args: Any) -> Any:
                    return method(obj, *args)
                return bound
            return UNDEFINED

        # General objects: dict, built‑ins, etc.
        if isinstance(obj, dict):
            return obj.get(key, UNDEFINED)
        if hasattr(obj, key):
            return getattr(obj, key)

        return UNDEFINED

    def _set_property(self, obj: Any, key: Any, value: Any) -> None:
        """Set a property on *obj*."""
        if isinstance(obj, JSArray):
            if key == "length":
                obj.length = value
                return
            if isinstance(key, int):
                obj.__setitem__(key, value)
                return
            if isinstance(key, str) and key.isdigit():
                obj.__setitem__(int(key), value)
                return
            # arbitrary property
            obj._extra[key] = value
            return

        if isinstance(obj, dict):
            obj[key] = value
            return
        if isinstance(obj, (list,)):
            if isinstance(key, int):
                if 0 <= key < len(obj):
                    obj[key] = value
                elif key >= 0:
                    while len(obj) <= key:
                        obj.append(UNDEFINED)
                    obj[key] = value
            return
        if hasattr(obj, key):
            setattr(obj, key, value)
            return

        # Silently ignore assignment on strings or other primitives
        return

    def _lookup_array_method(self, name: str) -> Optional[Callable]:
        if not self._array_methods:
            self._array_methods = {
                "push": JSArray.push,
                "pop": JSArray.pop,
                "shift": JSArray.shift,
                "unshift": JSArray.unshift,
                "indexOf": JSArray.index_of,
                "join": JSArray.join,
                "slice": JSArray.slice,
                "map": JSArray.map,
                "filter": JSArray.filter,
            }
            try:
                from .builtins import ArrayPrototype
                for attr_name in dir(ArrayPrototype):
                    if attr_name.startswith("_"):
                        continue
                    attr = getattr(ArrayPrototype, attr_name)
                    if callable(attr):
                        self._array_methods[attr_name] = attr
            except ImportError:
                pass
        return self._array_methods.get(name)


    def _lookup_string_method(self, name: str) -> Optional[Callable]:
        if not self._string_methods:
            # Explicitly type the temporary dict as Dict[str, Any]
            methods_dict: Dict[str, Any] = {
                "charAt": lambda s, i=0: s[i] if 0 <= i < len(s) else "",
                "toUpperCase": str.upper,
                "toLowerCase": str.lower,
                "slice": str.__getitem__,
                "indexOf": str.find,
                "length": None,
            }
            # Assigning this explicitly-typed dictionary will not trigger errors
            self._string_methods = methods_dict
            try:
                from .builtins import StringPrototype
                for attr_name in dir(StringPrototype):
                    if attr_name.startswith("_"):
                        continue
                    attr = getattr(StringPrototype, attr_name)
                    if callable(attr):
                        self._string_methods[attr_name] = attr
            except ImportError:
                pass
        return self._string_methods.get(name)
