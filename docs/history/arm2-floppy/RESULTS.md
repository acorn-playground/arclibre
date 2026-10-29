# Read-only floppy results

The bounded milestone passes on an emulated A440/1, ARM2, 4 MiB, standard monitor. A genuine FileSwitch → FileCore → ADFS → WD1772 → FIQ path reads the generated floppy and runs its ARM2 program. The original kernel component is byte-for-byte unchanged.

## Source cohort and implementation

The baseline is the publicly released **cleaned RISC OS 3.60 import**, not RO26. FileCore `708e0ddb5a077e68690a1719038368860081e785` (2.91, 31 March 1995) and ADFS `b32ebc4dd79436ecb942c773759583cd7365b178` (3.13, 24 March 1995) match the approved cohort. Complete public snapshots, their LICENSE files and per-file hashes are preserved. Only these two specific dependencies were retrieved. Earlier component revisions remain pinned in `manifests/cohort.json`.

The new modules use the original A1 configuration: WD1772 at `&03310000`, MEMC1A support, original ST506 support, IOC latches, original workspaces and FIQ handler-copy machinery. The build exports their original headers, tokenises their original help sources with the pinned public Tokenise/dictionary, and adds their two original message resources. There are now twelve ResourceFS resources and eleven runtime modules including UtilityModule.

The changes are independently replayed with zero patch fuzz:

| Patch | Change and reason |
|---|---|
| 24 | Select the existing `Ver.A1`; use relocatable module areas; reconcile ENTRY/backslash syntax and full public SWI allocations; add ARM2 bank-settling instructions. |
| 25 | Restore missing operator delimiters in two FileCore expressions (`:MOD:` and `:LOR:`), retaining the assertions and conditions. |
| 26 | Restore two missing operator delimiters in the ST506 source (`:SHR:` and `:INDEX:`). |
| 27 | Select byte-addressed ADFS when `Top16Write` is enabled. The original ST506 driver explicitly asserts `:LNOT: BigDisc`. The original FileCore low-level dispatch already converts sector addresses for drivers without `BigDiscSupport`; that real interface is retained. |
| 28 | Give A1 an explicit 26-bit save/mask/restore sequence around the alternate FDC handler copy. Four ARM600 MRS/MSR words had been emitted as data by header macros and were caught by the branch-target audit. The A1 sequence keeps the current mode, masks IRQ/FIQ, copies the handler and restores the saved PSR with settling. The non-A1 source is preserved conditionally. |

No invented workspaces, dummy services, disabled assertions or unsupported opcodes are used to obtain assembly success. The alternate FDC765 path and ST506/IDE transfers are not claimed runtime-tested; the WD1772 path is exercised directly.

One assembler warning is retained with a specific review: FileCore31's original `Push "R3, R7-R13"` reserves the existing 32-byte `AllocWork2` frame. The saved SP occupies `LastSize`, which is overwritten before its only read; only R3 is restored from the frame. Its stored-SP value is not consumed. This allocation/write path is outside the read-only runtime coverage. All other warnings are ADR/ADRL optimisation hints. See `artifacts/diagnostics-review.json`.

## Assembly and execution evidence

Normal AsAsm builds each module twice; the observation build produces the same AOF bytes. All ten modules have zero unresolved symbols and zero relocation records. The independent decoder checks **39,564 emitted instructions**, **8,420 direct branches** and **209 PSR/user-bank settling sequences**, as well as relocatable ADR materialisation. FileCore is 67,788 bytes; ADFS is 34,596 bytes.

The generated disc follows the pinned FileCore `Doc/DFormat`, `Doc/Dirs` and `Doc/OldMaps`: 80 tracks, two interleaved sides, five 1024-byte sectors per track, sector IDs 0–4, old free-space map and a 2048-byte Hugo root directory at `&400`. No hard-disc boot block or automatic boot file is added. It contains:

| File | Bytes | Purpose |
|---|---:|---|
| Hello | 47 | Original ARM2 program at load/entry `&10000`; calls OS_Write0 and OS_Exit. |
| Pattern | 40,973 | Deterministic binary data spanning sides and tracks. |
| ReadMe | 95 | Original explanatory text. |

Every run mounts the image **write-protected** and checks that the write overlay remains empty after every filing call and at completion. The 35 real client calls include catalogue, metadata, open, length, BGet, seek, sequential GBPB, position, EOF, random cross-side read, close, OS_File loads, a genuine missing-file error and allocation/free of the client workspace. The client occupies ordinary test-owned RAM; it implements no ROM service.

All three files are compared byte-for-byte after stream reads and whole-file loads. The pattern's random read compares another 4096 bytes at offset 9500. OS_CLI then loads Hello through the filesystem; an execute breakpoint observes its exact catalogue address and bytes in **USR26 with PSR zero**. Its actual OS_Write0 prints `ARM2 FLOPPY PROGRAM EXECUTED`; its actual OS_Exit returns to the Supervisor input loop.

