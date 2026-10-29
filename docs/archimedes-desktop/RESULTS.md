# Original Archimedes desktop profile and Palette

ArcLibre's desktop uses the system bitmap font and flat backgrounds by default.
The optional `ArcLibreDesktopDefaults` kernel profile sets DesktopFeaturesCMOS
(OS byte &8C, RTC byte &CC) to &83: retain 3D furniture, choose font index 1,
disable global tiling. The font selection and tiling rules are the real original
Wimp implementations in `s/Wimp10` and `s/Tiling`. Outline fonts remain available
to applications. The final resource pack also selects the original plain Tools furniture,
removing the textured title bars and scroll wells.

The reference images were named backwards: `311.png` showed ArcLibre;
`360.png` showed RISC OS 3.11. The softer text was Wimp's selected outline font,
not evidence that the emulator rescaled the framebuffer. High-resolution sprite
variants alone do not imply an unsupported colour depth.

## Resource selection

The final desktop resource pack omits these global decorative sprites:

| File | Sprite | Bytes | Reason |
| --- | --- | ---: | --- |
| Wimp Sprites | tile_1 | 16,228 | Unused flat-profile decoration, 4bpp |
| Wimp Sprites22 | tile_1 | 17,108 | Unused flat-profile decoration, 4bpp |
| Wimp Sprites22 | tile_1-8 | 33,540 | Unused flat-profile decoration, 8bpp |
| Wimp Sprites22 | tile_1-16 | 66,404 | 16bpp screen tile unsupported by original VIDC |

The four tiles save **133,280 bytes**. Selecting the unmodified plain
`Resources/UK/Tools,ff9` instead of `Tools3d,ff9` saves another **22,432 bytes**
(11,500 versus 33,932). Both come from the same pinned Wimp source cohort,
`530acd4a18ffa97ce7a6b5b20fdef0a4db3ef647`; see
`manifests/archimedes-furniture.json`. Sprite and furniture saving: **155,712 bytes**.
Messages `#` comment lines are also removed (5,316 bytes in 44 files); no comment
carries a notice and every message line is unchanged.
The plain file has no textured title/scroll caps, so Wimp uses its original
plain rectangle rendering. Original asset bytes and notices are preserved. The 8bpp tile is removed because this profile
uses flat backgrounds, not because original VIDC lacks 256-colour modes.
No application font, ordinary icon or useful higher-resolution variant is
removed. The complete pinned sprite files remain unchanged in `src/Wimp`.
`tools/archimedes_resources.py` rebuilds sprite-file headers, checks retained
sprite records byte for byte, and records individual hashes and reasons in
`build/arclibre/desktop-resource-selection.json`. It also audits every bundled
ResourceFS sprite file against the retained original-VIDC mode table. The
isolated historical font/Wimp tests keep their original resource packs.

## Palette implementation

`src/ArcPalette/s/ArcPalette` is new Apache-2.0 ArcLibre code, **not** recovered
Acorn Palette source. The public cleaned-3.60 Display design document
`Sources/Video/UserI/Display/Doc/0197254.02` explicitly excludes the old Palette
utility. No matching original implementation was found in the available local
source cohorts. DisplayManager is a mode chooser, not a substitute palette
editor. The icon uses the existing `palette` sprite in the pinned Apache-licensed
Wimp source assets; no proprietary ROM image or external artwork is used.

Version 0.10 (module title `PaletteUtil`, task "Palette Utility") follows the
3.11 utility closely: the RISC OS 3 User Guide (3.10, pp.115-118), the PRM
(vol. 3) and measured 3.11 screenshots. It starts through Service_StartWimp.
Its window (288 × 360 OS units, Back and Close only) has three outlined R/G/B
sliders, sixteen contiguous swatches (the selected one shows its logical colour
number in a contrasting colour inside an outline) and Bor/Ms1/Ms2/Ms3 boxes,
inverted when selected. Dragging a slider changes the screen live;
Message_PaletteChange is broadcast on release. Releasing after editing colour 0
or 7 re-spreads greys 1-6 in VIDC1's four-bit steps (`n0 + (n7-n0)·i/7`,
truncated), which reproduces the standard greys exactly.

The icon-bar menu is the original Invert, Mode ⇒, Save ⇒, Default. Mode lists
12 (16 colours), 15 (256 colours), 35 (wide 16) and 36 (wide 256) for the
standard monitor, plus a writable mode field; unsupported modes report the real
error. Save opens a "Save as" box with the palette-file icon: drag it to a
directory (DataSave/DataSaveAck/DataLoad) or enter a full pathname. The file is
type &FED in the PRM's VDU 19 form (colours 0-15, border, pointer 1-3).
Dropping a palette file on the icon or window applies it through the Wimp's
`*WimpPalette`. Invert reverses greys 0-7; Default applies Wimp_SetPalette's
standard palette. There is no Quit, as in the original.

