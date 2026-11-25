# Novaq 1.9.17 local patch (t967) — box copy only

This folder is a patched local copy of Desktop 1.9.17 plus the newer GitHub main `vnext.py` condition fix. Nothing here was pushed to GitHub or written to the Windows PC.

Arabic spellings were not renamed. Natural English aliases from the proposed table (`say`, `ask`, `calc`, `rep`, …) are implemented in this patched copy. `rep` is used for `كرر` because dictionary `كرر` already means Python `iter`. Further calc, dict, file, and try/catch work landed in t1013 (below).

## What changed

1. Commands ignore tashkeel and RTL/bidi marks (`قُول` and `‏قول` run as `قول`). Identifiers may contain shadda (`غيّر_السعر`). `__init__` is a valid method name.
2. Loops have a time/iteration cap. Default is 8 seconds and 1,000,000 iterations. A hanging `طالما صح` or `while True` stops with a clear Arabic error. Set `DAD_MAX_SECONDS=0` and `DAD_MAX_ITERS=0` to disable. You can also lower the cap for tests.
3. `صنف` is no longer typo-corrected to `أضف`/`ضيف`. Arabic classes work, including `__init__`.
4. Natural `إذا` / `طالما` accept function-call conditions such as `إذا طول(الاسم) أصغر من 1` and `طالما طول(السجل) أصغر من 3:`. Bare `طالما صح` works. `لكل` also accepts dotted collections (`لكل س في نفسه.الأصناف`) and parameter names.
5. `قول(س.اسم)` and `قول(س.سطر())` print the attribute/call, not the pieces of the name.
6. Nested `اسأل «...»` inside an expression is rewritten to `_dad_ask(...)`.
7. The leftover number after list/help in the earlier demo was the program printing a function’s return value, not the engine auto-printing it. Confirmed by tests; the new demos do not print that extra number.
8. `examples/money_manager.dad` and `examples/materials_calculator.dad` are present (already at the package root; now also under `examples/` as the GitHub README describes). `vscode/extension/runner.js` was already in the Desktop tree.
9. User-defined methods keep their Arabic names after a dot (`المخزن.ابحث()`, `المخزن.حمل()`), instead of being rewritten to `find`/`load`. Built-in list/file methods such as `.أضف` still translate.
10. The GitHub `parse_cond` fix for comparator words inside a multi-word name is included, with its two tests.

New tests: `current_tests/test_t967_fixes.py` (18 tests, Arabic and English for each fix).

## Test counts (Asia/Kuwait, 25 Nov 2026)

- Before this patch (Desktop 1.9.17 + GitHub `vnext.py`/`test_engine_fixes` only): **1308 collected, 1308 passed**.
- After: **1326 collected, 1326 passed** (the previous 1308 plus 18 new tests). 0 failed.

## Inventory demos without the earlier workarounds

- `/workspace/aldad-review/big-demo/natural/inventory_ar.dad` (303 lines)
- `/workspace/aldad-review/big-demo/natural/inventory_en.dad` (306 lines)

Both ran to the end (exit 0) on the same scenario: 3 items, stock value 43.5, sale 1.5, oversell rejected, save/load of items and the movement log. Arabic used `صنف`, shadda names, `إذا`/`طالما` with `طول(...)`, `قول(س.سطر())`, and nested `اسأل`.

## t1013 — English aliases, calc, dicts, files, try/catch (box copy only)

Nothing here was pushed to GitHub or written to the Windows PC. `/workspace/novaq-perf` was not touched.

