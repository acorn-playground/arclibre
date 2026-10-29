# Results — matching UK territory integration

**PASS for the bounded milestone.** Genuine TerritoryManager and UK implementations from the public cleaned 3.60 import register and execute on the original A440/1 ARM2 configuration. All three fresh cold resets and their test continuations agree. The ultimate requirement remains unmodified **RISC OS 3.11 desktop applications, games and utilities**; this milestone makes no such compatibility claim.

The ROM is `artifacts/territory.rom`, 2,097,152 bytes, with 252,544 bytes used. SHA-256: `e5d6697f0825a9016c0c961c261f4fc8041334ef9ae74eaa14f7c0623ae398d3`.

## Source cohort and changes

The unchanged 145,152-byte kernel retains SHA-256 `cd2c3eb18de6ffab8fabb59406efb50eafd6851c305a58e88e2cc554facfcc30`. Its complete source tree matches the keyboard milestone. Existing module pins remain those recorded in the MessageTrans milestone. Exact repositories, revisions and individual file hashes are in `manifests/`.

| Added input | Revision | Use |
|---|---|---|
| TerritoryManager | `e2654fe5c068ae403d13cb09f03e5162895a736f` | Manager, interface and original SystemDisc sprite |
| Original UK repository | `55aa82c8862f02d9db5bb4b2a9350dc8baf97192` | UK code, character tables and message resource |
| Squash | `a21ce91e3d0a1a8c04f3e0dd72683a6d7fa2ab76` | Existing header plus host asset compression/decompression algorithms |

The later combined TerritoryModule implementation is **not** used at runtime. A narrowly scoped later resource/license comparison is retained separately in `licenses/uk-resource-provenance/`.

Patches 16–18 are preserved from the preceding module integration. New patches are:

- **19:** adapt ENTRY/ORG syntax, quoted backslashes, compressed sprite filename and the Territory SWI allocation. The original allocation expression double-counted the public system base; registration now uses the published `TerritorySWI_Base = &43040`. Add the one required conservative ARM2 PSR settling instruction. No character values or algorithms change.
- **20:** remove unused `kernel.h` includes from the portable Squash compressor/decompressor in the isolated work tree. Compile with unsigned-char semantics matching Acorn C. The host driver reproduces MakeSprite's normal compression and uses the matching original decoder to verify the entire 22,072-byte asset. Two runs yield identical 1,591-byte streams. No compressed asset is extracted from a ROM.
- **21:** assemble all six movable modules in relocatable read-only code areas, instead of `ORG 0`. Module-relative header expressions resolve completely: **zero unresolved symbols and zero relocation records**. The ROM packer needs no relocation engine.

Patch 21 fixes a real integration defect. With an absolute area, AsAsm's ADRL optimiser can choose `MOV #offset` when it is shorter than PC-relative ADD/SUB. The first territory client reached a stored TransformString entry of `&1900`, instead of its ROM address, and entered unrelated low-memory contents. The same optimisation affected NameToNumber, a manager error-title pointer and FileSwitch paths. The relocatable area expresses the actual module contract and prevents these optimisations. The rejected ROM and failure instruction trace remain under `artifacts/negative/`; they are not the delivered image. A new static gate rejects ADR/ADRL emissions that materialise absolute offsets. The runtime gate checks all 24 UK entry addresses against real decoded ROM instructions.

The observer assembler also needed a null-caller guard when emitting an end-of-file literal pool after LNK/END. `patches/asasm-observation-eof.patch` and `scripts/build_observer.py` modify only an isolated host tool copy. Its objects match both normal assembler runs exactly. No instruction encoding logic is modified.

## Memory and interface contract

The original public layouts are retained; no structures or handlers were invented.

| Structure | Contract |
|---|---|
| TerritoryManager RMA workspace | 160 bytes; message descriptor/flag at 0, territory-list head at 20, 20-byte scratch area at 24, configured territory at 44, 100-byte error area at 48, original alignment |
| Territory registration block | 112 bytes: next link at 0, number at 4, UK workspace pointer at 8, 25 copied words starting at 12 |
| UK RMA workspace | 224 bytes: message descriptor/flag at 0, timezone-name word at 20, 100-byte scratch area at 24, 100-byte error area at 124 |
| Reachable UK entries | 24 genuine routine pointers. The manager reserves SWI offsets 34–52 before territory dispatch, so nominal entry 24 is unreachable. Both ends of that reserved interval return the original range error; no 25th implementation is invented |
| ResourceFS | Prior seven byte-exact resources plus `Resources.TerrMgr.Messages` and `Resources.UK.Messages`; original pack structure and dictionary unchanged |
| Module chain | UtilityModule, FileSwitch, ResourceFS, MessageTrans, Messages, TerritoryManager, UK |

