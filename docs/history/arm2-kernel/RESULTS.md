# Assembly result and stop decision

25 October 2026. Target: original A440/1, ARM2, IOC-A1, MEMC1a/MEMC1, VIDC1a, WD1772, original keyboard interface. Scope: one kernel component, static assembly only.

## Result

**FAIL: the exact proposed kernel/header combination does not have ARM2 assembly/architecture closure.** An open-source assembler and help generator are available and run locally, built with the installed Apple Clang/macOS SDK. The remaining substantive blocker is the selected kernel's integration with later memory-management and hardware assumptions. No valid kernel object, raw kernel component, instruction listing, symbol map or executable byte-range map exists for this attempt. No ROM was joined, loaded or executed.

The final normal assembly exits **1**. It records **31 error diagnostics and 54 warnings** before AsAsm's normal error limit stops it. These counts describe the retained diagnostics, not independent defects. See structured diagnostics and the complete reproduction log. Earlier failed attempts remain under `logs/`.

The first pass traverses the entire selected include graph, including MEMC1, VIDC1 palette code, A1 keyboard code, system font and AMB source. It is not a successful assembly: forward references are resolved later. A separate `-no_code_gen` investigation traversed that graph but hit an AsAsm output-phase assertion and exited by SIGABRT. An increased-error-budget diagnostic build also hit a literal-pool consistency assertion after recording more second-pass errors. Neither run is treated as a pass or a complete error inventory. The normal assembler was restored for the final reproduction; empty/partial `kernel.aof` files are removed on failure.

## Inputs and completed work

| Input | Exact revision | Actual role |
|---|---|---|
| Kernel | `24044755f08dc3b99779833a57eecf3899561ce6` | Candidate source, old workspace, font and help strings |
| HdrSrc original | `c9113ab79d9ca2ccc49a9b7518911132ca9ffa1b` | A440 machine, ARM2/Generic26, IOC, MEMC1, VIDC1a, macros and token dictionary |
| HdrSrc later | `403c6dd8bce92d0629634cbf57f68f43b2f30d38` | Missing global public interface exports; hardware selection never taken from it |
| BuildSys | `5a1cb51c56a0c7c8b648c63d09f17ecae98d004a` | Recipe/export reference only; not an assembly input |
| Other interfaces and tokenise | Full pins | Exact audit `twentysix` revisions, no moving branch substitution |
| GCCSDK AsAsm | `212d4567f007e7d30f4af3d6e1919a3d8a115b1c` | Newly selected public tool source, AsAsm 2.01 |

The initial plan labelled the later HdrSrc pin “comparison only”. The build needed its global interface definitions absent from the 1996 HdrSrc snapshot, including SWIs, CMOS and NewErrors. These were explicitly exported as a build adaptation using that same audited revision. Original machine/CPU/IO/MEMC/VIDC and macro headers retain priority. The export map makes this hybrid visible; it is not claimed to be a historically shipped configuration.

There are 352 recovered source/reference files, 137 exported headers and 134 distinct actual assembly inputs including the generated wrapper. The included components plus the help generator have 17 component licence records. The actual-input manifest links each file to its original hash, build hash, revision, licence and modification status. No missing header was replaced by a stub. The generated help text comes from the pinned Kernel `HelpStrs`, original HdrSrc `Tokens` and public `tokenise` source.

## Why this is an architectural blocker

The following references are to the **unmodified pinned source snapshots**, so they remain stable independently of inserted modification comments.

1. **Cold reset calls code unavailable on the selected memory controller.** NewReset:2158 unconditionally calls `L1L2PTenhancements`, then `InitVariables`, then `AMBControl_Init`. The sole definition of `L1L2PTenhancements` is in ARM600:3800, which the MEMC1 configuration correctly excludes. That routine accesses `MMUControlSoftCopy`, `L1PT`, `L2PT` and IOMD ROM timing registers. It is not a missing generic header or an external module to link. The assembly log reports the call as an implicitly imported symbol.
2. **The included application memory manager is not a MEMC1 implementation.** GetAll:773 includes `s.AMBControl.AMB` without a MEMC feature gate. AMBControl/main:64 reads `PhysRamTable`; Options:33 fixes pages at 4 KiB; memmap:47 updates ARM600-style level-two tables. The old workspace does not define those structures. Its presence in the ROM is not merely unused data: hard reset invokes its initializer.
3. **The reset/CAM contract has drifted.** NewReset:1754 combines the original system-heap page protection with `PageFlags_Unavailable` before the nearby ARM600 conditional. That flag belongs to the newer memory-management scheme and is undefined in the selected original workspace. `ResetType` and later `RawMachineID` references likewise do not have the required old-workspace definitions. Filling them with guessed addresses or zero-valued constants would conceal the contract mismatch.
4. **A selected public hardware query assumes IOMD.** Middle:1531 reads `IOMD_Base`/`IOMD_ID0` and a table of IOMD part IDs without an original-IOC alternative. The second pass faults on these operands. Supplying the IOMD constants would make assembly appear closer while retaining accesses to the wrong hardware.

