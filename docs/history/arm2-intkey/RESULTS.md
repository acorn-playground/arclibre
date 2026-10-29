# Results — genuine A1 keyboard selection

**PASS.** The restored UK territory can now select its keyboard successfully. `Territory_SelectKeyboardHandler` calls the original `Keyboard UK` command supplied by International; the resulting International service reaches IntKey and selects its genuine A1 tables. No replacement command, dummy service or emulator change was introduced.

`artifacts/intkey.rom` is 2,097,152 bytes, with 270,912 bytes used. SHA-256: `7dff5b428ba7c0a073d769c513a93c104c08b8ac1df0be7eca3de8ab5e943faa`.

## Pinned sources and modifications

| Component | Exact revision | Original identity |
|---|---|---|
| IntKey | `e2ab8c65d06e832e7444f73e1ff2bf3a40022583` | InternationalKeyboard 0.36, 27 June 1994 |
| Inter | `e90aa354462e1d0f8826e3f19fc82b31f22c49d3` | International 1.26, 28 October 1994 |

Both are the public **cleaned 3.60 import**, matching the approved cohort. Repositories and per-file hashes are recorded in `manifests/`. Targeted retrieval was limited to these actual dependencies. The earlier kernel, headers, modules and resources retain their exact pins.

Patch **22** selects IntKey's existing `UkPCKeyboard = FALSE` branch and fixes the UK include path for the host build. The historical UK wrapper defaults to a PC keyboard file absent from that snapshot; the original `UK/Source/UkA1Kbd` is present and directly matches the emulated ID-1 A1 keyboard. No PC table was invented or substituted. The patch also adapts ENTRY and relocatable-area syntax and adds conservative ARM2 settling after explicit PSR changes. The existing shared-header adaptations supply the macro-level settling sites. Original A1 translation data and algorithms remain intact.

International, rather than IntKey itself, owns the `Keyboard` command. Its original help-source generator is assembled and its output processed by the previously pinned public Tokenise tool. The original `Resources/UK/Messages` is added as `Resources.Internatio.Messages`, the tenth ResourceFS file. No help strings, country tables or fonts were extracted from ROM images. `artifacts/help-build.json` records tool/dictionary/output hashes.

Patch **23** bounds International's service dispatch by its actual seven-entry table. The recovered public Services header includes newer UCS reasons 7 and 8, and consequently `Inter_Highest = 9`; this 3.60 implementation supports reasons 0–6. A local count derived from the table replaces the global maximum for this dispatch, while retaining the original reason-number assertions and a seven-entry assertion. Runtime tests establish that reasons 7, 8 and 255 remain unclaimed with their parameter registers preserved. No unsupported service is reported as implemented.

Patches 16–21 are inherited unchanged in intent and replayed in this isolated experiment. The finalizer verifies patch replay without fuzz and preserves every source snapshot. Five prior standalone module binaries—FileSwitch, ResourceFS, MessageTrans, TerritoryManager and UK—are byte-identical to the territory milestone. Messages changes only through the genuine added resource. The original kernel is still 145,152 bytes with SHA-256 `cd2c3eb18de6ffab8fabb59406efb50eafd6851c305a58e88e2cc554facfcc30`, and its source tree is unchanged.

## Installed handler and workspace

Independent saved-memory checks follow the kernel's module and incarnation lists, rather than assuming fixed new allocations.

- IntKey has its original **64-byte RMA workspace**. Its first 44 bytes are the 11-word keyboard header. Every pointer field is reconciled against the real ROM KeyStruct1-relative value; the translation count is 101 entries.
- The remaining fields are OldKeyHandler at 44, CurrentKeyboard at 48, CurrentKeyAlphabet at 52, OsbyteVars at 56 and AltDigitValue at 60.
- Kernel KeyVec points to that actual RMA header, with keyboard ID 1 and alphabet 101. OldKeyHandler still points to the resident kernel NewKeyStruct. The original Die routine is retained; unload/restoration was not exercised in this milestone.
- International uses its original **20-byte RMA message-file workspace**. The successful image contains nine real modules, including International and InternationalKeyboard.
- Repeated selection runs IntKey's real setup routine three times. Since it already owns the handler, it does not unnecessarily reinstall/reinitialise it. Subsequent modifier and input tests confirm working state.
- Independently parsed source data matches the complete 404-byte ordinary translation table and 464-byte top-bit table. Backslash is a special-key entry in this module; its top-bit record contains the genuine backslash, vertical-bar and Ctrl values. It is not assumed to have the resident kernel table's layout.

Actual addresses and header values are recorded in `artifacts/selection-verification.json`.

## Execution and verification