Independent inspection of each natural-boot snapshot follows the kernel module/incarnation lists to the genuine RMA workspaces. It checks the configured territory, linked registration block, UK workspace pointer and every reachable entry address. `artifacts/territory-verification.json` records the actual addresses.

## Verification

| Gate | Result |
|---|---|
| Assembly reproducibility | Two normal and one observer assembly per module are byte-identical |
| ARM2 decoding | 14,454 module instructions, 3,166 direct branches, 65 PSR/user-bank settling sites; no unresolved symbols/relocations |
| Original kernel | Byte/source identity plus all earlier static checks retained |
| Cold boot | Three actual resets pass ARM2/26-bit state, RAM detection, MEMC/CAM, workspace, stacks, exception vectors and pre-module boundary |
| Hardware accesses | 1,916,550 pre-module writes independently decoded, with raw compressed logs retained |
| CAM/dynamic areas | Three natural continuations and three real page-transfer suites pass |
| Keyboard | Three identical suites: 56 key events, 32 returned characters, 12 repeated characters, 226 KART accesses each; modifiers/editing/Escape/full Help retained |
| MessageTrans | 43 real client calls each run, nine byte-exact ROM resources, dictionary expansion, substitution, error and reopen tests |
| Territory clients | 157 real client calls per run; current/explicit UK, alphabet 101/Latin1, write direction, 17 complete tables, NameToNumber, TransformString and Collate |
| Tables | Independently parse every original literal: 2,816 property bits, 1,296 conversion/representation bytes; compare all returned bytes and actual ROM addresses |
| Resource case handling | Original, lowercase, uppercase and mixed-case forms of all nine resource names resolve to identical data addresses and bytes: 36 variants |
| Genuine errors | Unknown property, absent territory and both reserved-SWI boundaries return readable V-set errors; no success substitutes |
| Text | Original font and two complete active-display pixel comparisons pass |
| Repeatability | Saved results, SWI traces, instruction traces and machine states match across the three territory runs |
| Preservation | All 5,784 manifest-listed files across six earlier milestones remain unchanged |

The guest-client fixtures use a small real SWI caller in application RAM and allocate client data through OS_Module RMA claim/free. They do not replace runtime services. Natural boot and keyboard tests do not inject guest code. Complete call arguments/results/flags, exception counts, SWI logs, final instruction windows and memory states are saved in `artifacts/territory-{1,2,3}/`. Boot and keyboard hardware traces remain in their respective folders. No undefined instruction, abort, address exception or FIQ occurred in the successful tested paths.

The final image was also cold-booted through MCP. `Territories` printed `1 UK`; `Type Resources:$.rEsOuRcEs.uK.mEsSaGeS` displayed the original resource text through the actual keyboard/CLI/FileSwitch path. The transcript and snapshot are included. Existing MCP capabilities were sufficient.

## Outstanding issues and next milestone

1. **Keyboard selection:** `Territory_SelectKeyboardHandler` calls the original `Keyboard UK` command. That command is absent and returns `File 'Keyboard' not found`; the test records the real error. Resident A1 input remains working. Resolve this contract with the matching public international keyboard implementation (IntKey), first checking its original-machine/A1 support, while preserving current input, modifier, repeat and Escape tests. This is the recommended next bounded milestone.
2. **Startup ordering:** early FileSwitch/ResourceFS probes precede territory registration and still log missing case-table SWIs. The later real services and all steady-state case-folding tests pass. Early MessageTrans probes similarly precede its provider. These events are retained, not removed from logs.
3. **Other runtime dependencies:** Portable_Speed and Sound_QInit remain absent on the tested idle/Escape paths. Startup also probes podule enumeration, ColourTrans and Sound_ControlPacked. The missing-territory disc/icon fallback retains its real Squash/Wimp/ColourTrans calls, but those providers are absent and that fallback has not been validated. The rebuilt sprite is not evidence of a complete runtime Squash service.
4. **Unvalidated APIs:** all code is instruction-audited, but date/time/calendar conversion, territory switching/deregistration, locale edge cases and failure paths are not comprehensively executed. The original manager's ConvertTextToString is explicitly marked unsupported in upstream source; it has not been replaced or claimed to work.
5. **System scope:** only the read-only ROM ResourceFS is supplied. No disc drivers, persistence, BASIC, desktop, mouse, Break/reset handling, ARM3/physical-machine validation or general application/game compatibility are claimed.

No emulator code, prior source snapshot or prior artifact was changed. The 3.60 cohort is a reconstruction baseline, not a substitute for the final RISC OS 3.11 compatibility target.