Several initially similar failures were ordinary configuration issues and were resolved: the Chocolate optimisation switches, 32-bit foreground interrupts, A7000 VCO fix, later sound/LCD options, inactive pointer-code indentation and missing feature declarations. The remaining points above require a reviewed restoration of machine abstractions/workspace/API behaviour or a different coherent historical source set. They are not repaired by changing assembler flags.

No calls were replaced with returns, no later hardware was emulated in the build, no missing structures were fabricated, and the ARM600 memory implementation was not imported under an ARM2 label. Work stopped at this boundary as requested.

## What was verified about ARM2

- The actual include trace selects the original A440 header, `CPU/ARM2`, `CPU/Generic26`, `IO/IOC-A1`, `MEMC/MEMC1a`, `MEMM/MEMC1`, `VIDC/VIDC1a`, `Old/NewSpace`, `s/MEMC1`, VIDC1 palette and A1 keyboard paths.
- Source mode values are USR/FIQ/IRQ/SVC = 0/1/2/3; interrupt masks occupy PSR-in-PC bits 27 and 26. ROM is `0x03800000`, IOC `0x03200000`, VIDC `0x03400000`, MEMC `0x03600000`; the remaining source layout is recorded.
- Six independently specified instruction words from an original smoke fixture match the assembler output exactly, including `TEQP`, `MOVS pc,lr`, exception return and `LDM ... pc^`. The host IEEE-754 layout adapter also passed its native layout test.
- **`-cpu=ARM2` is insufficient as a validation gate.** The negative fixture deliberately assembles `MRS` and `SWP`; AsAsm emits warnings and exits zero. Future successful kernel assembly still requires explicit opcode/range and reachability checking, especially macros emitting `DCD` words.

There is **no resulting kernel code to certify**. Source selection and a tool smoke test do not prove ARM2-safe startup/IRQ/FIQ/SWI/abort execution, internally consistent workspace, or bootability. No trustworthy kernel size can be inferred from first-pass progress messages. The 2 MiB `ImageSize` header is a prospective ROM configuration constant, not an achieved footprint.

## Remaining issues

| Issue | Status / implication |
|---|---|
| ARM600 reset/AMB assumptions and old workspace | Architectural blocker described above |
| IOMD-only hardware query | Requires an original-machine implementation/selection decision |
| Relocated reset-vector branch | `B MOSROMVecs+IRQ_Test_CTRL_or_R_Pressed` exceeds AsAsm's ordinary signed branch range; 26-bit wrap/relocation semantics need a targeted verified adaptation, not a blind offset change |
| AAsm dialect completeness | ENTRY shadowing was repaired; ADR/ADRL and subsequent pass-size diagnostics remain. Some later redefinition errors follow earlier invalid operands and cannot yet be treated as independent source defects |
| AsAsm diagnostic robustness | Increased-budget and no-code-generation investigations assert; recorded separately from the kernel failure |
| Machine header generation gap | Explicit reviewed switches provided, but this hybrid is not a historical build lock |
| Emitted instruction/range audit | Not possible until a valid resolved component exists; no coverage claim |
| Boot, ROM size, complete payload licences | Not attempted / not established |
| RISC OS 3.11 desktop and applications | Entirely untested; later kernel version strings, later API headers and the selected Latin-1 bitmap font do not establish 3.11 behaviour |

## Recommendation

Do **not** proceed to boot testing, desktop integration or ROM joining from this result. The Phase-0 assumption that the immediate pre-April-2000-conversion kernel would be a useful near-buildable ARM2 base has been weakened: relevant original-machine code survives, but the last pre-conversion commit is not the last coherent ARM2 build.

The next milestone should be a bounded **historical source-coherence investigation**: identify and pin the newest published kernel/header/export set before these unconditional ARM600/AMB/workspace changes, verify its available licences and dependencies, and repeat this assembly gate. Do not assume that such a complete published snapshot exists. If it cannot be found, produce a reviewed kernel-only restoration design with the required workspace and hardware/API changes before authorising that port. Preserve the RISC OS 3.11 behavioural target throughout; success with Risc PC or a later desktop is not a substitute.
