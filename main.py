# js_runtime\main.py

"""
Entry point for the JavaScript runtime.

Reads JavaScript source code from a file or stdin, then executes the full
pipeline: tokenization, parsing, registration of built‑ins, interpretation,
and finally prints the captured console output to stdout.
"""

import sys
from runtime.tokenizer import Tokenizer
from runtime.parser import Parser, ParseError
from runtime.environment import Environment
from runtime.builtins import Builtins, get_console_output
from runtime.interpreter import Interpreter

def execute_javascript(source: str) -> str:
    """
    Execute JavaScript source code and return the captured console output.

    The function runs the full pipeline: tokenizing, parsing, registering
    built‑ins, interpreting, and finally returning the console output as a
    string.

    Exceptions (ParseError, runtime errors, etc.) are allowed to propagate
    so that tests can inspect the traceback.
    """

    tokenizer = Tokenizer(source)
    tokens = tokenizer.tokenize()
    parser = Parser(tokens)
    program = parser.parse()
    global_env = Environment()
    Builtins.register(global_env)
    interpreter = Interpreter(global_env)
    interpreter.interpret(program)
    return get_console_output()

def main() -> None:
    """
    Parse command‑line arguments, execute the JS code, and handle errors.

    If a filename is provided as the first argument, its contents are read.
    If the file does not exist, an error is printed to stderr and the process
    exits with code 1.  When no argument is given, code is read from stdin.
    """

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                code = f.read()
        except FileNotFoundError:
            print(f"Error: file '{filepath}' not found.", file=sys.stderr)
            sys.exit(1)
    else:
        code = sys.stdin.read()

    try:
        output = execute_javascript(code)
        if output:
            sys.stdout.write(output)
    except ParseError as e:
        print(f"Parse error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Runtime error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()