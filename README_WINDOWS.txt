ALDAD 1.9.17 — Windows

1) Extract the whole ZIP before running anything.
2) Install Python 3.9 or newer if needed.
3) Run START_ALDAD.cmd; use REPAIR_ALDAD.cmd for startup diagnosis.
4) The IDE opens in the browser. Programs use .dad or .ضاد.
5) To run a program directly: py -3 dad.py run examples/receipt.dad
6) Install Aldad_VSCode_1.9.17.vsix using VS Code > Install from VSIX.

This delivery contains tested Python sources and a VSIX, not a prebuilt Windows EXE.
BUILD_ALDAD_IDE_EXE.cmd is retained and updated for the new modules. It requires
Windows and PyInstaller. No Windows EXE build or Windows GUI run was performed
in this Linux verification environment. See the Arabic release report.

Language execution, known-shape SVG drawing and normal HTML apps need no model
or internet. The optional editor writing assistant is separate.
