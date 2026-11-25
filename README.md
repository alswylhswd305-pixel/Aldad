# Novaq (نوفاك)

**Novaq** is a simple programming language for beginners. You write clear commands in Arabic or English, and the program does what the words say.

The older name was **Aldad** / **الضاد**. The language is the same; the official name is now Novaq / نوفاك. File extensions (`.dad`) and internal module names are unchanged.

Current version: **1.9.17 Preview**. It is usable and tested, but it is not a claim that the language is finished or free of gaps.

Novaq runs offline. The core language does not use the internet or an AI model.

## What it looks like

Arabic:

```dad
اسأل شنو اسمك واحفظه في الاسم
قول «أهلا {اسمك}»
احسب 5 زائد 3 و قول الناتج
```

English:

```dad
ask what is your name and save it in name
say "hello {name}"
calc 5 plus 3 and say result
```

Other everyday forms that work:

```dad
قول كم الساعة
شنو التاريخ
احسب كم جرام في 2 كيلو
قول اكل ثم نام
say hi then say bye
```

- `قول` / `say` prints text.
- `اسأل` / `ask` asks you a question and stores the answer.
- `احسب` / `calc` calculates and stores the value in `الناتج` / `result`. It does not print by itself; use `قول الناتج` or `say result`.
- `و` / `ثم` / `and` / `then` link two clear commands. If `then` is only part of the sentence (`قول اكل ثم نام`), it stays text.
- `كم الساعة` and `what's the date` show the current time or date; they are not questions to you.
- Unclear input gets a clear Arabic error with a copyable suggestion. The language does not guess.

The beginner reference is [`rules_ar.md`](rules_ar.md) (Arabic) and [`rules_en.md`](rules_en.md) (English). The IDE also has a click-to-run **Beginner guide** / **دليل المبتدئ**.

## Run a program from source

You need Python 3.9 or later.

```bash
python dad.py شغل program.dad
python dad.py run program.dad
```

Both forms do the same thing. If the program asks a question, type the answer and press Enter.

Examples:

```bash
python dad.py شغل example.dad
python dad.py run examples/receipt.dad
```

To open the local IDE (browser on this computer only, `127.0.0.1`):

```bash
python aldad_ide.py
```

On Windows you can also start the IDE with `START_ALDAD.cmd` (the file name is historical; it launches Novaq).

## Run the Windows EXE

A ready Windows build does not need Python installed:

- `Novaq_1.9.17_Windows.exe` — console runner
- `Novaq_IDE_1.9.17_Windows.exe` — local IDE

Run a file:

```bat
Novaq_1.9.17_Windows.exe samples\ar_smoke.dad
Novaq_1.9.17_Windows.exe samples\en_smoke.dad
```

If the program asks a question, type the answer, or pipe a file:

```bat
Novaq_1.9.17_Windows.exe samples\ar_smoke.dad < samples\answers_ar.txt
```

Open an interactive prompt (no file name):

```bat
Novaq_1.9.17_Windows.exe
```

Type a command such as `قول «هلا»` or `say "hello"`, then Enter. Type `exit` or `خروج` to leave.

The IDE exe stays on this computer only. Work files are saved in a `work` folder next to the exe, not in Documents.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest current_tests
```

## License

MIT License — Copyright © 2026 Saud.
