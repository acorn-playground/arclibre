# Draw and Paint integration

The current [editing and interchange milestone](EDITING.md) adds outline text,
Undo/Redo, grouping, transforms, Paint sprite import and Edit selection/find
operations, with independent cold save/reopen verification. The report below
records the earlier basic persistence milestone and its historical ROM hash.

The graphics milestone passed on an ARM2 A440/1: launch the original Draw and
Paint from Apps, create artwork, save to the real ST506 driver, power off, then
double-click each document after a fresh boot. Three identical trials per
application used 12 independent cold machines. No emulator changes, injected
guest code, dummy services or proprietary ROM content were used.

ROM SHA-256: `7d12851323365238211dad1903392dc826471f9c40764ee3658d14b459640a3e`.
The image contains 42 modules. Its kernel is byte-identical to the preceding
Edit/ST506 desktop milestone; the pinned historical baseline is unchanged.

The real DrawFile contains a completed closed rectangle path and original Draw
options, not unfinished construction geometry. The real 32 by 32, mode-12 Paint
sprite contains a ten-pixel red diagonal and its opaque mask. An independent
host reader checks file types, geometry, sprite headers, pixels, directory and
free-map checksums, and complete non-overlapping allocation accounting.
Read-only observers inspect Draw's original diagram object buffer and Paint's
original sprite area while their task slots are mapped. Both saved and reopened
artwork match the corresponding on-disk bytes exactly. Reopening performs no
writes and leaves each image byte-identical. Screenshots and instruction/HDC
traces accompany every trial. All undefined exceptions are classified software
FPA calls; there are no abort or address exceptions. See
acceptance.json.

The existing integrated regressions also pass on this exact final ROM: three
desktop cold boots plus three disk-app launches and cursor negative controls;
three sound trials; three drag/Pinboard trials; 15 filing/C ABI trials; six
Edit save/reopen cold boots; and three bounded private Zarch runs. See
[integration.json](reports/integration.json). Private game bytes and captures
are not included in the release. These are bounded tests, not exhaustive
application or game compatibility claims.

## Source and build

The pinned cleaned-3.60 Draw and Paint source revisions, individual original
and maintained hashes are recorded in `manifests/graphics-app-inputs.json`.
The imported sources exclude prebuilt applications and upstream test artwork.
Component licences, resources and original notices are documented in
`LICENSING.md`. The real existing SharedCLibrary and RISC_OSLib provide the C
runtime. No guest GCC target library, replacement service or dummy handler is
linked.

After the normal Edit/desktop build prerequisites:

```
python3 tools/build_graphics_apps.py
python3 tools/build_arclibre_rom.py --with-graphics
```

The isolated candidate is `build/arclibre-graphics/arclibre.rom`. Explicit
candidate builds never install into MacArch. The normal `make arclibre-rom`
now includes the same graphics modules and follows the configured ROM install
policy. Use `ARCLIBRE_INSTALL_ROM=0` for acceptance builds. All existing modules remain.
The linked image uses 2,042,480 of 2,097,152 bytes. Both graphics modules have
zero unresolved symbols and pass the independent final-byte ARM2 instruction,
software-FPA, branch-target and relocation audits.

## Adaptations

- Draw's two five-column grid menu arrays now have explicit inner dimensions,
  replacing a Norcroft extension rejected by GCC.
- Draw and Paint use the same real SharedCLibrary jump ABI adapters as Edit,
  without the separate GCC alloca bookkeeping runtime. Neither application
  uses alloca or variable-length arrays.
- The original JPEG and pixel-writing SWI veneers have ARM2 status-settling
  instructions after 26-bit returns. Their actual SWIs and error paths remain.
- Build-time copies preserve the original resource catalogue suffixes and
  use the matching original module wrapper and generated AppName definitions.

Every upstream change is reversible through `patches/graphics-apps/series`.
The original source revision bytes remain independently recoverable and checked.

## Verification and scope