Each of the three cold-derived runs records **107 FDC commands**, **90,261 FIQ exceptions**, no undefined instruction/prefetch abort/data abort/address exception, and an empty disc write overlay. Commands cover both sides and tracks 0–4. Eight sampled FIQ entries per run include the read-address/read-track and sector-read handlers. Each copied handler is matched to the original module, including the appended `LDR pc,[pc,#-4]` and the exact relocated `NotDrq` address. The independently decoded **227 sampled instructions per run** include the ROM completion path; all eight returns restore the saved 26-bit PSR and return to saved LR minus four. These are sampled instruction paths, not a claim to have recorded all 90,261 FIQ executions instruction-by-instruction.

Results, command logs, copied handlers, sampled registers/instructions, SWIs and memory captures are in `artifacts/floppy-{1,2,3}/`. The verifier compares the three runs' results, FDC logs, handler captures and program memory snapshots exactly.

The same ROM was also cold-started through MCP, then the protected natural-Supervisor snapshot was restored for keyboard-driven `cat adfs::0.$`, `dir adfs::0.$`, `cat` and `/adfs::0.$.Hello`. The catalogue and program marker appeared through the genuine command parser. The final snapshot confirms write protection and zero overlay entries; `mcp-transcript.json`, `mcp-screen.png` and `mcp-observation.json` record the demonstration. This restored-state demonstration is additional evidence, not another independent cold run. Bare `cat` before selecting drive 0 reports `Disc drive not known` under the original reset defaults with no hard disc; the explicit directory selection resolves it.

## Retained regressions and observation corrections

All existing checks remain: three identical reset/MEMC/RAM/CAM/vector boots, natural startup, real heap/RMA page-transfer fixtures, resident keyboard, International/IntKey selection, messages, territories and pixel/font checks. Each message suite now covers twelve byte-exact resources and 52 calls; each territory suite performs 196 calls. No earlier evidence directory is modified.

FileCore/ADFS legitimately increase RMA size from 32 KiB to 96 KiB: physical page 127 maps to `&01808000`, page 126 to `&01810000`, and application end falls from `&003B0000` to `&003A0000`. Software CAM entries and hardware descriptors agree; the final system-heap shrink moves no page and leaves the heap at `&6000` bytes. The natural regression now identifies the actual kernel shrink call site, rather than assuming the first OS_ChangeDynamicArea call belongs to that operation. The independent verifier requires exactly these two new RMA mappings and programming events.

Two test assumptions were corrected without ROM changes: the text probe's whole-startup timeout was extended to include genuine ADFS initialization, and the application exit check now expects the inherited Supervisor exit environment rather than a return to an injected OS_CLI caller. The first program already printed its marker and reached Supervisor before that expectation was corrected.

## Artifacts

`floppy.rom` is 2,097,152 bytes, with 381,128 occupied:

```text
ROM    bf5ca56ebd6f7fd7dc4149360d97f76f009abed8879693470421998d59f11791
Disc   fe6da71633fe82c803b91d134fbacf6b5ab6b292a05325dfbf556cbef25d2d21
Kernel cd2c3eb18de6ffab8fabb59406efb50eafd6851c305a58e88e2cc554facfcc30
```

The sibling `arm2-floppy-evidence.tar.gz` contains this source/patch/evidence set and the previous IntKey evidence chain. `SHA256SUMS` and the archive's SHA-256 sidecar record exact contents. See BUILD.md for reproduction.

## Remaining issues and recommended next milestone

This is one generated D-format disc, one drive and a small original program. It does not establish E/F/L formats, arbitrary fragmented discs/directories, media changes, error recovery, writing, ST506/IDE, physical hardware timing, ARM3, hot reset or general application compatibility. Original-module presence is not proof of every code path. Optional absent-module calls remain recorded in `artifacts/runtime-dependencies.json`; sound, ColourTrans, Portable and podule support are not implemented by this milestone.

The next milestone should remain **read-only filing robustness**: deterministic nested-directory and fragmented-file fixtures, media removal/change, missing/corrupt sectors and bounded recovery, plus a small public ARM2 application exercising documented RISC OS 3.11 filing semantics. Validate metadata, handles, EOF/errors and loaded bytes before expanding to writes or desktop components. Preserve a separate 3.11 compatibility checklist; restoring 3.60 modules does not automatically satisfy it.

No emulator changes or MCP extension were needed for the execution gates; the external harness uses existing MacArch APIs. The MCP `load_disc` tool currently lacks a write-protection argument, so protected test mounts are made through the existing core API. An optional future MCP improvement would expose that existing flag and report overlay status; it is not a blocker.
