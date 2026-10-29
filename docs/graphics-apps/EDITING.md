# Original application editing and interchange

This milestone extends the earlier basic save/reopen gate. It exercises the
original Draw, Paint and Edit implementations through real mouse and keyboard
input, with no injected guest code or emulator changes. It retains the
unmodified RISC OS 3.11 application-compatibility target.

## Workflows

- **Draw:** create a rectangle and text, undo and redo the text, choose the real
  Corpus.Bold outline font, group and ungroup the objects, scale their width,
  insert a sprite saved by Paint, save, power off, and reopen from Filer.
- **Paint:** create and paint a mode-12 sprite, flip it, rotate by 90 degrees,
  scale horizontally, remove and recreate its mask, save, power off, and reopen.
- **Edit:** select text in one document, copy it into another, undo and redo
  that copy, find and replace a word, save, power off, and reopen.

`tests/run_app_workflows.py` independently checks the saved file formats, text,
font reference, group contents, path coordinates, sprite pixels and mask. It
also checks the ST506 directory/free-map checksums and complete non-overlapping
allocation map. Reopening must leave the disk byte-identical. Draw's embedded
sprite must equal the original Paint image, palette and mask byte for byte.
Every application runs three write/reopen pairs: 18 independent cold machines.
Sampled execution is checked against decoded final ROM bytes; every undefined
exception must be a classified software-FPA call.

Mode 12 has rectangular pixels: two by four OS units. Rotating a 32×32 sprite
by 90 degrees therefore produces 64×16 pixels at the same physical scale.
Nearest-neighbour sampling can lose a one-pixel pattern that falls between
sample rows. The test uses two-pixel-wide marks and calculates the expected
sampled pixels independently. It does not change the original renderer to
conceal this expected resampling effect.

## Corrected stack-extension contract

The first real Draw sprite import failed in `flex__budge` while allocating a
new C stack chunk. The diagnostic captured this call chain:

```
SharedCLibrary GetStackChunk
  -> malloc
     -> _kernel_alloc
        -> flex__budge
           -> recursive stack overflow
```

The pinned source explicitly disables stack checks with Norcroft
`#pragma -s1` throughout `RISC_OSLib/c/alloc`, and only around `flex__budge` in
`RISC_OSLib/rlib/c/flex`. GCCSDK ignores those pragmas. Its generated checks
recursively invoked stack extension while using the allocator's special
636-byte extension chunk. That chunk deliberately uses space below the normal
SL checking threshold; its real header and allocation bounds remain valid.

`tools/build_c_desktop.py` now applies those two original unchecked regions.
`original_unchecked_prologues` in `tools/c_build_support.py` removes only the
generated `CMP sp/ip,sl` and conditional call to `__rt_stkovf_split_*` from
their entry prologues. It validates the compiler's prologue shape and rejects
unexpected instructions. It retains all frame allocation, register saves,
SL/static-base conventions, allocator code and calls. Ordinary functions keep
their checks. The library's other unchecked pragmas are not silently applied
as part of this narrowly scoped correction.

The adaptation affects eleven allocator prologues and `flex__budge`, removing
24 ARM instructions (96 bytes). Exact source hashes and affected functions
are recorded in `build/desktop-c-runtime/unchecked-stack-prologues.json` and
copied alongside the final ROM's C-runtime evidence. The original source files,
root/extension stack sizes, 6,116-byte public library workspace and historical
source revisions are unchanged. No replacement allocator or success handler
is introduced. The normal independent instruction and relocation checks remain
enabled. Draw's acceptance run observes a real new stack chunk and a normal
return through StackOverflowExit, checking the original chunk headers and bounds.

## Build, tests and demonstrations

With the existing toolchain and desktop prerequisites built:

```sh
python3 tools/build_c_desktop.py
python3 tools/build_desktop_apps.py
python3 tools/build_graphics_apps.py
ARCLIBRE_INSTALL_ROM=0 python3 tools/build_arclibre_rom.py
python3 tests/run_app_workflows.py
```

`make arclibre-test` retains the earlier desktop, Palette, sound, dragging,
filing/C ABI, Edit and Draw/Paint gates and adds this gate. Packaging requires
its exact ROM hash. `tests/check_apps_build.py --graphics` repeats the full
C/application builds to verify reproducibility.

The packaged Draw disk contains the rectangle, outline text and embedded Paint
sprite, plus its original `PaintSrc` file. The Paint disk contains the transformed
sprite. The Edit disk contains the text after the find/replace operation. Import
the corresponding `arclibre-draw.machine.json`, `arclibre-paint.machine.json` or
`arclibre-hard-disc.machine.json`, open ArcDisc and double-click the document.
These files were produced by the actual applications, not authored as substitute
document fixtures. Reopen a MacArch machine to reload an updated ROM.

Cold-reopened documents: [Draw](reports/draw-edited-reopened.png),
[Paint](reports/paint-edited-reopened.png),
[Edit](reports/edit-edited-reopened.png). These are raw VIDC captures; the
emulator display scales the rectangular pixels to their intended aspect ratio.

## Scope

This is a defined native editing/interchange milestone, not certification of
every menu command or every third-party file. Modern clipboard conventions are
not substituted for original Edit selection-copy behaviour. Printing still
needs a selected real printer driver/configuration and its own test; TaskWindow
is a separate runtime dependency. JPEG and high-colour ColourPicker services
are not supplied by this original-VIDC profile. Their later-version features
do not replace the 3.11 compatibility target. Physical ARM2/ARM3 testing and
broader malformed-file, low-memory and numerical-edge testing remain separate.

Final acceptance and ROM identity are recorded in `reports/editing-acceptance.json`
and the current desktop release manifest. All 18 cold machines passed, with
identical results across the three trials of each application.

ROM SHA-256: `2e0fda2cd4217ad2d7185c77218e8484bd0a947ce6b984a9891a0ce68a73453c`.
The image uses 1,893,160 bytes of the 2 MiB container, leaving 203,992 bytes.
The baseline desktop, Palette, filing/C ABI, sound, dragging, application
persistence and bounded private Zarch regressions pass against this same ROM.
Two complete C/application builds and links reproduce it exactly.

The pre-fix stack registers and call chain are retained in
[pre-fix-stack-fault.json](reports/pre-fix-stack-fault.json); this deliberately
failing diagnostic used the preceding `7a7fce57…` ROM. The successful new stack
chunk and return observations are in the editing acceptance report.

The current ROM additionally includes the original
[SpriteUtils command module](../spriteutils/RESULTS.md); all editing gates were
repeated against this exact image.
