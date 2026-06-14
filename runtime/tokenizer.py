# js_runtime\runtime\tokenizer.py

"""
runtime/tokenizer.py – Lexical analysis for a JavaScript subset.

This module defines the `Token` dataclass and the `Tokenizer` class,
which breaks a JavaScript source string into a flat list of tokens.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, List, Set

@dataclass
class Token:
    """A single token produced by the lexer.

    Attributes:
        type: The category of the token (e.g. ``'NUMBER'``, ``'IDENTIFIER'``,
            ``'+'``, ``'LET'``).
        value: The associated value (string for keywords/identifiers/strings,
            numeric for numbers, operator/punctuation string otherwise).
        line: 1‑based line number where the token starts.
        column: 1‑based column number where the token starts.
    """
    type: str
    value: Any
    line: int
    column: int

# ------------------------------------------------------------------
# OPERATORS
# ------------------------------------------------------------------

OPERATOR_TYPE_MAP = {
    # assignment
    "=": "ASSIGN",
    "+=": "PLUS_ASSIGN",
    "-=": "MINUS_ASSIGN",
    "*=": "MULTIPLY_ASSIGN",
    "/=": "DIVIDE_ASSIGN",
    "%=": "MOD_ASSIGN",
    "**=": "POWER_ASSIGN",  # if you support **=
    # comparison
    "==": "EQUALS",
    "===": "STRICT_EQUALS",
    "!=": "NOT_EQUALS",
    "!==": "STRICT_NOT_EQUALS",
    "<": "LESS",
    ">": "GREATER",
    "<=": "LESS_EQUAL",
    ">=": "GREATER_EQUAL",
    # logical
    "&&": "LOGICAL_AND",
    "||": "LOGICAL_OR",
    "!": "BANG",
    # arithmetic
    "+": "PLUS",
    "-": "MINUS",
    "*": "MULTIPLY",
    "/": "DIVIDE",
    "%": "MOD",
    "**": "POWER",  # if you use it
}

# ------------------------------------------------------------------
# PUNCTUATION
# ------------------------------------------------------------------

PUNCTUATION_TYPE_MAP = {
    ";": "SEMICOLON",
    "(": "LPAREN",
    ")": "RPAREN",
    "{": "LBRACE",
    "}": "RBRACE",
    "[": "LBRACKET",
    "]": "RBRACKET",
    ",": "COMMA",
    ".": "DOT",
}

class Tokenizer:
    """Lexical analyser (tokenizer) for a subset of JavaScript.

    The tokenizer handles:
    * Keywords: ``let``, ``const``, ``if``, ``else``, ``for``, ``while``,
      ``function``, ``return``, ``true``, ``false``, ``null``, ``undefined``.
    * Identifiers: ``[a-zA-Z_$][a-zA-Z0-9_$]*``
    * Numeric literals (integers and floats, including negative numbers when
      the minus sign is unary).
    * String literals (single- or double‑quoted, supporting escapes ``\\\\``,
      ``\\'``, ``\\"``).
    * Operators: ``+``, ``-``, ``*``, ``/``, ``%``, ``**``, ``=``, ``==``,
      ``===``, ``!=``, ``!==``, ``<``, ``>``, ``<=``, ``>=``, ``&&``, ``||``,
      ``!``, ``+=``, ``-=``, ``*=``, ``/=``, ``%=``, ``**=``.
    * Punctuation: ``;``, ``(``, ``)``, ``{``, ``}``, ``[``, ``]``, ``,``, ``.``.
    * Comments: ``// ...`` and ``/* ... */`` (skipped).
    * Whitespace (spaces, tabs, newlines) is skipped, but line/column counters
      are updated.

    Usage::

        source = 'let x = 42;'
        tokenizer = Tokenizer(source)
        tokens = tokenizer.tokenize()
        for t in tokens:
            print(t)
    """

    # ------------------------------------------------------------------
    # Keyword set and mapping to token types
    # ------------------------------------------------------------------
    KEYWORDS: Set[str] = {
        "let",
        "const",
        "if",
        "else",
        "for",
        "while",
        "function",
        "return",
        "true",
        "false",
        "null",
        "undefined",
    }

    KEYWORD_TO_TYPE: dict[str, str] = {
        "let": "LET",
        "const": "CONST",
        "if": "IF",
        "else": "ELSE",
        "for": "FOR",
        "while": "WHILE",
        "function": "FUNCTION",
        "return": "RETURN",
        "true": "BOOLEAN",
        "false": "BOOLEAN",
        "null": "NULL",
        "undefined": "UNDEFINED",
    }

    # ------------------------------------------------------------------
    # Operators (longest first to ensure greedy matching)
    # ------------------------------------------------------------------
    OPERATORS: List[str] = [
        "===", "!==", "**", "==", "!=", "<=", ">=",
        "&&", "||", "+=", "-=", "*=", "/=", "%=", "**=",
        "+", "-", "*", "/", "%", "=", "<", ">", "!",
    ]


    # Token types that cannot be immediately followed by a unary minus
    # (the minus would be interpreted as the binary subtraction operator).
    _UNARY_MINUS_DISALLOWED_AFTER: Set[str] = {
        "IDENTIFIER",
        "NUMBER",
        "STRING",
        "BOOLEAN",   
        "NULL",
        "UNDEFINED",
        "RPAREN",    
        "RBRACKET",  
        "RBRACE",    
    }

    # ------------------------------------------------------------------
    # Regular expressions for numbers and identifiers
    # ------------------------------------------------------------------
    _ID_PATTERN: re.Pattern = re.compile(r"[a-zA-Z_$][a-zA-Z0-9_$]*")
    _NUMBER_PATTERN: re.Pattern = re.compile(r"\d+(\.\d+)?([eE][+-]?\d+)?")
    _DOT_NUMBER_PATTERN: re.Pattern = re.compile(r"\.\d+([eE][+-]?\d+)?")

    # ------------------------------------------------------------------
    def __init__(self, source: str) -> None:
        """Initialise the tokenizer with JavaScript source code.

        Args:
            source: The JavaScript program as a single string.
        """
        self.source: str = source
        self.pos: int = 0
        self.line: int = 1
        self.column: int = 1
        self.tokens: List[Token] = []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def tokenize(self) -> List[Token]:
        """Break the source into a flat list of tokens.

        Returns:
            A list of :class:`Token` objects in the order they appear.

        Raises:
            SyntaxError: If an unexpected character or unterminated
                string/comment is encountered.
        """
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []

        while self.pos < len(self.source):
            self._skip_whitespace_and_comments()

            if self.pos >= len(self.source):
                break

            # Record position for the new token
            start_line = self.line
            start_col = self.column
            ch = self.source[self.pos]

            # --- Identifier or keyword ---
            if ch.isalpha() or ch == "_" or ch == "$":
                self._lex_identifier_or_keyword(start_line, start_col)
                continue

            # --- Number literal (positive) ---
            if ch.isdigit() or (
                ch == "."
                and self.pos + 1 < len(self.source)
                and self.source[self.pos + 1].isdigit()
            ):
                self._lex_number(start_line, start_col, negative=False)
                continue

            # --- Negative number literal (unary minus context) ---
            if (
                ch == "-"
                and self._is_unary_minus_allowed()
                and self.pos + 1 < len(self.source)
                and (
                    self.source[self.pos + 1].isdigit()
                    or (
                        self.source[self.pos + 1] == "."
                        and self.pos + 2 < len(self.source)
                        and self.source[self.pos + 2].isdigit()
                    )
                )
            ):
                # Consume the minus
                self.pos += 1
                self.column += 1
                self._lex_number(start_line, start_col, negative=True)
                continue

            # --- String literal ---
            if ch in ('"', "'"):
                self._lex_string(start_line, start_col, ch)
                continue

            # --- Operators (longest match) ---
            matched = False
            # for op in self.OPERATORS:
            #     if self.source.startswith(op, self.pos):
            #         self.tokens.append(Token(op, op, start_line, start_col))
            #         self.pos += len(op)
            #         self.column += len(op)
            #         matched = True
            #         break
            for op in self.OPERATORS:
                if self.source.startswith(op, self.pos):
                    token_type = OPERATOR_TYPE_MAP.get(op, op)  # fallback, but all should be mapped
                    self.tokens.append(Token(token_type, op, start_line, start_col))
                    self.pos += len(op)
                    self.column += len(op)
                    matched = True
                    break
            if matched:
                continue

            # --- Punctuation ---

            if ch in PUNCTUATION_TYPE_MAP:
                token_type = PUNCTUATION_TYPE_MAP[ch]
                self.tokens.append(Token(token_type, ch, start_line, start_col))
                self.pos += 1
                self.column += 1
                continue

            # If we get here, the character is not recognised
            raise SyntaxError(
                f"Unexpected character {ch!r} at line {start_line}, column {start_col}"
            )

        # Append EOF token
        self.tokens.append(Token("EOF", "", self.line, self.column))
        return self.tokens

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _skip_whitespace_and_comments(self) -> None:
        """Advance past whitespace and comments, updating line/column."""
        while self.pos < len(self.source):
            ch = self.source[self.pos]

            # Whitespace
            if ch in " \t\r\n":
                if ch == "\n":
                    self.line += 1
                    self.column = 1
                else:
                    self.column += 1
                self.pos += 1
                continue

            # Line comment //
            if (
                ch == "/"
                and self.pos + 1 < len(self.source)
                and self.source[self.pos + 1] == "/"
            ):
                self.pos += 2
                self.column += 2
                while self.pos < len(self.source) and self.source[self.pos] != "\n":
                    self.pos += 1
                    self.column += 1
                # Do not consume the newline itself; it will be handled on the next loop iteration.
                continue

            # Block comment /* ... */
            if (
                ch == "/"
                and self.pos + 1 < len(self.source)
                and self.source[self.pos + 1] == "*"
            ):
                self.pos += 2
                self.column += 2
                while self.pos < len(self.source):
                    if (
                        self.source[self.pos] == "*"
                        and self.pos + 1 < len(self.source)
                        and self.source[self.pos + 1] == "/"
                    ):
                        self.pos += 2
                        self.column += 2
                        break
                    if self.source[self.pos] == "\n":
                        self.line += 1
                        self.column = 1
                    else:
                        self.column += 1
                    self.pos += 1
                else:
                    raise SyntaxError(
                        f"Unterminated block comment starting at line {self.line}"
                    )
                continue

            # Not whitespace or comment – stop skipping
            break

    def _is_unary_minus_allowed(self) -> bool:
        """Return True if a minus at the current position should be treated
        as part of a negative number literal (unary minus)."""
        if not self.tokens:
            return True
        last_type = self.tokens[-1].type
        return last_type not in self._UNARY_MINUS_DISALLOWED_AFTER

    def _lex_identifier_or_keyword(self, line: int, col: int) -> None:
        """Tokenise an identifier or keyword starting at the current position."""
        match = self._ID_PATTERN.match(self.source, self.pos)
        assert match is not None # To avoid pylance error 
        word = match.group()  # guaranteed to match because we checked the first char
        self.pos += len(word)
        self.column += len(word)

        # token_type = self.KEYWORD_TO_TYPE.get(word, "IDENTIFIER")
        # self.tokens.append(Token(token_type, word, line, col))
        token_type = self.KEYWORD_TO_TYPE.get(word, "IDENTIFIER")
        if token_type == "BOOLEAN":
            value = True if word == "true" else False
        elif token_type == "NULL":
            value = None
        else:
            value = word
        self.tokens.append(Token(token_type, value, line, col))

    def _lex_number(self, line: int, col: int, *, negative: bool) -> None:
        """Tokenise a numeric literal (possibly negative)."""
        if self.source[self.pos] == ".":
            pattern = self._DOT_NUMBER_PATTERN
        else:
            pattern = self._NUMBER_PATTERN

        match = pattern.match(self.source, self.pos)
        assert match is not None # To avoid pylance error; we checked the first char before calling this method 
        num_str = match.group()
        self.pos += len(num_str)
        self.column += len(num_str)

        if negative:
            full_str = "-" + num_str
        else:
            full_str = num_str

        # Determine Python numeric type
        if "." in full_str or "e" in full_str.lower():
            value: int | float = float(full_str)
        else:
            value = int(full_str)

        self.tokens.append(Token("NUMBER", value, line, col))

    def _lex_string(self, line: int, col: int, quote: str) -> None:
        """Tokenise a string literal delimited by *quote* (``'`` or ``"``)."""
        # Consume opening quote
        self.pos += 1
        self.column += 1

        chars: List[str] = []
        while self.pos < len(self.source):
            c = self.source[self.pos]

            if c == "\\":
                # Escape sequence
                if self.pos + 1 >= len(self.source):
                    raise SyntaxError("Unexpected end of input in string literal")
                next_c = self.source[self.pos + 1]
                if next_c in ("\\", "'", '"'):
                    chars.append(next_c)
                    self.pos += 2
                    self.column += 2
                else:
                    # According to the spec no other escapes are needed,
                    # but we treat any other backslash as literal backslash
                    # followed by the next character.
                    chars.append("\\")
                    chars.append(next_c)
                    self.pos += 2
                    self.column += 2
                continue

            if c == quote:
                # Closing quote
                self.pos += 1
                self.column += 1
                break

            if c == "\n":
                raise SyntaxError("Unterminated string literal (newline inside string)")

            # Regular character
            chars.append(c)
            self.pos += 1
            self.column += 1
        else:
            raise SyntaxError("Unterminated string literal")

        self.tokens.append(Token("STRING", "".join(chars), line, col))