`python3 tests/run_graphics_apps.py` exercises the normal image, and
`make graphics-test` builds/tests the isolated candidate. `python3 tests/check_apps_build.py --graphics` repeats the complete C library, Edit,
Draw and Paint build twice and checks identical objects and final ROM bytes:
[reproducibility.json](reports/reproducibility.json). The final linked code,
all relocations, ARM2 instructions, software-FPA sites and 26-bit return
settling are independently checked in
[c-verification.json](reports/c-verification.json). The original C library's
6,116-byte workspace contract is unchanged. Patch reversal and forward
application recover both pinned original and maintained hashes without fuzz.

The desktop bundle provides `arclibre-draw.machine.json` and
`arclibre-paint.machine.json` with their matching demo hard disks. Each image
contains only a project-authored ReadMe and the document created by the actual
application. The existing hard-disc configuration still demonstrates Edit.
The bundle also includes the maintained source archive and verification evidence.
Close and reopen a MacArch machine after updating its ROM; Power Cycle keeps
its already-loaded ROM bytes.

This validates basic native graphics editing and persistence on one emulated
20 MB ST506 disk. It does not establish JPEG import, printing, 24-bit colour
pickers, exhaustive editing, clipboard interoperability or physical ARM2/ARM3
hardware compatibility. The ultimate target remains unmodified RISC OS 3.11
software. The 3.60 source baseline is not a substitute for that requirement.

Subsequent milestones added [native editing and interchange](EDITING.md),
TaskWindow, stream/RAM filing and standard utilities. The space figures above
belong to this initial graphics milestone; see the [current desktop report](../archimedes-desktop/RESULTS.md)
for current occupancy and exact-ROM evidence. All three editors remain in ROM.

Clean-export verification also corrected Draw's embedded ResourceFS catalogue:
`patches/graphics-apps/0002-deterministic-sprite-catalogue.patch` uses the original
sprite asset's &FF9 file type and deterministic zero datestamp instead of Unix
`:FLOAD:`/`:FEXEC:` metadata. The linker independently checks the complete
catalogue and original sprite payload. C source paths are now relative so
`__FILE__` is stable across checkouts. Neither correction changes the artwork
or substitutes a different application implementation.

## Colour dialogue (owner bug report, 28 Oct 2026)

Draw's Style → Line colour and Fill colour (and its text colours), and
Paint's Edit palette, failed with "SWI &47702 not known". RISC_OSLib 3.60's
`dboxtcol` opens the ColourPicker module (`ColourPicker_OpenDialogue`),
which arrived with RISC OS 3.5 and is not in an Archimedes ROM. RISC OS 3.11's
RISC_OSLib instead drove a "dboxtcol" window from the application's own
Templates: red, green and blue percentages with arrows, a bar and a writable
field each, the 16 desktop colours, None, a colour patch and OK.

- `patches/desktop-c/0003-archimedes-colour-dialogue.patch` replaces the
  body of `src/RISC_OSLib/rlib/c/dboxtcol` with new ArcLibre code (the
  original 1989 implementation was not published) that drives that
  template through RISC_OSLib's dbox library. Its interface is unchanged:
  Select on OK applies and closes, Adjust on OK applies and stays open,
  Adjust on an arrow reverses it, and bars follow click-and-drag. It costs
  1,864 bytes in SharedCLibrary.
- Draw's pinned Templates still contain the "dboxtcol" window. Paint's
  lost it when Paint moved to ColourPicker, so `tools/build_graphics_apps.py`
  adds Draw's window to Paint's Templates resource (1,372 bytes) and records
  the derivation in `resources.json`. Paint's other ColourPicker use is for
  sprites with more than 256 colours, which an Archimedes cannot display.
- As before, choosing "Line colour" itself does nothing; the dialogue opens
  as its submenu, exactly as Draw's menu handler is written.
- `tests/run_graphics_apps.py` now chooses Draw's fill colour (the desktop's
  yellow) and Paint's painting-colour palette entry (red) through the real
  submenus in each of its six cold boots. Any Wimp error report fails the
  probe, and the saved files must carry exactly those colours: the Draw
  path's fill is &00EEEE00, and both words of the sprite's palette entry are
  &0000DD00.
