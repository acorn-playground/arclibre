# Controlled filing writes

## Status

**PASS.** The complete `make test` gate passed: all existing static/runtime checks and 42 read-only filing scenarios, plus 18 write/reopen/protection flows across three independent cold-derived runs. Physical images, guest calls, controller traces and sampled FIQ evidence are identical across repetitions. See [full acceptance](reports/acceptance.json), [independent write verification](reports/writes-verification.json), and [exact test inputs](reports/writes-build-inputs.json).

Each writable D/E sequence completed 55 SWI calls and nine physical image checkpoints. D issued 361 controller commands and E issued 371; each sampled write FIQ returned through six verified ARM2 instructions. There were no undefined-instruction, prefetch/data-abort or address exceptions. Across all runs the new suite performed 438 SWI calls and retained 54 writable-image checkpoints plus six unchanged protected images.

This milestone exercises existing restored FileSwitch, FileCore and ADFS code. It adds no guest implementation, runtime module, desktop component or emulator patch. The kernel and all ten appended modules reproduce the migration baseline exactly:

```text
ROM    bf5ca56ebd6f7fd7dc4149360d97f76f009abed8879693470421998d59f11791
Kernel cd2c3eb18de6ffab8fabb59406efb50eafd6851c305a58e88e2cc554facfcc30
```

## What is exercised

Each format starts with its own original generated 800 KiB image. All writes go through actual guest SWIs, FileSwitch, FileCore, ADFS, MEMC, IOC and the WD1772. The native harness supplies caller registers and buffers and observes execution; it does not implement guest filing operations. MacArch's existing sector overlay captures the writes without modifying the base image.

The write sequence covers:

- `OS_File 0`: create a 32,791-byte file, overwrite it with 7,191 bytes, and verify explicit load/execute metadata.
- `OS_Find &80`, `OS_GBPB 2`, `OS_BPut`, `OS_Args &FF` and close: output a 16,393-byte stream, append one byte, flush and close it.
- `OS_Find &C0`, `OS_GBPB 1` and `OS_Args 3`: update across a sector boundary and truncate to 10,013 bytes.
- Update the existing fragmented file across offsets 8,190 and 20,478, traversing both real E-map fragment boundaries. The original file is read-only: the first update must return `&C1`, then `OS_File 4` grants write access before the successful writes.
- `OS_FSControl 25` and `OS_File 8/6`: rename a file, create a directory and child, delete another file, and delete the child and empty directory.
- Request a 900,000-byte allocation on an 819,200-byte disc. The real `&108C6` disc-full error must leave the entire serialized image unchanged. A subsequent small save must succeed.
- Attempt a save on each write-protected format. The real `&108C9` error must leave both the base image and overlay unchanged, with successful reads afterward.

Nine dismounted image checkpoints per writable format retain the on-disc results, including the appended stream before truncation and the images immediately before and after the failed allocation. Two new emulated machines reopen the final serialized images with no inherited writer cache, handles or disc overlay, read the changed files, and check that deleted/failed names are absent.

The source interface definitions are [HighFSI](../../src/FileSwitch/hdr/HighFSI). The raw image contracts are [OldMaps](../../src/FileCore/Doc/OldMaps), [EMaps](../../src/FileCore/Doc/EMaps) and [Dirs](../../src/FileCore/Doc/Dirs).

## Independent verification

[disc_image.py](../../tests/verify/disc_image.py) decodes the saved physical images independently of both MacArch's disc reader and the fixture generator. It checks old-map checksums/free extents; both E-map copies, zone/cross checks, fragment termination and free chains; directory signatures, sequence numbers, checksums, order and parent pointers; object bounds and overlapping allocations; all surviving and newly written file bytes; and unchanged unrelated metadata. It rejects deliberately damaged map and directory checksums.

A modified typed file is timestamped by the real filing implementation on close. The check preserves its file type and records the resulting timestamp rather than requiring the fixture's old zero timestamp. Explicit non-typed load/execute addresses supplied to `OS_File 0` must be preserved exactly.

[verify_writes.py](../../tests/verify/verify_writes.py) also checks completed SWIs, transfer pointers/counts, exception state, write-protection and disc-full errors, fresh-machine reopens and controller write completions. It independently matches the copied write-sector FIQ handler against the assembled ADFS module, decodes its actually executed instructions as ARM2, verifies the FDC byte-write address, and verifies FIQ26 masks and the return PC/PSR. No handler is replaced or patched for testing.

The full gate requires identical images, calls, controller traces and sampled FIQ evidence across all three cold-derived runs. The existing static kernel/module checks, negative CAM control, read-only filing, keyboard, module, display and emulator media-change tests remain enabled.

## Changes and reproduction

New project-owned Apache-2.0 test code lives in [WriteProbe](../../tests/harness/Sources/WriteProbe/main.swift) and the two independent Python verifiers. The existing harness package and regression runner include the new probe. The runner removes any earlier acceptance marker before starting, so a failed rerun cannot leave a previous suite success in place. No new upstream source or licensing dependency was introduced; [LICENSING.md](../../LICENSING.md) remains applicable.

Run the entire gate using the prerequisites in [BUILD.md](../../BUILD.md):

```sh
ARCLIBRE_OUTPUT="$PWD/build/filing-writes" make test
```

The ROM is `build/filing-writes/artifacts/floppy.rom`. Write traces, SWI results, physical image checkpoints and sampled FIQ instructions are under `build/filing-writes/artifacts/writes-{1,2,3}/`; the independent summary is `writes-verification.json`. `acceptance.json` is emitted only after every suite succeeds. Generated images contain original project data, not commercial applications or disc extracts.

The milestone was delivered as the unchanged ROM, the updated source and tests, an evidence archive of the complete runs, and a reviewable patch of the repository changes. Compact reports remain in this directory; full generated captures are written under the ignored `build/`.

## Limits and next milestone

These are controlled D/E filing results, not complete RISC OS 3.11 application compatibility. The writer SWI client runs from Supervisor; this milestone does not add an unmodified third-party application or claim user-mode writing coverage. The existing original ARM2 user-mode read client remains in the regression suite.

Still untested are write interruption/power loss, write-time CRC/missing-sector errors, delayed flush failures, media removal with dirty buffers, file growth with holes and zero filling, directory-capacity exhaustion, general multi-zone E/F/L layouts, and real drive timing. Image export verifies guest writes, not the MacArch GUI's save-media workflow.

The recommended next phase is an original user-mode ARM2 save/update client, then interrupted-write and dirty-media-change recovery on disposable images. Retain this suite before expanding into desktop modules. The ultimate target remains unmodified RISC OS 3.11 applications and games on original ARM2/ARM3 hardware.