This is new ArcLibre code reproducing the documented appearance and behaviour,
not Acorn's unpublished implementation. Not modelled: other monitor types' mode
lists, 256-colour slider behaviour, and an Info box (the 3.1 menu has none).

### Default border colour

RISC OS 3.11 fills the screen border with the desktop background grey (Wimp
colour 4, `&777777`); the pinned 3.60 Wimp default palette makes it black.
[0004-wimp-border-colour.patch](../../patches/desktop-source/0004-wimp-border-colour.patch)
changes only entry 16 of the Wimp's built-in `!Palette` to `&77777700`. The
Wimp still programs VIDC from that entry through its original
`recalcpalette`/`setmousepalette` path, so startup, mode changes and Palette's
Default (Wimp_SetPalette with R1=0) all use it. The kernel's pre-desktop border
remains black, and the border is still independently editable. The source of
the 3.11 value is direct observation on a 3.11 machine; no proprietary ROM bytes
were used. The candidate ROM differs from the previous release in exactly
those three bytes. The Palette gate asserts the default VIDC border is `&777`
and equal to a desktop palette entry, at boot and after Default; the previous
ROM fails that assertion.

The earlier 0.01 event dispatch was wrong: it treated pointer-leaving event 4
as a Close_Window_Request. That caused the editor to disappear while its icon
remained. The dispatch now uses original named Wimp constants, including the
real redraw/open/close reasons 1/2/3. Tests now assert the actual window open
flag and distinguish the Close gadget from Back. Merely counting tasks was
insufficient to detect the previous bug.

Wimp_ReadPalette/SetPalette transfer the complete 20-word palette, and the
module broadcasts Message_PaletteChange. Live slider fill icons use the real
maintained Wimp_ResizeIcon API. This utility is built for ArcLibre's maintained
Wimp; it is not claimed to run unchanged on a proprietary 3.11 ROM. The emitted
module uses ARM2/USR26 and has no C runtime or FPA dependency. Its private 4 KiB
RMA allocation contains state at 0–31, current/saved palettes at 32–191, Wimp
block at 192–447, label at 448–511, menus at 512–827, mode text at 832–839,
and a descending user stack above byte 1024. No historical kernel workspace
structure is replaced.

Palette file loading/saving, persistent settings and the original utility's
automatic grey-ramp recalculation on editing colours 0/7 remain unimplemented.
The current sliders, grid, border/pointer editing and mode menu address the
reported usability gaps; this is not a claim of complete original Palette
feature parity. Unmodified RISC OS 3.11 applications remain the project target.

## Build and use

`make arclibre-rom` builds Palette as part of the desktop application components,
selects the resources, and follows the existing local MacArch install policy.
The complete gate is `ARCLIBRE_INSTALL_ROM=0 make arclibre-test`; packaging is
`make arclibre-package`. To rebuild after these source changes with dependencies
already built:

```sh
ARCLIBRE_OUTPUT="$PWD/build/desktop-defaults" python3 tools/build.py --desktop-defaults
python3 tools/build_palette.py
ARCLIBRE_INSTALL_ROM=0 python3 tools/build_arclibre_rom.py
python3 tests/run_palette.py
```

The profile change is reversible in restoration patch 0031. Without the desktop
flag, the pinned kernel and baseline ROM remain byte-identical. The Palette
builder independently decodes every emitted instruction, checks branches and
code/data mappings, rejects unresolved symbols/relocations, and compares two
ordinary assemblies with the observer assembly byte for byte.

**Existing CMOS settings are preserved.** To select the new appearance in an
existing machine, enter `*Configure WimpFont 1` at F12, then restart the desktop
or machine. This command accepts a font index from 0 to 15 and preserves the
other desktop feature bits; 131 (&83) is the complete CMOS byte, not a valid
font index. To apply both the bitmap-font and flat-background CMOS defaults,
import the newly packaged machine/CMOS pair. Close
and reopen the MacArch machine to reload changed ROM bytes; Power Cycle alone
retains the already loaded ROM. Palette colour edits last for the current
session and do not alter CMOS.

## Verification

`tests/run_palette.py` repeats three natural cold boots with real mouse input,
no guest memory writes or code injection. It checks actual bitmap font selection
in Wimp workspace, CMOS &83, live task registration in USR26, exact VIDC register
changes for each RGB channel, endpoint clamping during held drags, border/pointer editing, Restore, Default,
true close/reopen, title dragging and Quit. Leaving the window must not close
it. Preset and typed mode changes verify both Wimp mode and actual VIDC depth;
a rejected text mode must leave the task and editor alive. Screenshots, instruction
traces and independent final-ROM byte audits accompany each trial. Existing
desktop, filing, sound, Edit, Draw/Paint and private game gates remain required.
Final exact-ROM evidence is recorded in `reports/` after those gates complete.

