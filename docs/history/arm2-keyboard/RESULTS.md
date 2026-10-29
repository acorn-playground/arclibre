# Keyboard restoration and execution results

## Outcome

Keyboard input works at the genuine Supervisor prompt on MacArch's A440/1, ARM2, 4 MiB configuration. All three fresh cold boots pass the bounded suite. Each boot follows real reset, memory detection, workspace/vector setup and natural startup before keyboard testing. No guest PC/register/RAM injection is used in the keyboard suite. Separate retained CAM and text fixtures still use their documented test-owned guest programs.

The image contains the kernel and its existing UtilityModule only. The original 3.60 cohort and patches 1–13 remain unchanged as inputs. No ROM resources, proprietary binaries or new runtime module were added.

## Defect and changes

The prior image reported keyboard ID 1 but had `KeyVec = &FFFFFFFF` and scanning disabled. Its build selected `AssembleA1KeyHandler = FALSE`, leaving translation to an absent module. The baseline MCP captures in `traces/` and `artifacts/no-input.macarch-state` record the failed input experiment.

Patch **14** selects the existing resident handler when `MEMM_Type = MEMC1` and `Keyboard_Type = A1A500`. This uses the original `KeyStructInit`, `NewKeyStruct`, translation tables and IOC serial driver from the pinned public sources. It does not invent a handler or replace services with stubs. Other machine configurations retain the disabled setting.

Patch **15** expresses two legacy backslash/vertical-bar table entries as the intended four bytes `5C 7C 1C 1C`. AsAsm interprets the original backslash string escape and trailing comment backslash differently, corrupting table lengths when this previously excluded code is assembled. Both table-width assertions remain enabled. Independent checks verify the emitted entries in both old and new tables. Only `Kernel/s/GetAll` and `Kernel/s/PMF/key2` differ from the preceding milestone; the patches replay without fuzz.

## Execution checks

| Test | Observed result on each of three runs |
|---|---|
| Ordinary typing | `abc` produces ASCII 97, 98, 99 and visible `*abc` |
| Backspace | ASCII 8 removes `c`, leaving `*ab` |
| Left and right Shift | `D`, `E`, then unshifted `f` after release |
| Ctrl-U | ASCII 21 clears the line; subsequent unmodified `u` works |
| Caps Lock | `A` while enabled, then `b` after disabling; LED byte 2 → 3 → 2 |
| Escape | ASCII 27 cancels the line, displays `Escape`, returns to the prompt |
| Autorepeat | One 1.2-second `x` hold produces 12 characters; no further characters for 0.95 seconds after release |
| Recovery after repeat | Ctrl-U followed by `a` produces a normal new line |
| Return and command dispatch | `help` plus ASCII 13 reaches the real Help handler once |
| Released state | All host keys up, 160-bit kernel KeysDown bitmap clear, CurrKey/OldKey = FF, protocol idle and queues empty |

Per run, 56 actual down/up events match 56 kernel key events in order, each delivered within 10 ms of guest time. There are 32 character returns and 226 observed IOC KART accesses. Two additional KEYV reason-3 calls request the real LED changes. No keyboard protocol errors or undefined/abort/address exceptions occur. Final instruction counts, ticks, keyboard states, logs and RAM/MEMC captures agree across all three runs. IRQs remain active throughout input.

`artifacts/keyboard-{1,2,3}/` contains input ticks, KEYV/character/KART logs, stage register/workspace/screens, raw keyboard sections, final complete machine snapshots, instruction traces and PNG captures. `scripts/verify_keyboard.py` checks these separately from the harness.

## Genuine remaining runtime dependencies

`*Help` prints `==> Help on keyword Help`, then `NoSuchSWI1:SWI &%0 not known`, and returns to the prompt. Trace identifies missing `MessageTrans_Lookup` (&41502), `MessageTrans_OpenFile` (&41501) and `MessageTrans_Dictionary` (&41509). Thus **Help dispatch passes; complete Help output does not**. The unexpanded error text is another consequence of missing MessageTrans, not font corruption.

The first idle input wait probes absent `Portable_Speed` (&42FC0) and tolerates the failure. Escape invokes absent `Sound_QInit` (&401C0) and MessageTrans; cancellation still works. No dummy module or success handler was installed. These observations extend, rather than remove, the prior list of missing Podule, ColourTrans, Sound and MessageTrans services. FileSwitch and filing-system drivers remain absent; the inherited default FSCV handler is not a filing-system implementation.

## Retained verification

- Two normal AsAsm assemblies and one observer assembly yield identical objects: 145,152-byte kernel, zero unresolved symbols and relocations.
- Independent ARM2 decoder: 27,870 instructions, 5,054 direct branch targets, 198 bank-settling checks and the existing same-mode dispatcher exception; no opcode failures.
- Original emitted-routine checks pass, including 10,240 CAM encoding cases and hardware queries.
- Three fresh reset-to-pre-module runs pass RAM detection, fixed mappings, copied dispatch/vector code, stacks and 26-bit state checks. All 1,916,550 pre-module hardware writes from the first run are independently decoded.
- Three natural startup continuations and three real dynamic-area suites pass the prior partial-shrink, heap/RMA transfer, physical-content and CAM invariants. The prior immutable negative-control captures still establish the pre-patch-13 failure; they were not rerun or relabelled as this image.
- Soft-font bytes, 95 printable glyphs and two full 163,840-pixel display comparisons pass.
- Checksums verify all 2,874 manifest-listed files in the four preceding milestones remain unchanged. The MacArch core revision and recorded source hashes are unchanged.

The initial validation wrapper ended because the independent keyboard verifier had not yet been written. Its subsequent execution and final acceptance pass are recorded in `logs/final-validation.log`; the retained guest captures all come from the completed three-run execution. The completed wrapper now includes all validation steps.

## Source and licensing

Kernel source pin: `3da129d209b2c78d19f6c28d9a8f15cd6f1c3bfc`, with the approved 3.60 header/workspace cohort and patches 1–13 inherited from `arm2-cam-transition`. No revision substitution or additional source archaeology was needed. Source notices and the Apache-2.0 license are retained. New patches and harness/script source are Apache-2.0. The normal and observer AsAsm tools remain build-time dependencies from the preceding restoration. MacArch core at `550bee4842e45eafdf331f0d06e11df1368403e8` is an unchanged GPL-3.0-covered host test dependency; its license is included. No emulator executable is included in the evidence archive and no emulator code is linked into the ROM. Native build/cache products are excluded from packaging.

## Recommended next milestone

Integrate the matching public MessageTrans implementation and its genuine message/dictionary resources, following its actual dependencies and licensing. Require successful `*Help`, readable error lookup, return to the prompt and all current regressions across cold boots. If this requires ResourceFS or another real resource provider, include that dependency explicitly in the proposed bounded module milestone.

Do not treat the resident UK keyboard tests as international keyboard, mouse, Break/reset, ARM3, physical-hardware or application/game compatibility validation. Those remain separate work. No desktop integration was started. Existing MCP and public core diagnostics were sufficient; no MCP extension or emulator change was required.
