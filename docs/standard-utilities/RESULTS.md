# ScreenBlanker and StringLib restoration

These two original cleaned-3.60 components assemble reproducibly for ARM2:
ScreenBlanker 2,016 bytes and StringLib 2,692 bytes. The explicit candidate
profile uses 1,916,308 bytes of a 2 MiB ROM, leaving 180,844 free. They now pass the dedicated runtime gate on three identical cold boots.
The source set is the default desktop profile. The [final integration report](../archimedes-desktop/reports/integration.json)
records the completed combined release regression alongside this dedicated gate.

The [assembly report](reports/assembly.json) covers two normal builds and an
independent observer build with identical AOF bytes, no unresolved symbols or
relocations, independent ARM2 instruction/branch decoding, code/data boundaries
and PSR settling checks. Original 26-bit paths and StringLib's original RAM
voice-code copy are retained. The patches only supply a relocatable AREA,
rename the colliding ENTRY macro, remove obsolete LEADR and select the exported
ScreenBlanker SWI base.

The 13 pinned inputs retain their Apache notices and component LICENSE files.
Only the original UK message files are installed as resources:
`Resources.ScrBlanker.Messages` and `Resources.StringLib.Messages`. StringLib
synthesises its voices algorithmically; no sampled audio, ROM resource or
external music is imported. The unused tokenised BASIC build source is omitted.

```sh
python3 tools/build_standard_utilities.py
ARCLIBRE_INSTALL_ROM=0 python3 tools/build_arclibre_rom.py --with-standard-utilities
```

The kernel and emulator remain unchanged. The default profile includes these
modules; the runtime gate establishes real blank/unblank and timer behaviour,
original RAM voice-code execution, named attachment and non-silent sound DMA
for all four voices. This is not exhaustive 3.11 compatibility.

## ScreenBlanker timeout contract

The pinned source's `Doc/ScrBlank` incorrectly describes reason 4's result as
centiseconds. `Go_ReadTimeout` actually calls `ConvertTicksToSecs`; a 500 cs
minimum reads back as 5. The targeted history check at
`4e46226be050754707e7ba8a2eacb5228d7ad00c` (23 April 1998) retains that path
and exposes a separate reason 5 using `ConvertTicksToCS` to non-LCD builds.
ArcLibre preserves the cohort's reason 4 behaviour and does not add reason 5.
No newer implementation was imported. The fixture was corrected to distinguish
these units instead of altering original code to match the mistaken comment.

The [published PRM](https://www.riscos.com/support/developers/prm/screenblanker.html)
describes `*BlankTime` in seconds and reserves ScreenBlanker_Control for internal
Portable use. The guest test exercises that internal interface for diagnostics;
it is not advice for applications to depend on it. Invalid reasons return the
module's &110 error, distinct from the kernel's unregistered-SWI error.

## Runtime verification

[Acceptance](reports/acceptance.json) records three identical cold executions
of a new file-loaded C client on candidate ROM
`1059cfb0b5b4b87ca1828a428a5cf8f0fa01c9b1f305ec6f1f395fbf813624ee`.
Immediate and timer-driven blanking produce zero lit frame pixels and zero
display palette entries; explicit restoration and character-output wake-up
restore the complete prior VIDC palette. Real mouse movement and a keyboard
press also wake independently blanked displays, with character-output wake-up
disabled so the diagnostic markers cannot cause restoration. Flashing alternates real blanked and
visible frames, with ScreenBlanked/ScreenRestored service calls observed.

All four named StringLib voices attach, enter their original GateOn routines
in RAM and emit more than 1,000 non-silent DMA bytes apiece. Every copied
instruction is compared with the independently decoded module image; sampled
executed RAM instructions are checked against those words. The
[workspace contract](reports/workspace-contract.json) records original module
allocations, source-image bounds and voice data structures. No emulator change,
code injection, sampled-audio substitute or dummy provider is used.

The module-absent ROM fails on the genuine unknown ScreenBlanker SWI. All
undefined exceptions in positive runs are accounted for as software-FPA traps;
there are no data/prefetch aborts. The client exits to seven original desktop
tasks. This gate does not establish physical monitor operation, perceptual
audio accuracy, every channel/pitch combination, module removal with active
voices, or full RISC OS 3.11 compatibility.

```sh
python3 tests/run_standard_utilities.py
```
