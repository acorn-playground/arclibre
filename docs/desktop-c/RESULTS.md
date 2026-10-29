# Original C desktop runtime and FilerAct

The pinned cleaned-3.60 SharedCLibrary, RISC_OSLib, FilerAct and FilerSWIs now
build together for ARM2/APCS-26. The candidate starts the real FilerAct task
and performs mouse-driven copy, Shift-drag move and menu Delete. A separate
disk-loaded C application exercises the actual shared-library entry interface.
These are original implementations, not command-line fallbacks or replacement
success handlers. The kernel and MacArch core are unchanged.

All fifteen cold-run scenarios passed: three each for copy, move, Delete,
write-protected copy/Abort and the C ABI application. The ROM SHA-256 is
`94fb12c8fdde58bff239890de5f66f95bf6b4590f7a7cdb60d2812903a6a45a0`.
The gate is `tests/run_filer_actions.py`; a compact report is retained in
`reports/acceptance.json`.
The experimental component is not a general 3.11 compatibility claim.

## Reproduce

```
make arclibre-c-desktop
python3 tests/check_c_build.py
python3 tests/run_filer_actions.py build/arclibre-c-desktop
```

The candidate is `build/arclibre-c-desktop/arclibre.rom`; this explicit candidate
profile never installs itself over the user's MacArch ROM. Logs, instruction
inventories, linked areas, resources, workspace contract and acceptance captures
are in `build/desktop-c-runtime`. The normal `make arclibre-rom` includes these modules; `make arclibre-test`
includes their runtime gate. `--without-c-desktop` builds the preceding profile
in its own directory without installing it. Source hashes and exact commits are in `manifests/desktop-c-inputs.json`
and `desktop-action-inputs.json`. The public compiler is documented in
[TOOLCHAIN.md](TOOLCHAIN.md).

## Restoration changes

- Export the original C headers under their Unix include spellings. Generate
  `swis.h` using the original source generator and the established original-machine
  header exports. The profile records unneeded unavailable GETs; no missing
  interface bodies are fabricated.
- Preserve the original array-of-one `va_list` public ABI, with GCC builtins
  handling argument register spilling. Keep stdio's matching declaration.
- Guard Norcroft-only mathematical intrinsic names and its syntactic `___type`
  qualifier. GCC calls the real sin/cos/atan/fabs implementations.
- Correct the original `trace .h` include spelling, two immediate register-number
  operands rejected by AsAsm, and two ARM2 processor-state settling sequences in
  the C runtime's escape/event handlers.
- Keep readonly constants in ROM, using the recorded compiler target patch.
  Merge repeated GCC AOF areas for AsAsm, materialise zero-initialised template
  bytes, and keep the original Makefile's object order. Drlink inserts equal-named
  areas in reverse input order, so the input list is reversed deliberately.
- Pad the existing private data reservations using measured C and assembly data
  sizes. This retains the old public/private contracts rather than enlarging them.
- Adapt GCC's division argument order to the library's real arithmetic routines.
  A small `main` branch enters FilerAct's actual C body without GCC's unrelated
  C++ constructor startup; the original module wrapper performs C initialisation.
- Bind ROM client imports to actual linked SharedCLibrary exports. Image/area
  boundary symbols remain local to the client. No unresolved strong reference is
  tolerated by the linker.
- Restore FilerSWIs 0.03's real three-SWI message interface at `&40F80`. Its
  changes are limited to relocatable AOF packaging, the shared KernelEntry macro
  spelling and the canonical SWI base. FilerAct alone is insufficient: without
  FilerSWIs the original Filer falls back to command-line Copy, which is expressly
  rejected by this gate.

`patches/desktop-c/0001-gcc-arm2-library.patch` and
`patches/desktop-actions/0002-filerswis-arm2.patch` reverse to every exact pinned
original hash and reapply without fuzz. Compiler changes are a separate patch
series in `third_party/patches`. Original notices and explicit modification
notices are preserved. Licensing and the four original message/template assets
are recorded in `LICENSING.md`.

## Workspace and memory contract

The actual linked Lib$$Init table retains these contiguous data templates:

