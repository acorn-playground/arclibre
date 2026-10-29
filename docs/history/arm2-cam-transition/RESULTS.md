# CAM transition findings

## Root cause and repair

The failure was not an initially missing CAM mapping. The pinned legacy configuration has `UseFreePool=false` and allocates its remaining RAM directly to application space. Startup calls `OS_ChangeDynamicArea(0, -4 MiB)` to shrink the system heap as far as possible after module initialization.

The heap begins at `&01C02000`, has size `&6000`, and at this point has `hpdbase=&1C0`. Only `&5E40` bytes are unused, less than one 32 KiB MEMC page. The correct result is therefore **zero pages moved**, restoration of the heap's unlocked size and the real `NotAllMoved` result (`&1C1`). The existing reset caller deliberately proceeds after that best-effort request.

In `ChangeDyn`, the shortfall path's branch past `testrestoreheapend` was inside the `UseFreePool` conditional. With that feature disabled, execution fell into the out-of-line helper without a `BL`. Its `MOV pc,lr` used the stale LR from the earlier interrupt-state save and jumped back into the heap-locking sequence. R10 then held a byte count rather than a descriptor pointer. The second pass read zero as the heap size, underflowed the available-byte calculation and attempted a 4 MiB move from nonexistent logical address `&01BFA000` to application end `&003B0000`. The CAM search correctly reported failure.

Patch 13 moves the existing forward branch outside that conditional. Both allocation models now skip the helper and reach the existing size-rounding and partial-result logic. No error is suppressed, CAM entry invented, workspace changed or service replaced. The free-pool-enabled path retains its existing branch behavior; it was not independently executed in this ARM2 configuration.

The independent baseline negative control reproduces the original failure, including exhausted CAM index `&FFFFFFFF` and old address `&01BFA000`. Recorded MCP instruction history also shows the uncalled helper, stale return and second heap-locking pass. The repaired branch is at `&03806D48`, preceding the relocated helper at `&03806D4C`; its target is verified from the emitted instructions.

## Execution results

| Checkpoint | Instructions | 24 MHz master ticks |
|---|---:|---:|
| Original pre-module boundary | 15,369,106 | 183,078,399 |
| Startup heap-shrink entry | 15,385,614 | 183,284,514 |
| Correct heap-shrink return | 15,385,787 | 183,286,923 |
| First Supervisor input-loop entry | 16,172,228 | 193,977,486 |

The prompt is reached after **8.08239525 emulated seconds**. All three cold-start continuations produce identical checkpoint registers and exported machine state. At the Supervisor boundary the exception counters record 4,516 SWIs and 118 IRQs, with zero undefined-instruction, prefetch/data abort, address or FIQ exceptions. These counts prove observed paths, not exhaustive exception coverage.

The startup shrink leaves hardware CAM entries, write ordering, software CAM, page tables and application extent unchanged. The heap descriptor is restored to its original size. Its real partial-result error is `NotAllMoved`, not `CAM Map Corrupt`; no CAM lookup or mapping write occurs for this zero-page result.

## Actual page-transfer contract

Test-owned ARM2 programs at application address `&8000` invoke the real `XOS_ChangeDynamicArea` SWI. They do not patch handlers, install return-success routines or fabricate mappings. A separate guest program writes and reads the marker `&51A7C0DE` through a newly mapped heap page. Each suite starts from a fresh cold boot's pre-module snapshot and repeats identically three times.

| Operation | Expected and measured result |
|---|---|
| Oversized initial heap shrink | Zero bytes moved, genuine partial-result error; all mappings retained |
| System heap +32 KiB | Physical page 127 moves from logical `&003A8000` to `&01C08000`; application end becomes `&003A8000`; heap size becomes `&E000` |
| Guest write/read, then heap −32 KiB | Marker is stored in physical RAM at `&003F8000` and survives the page's return to application logical `&003A8000`; original extents restored |
| Heap +64 KiB | Physical pages 127 and 126 move to `&01C08000` and `&01C10000`; heap size becomes `&16000` |
| Request heap −4 MiB | Exactly 64 KiB is returned; `R1=&10000`, V set, genuine `NotAllMoved`; minimum heap and original application extent retained |
| RMA +32 KiB / −32 KiB | Physical page 127 moves to `&01808000` then back; RMA size grows from `&8000` to `&10000` and returns; application accounting and original CAM restored |

