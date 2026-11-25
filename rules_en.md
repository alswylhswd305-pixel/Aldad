# Novaq 1.9.17 rules

Novaq is a simple language: write a clear command, and the value stays clear. Execution is deterministic, with no internet and no AI.
The older name was «الضاد» / Aldad; the commands and their meaning are the same.

| Word | Meaning | Example |
|---|---|---|
| say / قول | Show text on the screen | `say "hi"` · `قول «هلا»` |
| ask / اسأل | Ask for an answer at run time | `ask what is your name` · `اسأل شنو اسمك` |
| كم | Asks you for a number | `اسأل كم العدد` |
| what time is it / كم الساعة | Current time, not a question | `say what time is it` → like 17:05 |
| what's the date / شنو التاريخ | Today's date | `what's the date` → like 2026/11/25 |
| calc / احسب | Calculate; the result is in `result` / `الناتج` | `calc 5 plus 3 times 2` → 11 |
| more / كمل | Continue the last answer or calculation | `كمل ناقص 4` |
| then / and / ثم / و / بعدين | Link two clear commands | `calc 5 plus 3 and say result` |
| if / else / إذا / وإلا | A condition and its alternative | see the lesson below |
| rep / كرر | Repeat | `rep 3 times` |
| draw / ارسم | Draw a shape on the screen | `draw a red circle` · `ارسم دائرة حمراء` |
| save / احفظ | Save a value in a name or a file | `save result in total` |
| add / أضف | Add to a list | `add "apple" to basket` |

## Asking, saving, and greeting by name

```dad
ask what is your name and save it in name
say hello (name)
say "hello {name}"
```

- `ask what is your name and save it in name` stores the answer in `name`, and the prompt stays short: «what is your name?».
- The short form `ask what is your name` also stores the answer in `name`.
- After the question, greet in any of these ways: `say hello name`, `say hello (name)`, or `say "hello {name}"`.
- In Arabic: `اسأل شنو اسمك واحفظه في الاسم` then `قول اهلا (الاسم)` or `قول «أهلا {اسمك}»`.
- `كم` asks for a number. A text question such as `what is your name` accepts text.

## Linking commands: then, and

`then` runs commands in order. If the second command is clear, `and` works the same way (in Arabic also `و` or `بعدين`):

```dad
say "hi" then say "hello"
calc 5 plus 3 and say result
```

Ordinary text is not split: `say apples and oranges` stays one sentence. If `then` is inside speech and the next words are not a command, it stays text: `say eat then sleep` prints «eat then sleep». Quoted text is also safe: `say "eat then sleep"`. If one command in a chain fails, the rest stops.

## Calculation, parentheses, and text

- Multiplication and division come before addition and subtraction. `calc 5 plus 3 times 2` gives 11. `calc (5 plus 3) times 2` gives 16.
- `calc` alone asks «what should I calculate?». `calc` does not print by itself; use `say result`.
- `more` / `كمل` builds on the last successful question or calculation. `say` does not change that value.
- Text goes in `" "` or `«»`. Parentheses group values: `say(result)` and `say (result)` mean the same. To show the word literally: `say "result"`.
- Text with a value: `say "hello {name}"` or `قول «أهلا {اسمك}»`.
- Compound names work, and may include a number after a word, such as `sale price 1`.
- Comparisons: `greater than` / `gt`, `less than` / `lt`, `greater than or equal` / `gte`, `less than or equal` / `lte`.

With the answer 22:

```dad
ask how many is the number
say "I will finish the rest"
كمل ناقص 4
say result
say number
```

The result is 18, and `number` stays 22.

## Time, unit conversion, and كم in calculations

- `say what time is it` or `كم الساعة` shows the current time (like 17:05). `what's the date` or `شنو التاريخ` shows today's date. These are not questions waiting for your answer.
- `ask how many eggs` or `اسأل كم العدد` stay questions, because they ask *you*.
- Conversion: `calc how many grams in 2 kilos` → 2000. The same works for meter/kilometer/cm, minute/hour/second, and day/week. In Arabic: `احسب كم جرام في 2 كيلو`.
- If `كم` is followed by a clear calculation, it is calculated: `كم 4 زائد 5 احسب` → 9.

## Slicing

Numbering starts at 1, and both ends are included:

```dad
save [10, 20, 30, 40, 50] in items
say slice items from 1 to 3
```

gives `[10, 20, 30]`. In Arabic: `قول قطعة القائمة من 1 إلى 3`.

## Conditions, loops, and drawing

Lines inside a condition or a loop are indented (spaces or a tab). A bare English `else` works; `else:` is also fine.

```dad
ask how many years
if years gt 18
    say "you are an adult"
else
    say "you are young"
rep 2 times
    say "hi"
draw a red circle and a blue square
```

Simple shapes: circle, square, rectangle, triangle, line — with an Arabic or English color (`red` / `حمراء`, `in green`). Well-known scenes such as a house, a tree, or a ship also work. An unknown description raises a clear error; the language does not guess.

## Files and reserved names

```dad
calc 5 plus 3
save result in order total
save result in file result.txt
open result.txt
say content
```

After saving to a file you may see a line `✓ انحفظ في …`. `content` / `المحتوى` holds the last opened file.

Reserved names you cannot use as variables: `result`, `الناتج`, `content`, `المحتوى`, `كم`, `then`, `ثم`, and command names. Ambiguity raises an error with a copyable suggestion; the language does not guess and run.
