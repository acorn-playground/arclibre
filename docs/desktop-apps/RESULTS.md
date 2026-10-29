# Original Edit and Apps source integration

The current [editing and interchange report](../graphics-apps/EDITING.md)
adds verified selection copying between Edit documents, Undo/Redo and
find/replace, alongside Draw and Paint editing. The report below preserves
the earlier basic persistence milestone and its historical ROM identity.

The milestone passed: cold-boot an ARM2 A440/1, open its ST506 hard drive in
Filer, launch the original Edit from Apps, create and save a document, power off,
and reopen that document by double-clicking it after a fresh boot. Three
identical trials used six independent machines. No emulator changes, injected
guest success code, fabricated services or proprietary ROM/media were used.

ROM SHA-256: `c5855025f912c86f056e5a6e0b6979866022e3eba8be210290e956f4969fd9a3`.
The image contains 40 modules and uses 1,688,368 of 2,097,152 bytes.
The kernel with revised reset defaults is
`744b8065624c15191bcc8e56555b9068a4ed382fdfd56a5602e2f92a20d41410`; the original historical kernel/filing ROM
still reproduces its pinned hashes with the feature flags absent.

The independent media reader verifies exact file contents, file type and
attributes, directory/free-map checksums and complete non-overlapping space
accounting. The saved document is 83 bytes; the test observed 11 controller
sector writes. Reopening issues no writes and leaves the disk byte-identical.
The observer reads the original `txt1_str` ring/gap buffer while Edit's task is
mapped and verifies those same bytes after reopening. Screenshots and hardware
command/instruction traces accompany each phase. All undefined exceptions are
classified as the original software-FPA dependency; there are no abort or
address exceptions. See [acceptance.json](reports/acceptance.json).

## Build

```
python3 tools/build_hard_disc.py
ARCLIBRE_OUTPUT="$PWD/build/desktop-defaults" python3 tools/build.py --desktop-defaults
python3 tools/build_c_desktop.py
python3 tools/build_desktop_apps.py
python3 tools/build_arclibre_rom.py --with-apps
```

The normal `make arclibre-rom` now builds this stack and updates the configured
local MacArch ROM destination. `make apps-test` exercises the isolated candidate;
`python3 tests/run_desktop_apps.py` tests the normal build.

These individual commands use the already documented host tools, original baseline,
desktop, sound and C-runtime prerequisites. The candidate is
`build/arclibre-apps/arclibre.rom`; explicit candidate builds do not install it.
The original 2 MiB ROM limit is retained. No emulator source was changed.

## Source changes and dependencies

`manifests/desktop-app-inputs.json` identifies all 74 imported files, their exact
cohort commits, original hashes and maintained hashes. The app patch series
reverses and reapplies without fuzz. It contains explicit relocatable AOF areas,
KernelEntry spelling, backslash literals, ARM2 processor-state settling and
alignment of BASICTrans code following strings. BASIC105 uses its original
integer floating-point implementation. BASIC64 is not selected.

Edit uses the existing original SharedCLibrary and RISC_OSLib. A tail-call entry
retains their real C startup; jump adapters call the real 22-word SCL setjmp/
longjmp ABI, preserving GCC's returns-twice/noreturn annotations. The build undefines GCCSDK's `__JMP_BUF_SIZE=26` so the original header supplies
its real 22-word contract. Edit does not use GCC alloca or variable-length arrays.
The public C ABI fixture additionally tests returns-twice behaviour across 33
stack frames and normalisation of `longjmp(env,0)` to return one. No dummy runtime or target libgcc
has been added. Its original BASIC Export helper supplies actual BASIC
conversion entry points. Explicit `&FFB` metadata prevents Unix host copies
being mistaken for Text and recursively relaunched through Edit's text alias.

The C section normaliser now preserves four-byte alignment at every original
AOF area boundary. Without this, the real Edit menu pointers following character
buffers were misaligned and caused an address exception. The existing 6,116-byte
shared-library workspace contract remains intact; padding absorbs the change.
The emitted linked images are independently decoded with every relocation and
code/data boundary checked. BASIC, BASICTrans and ResourceFiler also have
ordinary/observer byte identity and independent ARM2 instruction audits.

## Startup settings

The opt-in `ArcLibreDesktopDefaults` changes only the kernel's CMOS-reset
configuration: one floppy, zero assumed hard drives, Drive 0, NoBoot, Desktop
language 10 and Wimp mode 12. The real reset machinery still controls when
these defaults apply. Valid saved configurations are respected; an existing
machine configured to boot an absent drive still needs its settings changed
or a Delete power-on reset. MacArch already sets attached ST506 drive counts.
The historical build without this flag retains its exact baseline bytes.

The ultimate target remains unmodified RISC OS 3.11 applications and games.
This is not a claim of complete Edit, BASIC or desktop compatibility; printing,
TaskWindow and other built-in applications are separate work.

## Reproduction and delivered files

Two complete original C/application compile, assemble and link runs produce
identical objects and final ROM bytes. `tests/check_apps_build.py` records this
in [reproducibility.json](reports/reproducibility.json). The BASIC,
BASICTrans and ResourceFiler observer builds match ordinary AsAsm bytes;
[assembly.json](reports/assembly.json) and
[c-verification.json](reports/c-verification.json) record independent instruction
and relocation checks. All candidate patch series reverse to pinned originals
and reapply without fuzz.

`make arclibre-package` requires this gate and the existing integrated desktop,
filing, sound and dragging gates to match the delivered ROM hash. It exports:

- `dist/arclibre.rom` and its SHA-256 sidecar.
- `dist/arclibre-demo.hdf`, containing only project-authored ReadMe and Document.
- `dist/arclibre-hard-disc.machine.json` for the demonstrated ST506 configuration.
- `dist/arclibre.machine.json` for floppy-only use, plus `arclibre.cmos`.
- Source and evidence archives with licensing/provenance records.

Reopen a MacArch machine after installing a new ROM; Power Cycle keeps the
ROM bytes already loaded by that machine. The generated hard disk is writable;
keep a fresh copy if repeating the demonstration manually.

## Remaining scope and recommended next milestone

This validates one 20 MB old-map ST506 disk on the emulated ARM2 A440/1, not IDE,
all disk geometries, formatters, damaged/full-disk recovery or physical hardware.
Edit's basic text workflow and original BASIC startup dependency work; printing,
TaskWindow, exhaustive editing commands and BASIC language compatibility are
not certified. No full RISC OS 3.11 compatibility claim follows from these tests.

The next useful milestone is the original Draw and Paint applications, tested
by creating graphics, saving them to this hard disk and reopening them after a
restart. Keep the desktop, storage and Zarch gates as regression checks. Broader
hard-disk write/error testing and real ARM2/ARM3 hardware validation remain
separate acceptance work.


The final-ROM integration checks also passed: three desktop cold boots plus
three application-launch trials and pointer negative controls; three sound
trials; three DragASprite/Pinboard trials; fifteen filing/C ABI trials; and the
bounded private Zarch gate. All match the delivered ROM SHA-256. See
[integration.json](reports/integration.json). Private game bytes and captures
are excluded from the release bundle.
