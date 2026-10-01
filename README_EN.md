# Aldad — الضاد

**Aldad** is an experimental Arabic-first programming language focused on simple, natural commands for beginners. Version **1.9.17 Preview** prioritizes predictable rules, Arabic error messages, and explicit behavior instead of guessing user intent.

## Example

```dad
اسأل كم العدد ثم احسب العدد ضرب 2 ثم قول الناتج
```

Core principles:

- One clear meaning per language keyword whenever possible.
- `ثم` executes left-to-right.
- Ambiguous input is rejected with a clear Arabic error instead of being guessed.
- The core runtime works offline and does not require an AI model.
- Backward compatibility is preserved unless an older rule is incorrect or contradictory.

## Run

Windows: install Python 3.9+ and run `START_ALDAD.cmd`.

Linux/macOS:

```bash
python3 aldad_ide.py
```

Run an example directly:

```bash
python3 dad.py run examples/receipt.dad
```

## Tests

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest current_tests
python3 verify_all.py --label local
```

The repository includes CI for Windows and Linux. Version 1.9.17 is published as a Preview rather than Stable until full Windows validation is completed.

## License

MIT License — Copyright © 2026 Saud.
