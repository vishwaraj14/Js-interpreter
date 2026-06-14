# js_runtime\runtime\ast_nodes.py

"""
AST node definitions for the JavaScript runtime.

This module contains the base :class:`ASTNode` class, a :class:`Visitor` abstract
class, and concrete node classes for all supported syntactic constructs.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Base node
# ---------------------------------------------------------------------------

class ASTNode(ABC):
    """Abstract base class for all AST nodes."""

    @abstractmethod
    def accept(self, visitor: 'Visitor') -> Any:
        """Accept a visitor (double‑dispatch)."""
        ...

# ---------------------------------------------------------------------------
# Visitor interface
# ---------------------------------------------------------------------------

class Visitor(ABC):
    """Abstract visitor that dispatches to node‑specific ``visit_*`` methods.

    The default implementation of :meth:`visit` calls :meth:`ASTNode.accept`,
    which in turn calls the correct ``visit_*`` method on the visitor.
    Subclasses should override the ``visit_*`` methods they are interested in.
    """

    def visit(self, node: ASTNode) -> Any:
        """Entry point: dispatch to ``visit_Program``, ``visit_Identifier``, etc."""
        return node.accept(self)

    # -- Top‑level ----------------------------------------------------------

    @abstractmethod
    def visit_Program(self, node: 'Program') -> Any: ...

    @abstractmethod
    def visit_SpreadElement(self, node: 'SpreadElement') -> Any: ...

    # -- Statements & Declarations ------------------------------------------

    @abstractmethod
    def visit_VariableDeclaration(self, node: 'VariableDeclaration') -> Any: ...

    @abstractmethod
    def visit_VariableDeclarator(self, node: 'VariableDeclarator') -> Any: ...

    @abstractmethod
    def visit_BlockStatement(self, node: 'BlockStatement') -> Any: ...

    @abstractmethod
    def visit_ExpressionStatement(self, node: 'ExpressionStatement') -> Any: ...

    @abstractmethod
    def visit_IfStatement(self, node: 'IfStatement') -> Any: ...

    @abstractmethod
    def visit_ForStatement(self, node: 'ForStatement') -> Any: ...

    @abstractmethod
    def visit_WhileStatement(self, node: 'WhileStatement') -> Any: ...

    @abstractmethod
    def visit_FunctionDeclaration(self, node: 'FunctionDeclaration') -> Any: ...

    @abstractmethod
    def visit_ReturnStatement(self, node: 'ReturnStatement') -> Any: ...

    @abstractmethod
    def visit_ThrowStatement(self, node: 'ThrowStatement') -> Any: ...

    @abstractmethod
    def visit_TryStatement(self, node: 'TryStatement') -> Any: ...

    @abstractmethod
    def visit_CatchClause(self, node: 'CatchClause') -> Any: ...

    # -- Expressions --------------------------------------------------------

    @abstractmethod
    def visit_Identifier(self, node: 'Identifier') -> Any: ...

    @abstractmethod
    def visit_Literal(self, node: 'Literal') -> Any: ...

    @abstractmethod
    def visit_BinaryExpression(self, node: 'BinaryExpression') -> Any: ...

    @abstractmethod
    def visit_UnaryExpression(self, node: 'UnaryExpression') -> Any: ...

    @abstractmethod
    def visit_AssignmentExpression(self, node: 'AssignmentExpression') -> Any: ...

    @abstractmethod
    def visit_LogicalExpression(self, node: 'LogicalExpression') -> Any: ...

    @abstractmethod
    def visit_ConditionalExpression(self, node: 'ConditionalExpression') -> Any: ...

    @abstractmethod
    def visit_CallExpression(self, node: 'CallExpression') -> Any: ...

    @abstractmethod
    def visit_MemberExpression(self, node: 'MemberExpression') -> Any: ...

    @abstractmethod
    def visit_ArrayExpression(self, node: 'ArrayExpression') -> Any: ...

    @abstractmethod
    def visit_ArrayLiteral(self, node: 'ArrayLiteral') -> Any: ...

    @abstractmethod
    def visit_ObjectExpression(self, node: 'ObjectExpression') -> Any: ...

    @abstractmethod
    def visit_Property(self, node: 'Property') -> Any: ...

    @abstractmethod
    def visit_UpdateExpression(self, node: 'UpdateExpression') -> Any: ...

    @abstractmethod
    def visit_ThisExpression(self, node: 'ThisExpression') -> Any: ...

    @abstractmethod
    def visit_NewExpression(self, node: 'NewExpression') -> Any: ...

    @abstractmethod
    def visit_FunctionExpression(self, node: 'FunctionExpression') -> Any: ...

# ---------------------------------------------------------------------------
# Concrete nodes
# ---------------------------------------------------------------------------

@dataclass
class SpreadElement(ASTNode):
    argument: ASTNode

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_SpreadElement(self)

@dataclass
class Program(ASTNode):
    """Top‑level node: a complete script or module."""
    body: List[ASTNode]

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_Program(self)


@dataclass
class Identifier(ASTNode):
    """An identifier (variable name)."""
    name: str

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_Identifier(self)


@dataclass
class VariableDeclarator(ASTNode):
    """A single binding in a ``let`` or ``const`` declaration.

    Attributes:
        id: The variable name.
        init: The initialiser expression, or ``None``.
    """
    id: Identifier
    init: Optional[ASTNode] = None

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_VariableDeclarator(self)


@dataclass
class VariableDeclaration(ASTNode):
    """A ``let`` or ``const`` declaration.

    Attributes:
        kind: ``"let"`` or ``"const"``.
        declarations: One or more :class:`VariableDeclarator` nodes.
    """
    kind: str
    declarations: List[VariableDeclarator]

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_VariableDeclaration(self)
    

@dataclass
class Literal(ASTNode):
    """A literal value: number, string, boolean, ``null``, ``undefined``, regex."""
    value: Any

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_Literal(self)


@dataclass
class BinaryExpression(ASTNode):
    """Arithmetic or comparison expression (``+``, ``-``, ``*``, ``/``, ``==``, etc.)."""
    left: ASTNode
    operator: str
    right: ASTNode

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_BinaryExpression(self)


@dataclass
class UnaryExpression(ASTNode):
    """Unary expression: ``!``, ``-``, ``+``, ``typeof``, ``void``, ``delete``."""
    operator: str
    argument: ASTNode

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_UnaryExpression(self)


@dataclass
class AssignmentExpression(ASTNode):
    """Assignment or compound assignment (``=``, ``+=``, ``-=``, etc.)."""
    left: ASTNode
    operator: str
    right: ASTNode

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_AssignmentExpression(self)


@dataclass
class LogicalExpression(ASTNode):
    """Short‑circuit logical expression: ``&&``, ``||``, ``??``."""
    left: ASTNode
    operator: str
    right: ASTNode

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_LogicalExpression(self)


@dataclass
class ConditionalExpression(ASTNode):
    """Ternary expression: ``test ? consequent : alternate``."""
    test: ASTNode
    consequent: ASTNode
    alternate: ASTNode

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_ConditionalExpression(self)


@dataclass
class IfStatement(ASTNode):
    """``if`` / ``else`` statement."""
    test: ASTNode
    consequent: ASTNode
    alternate: Optional[ASTNode] = None

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_IfStatement(self)


@dataclass
class ForStatement(ASTNode):
    """C‑style ``for`` loop.

    ``init``, ``test``, and ``update`` are optional and may be ``None``.
    ``init`` can be a :class:`VariableDeclaration` or an expression.
    """
    init: Optional[ASTNode]
    test: Optional[ASTNode]
    update: Optional[ASTNode]
    body: ASTNode

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_ForStatement(self)


@dataclass
class WhileStatement(ASTNode):
    """``while`` loop."""
    test: ASTNode
    body: ASTNode

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_WhileStatement(self)


@dataclass
class BlockStatement(ASTNode):
    """A block of statements enclosed in ``{`` ... ``}``."""
    body: List[ASTNode]

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_BlockStatement(self)


@dataclass
class ExpressionStatement(ASTNode):
    """A statement consisting of an expression (e.g., ``foo();``)."""
    expression: ASTNode

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_ExpressionStatement(self)


@dataclass
class FunctionDeclaration(ASTNode):
    """A named function declaration (hoisted)."""
    id: Identifier
    params: List[Identifier]
    body: BlockStatement

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_FunctionDeclaration(self)

@dataclass
class CallExpression(ASTNode):
    """Function or method call: ``callee(arguments)``."""
    callee: ASTNode
    arguments: List[ASTNode]

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_CallExpression(self)


@dataclass
class ReturnStatement(ASTNode):
    """``return`` statement, optionally with a value."""
    argument: Optional[ASTNode] = None

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_ReturnStatement(self)


@dataclass
class ArrayExpression(ASTNode):
    """Array literal, e.g., ``[1, 2, a]``."""
    elements: List[ASTNode]

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_ArrayExpression(self)

@dataclass
class ArrayLiteral(ASTNode):
    """Array literal, e.g., ``[1, 2, a]``.

    Alias for ``ArrayExpression``; used by the parser directly.
    """
    elements: List[ASTNode]

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_ArrayLiteral(self)

@dataclass
class ObjectExpression(ASTNode):
    """Object literal: ``{ key: value, ... }``."""
    properties: List['Property']

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_ObjectExpression(self)


@dataclass
class Property(ASTNode):
    """A property inside an object literal.

    Attributes:
        key: The property key (identifier, string literal, or computed expression).
        value: The property value.
        kind: ``"init"`` for normal properties (others may be added later).
    """
    key: ASTNode
    value: ASTNode
    kind: str = "init"

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_Property(self)


@dataclass
class MemberExpression(ASTNode):
    """Member access: ``object.property`` or ``object[property]``.

    Attributes:
        object: The object being accessed.
        property: The member name (Identifier or expression).
        computed: ``True`` for bracket notation, ``False`` for dot notation.
    """
    object: ASTNode
    property: ASTNode
    computed: bool

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_MemberExpression(self)


@dataclass
class UpdateExpression(ASTNode):
    """Update expression: ``++argument`` or ``argument++`` (and ``--``).

    Attributes:
        operator: ``"++"`` or ``"--"``.
        argument: The expression being updated.
        prefix: ``True`` if the operator appears before the argument.
    """
    operator: str
    argument: ASTNode
    prefix: bool

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_UpdateExpression(self)


@dataclass
class ThisExpression(ASTNode):
    """The ``this`` keyword."""
    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_ThisExpression(self)


@dataclass
class NewExpression(ASTNode):
    """Constructor call: ``new callee(arguments)``."""
    callee: ASTNode
    arguments: List[ASTNode] = field(default_factory=list)

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_NewExpression(self)


@dataclass
class ThrowStatement(ASTNode):
    """``throw`` statement."""
    argument: ASTNode

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_ThrowStatement(self)


@dataclass
class TryStatement(ASTNode):
    """``try ... catch ... finally`` statement."""
    block: BlockStatement
    handler: Optional['CatchClause'] = None
    finalizer: Optional[BlockStatement] = None

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_TryStatement(self)


@dataclass
class CatchClause(ASTNode):
    """``catch`` clause inside a :class:`TryStatement`."""
    param: Identifier
    body: BlockStatement

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_CatchClause(self)

@dataclass
class FunctionExpression(ASTNode):
    """A standard function expression or anonymous function."""
    id: Optional[Identifier]      # The function name (None if anonymous)
    params: List[Identifier]      # List of parameter nodes
    body: ASTNode                 # BlockStatement representing the function body

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_FunctionExpression(self)



# ---------------------------------------------------------------------------
# Module public API
# ---------------------------------------------------------------------------
__all__ = [
    "ASTNode",
    "Visitor",
    "Program",
    "VariableDeclaration",
    "VariableDeclarator",
    "Identifier",
    "Literal",
    "BinaryExpression",
    "UnaryExpression",
    "AssignmentExpression",
    "LogicalExpression",
    "ConditionalExpression",
    "IfStatement",
    "ForStatement",
    "WhileStatement",
    "BlockStatement",
    "ExpressionStatement",
    "FunctionDeclaration",
    "FunctionExpression",
    "CallExpression",
    "ReturnStatement",
    "ArrayExpression",
    "ArrayLiteral",
    "ObjectExpression",
    "Property",
    "MemberExpression",
    "UpdateExpression",
    "ThisExpression",
    "NewExpression",
    "ThrowStatement",
    "TryStatement",
    "CatchClause",
]