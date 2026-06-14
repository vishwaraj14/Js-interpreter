# js_runtime\runtime\parser.py

"""
runtime/parser.py – Recursive‑descent parser
============================================
Converts a flat list of tokens into an AST (:class:`Program` node).

Usage::

    from runtime.parser import Parser
    program_ast = Parser(tokens).parse()
"""

from typing import List, Optional, Union

from .ast_nodes import (
    # Statements
    Program,
    VariableDeclaration,
    VariableDeclarator,
    FunctionDeclaration,
    BlockStatement,
    IfStatement,
    ForStatement,
    WhileStatement,
    ReturnStatement,
    ExpressionStatement,
    # Expressions
    AssignmentExpression,
    BinaryExpression,
    UnaryExpression,
    CallExpression,
    MemberExpression,
    Literal,
    Identifier,
    ArrayLiteral,
)
# We assume the tokenizer module exports a Token class with:
#   type: str   (e.g. 'NUMBER', 'IDENTIFIER', ...)
#   value: str  (the lexeme)
#   line: int
#   column: int    (column)
# If your Token class uses different attribute names, adjust accordingly.
from .tokenizer import Token


class ParseError(Exception):
    """Raised when the parser encounters an unexpected token."""

    def __init__(self, message: str, token: Optional[Token] = None) -> None:
        loc = ""
        if token is not None:
            loc = f" at line {token.line}, column {token.column}"
        super().__init__(f"{message}{loc}")
        self.token = token
        self.line = token.line if token else -1
        self.column = token.column if token else -1


