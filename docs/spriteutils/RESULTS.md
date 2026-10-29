# Restored system sprite commands

Nevryon's unmodified disc-1 launch failed with error 214, `File 'SLOAD' not
found`. The kernel already implements the sprite SWIs; the omitted component
was **SpriteUtils**, which registers the `*SLoad`, `*SChoose` and related command
names. An unknown command falls through to file lookup, explaining the
misleading missing-file message. No replacement game file is required.

The baseline failure was reproduced with ROM `175cd8a2…`. Adding the original
SpriteUtils lets the game load its loading sprite, select it, load its score
sprites and reach the animated title screen. The private test is deliberately
bounded: it does not certify gameplay, disc swapping, saved scores or the whole
game. Both original disks remain untouched. No commercial game data is
included in the ROM, source export or public evidence bundle.

## Source and build

The exact source is the cleaned-3.60 cohort of the public SpriteUtil repository,
revision `b74d38f3b2b69d1b6cda5377c4b102de1f5be10f`, version 1.10 dated
28 October 1994. All selected source/resource files retain their original
notices and Apache-2.0 licence. `manifests/desktop-action-inputs.json` records
both original and maintained hashes. See [LICENSING.md](../../LICENSING.md).

The reversible `0003-spriteutils-arm2.patch` makes three assembly adaptations:

- Replace the old absolute `LEADR` container with a relocatable code area.
- Use the maintained `Entry` macro spelling, avoiding AsAsm's `ENTRY` directive.
- Spell the original R12-relative message workspace addresses explicitly as
  `ADD`, avoiding AsAsm interpreting these `ADR` operands as absolute addresses.

The original command handlers, sprite operations, error handling and lazy
20-byte message workspace are retained. There are no dummy commands or game
patches. The build generates tokenised help from the original HelpSrc and
exports the original message file as `Resources.SpriteUtil.Messages`.

`tools/build_desktop_actions.py` assembles twice plus an observer build. The
result is a **1,508-byte** module, with identical output between those builds,
independently decoded ARM2 instructions, no unresolved symbols and no remaining
relocations. Source patches reverse and reapply without fuzz. The module and
its messages add 3,264 bytes to the complete ROM; the kernel is unchanged.

## Verification

`tests/run_sprite_commands.py` launches a public, file-loaded application from
Filer on three cold ARM2 A440/1 machines. Its actual OS calls allocate the system
sprite area, load a project-authored 8×2 mode-12 sprite, select/copy/rename/delete
sprites, flip both axes twice, list/query/help, and save through the real WD1772
filing path. It checks every pixel through OS_SpriteOp, verifies genuine missing
file error propagation and recovery, clears the sprites and releases its area.
An independent host reader verifies the saved sprite is byte-identical to the
input and that directory/free-map checksums are valid. The test returns to the
real desktop. No guest code is injected and no emulator changes are used.

`tests/run_nevryon.py` (a private gate, kept with the disc in the development
archive, not this repository) uses the user's original disc 1. It double-clicks !Nevryon
from Filer, observes the original sprite/title loading commands, runs to the
title-screen boundary and checks USR26 execution, faults and repeatability.
Only compact acceptance metadata and image hashes are public; the disk, game
code, memory dumps, screenshots and execution traces stay in ignored
`build/private-nevryon`.

The expanded Draw regression exposed an observation-boundary bug in the test
harness: calling `Debugger.resume()` unconditionally at the beginning of each
timed run suppresses a breakpoint at the current PC, even when that breakpoint
has not yet been observed. One software-FPA exception fell at such a boundary.
GraphicsProbe now resumes only a real stop. Three repeated Draw write/reopen
pairs capture the missing exception; all other observations, exception counts,
saved disks and screenshots match the earlier runs exactly. The strict
exception-count and instruction checks are unchanged. See the
[comparison](reports/trace-boundary.json). No emulator or ROM change is involved.
`tests/run_app_workflows.py --verify-existing` independently revalidates the
captured current-ROM runs without rerunning the machines; the default command
still creates all 18 cold runs from scratch.

The public [command gate](reports/commands.json) and private
[Nevryon title gate](reports/nevryon.json) both pass three identical cold boots.
The [negative control](reports/negative-control.json) records the original
missing-command failure. The independent [assembly audit](reports/assembly.json)
classifies all 185 module instructions as ARM2-compatible; runtime traces cover
125 of them in the public command test.

Final ROM SHA-256: `2e0fda2cd4217ad2d7185c77218e8484bd0a947ce6b984a9891a0ce68a73453c`. The 44-module image uses
1,893,160 bytes and leaves 203,992 bytes free. Two complete C/application builds
and links reproduce it exactly. All existing desktop, Palette, filing/C ABI,
sound, dragging, Draw/Paint/Edit persistence and editing, and bounded Zarch
regressions pass on this same ROM; see the
[integration inventory](../archimedes-desktop/reports/integration.json).