| Chunk | ID | Bytes |
| --- | --- | ---: |
| C runtime kernel | 1 | 796 |
| C library | 2 | 2,888 |
| RISC_OSLib | `&80000003` | 2,432 |
| Total / original ROM client reservation | | 6,116 |

The C library prefix is 928 bytes plus the original 1,960-byte private reserve.
Actual compiled private C data is 1,528 bytes; padding is 432 bytes. RISC_OSLib's
prefix is four bytes plus its original 2,428-byte private reserve: 2,420 bytes of
compiled C data and four assembly-owned poll bytes leave four padding bytes.
The library relocation word is at SL−540 and the client word at SL−536.
`workspace-contract.json` checks the actual linked ranges against the original
client veneer reservation. These are C runtime contracts, not changes to MEMC
or the kernel's fixed workspace.

## Verification and bounds

Two complete compiler/assembler/link runs produce identical object and ROM bytes.
`reproducibility.json` records the hashes. The independent final-image decoder
checks 44,171 integer ARM2 instructions in SharedCLibrary and 6,015 in FilerAct,
all branch destinations, code/data mapping and processor-state settling. All
non-relocated linked bytes must equal their input AOF bytes. The 336 original
library FPA instructions are separately inventoried and require the real
software FPEmulator; they are not accepted as ARM2 integer instructions.

The public C application covers signed/unsigned division and remainders,
variadic formatting including double arguments, readonly pointer tables,
malloc/realloc/free, qsort/bsearch, sin/atan/fabs/sqrt, and clean return through
the real shared-library ABI. Its original entry veneers are populated by the
library at runtime; the gate checks their branches against known library code.
The application-only profile excludes unused relocatable-module entry code.

The filing fixture is a newly authored 800 KB D-format floppy with a 32,791-byte
pattern file and an empty destination directory. Verification checks payload,
load/execute metadata, attributes, directory checksums, free-map checksums,
non-overlapping allocation and complete used/free accounting. Copy preserves
the source; move removes it; Delete returns its allocated space. The protected
fixture must remain byte-identical and recover through the actual error dialog.
No private game data appears in this fixture or in the release evidence.

The test suite repeats each scenario on three independently powered-on A440/1
ARM2 machines. Runtime traces must match the checked ROM bytes, all undefined
exceptions must match known software-FPA instructions, and abort/address faults
are rejected. Tests retain screenshots and actual mouse/SWI observations.

This does not yet cover recursive or cross-volume operations, full discs,
rename collisions, long interactive sessions, TaskWindow, settings or the wider
3.11 application matrix. The successful bounded Zarch work is documented
separately in `docs/sound/RESULTS.md`; a complete game playthrough and ARM3/real
hardware validation remain outstanding.

The first repeat comparison exposed an ordering issue in the host report: the
SpriteExtend generator can emit different words at the same buffer address.
Its instruction inventory is a set and now sorts by both address and word.
All fifteen original runs passed their functional, media and instruction checks;
re-verifying those captures with the canonical ordering established identical
observations. No guest change or weakened instruction check was needed.

The final ROM also passed the retained desktop/pointer, sound, DragASprite/Pinboard
and exact private Zarch gates. `reports/integration.json` records their matching
ROM hashes. Test output directories are cleared before fresh sound/drag runs so
old traces cannot contaminate a new ROM audit. The Zarch repeat check compares
real framebuffers, machine observations and paired-input results; guessed text
from graphics is retained as diagnostic output but excluded from equality.
The kernel and emulator remain unchanged.


## Edit integration follow-up

The Edit milestone exposed a word-alignment loss when the build normaliser
merged successive original GCC AOF areas. It now preserves each area's initial
four-byte alignment; otherwise menu pointers after byte buffers could be
unaligned. The existing shared-library workspace reservation remains unchanged.

The extended public C ABI fixture also exercises the original SCL setjmp/
longjmp implementation across 33 stack frames and verifies that a zero jump
value becomes one. It uses the original 22-word buffer definition by removing
GCCSDK's alternate `__JMP_BUF_SIZE` predefine and binds through real tail-call
adapters. No target libgcc is introduced. Current integrated results are in
`docs/desktop-apps/reports`; the hashes earlier in this document identify the
preceding historical checkpoint.
