# Findings and validation

## Root cause

The baseline's `HardFont` is at `&0381EE8A`, two bytes off a word boundary. `DoResetFont` uses `LDR r2,[r0],#4` followed by `STR r2,[r3],#4` to copy 1,792 bytes to the original soft-font workspace at `&3700`. For an ARM2 word load at address modulo four equal to two, the aligned word is rotated right by 16 bits. Consequently this loop does not copy the intended byte sequence.

The original ROM contains the correct public-source font bytes. An independent simulation of that unaligned copy predicts **every byte** of the captured corrupt soft font: 757 incorrect bytes, affecting 221 of 224 glyphs. For example, capital A should contain `3C 66 66 7E 66 66 66 00`; the baseline RAM contains `3C 66 3C 00 66 66 66 7E`. No font asset was missing.

The source inclusion follows 950 bytes of teletext glyph data. This build lacked an explicit alignment boundary before the system font. No broad historical investigation was needed to establish the concrete load/copy contract.

## Repair

Patch 0012-align-system-font.patch applies after the existing eleven restoration patches. It adds `ALIGN` immediately before the selected system-font include in `Kernel/s/GetAll`, and `ASSERT (HardFont :AND: 3) = 0` afterward. The assertion also protects the alternate selected font variant's alignment.

The new font address is `&0381EE8C`. Kernel length remains 142,148 bytes and the ROM remains a 2 MiB zero-padded container. All decoded instruction addresses stay unchanged. Only four instruction words change: the two-instruction address calculations for `DoResetFont` and the VDU 5 hard-font reference. The glyph data shifts by two bytes, consuming the former trailing alignment padding. No workspace, reset vector, hardware constant, missing service or error handler is changed.

The source patch replays without fuzz. The original restoration and first-boot checksum manifests remain intact. New files and modified candidate sources live entirely in this experiment. No emulator file was edited. Two existing user edits in MacArch's app UI were observed; the linked ArchimedesCore source was unchanged at commit `550bee4842e45eafdf331f0d06e11df1368403e8`.

## Tests

| Check | Result |
|---|---|
| Two normal assemblies and observer assembly | Identical AOF bytes; no unresolved symbols or relocations |
| Unchanged independent ARM2 static suite | Pass: 27,751 instruction words, 5,040 direct branch targets and 198 bank-settling sites |
| Unchanged bounded kernel routine tests | Pass |
| Regression negative control | Removing ALIGN while retaining ASSERT makes assembly fail |
| Three repaired cold boots | Identical checkpoint registers, timing and state across runs; all original MEMC/CAM/vector/stack checks pass |
| Comparison with original boot | Same checkpoint registers and timing; final captured device/memory state differs only in soft-font bytes |
| Public source → ROM → RAM font | All 1,792 bytes match; all 224 definitions correct in all three repaired boots |
| Genuine OS_Write0 fixture | All 95 printable ASCII glyphs match the font, checking 6,080 glyph pixels |
| CPU screen buffer → physical DMA buffer | Exact equality over the active screen buffer |
| Framebuffer → MacArch VIDC output | All 163,840 active-display pixels match independent 4bpp decoding in each baseline/fixed banner/fixture capture |
| Existing hardware capture/decoder | All 1,916,545 writes retained and decoded for a repaired cold boot |
| MCP reproduction | Observes aligned copy source, correct A bytes and readable error display |

The text fixture is explicitly separate from natural boot: it restores the pre-module snapshot, places a small test program/string in application RAM at `&8000`/`&8100`, then executes real `OS_Write0` with clear/home and ASCII text. Its ending branch loops in test-owned RAM while VIDC completes frames. It does not replace a kernel routine or synthesize a successful service return. Natural banner captures instead resume the genuine startup path to the first `RdchLoop` entry, then allow three frames.

Frame PNGs preserve the native 832×288 raster including borders. The active display is 640×256 at offset (96,16), 4bpp. The monitor presents these pixels with vertical scale two, as in the MCP screenshot. This investigation did not certify other modes, VDU 5 rendering or all extended glyph rendering; the complete font contents are checked separately.

## Separate error revealed by readable text

Both baseline and repaired images report:

```text
Error: !!!! CAM Map Corrupt !!!! (Error Number &0)
*
```

The apparent `80` in the initially viewed small image is actually `&0`. The source error block `CamMapBroke` contains error number zero. The error is already present with the old font; it was not introduced by alignment.

At `&038072D0`, `MoveCAMatR0toR3` has exhausted the software CAM search. Captured inputs are old logical address `&01BFA000`, requested new address `&003B0000`, flags zero, index `&FFFFFFFF`, CAM base `&164`, LR `&A3806EFF`. Both natural banner captures record this same event at tick 183,296,184. It occurs after the previous milestone's boundary at tick 183,078,399. The ASCII-only fixtures before module initialization do not hit this path.

Later startup also makes unavailable SWIs `&4028A`, `&41502` and `&41506` before the captured prompt. The exact calls and CAM event are in the fixed banner log, with a matching baseline log. No service was substituted or module added. The rolling MCP log retains older entries across resets; use the fresh native capture logs for per-run events.

**Recommended next task:** investigate that precise CAM lookup failure and its caller during the initial dynamic-area/free-pool transition, retaining this repaired ROM as the baseline. Establish the expected mapping contract before changing code; do not suppress the error or invent a CAM entry. Keep runtime-module and RISC OS 3.11 compatibility work separately bounded. Desktop integration remains out of scope.

## Evidence and licensing

acceptance.json hashes the assembly, routine, alignment, boot and rendering reports. text-verification.json records source/font/pixel comparisons. instruction-diff.json lists the four changed instruction words. traces preserves recorded MCP calls. Native snapshots and exported memory/device sections are under the four `artifacts/*-banner`/`*-fixture` directories and `artifacts/repeats`.

The kernel/source font retain their Apache-2.0 notices; new patch, scripts and harness source use Apache-2.0. The host harness uses the unchanged GPL-covered MacArch core, whose GPLv3 text is retained. No native harness/emulator executable is distributed in the evidence bundle. No proprietary ROM, extracted font or external target payload was used. Earlier source pins, patch series and licensing records remain in the companion first-boot/restoration evidence archives.