Current integrated ROM SHA-256: `e905575c4e064b9153138076ab05681067f760a2efbedbcc0c126662259ccce1`.
The image has 73 joined modules (74 identities including the kernel's
UtilityModule) and uses **2,076,436 of 2,097,152 bytes**, leaving
**20,716 bytes (20.2 KiB)** free. PaletteUtil 0.10 is 4,916 bytes, with independently
decoded ARM2 instructions and zero unresolved symbols or relocations.
The earlier flat-desktop release `2e0fda2c…` had 44 joined modules and used
1,893,160 bytes. Later milestones added the original TaskWindow and FilterManager,
Palette mode colour labels, the VIDC1 sample-period fix and corrected classic
Wimp message numbers. The kernel remains byte-identical.

[Task services](../task-services/RESULTS.md) pass protocol, filter and original
Edit/BASIC tests across six cold machines, plus a missing-modules control.
[Sound rate verification](../sound/RATE_FIX.md) measures elapsed DMA byte rates
for eight channel/period combinations, correcting the doubled four-channel
playback rate. The user has since confirmed Lemmings music and effects
play correctly on a direct manual test.
[Classic submenu verification](../menu-messages/RESULTS.md)
checks literal public message numbers independently of the shared headers,
including a deliberately incorrect-message control. Impression's six main
submenu branches also open in a bounded private application replay.

The Palette gate records three identical
cold boots and screenshots; resource selection
records retained and omitted assets. Repeated complete builds
produce the same ROM. The flag-absent baseline remains
exact. See [final integration results](reports/integration.json) for every
exact-ROM regression, including the bounded private Zarch and Nevryon checks; private game
bytes and captures are excluded from all public packages.

The [native editing milestone](../graphics-apps/EDITING.md) additionally passes
18 cold write/reopen machines across Draw, Paint and Edit. It checks outline
text, grouping, transforms, masks, selection copy, find/replace and actual
Paint-to-Draw sprite interchange. That earlier milestone restored original allocator stack-check exclusions
ignored by GCCSDK (96 bytes removed); its editing gates are repeated on the
current integrated image. See current editing acceptance.

The [SpriteUtils restoration](../spriteutils/RESULTS.md) supplies the original
`SLoad`/`SChoose` command layer required by Nevryon. Its public sprite round-trip
and private title-screen checks pass three cold boots each. The current ROM
retains the full desktop, editing and bounded Zarch regression results above.

## Restored standard services and reproducible release

The current image also includes original DeviceFS, SystemDevices, PipeFS,
RamFS, RAMFSFiler, Free, ScreenBlanker and StringLib. All retained test stages
pass on the exact ROM above, including three cold runs of each new service
gate, missing-provider controls and the TaskWindow SleepNoMore negative
control. Actual mouse/keyboard input wakes the blanker; all four string voices
execute their original copied ARM2 code and emit non-silent sound DMA.

The [space report](SIZE.md) records 23,660 bytes recovered through compiler
optimisation, plus 36 bytes from stable diagnostic filenames. All original
Draw/Paint/Edit applications remain in ROM. Packaging [rebuilds the exact published source archive](../../BUILD.md)
and its bundled host tools in an empty directory; the matching proof is
`dist/arclibre-source-build.json`, also included in the evidence bundle. The
earlier [clean-build report](../desktop-c/reports/clean-source-build.json) remains
historical evidence for the previous release. Draw's
embedded sprite catalogue now preserves the source's Sprite type with stable
metadata and byte-identical artwork. The kernel remains `71b0c301…`; no emulator
changes were made for this milestone.

This remains an experimental ROM. DOSFS needs its embedded boot-sector and
header-tool review; RTCAdjust/IIC, the remaining bundled utilities,
printing and physical ARM2/ARM3 validation remain on the [roadmap](../desktop-source/ROADMAP.md).
Lemmings sound was confirmed manually by the user rather than by a retained
gate. Module counts do not establish full RISC OS 3.11 compatibility.


## Original compression and desktop utilities

[Squash, Chars and Help](../desktop-utilities/RESULTS.md) now pass dedicated
three-cold-run gates on this exact image. The actual original BASIC programs
supply the character grid/font menu and live interactive help; the compression
SWIs retain the original codecs and wrapper with documented ABI and stream
restorations. No application has been moved out of ROM.

The C library now identifies this derivative as `[ArcLibre]` instead of embedding
the host compilation date. A two-calendar regression
requires identical generated code for simulated 1970 and 2099 dates.

## Hardware vectors as in RISC OS 3.11 (SWIV, 28 Oct 2026)