1. Natural English commands from the proposal table: `say`, `show`, `ask`, `calc`, `more`, `rep` (not `iter`), `then`, `times`/`twice`, `plus`/`minus`/`mul`/`div`, `gt`/`lt`/`eq`/`ne`/`gte`/`lte`, `def name takes x`, `result`, `save`/`write`, `add`, `read`, `append`, `dict`, `put`, `catch`. Python-layer `if`/`for`/`def`/`class`/`print`/`open`/`while` were left alone so existing programs keep working. `if 10 gt 3 then say "yes"` works when there is no trailing colon (`if x > 3:` stays Python).
2. Dictionaries: `قاموس بيانات` / `dict box`, `ضع «اسم» في بيانات بقيمة «علي»` / `put "name" in box as "Ali"`. `قول بيانات['اسم']` prints the value.
3. Files: `افتح` / `read`, `احفظ` / `write` / `save`, `ألحق` / `append`. Writes go under `DAD_OUT_DIR` in safe mode. The stored file content is the full value (not a rounded display form).
4. Errors: `حاول` / `try`, `عند_خطأ` / `catch`, `عند_نجاح` / `else`, `أخيرا` / `finally`. `عند_خطأ باسم خ` / `catch as err` binds the exception. Division by zero in `احسب`/`calc` is catchable and the message is bilingual: `قسمة على صفر — ما ينفع تقسم على صفر. / Division by zero.`
5. `احسب`/`calc` can call user functions and built-ins (`ضعف(5)`, `طول([1,2,3])`, `abs(-7)`). The stored `الناتج` keeps full precision; display is rounded to at most 6 decimals with trailing zeros trimmed (`1/3` prints `0.333333`, `الناتج * 3` prints `1`).
6. `احفظ ضعف(5) في القيمة` stores `10`, not the text. `احفظ صح في العلم` stores a boolean. A variable named `نصف` is not overwritten by the fraction `0.5`. `العرض = 7` is no longer typo-corrected to `اعرض`.

New tests: `current_tests/test_english_aliases.py` (26) and `current_tests/test_novaq_t1013.py` (20). One assertion in `test_generated_1_9_15.py` now compares printed text with `_dad_fmt(الناتج)` so display rounding is not required to match the stored full float.

## Test counts after t1013 (Asia/Kuwait, 25 Nov 2026)

- After t967: **1326 passed**.
- After English aliases + t1013: **1372 collected, 1372 passed** (1326 + 26 alias tests + 20 t1013 tests). 0 failed.
- dad2cpp (patched engine as `ALDAD_SRC`): **12/15** matched. Unchanged gaps: `_dad_write` and `_dad_svg` not supported in C++. New mismatch: `t4_more` (Python now keeps full `احسب` precision so `1/3 * 3` prints `1`; the experimental C++ path still uses rounded intermediate values).
- Shop apps and the satellite numeric checker were re-run on this tree (see results).

## t1018 — speedups, f-strings, 1-based slicing (patched copy only)

### Speedup P1: lower static calc/return to Python
`احسب` / `calc` and `يرجع` / `return` expressions that are known at transpile time are now emitted as real Python (inlined, not `_dad_evaluate` on a string). Errors (`ZeroDivisionError`, overflow, unknown name, complex results) are still turned into the same catchable Arabic `DadError` / `DadZeroDivisionError` messages. Interactive `احسب` with text typed at runtime still goes through `evaluate()`. Full numeric precision is stored; display is still at most 6 decimals.

### Speedup P2: cheap `_dad_tick`
Loop/time limits are read once in `_dad_reset_limits()` (called from `compile_user_code`). `_dad_tick` does not reimport modules or reread the environment. The iteration cap is checked every loop; the clock is sampled on the first tick and every 1024 iterations. Defaults remain 8 seconds and 1,000,000 iterations. Both set to 0 still disable the cap.

### Easy f-strings
`قول «مرحبا {الاسم}»` and `say "hello {name}"` interpolate variables and expressions (including Arabic operators such as `{س ضرب 2}`). `{{` / `}}` stay literal braces.

### Easy slicing — 1-based inclusive
`قطعة القائمة من 1 إلى 3` / `slice list from 1 to 3` means the first, second and third items, the same as Python `list[0:3]`.

- Index **1** is the first item (beginner-friendly; not Python's 0).
- Both ends are **included**.
- `قطعة القائمة من 3` / `slice list from 3` (no end) runs to the end of the sequence.
- **0 or a negative index is an error**, with a bilingual message.
- Mid-line Python `slice(1, 3)` is not rewritten; it stays the builtin (0-based, end exclusive).
