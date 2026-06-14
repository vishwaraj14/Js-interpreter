[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](#)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#)
[![Tests](https://img.shields.io/badge/Tests-100%25_passing-lightgrey.svg)](#)
[![Code Style](https://img.shields.io/badge/Code%20Style-black%20%2F%20flake8-000000.svg)](#)

---

# JS Runtime in Python

A lightweight JavaScript interpreter written entirely in Python. Execute .js files or inline code from the command line.

---

## Features

- Accepts JavaScript code via file, stdin, or command-line argument
- Supports variables (`let`, `const`), operators, control flow, loops, functions, arrays, strings, and more
- Built-in console, Math, Date, Array, and String methods
- Recursive-descent parser and tree-walking interpreter
- Full scope and environment handling
- Detailed error reporting with line/column information

---

## Workflow

```mermaid
flowchart TD
    A[Input<br/>File / Stdin / CLI Argument] --> B[Tokenizer<br/>Lexer]
    B --> C[Parser<br/>AST]
    C --> D[Interpreter<br/>Environment & Built-ins]
    D --> E[Output<br/>stdout]

    B --> F[Tokenizer Error<br/>line / column]
    C --> G[Parse Error<br/>line / column]
    D --> H[Runtime Error<br/>line / column]

    F --> I[Exit Non-Zero]
    G --> I
    H --> I

    style A fill:#f8f9fa,stroke:#6c757d,stroke-width:1px
    style B fill:#f8f9fa,stroke:#6c757d,stroke-width:1px
    style C fill:#f8f9fa,stroke:#6c757d,stroke-width:1px
    style D fill:#f8f9fa,stroke:#6c757d,stroke-width:1px
    style E fill:#f8f9fa,stroke:#6c757d,stroke-width:1px
    style F fill:#fff3cd,stroke:#856404,stroke-width:1px
    style G fill:#fff3cd,stroke:#856404,stroke-width:1px
    style H fill:#fff3cd,stroke:#856404,stroke-width:1px
    style I fill:#f8d7da,stroke:#721c24,stroke-width:1px
```

---

## Command-Line Usage

`main.py` reads the JavaScript source from `sys.argv` and supports both file input and piped stdin. The program prints captured console output to stdout and exits with `0` on success or a non-zero status on error.

### From a file

```bash
python main.py sample.js
```

### From stdin

```bash
echo "let x = 5; console.log(x * 2);" | python main.py
```

Direct inline argument support is not shown here because the current CLI is documented around file and pipe input modes.

---

## Installation & Setup

1. Clone the repository.
2. Ensure Python 3.10 or later is installed.
3. No dependencies need to be installed because `requirements.txt` is empty.
4. Run the runtime directly:

```bash
python main.py <file>
```

---

## Testing

Tests are located in `tests/test_runtime.py`. To run them:

```bash
python -m pytest tests/
```

Pytest is assumed to be available for test execution, but the runtime itself has no external dependencies.

---

## License

This project is distributed under the MIT License. See [LICENSE.md](LICENSE.md) for the full text.

---

## Author & Contributions

Author: @Kennny7 | Khushal Pareta

Contributions are welcome.