class Parser:
    """Recursive‑descent parser for a JavaScript‑like language.

    Builds an AST from a token list following operator precedence and
    statement grammar.
    """

    def __init__(self, tokens: List[Token]) -> None:
        """Initialise the parser with the token list.

        Args:
            tokens: Tokens produced by the tokenizer, ending with ``EOF``.
        """
        self.tokens: List[Token] = tokens
        self.pos: int = 0
        # A sentinel for error reporting when no tokens are left
        self._eof_token = Token("EOF", "", -1, -1) if not tokens else tokens[-1]

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def parse(self) -> Program:
        """Parse the whole token stream and return the root ``Program`` node.

        Returns:
            The AST root.
        """
        statements: List = []
        while not self._check("EOF"):
            statements.append(self._statement())
        return Program(body=statements)

    # ------------------------------------------------------------------
    # Helper methods (token navigation)
    # ------------------------------------------------------------------
    def _peek(self) -> Token:
        """Return the current token without consuming it."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self._eof_token

    def _previous(self) -> Token:
        """Return the token immediately before the current position."""
        if self.pos > 0:
            return self.tokens[self.pos - 1]
        return self._eof_token

    def _advance(self) -> Token:
        """Consume and return the current token, moving the position forward."""
        token = self._peek()
        if self.pos < len(self.tokens):
            self.pos += 1
        return token

    def _check(self, *token_types: str) -> bool:
        """Check if the current token matches any of the given types.

        Args:
            token_types: Variable number of token types to match.

        Returns:
            ``True`` if the current token type is in *token_types*.
        """
        if self.pos >= len(self.tokens):
            return "EOF" in token_types
        return self._peek().type in token_types

    def _match(self, *token_types: str) -> bool:
        """If the current token matches, consume it and return ``True``.

        Args:
            token_types: Variable number of token types to match.

        Returns:
            ``True`` if a token was consumed.
        """
        if self._check(*token_types):
            self._advance()
            return True
        return False

    def _expect(self, token_type: str, error_message: str) -> Token:
        """Consume a token of the given type or raise a ``ParseError``.

        Args:
            token_type: Expected token type.
            error_message: Human‑readable description for the error.

        Returns:
            The consumed token.

        Raises:
            ParseError: When the current token is not of the expected type.
        """
        if self._check(token_type):
            return self._advance()
        raise ParseError(error_message, self._peek())

    def _error(self, message: str) -> None:
        """Raise a ``ParseError`` at the current token position.

        Args:
            message: Error description.
        """
        raise ParseError(message, self._peek())

    # ------------------------------------------------------------------
    # Statement parsing
    # ------------------------------------------------------------------
    def _statement(self):
        """Parse a single statement.

        Returns:
            An AST statement node.
        """
        if self._check("LET", "CONST"):
            return self._variable_declaration()
        if self._check("FUNCTION"):
            return self._function_declaration()
        if self._check("IF"):
            return self._if_statement()
        if self._check("FOR"):
            return self._for_statement()
        if self._check("WHILE"):
            return self._while_statement()
        if self._check("RETURN"):
            return self._return_statement()
        if self._check("LBRACE"):
            return self._block_statement()
        # Must be an expression statement
        return self._expression_statement()

    def _expression_statement(self) -> ExpressionStatement:
        """Parse an expression followed by a semicolon.

        Returns:
            An ``ExpressionStatement`` node.
        """
        expr = self._expression()
        self._expect("SEMICOLON", "Expected ';' after expression.")
        return ExpressionStatement(expression=expr)

    def _block_statement(self) -> BlockStatement:
        """Parse a block ``{ ... }``.

        Returns:
            A ``BlockStatement`` node containing the list of inner statements.
        """
        self._expect("LBRACE", "Expected '{'.")
        statements: List = []
        while not self._check("RBRACE") and not self._check("EOF"):
            statements.append(self._statement())
        self._expect("RBRACE", "Expected '}' after block.")
        return BlockStatement(body=statements)

    def _variable_declaration(
        self, consume_semicolon: bool = True
    ) -> VariableDeclaration:
        """Parse a ``let`` or ``const`` variable declaration.

        Args:
            consume_semicolon: When ``False``, the trailing semicolon is not
                consumed (used inside ``for`` initialisation).

        Returns:
            A ``VariableDeclaration`` node.
        """
        kind_token = self._advance()  # LET or CONST
        kind = kind_token.type.lower()  # 'let' or 'const'
        declarations: list[VariableDeclarator] = []

        # ── Helper to parse one declarator ──
        def _parse_declarator() -> VariableDeclarator:
            name_token = self._expect("IDENTIFIER", "Expected variable name.")
            init_expr = None
            
            if self._match("ASSIGN"):          
                # FIX: Call _assignment() or your equivalent assignment/ternary/binary 
                # value parser instead of the top-level _expression(). This prevents 
                # the parser from getting confused by trailing tokens or commas.
                init_expr = self._assignment() 
                
            return VariableDeclarator(
                id=Identifier(name_token.value), init=init_expr
            )

        # First declarator
        declarations.append(_parse_declarator())

        # Subsequent declarators separated by ','
        while self._match("COMMA"):
            declarations.append(_parse_declarator())

        if consume_semicolon:
            self._expect("SEMICOLON", "Expected ';' after variable declaration.")
        return VariableDeclaration(kind=kind, declarations=declarations)

    def _function_declaration(self) -> FunctionDeclaration:
        """Parse a function declaration.

        Returns:
            A ``FunctionDeclaration`` node.
        """
        self._expect("FUNCTION", "Expected 'function'.")
        name_token = self._expect("IDENTIFIER", "Expected function name.")
        name = name_token.value

        self._expect("LPAREN", "Expected '(' after function name.")
        params: List[Identifier] = []
        if not self._check("RPAREN"):
            # At least one parameter
            param = self._expect("IDENTIFIER", "Expected parameter name.")
            params.append(Identifier(param.value))
            while self._match("COMMA"):
                param = self._expect("IDENTIFIER", "Expected parameter name after ','.")
                params.append(Identifier(param.value))
        self._expect("RPAREN", "Expected ')' after parameters.")

        body = self._block_statement()  # expects '{' on its own
        return FunctionDeclaration(id=Identifier(name), params=params, body=body)

    def _if_statement(self) -> IfStatement:
        """Parse an ``if`` / ``else`` statement.

        Returns:
            An ``IfStatement`` node.
        """
        self._expect("IF", "Expected 'if'.")
        self._expect("LPAREN", "Expected '(' after 'if'.")
        test = self._expression()
        self._expect("RPAREN", "Expected ')' after condition.")
        consequent = self._statement()
        alternate = None
        if self._match("ELSE"):
            alternate = self._statement()
        return IfStatement(test=test, consequent=consequent, alternate=alternate)

    def _for_statement(self) -> ForStatement:
        """Parse a ``for`` loop.

        Returns:
            A ``ForStatement`` node.
        """
        self._expect("FOR", "Expected 'for'.")
        self._expect("LPAREN", "Expected '(' after 'for'.")

        # Init
        init = None
        if self._check("LET", "CONST"):
            init = self._variable_declaration(consume_semicolon=False)
        elif not self._check("SEMICOLON"):
            init = self._expression()
        self._expect("SEMICOLON", "Expected ';' after loop initialiser.")

        # Test
        test = None
        if not self._check("SEMICOLON"):
            test = self._expression()
        self._expect("SEMICOLON", "Expected ';' after loop condition.")

        # Update
        update = None
        if not self._check("RPAREN"):
            update = self._expression()
        self._expect("RPAREN", "Expected ')' after for clauses.")

        body = self._statement()
        return ForStatement(init=init, test=test, update=update, body=body)

    def _while_statement(self) -> WhileStatement:
        """Parse a ``while`` loop.

        Returns:
            A ``WhileStatement`` node.
        """
        self._expect("WHILE", "Expected 'while'.")
        self._expect("LPAREN", "Expected '(' after 'while'.")
        test = self._expression()
        self._expect("RPAREN", "Expected ')' after condition.")
        body = self._statement()
        return WhileStatement(test=test, body=body)

    def _return_statement(self) -> ReturnStatement:
        """Parse a ``return`` statement.

        Returns:
            A ``ReturnStatement`` node.
        """
        self._expect("RETURN", "Expected 'return'.")
        value = None
        # No expression if followed by ';', '}', or EOF
        if not self._check("SEMICOLON", "RBRACE", "EOF"):
            value = self._expression()
        self._expect("SEMICOLON", "Expected ';' after return.")
        return ReturnStatement(argument=value)

    # ------------------------------------------------------------------
    # Expression parsing (operator precedence)
    # ------------------------------------------------------------------
    def _expression(self):
        """Parse any expression (lowest precedence: assignment)."""
        return self._assignment()

    def _assignment(self):
        """Parse an assignment expression (right‑associative)."""
        left = self._logical_or()
        if self._check(
            "ASSIGN",
            "PLUS_ASSIGN",
            "MINUS_ASSIGN",
            "MULTIPLY_ASSIGN",
            "DIVIDE_ASSIGN",
            "MOD_ASSIGN",
        ):
            op_token = self._advance()
            operator = op_token.type
            # Right‑associative: the right side is another assignment
            right = self._assignment()
            return AssignmentExpression(operator=operator, left=left, right=right)
        return left

    def _logical_or(self):
        """Parse logical OR (``||``), left‑associative."""
        left = self._logical_and()
        while self._match("LOGICAL_OR"):
            operator = "||"
            right = self._logical_and()
            left = BinaryExpression(operator=operator, left=left, right=right)
        return left

    def _logical_and(self):
        """Parse logical AND (``&&``), left‑associative."""
        left = self._equality()
        while self._match("LOGICAL_AND"):
            operator = "&&"
            right = self._equality()
            left = BinaryExpression(operator=operator, left=left, right=right)
        return left

    def _equality(self):
        """Parse equality comparisons (``==``, ``===``, ``!=``, ``!==``)."""
        left = self._relational()
        while self._match("EQUALS", "STRICT_EQUALS", "NOT_EQUALS", "STRICT_NOT_EQUALS"):
            operator = self._previous().type  # e.g. 'EQUALS' -> '=='
            # Map token type to operator string
            op_map = {
                "EQUALS": "==",
                "STRICT_EQUALS": "===",
                "NOT_EQUALS": "!=",
                "STRICT_NOT_EQUALS": "!==",
            }
            operator_str = op_map.get(operator, operator)
            right = self._relational()
            left = BinaryExpression(operator=operator_str, left=left, right=right)
        return left

    def _relational(self):
        """Parse relational comparisons (``<``, ``>``, ``<=``, ``>=``)."""
        left = self._additive()
        while self._match("LESS", "GREATER", "LESS_EQUAL", "GREATER_EQUAL"):
            operator = self._previous().type
            op_map = {
                "LESS": "<",
                "GREATER": ">",
                "LESS_EQUAL": "<=",
                "GREATER_EQUAL": ">=",
            }
            operator_str = op_map[operator]
            right = self._additive()
            left = BinaryExpression(operator=operator_str, left=left, right=right)
        return left

    def _additive(self):
        """Parse additive expressions (``+``, ``-``)."""
        left = self._multiplicative()
        while self._match("PLUS", "MINUS"):
            operator = self._previous().type
            op_map = {"PLUS": "+", "MINUS": "-"}
            operator_str = op_map[operator]
            right = self._multiplicative()
            left = BinaryExpression(operator=operator_str, left=left, right=right)
        return left

    def _multiplicative(self):
        """Parse multiplicative expressions (``*``, ``/``, ``%``)."""
        left = self._unary()
        while self._match("MULTIPLY", "DIVIDE", "MOD"):
            operator = self._previous().type
            op_map = {"MULTIPLY": "*", "DIVIDE": "/", "MOD": "%"}
            operator_str = op_map[operator]
            right = self._unary()
            left = BinaryExpression(operator=operator_str, left=left, right=right)
        return left

    def _unary(self):
        """Parse unary expressions (``!``, ``-``)."""
        if self._check("BANG", "MINUS"):
            op_token = self._advance()
            operator = op_token.type
            op_map = {"BANG": "!", "MINUS": "-"}
            operator_str = op_map[operator]
            right = self._unary()
            return UnaryExpression(operator=operator_str, argument=right)
        return self._postfix()

    def _postfix(self):
        """Parse postfix operations: function calls and member access.

        This handles chains like ``foo.bar[0]()``.
        """
        expr = self._primary()
        while True:
            if self._match("LPAREN"):
                # Function call
                args: List = []
                if not self._check("RPAREN"):
                    args.append(self._expression())
                    while self._match("COMMA"):
                        args.append(self._expression())
                self._expect("RPAREN", "Expected ')' after arguments.")
                expr = CallExpression(callee=expr, arguments=args)
            elif self._match("DOT"):
                # Property access (non‑computed)
                prop_token = self._expect(
                    "IDENTIFIER", "Expected property name after '.'."
                )
                expr = MemberExpression(
                    object=expr, property=Identifier(prop_token.value), computed=False
                )
            elif self._match("LBRACKET"):
                # Computed member access
                prop = self._expression()
                self._expect("RBRACKET", "Expected ']' after computed property.")
                expr = MemberExpression(object=expr, property=prop, computed=True)
            else:
                break
        return expr

    def _primary(self):
        """Parse primary expressions: literals, identifiers, arrays, parentheses.

        Returns:
            AST node.

        Raises:
            ParseError: When no primary expression can be formed.
        """
        if self._match("NUMBER"):
            token = self._previous()
            # Assume NUMBER token value is a string representation of the number
            return Literal(value=float(token.value))
        if self._match("STRING"):
            token = self._previous()
            return Literal(value=token.value)
        if self._match("BOOLEAN"):
            token = self._previous()
            # BOOLEAN tokens have value True or False (boolean)
            return Literal(value=token.value)
        if self._match("NULL"):
            return Literal(value=None)
        if self._match("IDENTIFIER"):
            token = self._previous()
            return Identifier(name=token.value)

        if self._match("LPAREN"):
            expr = self._expression()
            self._expect("RPAREN", "Expected ')' after expression.")
            return expr  # parenthesised expression

        if self._match("LBRACKET"):
            elements: List = []
            if not self._check("RBRACKET"):
                elements.append(self._expression())
                while self._match("COMMA"):
                    # Allow trailing comma
                    if self._check("RBRACKET"):
                        break
                    elements.append(self._expression())
            self._expect("RBRACKET", "Expected ']' after array elements.")
            return ArrayLiteral(elements=elements)

        # Nothing matched -> error
        self._error(
            f"Unexpected token '{self._peek().type}' ({self._peek().value})."
        )
        # Unreachable because _error raises, but keep type checkers happy
        return None  # type: ignore