The owner reported that SWIV (1992, Krisalis) stopped on a black screen
before its splash screen. SWIV installs its IRQ handler at &18 and chains to
the previous handler by relocating the branch it finds there. RISC OS 3.11
has a branch at &18 (`B` into the ROM's IRQ code); the 3.60 kernel had
`LDR pc, ProcVec_IRQ`, which SWIV decoded as a branch to &27FFE40, so the
first IRQ after the hook ran into zeroed RAM and the kernel spun translating
errors with interrupts off.

3.60's `ProcessorVectors` option indirects every hardware vector through a
page-zero table to support `OS_ClaimProcessorVector`, a RISC OS 3.5 SWI.
`patches/restoration/0033-arm2-branch-hardware-vectors.patch` turns it off
under `ArcLibreDelivered`, so the delivered kernel builds the source's own
non-indirected vectors, as 3.11 has them: branches at &0, &8 (the RAM SWI
dispatcher) and &18, and `LDR pc` from the environment slots for the aborts.
The three branch templates the kernel copies to &0 and &18 use the same
explicit 26-bit wrapped encoding as patch 0008, because their ROM targets lie
beyond ±32 MB. The frozen baseline still reproduces exactly. No ROM module
uses `OS_ClaimProcessorVector`; the ARM2 FPEmulator writes its own branch at
&4 and passes other instructions to the one it replaced, which also needs a
branch there. `tools/verify.py` checks every delivered vector's target, and
`tools/inspect_image.py` classifies the three reviewed branch words.

`tests/run_swiv.py` is a private gate on the owner's disc (it and the disc
are kept in the development archive, not this repository): three cold boots double-click !Swiv, and SWIV must hook &18 with a
branch to its own handler, draw its credits screen and show its options
screen on F1, identically each time.

## OS version and keyboard ID acknowledge as in RISC OS 3.11 (28 Oct 2026)

After the SWIV fix, a comparison of the delivered ROM with the owner's 3.11
ROM in MacArch (page zero after a cold boot to the `*` prompt, and OS_Byte
results; local only, nothing from the 3.11 ROM is kept) found two more 3.60
behaviours that 3.11 software can see.
`patches/restoration/0034-arm2-osversion-and-keyboard-id-ack.patch` fixes both
under `ArcLibreDelivered`; the frozen baseline is unchanged.

- `OS_Byte 129,0,255` (`INKEY(-256)`) returned &A6, RISC OS 3.60's
  identifier. 3.11 returns &A4, and software reads &A5 or above as RISC OS 3.5
  (Risc PC memory map, VIDC20). The delivered kernel now returns &A4. No ROM
  component tests this value. The `*FX 0` text and module help strings still
  say 3.60.
- After the keyboard sends its ID, the 3.60 driver calls KeyV (a RISC OS 3.5
  addition, `AssembleKEYV`) and then re-enables the KART transmit interrupt
  through R12 without reloading the IOC base, unlike the key-down and key-up
  paths after their KeyV calls. KeyV returns R12 = 0, so the store went to RAM
  &28, inside the FIQ code area &1C-&FF, instead of IOC interrupt mask B, and
  &28 held &40 after every boot. 3.11 leaves &28 zero. The delivered driver now
  reloads R12 there; &28 stays zero after boot and the keyboard still works.

Checked by hand in MacArch: OS_Byte 129 gives &A4, &20-&2F is the default FIQ
handler followed by zeros as on 3.11, and typing at the `*` prompt works.

## ArcLibre version text (28 Oct 2026)

At the owner's request, the delivered ROM names itself ArcLibre 0.8 in the
places that said "RISC OS 3.60 (13 Apr 1995)"
(`patches/restoration/0035-arclibre-version-strings.patch`, under
`ArcLibreDelivered`; the baseline still reproduces):

| Where | Text |
|---|---|
| `*FX 0` (OS_Byte 0,0) | `ArcLibre 0.8 (28 Oct 2026), compatible with RISC OS 3.11` |
| Kernel `*Help` title | `ArcLibre` `0.80 (28 Oct 2026)` |
| UtilityModule help | `MOS Utilities` `3.11 (28 Oct 2026) ArcLibre 0.8` |

UtilityModule keeps 3.11's version number because `!Run` files test it with
`RMEnsure UtilityModule 3.10` (needs RISC OS 3.1) and `3.50` (RISC OS 3.5
present). Checked in MacArch: 3.10 is satisfied and 3.50 is not, as on 3.11.
The `*FX 0` text keeps "RISC OS 3.11" because MacArch (unchanged) identifies a
ROM by the first "RISC OS"/"Arthur" string with a digit, and takes 2 MB images
only when it reads "RISC OS 3"; it now lists the ROM as "RISC OS 3.11". The
boot banner ("RISC OS 2MB") is unchanged.
