# Read-only filing robustness — PASS

The unchanged restored ROM passed fourteen filing scenarios from each of three independent cold-derived A440/1 ARM2 4 MiB Supervisor states: **42 scenarios and 885 host-issued filing/test SWIs**, plus genuine application SWIs. Register results, timings, FDC/SWI logs and captured memory repeat identically. All mounts remained write-protected with zero overlay writes. No undefined instruction, prefetch abort, data abort or address exception occurred.

The experiment found and repaired a real **MacArch media-change signaling defect**. The ROM required no changes. The isolated patch was subsequently applied to the MacArch checkout at the user's explicit request; see the application record below.

## Fixtures and actual execution

The original generator creates four 800 KiB images: D-format old-map and E-format new-map discs, each with A/B identities and distinct RootText contents. There are seven files, two directory levels, a zero-length file, metadata/attributes, and a 38,895-byte pattern. E-format object 6 occupies three noncontiguous extents, separated by other allocated objects; another object exercises shared-sector addressing. An independent verifier walks the encoded E map and reconstructs the fragmented file without using the generator's extent list. MacArch's independent host decoder also validates the directory tree; the decisive checks execute the original guest FileCore/ADFS code.

Each valid-format suite makes 118 host-issued calls. These cover case-folded catalogue lookup, one-entry directory pagination, wildcard filtering, nested/relative/parent paths, input handles, lengths, sequential and positioned reads, partial transfers, EOF carry, byte reads at EOF, closed-handle errors and whole-file loads. Buffer guards prove no writes before or beyond transferred data. Every loaded file is compared byte-for-byte. Random reads cross both fragmented-file boundaries and EOF.

The original 280-byte `CheckFile` application is loaded through real OS_CLI and observed at &10000 in USR26 with PSR zero. Its 48 independently decoded ARM2 instructions open the fragmented file, check the extent, read through OS_GBPB, check OS_BGet EOF, close, calculate checksum 4,958,583, select the success message, call OS_Write0 and exit through OS_Exit to Supervisor. Host inspection independently verifies the complete 38,895-byte guest buffer at &20000. The checksum/selected message is captured before OS_Write0; Supervisor re-entry clears the display, so the final screen is not used as the application's success oracle. This is an original diagnostic application, not evidence of unmodified third-party application compatibility.

## Faults and recovery

Ten fault fixtures alter only generated media. Their encoded changes are independently checked:

| Fault | Guest result |
|---|---|
| D/E root directory checksum | &108A8, Broken directory |
| Both E map checksums invalid | &D6, requested file not found; not claimed as a precise map-corruption diagnostic |
| First E map checksum invalid | Correct complete data recovered from the second map |
| Missing data sector, D/E | &100108C7, Disc error 10 |
| ID CRC, D/E | &180108C7, Disc error 18 |
| Data CRC, D/E | &080108C7, Disc error 08 |
| Empty drive with patched signaling | &108D3, The disc drive is empty |

Every fault is bounded to 60 emulated seconds and followed by real mount/dismount and an exact successful read from clean media. The empty-drive case returns without the harness's fallback Escape input, then succeeds after insertion. No guest error handler is replaced and no success result is injected.

## Demonstrated emulator defect and repair

On baseline core `550bee4842e45eafdf331f0d06e11df1368403e8`, read disc A, eject, wait one emulated second, insert B, wait one second, and read again: ADFS returns cached **A** bytes despite **B** being mounted. A real `ADFS:Dismount :0` makes the subsequent B read correct. `artifacts/baseline/media-change-baseline/` records this as `KNOWN_BASELINE_DEFECT`, not PASS.

The pinned original ADFS `s/Adfs15:OldDoPollChanged` reads IOC IRQB4 on A1 and pulses latch A bit 7 high/low/high to clear the drive-change signal. It distinguishes a persistent signal (empty) from a cleared one (changed). Baseline MacArch's WD1772 drive insertion/ejection path did not drive that signal; its similarly named IOC bit was used only by the later controller. This explains the stale cache while the motor remains running.

`patches/macarch-original-disc-change.patch` adds per-drive media-change latches, routes the selected original-machine change/empty signal to IOC IRQB4, clears it through the existing latch A reset line with media present, and persists the latches in an optional snapshot header field. It leaves A3000 and later IO wiring unchanged. These are device behaviors, not FileCore cache invalidation or synthetic guest success handlers.

With the patch, the same A/eject/B sequence reads exact B bytes **without dismount or reset** on all three cold-derived runs. Four synthetic unit tests cover insertion, direct replacement, ejection, empty-drive reset, independent drives, IRQ masking, excluded models, and old/new snapshot restoration. All pass. This validates the modeled original-machine protocol; it is not a physical floppy timing certification.

At the user's request the exact verified patch was applied, uncommitted, to the MacArch checkout on HEAD `6409c6c0b74174d19be6755197c28f2c1f8f2755`. Relative to the tested baseline, that checkout adds only an unrelated core library catalogue and its tests. The four changed/new files match the verified patch hashes, `git diff --check` is clean, and all four focused tests also pass against that checkout. `artifacts/applied-emulator-patch.json` and `logs/applied-disc-change-unit-tests.log` record this. The patch subsequently appeared in commit `369fb26` with a clean working tree while packaging was in progress; this agent did not create that commit. **This agent did not rebuild or restart application/server binaries.** The 42 full runtime scenarios were run against the pinned isolated core plus the patch, not against a rebuilt current MacArch application.

## Retained checks and provenance

All previous suites were rerun against the isolated patched core: three reset/RAM/MEMC/CAM/vector boots, natural startup, real heap/RMA page transfers, keyboard, MessageTrans resources/errors, territories, IntKey selection, font/pixel rendering, and the earlier floppy client with independently decoded FIQ paths. All independent verifiers pass. The earlier 107-command/90,261-FIQ floppy fixture remains identical across the three runs. Prior evidence was not modified.

Development corrected test-code issues without changing the ROM: CheckFile now keeps its handle in R8 because OS_GBPB returns R4; the E map generator includes the public free-link terminating bit required by FileCore's sanity check; and the application result is captured before Supervisor clears the display. Failed exploratory captures are retained locally under development/diagnostic directories and excluded from the release evidence archive.

The ROM is the cleaned public 3.60-cohort implementation, **not RO26**. ROM SHA-256 remains `bf5ca56ebd6f7fd7dc4149360d97f76f009abed8879693470421998d59f11791`; kernel SHA-256 remains `cd2c3eb18de6ffab8fabb59406efb50eafd6851c305a58e88e2cc554facfcc30`. The exact source pins, module patches and original build dependencies remain in the preceding evidence chain. The new GPL emulator patch and Apache diagnostic sources are separately identified in LICENSING.md. No proprietary ROM or disc content was used.

## Remaining issues and next milestone

The target remains **RISC OS 3.11 compatibility**, including unmodified desktop applications and games; the checklist in COMPATIBILITY.md keeps that separate from 3.60 restoration. This milestone covers read-only D/E fixtures and one original diagnostic app. It does not establish arbitrary multi-zone E/F/L discs, writes, ST506/IDE, ARM3 execution, physical hardware timing, desktop services, sound or third-party compatibility.

The next operational step is to rebuild/restart MacArch with the applied device patch and confirm the same media-change behavior through its UI/MCP. No new MCP capability was necessary; exposing its existing write-protection and overlay status APIs would still make direct MCP tests easier. After that, the next bounded ROM milestone should be controlled filing writes on disposable generated images—create, extend, close, rename, delete and remount verification—before desktop integration or general application testing. No such writes or desktop work began here.