| Check | Result across all three cold runs |
|---|---|
| Assembly | Each of eight modules assembles twice normally and once with the observer to identical objects; zero unresolved symbols/relocations |
| Independent ARM2 audit | 15,170 module instructions, 3,277 direct branch targets, 73 settling sites pass; prior kernel audit retained |
| Reset, RAM and mapping | Real reset vector, ARM2/26-bit state, 4 MiB detection, MEMC/CAM/workspace, stacks, vectors and pre-module boundary pass |
| Boot hardware | All 1,916,550 captured pre-module writes independently decoded |
| Natural startup/CAM | All nine real modules loaded, original FileSwitch FSCV installed, three real page-transfer suites pass |
| Existing keyboard suite | All original 56 key events, 32 characters, modifiers, Caps Lock, Escape, 12-character autorepeat and full Help checks pass through IntKey |
| New selection suite | 236 real down/up events and 105 returned characters per run; no guest PC/RAM/input-success injection |
| Repeated selection | Three `keyboard uk` commands succeed; ordinary and Shift input plus Ctrl-U work after each |
| Query and bad selection | `keyboard` reports `UK`; `keyboard nonsense` returns the real Unknown keyboard error `&642`; the selected handler remains usable |
| Special input | Backslash/vertical bar, keypad `65`, Alt-keypad `65` producing `A`, release and subsequent input pass |
| Help | `help keyboard` displays the original translated help/syntax and returns to Supervisor |
| Territory selection | The previously failing real SWI now returns with V clear |
| Territory regressions | 172 client calls per run; full tables, all 24 entry pointers, collation, genuine errors, 40 resource-name variants and unsupported International reasons pass |
| MessageTrans | 46 client calls per run; ten byte-exact public resources, dictionary, substitution, errors and reopen pass |
| Text | Original pre-module font and all 95 printable-ASCII rendering checks retained; full post-module font checked against public International Latin1 definitions |
| Exceptions/state | No undefined instruction, prefetch/data abort, address exception or FIQ in tested paths; all keys released, no stuck repeat or protocol error |
| Repeatability | Stage results, logs and saved machine sections agree across cold runs |
| Preservation | All 7,514 manifest-listed files in seven previous milestones remain unchanged |

International genuinely supplies alphabet glyphs through Service_International. Its Latin1 definition changes **one byte** relative to the kernel's initial font: character 252 (`ü`), row 2, `00 → 66`. The verifier derives the entire post-module font from the original InterFonts source. The early injected text fixture still expects the original kernel font; the natural banner expects the installed alphabet. Printable ASCII and the two complete 163,840-pixel framebuffer comparisons remain unchanged. This expected service effect is documented rather than suppressed.

Execution folders contain real input ticks, kernel key/character events, IOC KART accesses, IntKey routine observations, returned registers/flags, machine-state sections and instruction traces. `artifacts/selection-{1,2,3}/final.png` shows the selection, error recovery and Help result. Guest SWI client fixtures remain separate from keyboard tests and use genuine RMA allocation. `logs/final-validation.log` records final acceptance; runtime suites were executed after the three cold captures. Initial verifier assumptions about resident-handler identity and immutable post-module fonts were updated to verify the actual module contracts, without changing the successful ROM.

MCP also cold-booted the image and executed `keyboard uk` and `keyboard`; the latter printed `UK`. Existing diagnostic facilities were sufficient. No MCP extension was needed.

## Outstanding issues

- The artifact selects the original **UK A1 build only**. Other keyboard layouts, PC/Perth hardware, mouse input, hot/Break reset and module unload/reload are not validated. International advertises names beyond UK; this UK IntKey source maps its country table to the UK structure. No broader layout claim is made.
- International's newer UCS service reasons remain unsupported and unclaimed. Other alphabet switching/font services and locale/date/calendar APIs are not comprehensively exercised.
- Early MessageTrans and territory probes still occur before their modules load. The subsequent services and steady-state tests pass; early missing-SWI events remain in the evidence.
- Optional Portable_Speed and absent Sound_QInit remain observed on idle/Escape. Podule enumeration, ColourTrans and sound startup probes remain absent. The territory manager's missing-territory disc/icon fallback still lacks its real runtime Squash/Wimp/ColourTrans dependencies.
- FileSwitch and read-only ResourceFS are present; disc filesystems, persistence, BASIC and desktop integration are not. ARM3 and physical hardware remain unvalidated.

## Recommended next milestone

Bring up **read-only floppy access with matching FileCore/ADFS sources**, using a generated freely redistributable test disc. First establish the real IOC/floppy and filing-system contracts, then require repeatable catalogue/open/read operations and byte-exact loading of a small freely licensed ARM2 test program. Keep writes, desktop integration and general application compatibility outside that gate, and retain all current regressions.

The final objective remains unmodified **RISC OS 3.11 desktop applications, games and utilities on ARM2/ARM3 Archimedes hardware**. Successful 3.60 component restoration does not establish that compatibility.