The original SWI implementation returns the **magnitude** moved in R1 even for shrink requests. The host fixture initially expected a signed return, then was corrected to the source's actual contract; no kernel return convention was changed.

Every captured stage independently reconstructs all **8,192 MEMC page descriptors** from the raw CAM programming addresses and sequence values, compares all **128 packed software CAM entries**, and checks page alignment and lack of unintended aliases. Mapping changes are restricted to the expected physical pages. Hardware CAM write counts advance by exactly eight over the full transfer suite. The startup continuation makes none for the zero-page shrink.

## Regression coverage and provenance

- Two normal assemblies and one observer assembly produce identical AOF output with zero imports or relocations. The unchanged independent ARM2 checks accept 27,751 instruction words, 5,041 branch targets and 198 settling sites; bounded routine tests also pass.
- All original reset/MEMC/RAM/workspace/vector/stack checks pass on three cold boots. The complete pre-module hardware capture again contains 1,916,545 decoded writes without log loss.
- The font alignment repair remains intact. All 1,792 font bytes and 95 printable ASCII glyphs pass, and both captured active displays match independent decoding of all 163,840 framebuffer pixels.
- The natural prompt capture allows four display frames to settle. An earlier three-frame capture caught a cursor blink after scanout, giving eight framebuffer/display differences at the cursor underline. The final settled capture matches exactly; no rendering or emulator change was made to address that observation timing.
- All earlier restoration, first-boot and font-repair checksum manifests remain intact. Only `Kernel/s/ChangeDyn` differs from the font-repaired source tree. The additional patch replays without fuzz.
- MacArch's core remains unmodified at commit `550bee4842e45eafdf331f0d06e11df1368403e8`. Pre-existing user changes in two app UI files were left alone. No MCP extension was needed.

Kernel size remains 142,148 bytes. The source-level branch adds one executed instruction to the affected path; existing alignment padding absorbs its image-size increase. The same 2 MiB packaging and zero module-chain terminator remain in use. No runtime payload was added.

## Runtime boundary and next milestone

Only **UtilityModule** is present in the live module chain. `OS_FSControl` reaches the original `FSCV` default `NaffVector`, which claims the call and clears V without implementing filing-system operations. Thus a V-clear return from the configured filing-system selection does **not** mean FileSwitch or a filesystem exists. This behavior was observed, not introduced as a workaround.

The following unavailable module SWIs were observed on the natural continuation:

- `Podule_EnumerateChunksWithInfo` (`&4028A`)
- `MessageTrans_OpenFile` (`&41501`) and `MessageTrans_Lookup` (`&41502`)
- `ColourTrans_InvalidateCache` (`&40750`)
- `Sound_ControlPacked` (`&40186`)

The kernel's existing error/fallback paths allow entry to Supervisor. This does not implement the missing services. See runtime-dependencies.json and the per-run `events.log` files for evidence and counts.

The next milestone should select a minimal lawful, coherent runtime module set for **real filing-system and message services**, with explicit APIs and a stopping point before desktop launch. Retain this ROM and the page-transfer fixtures as regression baselines. Broader dynamic-area operations, exception/callback tests, other memory sizes, ARM3, actual hardware and unmodified RISC OS **3.11** applications/games remain unverified. Do not substitute 3.60 version identity or a Supervisor prompt for that compatibility requirement.

## Evidence and licensing

The acceptance report hashes the verification reports. Native snapshots, CPU traces and memory/device sections are in `artifacts/natural-*`, `artifacts/fixtures-*`, `artifacts/negative` and `artifacts/repeats`. traces preserves the recorded MCP experiment calls, including the old failure and corrected return.

The kernel retains the pinned public-source Apache-2.0 notices and previous patch provenance. This patch and new harness/scripts are supplied under Apache-2.0. The separate host emulator remains GPL-covered; its GPLv3 text is included. Native tool/harness binaries and compiler caches are excluded from the evidence archive. No proprietary ROM, ROM-derived resource, new target module or desktop asset was used.
