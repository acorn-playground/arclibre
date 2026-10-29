# ArcLibre !Calc

Acorn's RISC OS 3.11 `!Calc` was never published, so `src/ArcCalc` is new
Apache-2.0 ArcLibre code, documented as a replacement. Its appearance and
behaviour follow the RISC OS 3 User Guide (3.10, Applications Guide ch.6,
"Calculator"), the RISC OS 2 A3000 guide, and measured 3.11 screenshots. No
Acorn code, templates or artwork are used; the icon is the `!calc` sprite of
the pinned Wimp sprite set.

- Window "Calculator", 278 × 312 OS units, Back and Close only, fixed size,
  white work area. The display is right-justified black text, unboxed.
- A red C key with a cream legend and border beside the display, then a 4 × 4
  keypad: grey digit keys, a light-grey `.`, and cream `÷ x - +` and `=`.
- Four functions with immediate execution, nine displayed digits. Division by
  zero (or a result of a thousand million or more) shows `Error` until C.
- Keyboard and keypad digits and operators, Return/Enter for `=`, Delete for C.
- Icon-bar icon on the right; its menu has Info and Quit. The Info wording is
  not documented anywhere, so it honestly names ArcLibre.

`bas/Calc` is BBC BASIC text. `tools/build_calc.py` tokenises it with the ROM's
own BASIC 1.14 (`TEXTLOAD`, `SAVE` at the real F12 prompt, twice, identical),
numbers the leading licence REM lines 0, compacts it with the ArcLibre squish
tool (5,904 → 4,418 bytes, licence kept) and builds the ResourceFS block of
the new `!Calc` wrapper module (`s/ArcCalc`, 4,952 bytes in all). It is
registered as `Resources:$.Apps.!Calc`.

The gate (in `tests/run_basic_utilities.py`) launches it from the Filer,
checks the window furniture and key colours, 12+3=15 by clicking, 7×6=42 by
keyboard, chained 2+3×4=20, 9÷0 → Error ignoring digits until C, Delete, and
Quit. Not modelled: percentages, memory and square root (the original had
none), and the unknown exact digit count and overflow behaviour of 3.11.
