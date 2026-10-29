# Original Squash, Chars and Help restoration

The utility-specific restoration gates now pass. See [RESULTS.md](RESULTS.md)
for the exact image and measured limits. All retained release gates now pass on that exact image; the release and
source-package checks are recorded with the distributed artifacts. No application has
been moved out of ROM. The compatibility target remains RISC OS 3.11 on ARM2/ARM3.

## Sources and patches

`manifests/desktop-utility-inputs.json` pins every selected input, its public
repository and revision, upstream SHA-256 and maintained SHA-256. The cohort is:

- Squash: `a21ce91e3d0a1a8c04f3e0dd72683a6d7fa2ab76`, version 0.24.
- Chars: `6360d0336eff8cfd3a4857b0500c13f7c9d32e77`, version 1.18.
- Help: `01f0e2d2ee060eff698cc50d4c2a0731a8bf3d07`, version 2.28.

`patches/desktop-utilities/series` is independently reversed against the pinned
hashes and reapplied with zero fuzz by `tools/verify_candidate_patches.py`.

1. Record the pre-existing host codec include adaptations.
2. Adapt the original Squash module wrapper to the GCCSDK APCS-26 static-data
   ABI, normalise assembler paths and retain ARM2 status-settling slots.
3. Explicitly unsigned three-bit continuation fields. GCC's signed interpretation
   made valid restart positions 4–6 negative and produced error &923 in a real
   restartable-decompression test. This changes no field widths or allocation.
4. Assemble the original Chars/Help ResourceFS registration modules with AsAsm;
   embed explicitly typed, deterministic resources. Preserve their actual BASIC
   tokens and all licence REM lines, without a proprietary crunching dependency.
5. Restore the decompressor's own saved buffer size when resuming a stream.
   The original assignment wrote the preceding stream's global value into the
   resumed workspace; alternating two real SWI streams produced error &922.
   Use the advertised conservative compression bound for the fast path, and
   send empty input through the original state implementation rather than the
   assembler routine which unconditionally reads a first byte.

6. Restore the nine-bit initial code width when resuming before the header was
   written. A two-byte output buffer exposed this: continuation previously
   returned only the three-byte header, dropping the one-byte input entirely.
   The fixed live SWI test resumes both two- and four-byte initial buffers,
   checks the guard byte and decodes the completed stream.

The pinned Squash has its own public assembly wrapper: no CMHG/CMunge output
is needed. The codecs retain their BSD-3-Clause notices, and the module wrapper
and Chars/Help retain their Apache-2.0 notices; see `LICENSING.md`.

## Actual workspace contract

Squash allocates the size of its real linked RW image in RMA. Its original
assembler fields precede the compiler's statics. Initialisation copies that
actual ROM template, then stores the relocation delta. GCCSDK module loads
expect this delta at `[sl,#-536]`; the entry wrapper biases the register by 536,
without allocating fake padding or changing kernel workspace structures.
`workspace-contract.json` records the exact linked size, offsets and template
hash; live tests inspect the allocated RMA words and real MessageTrans handle.

The module uses the original build's no-stack-check contract; its static base
must not be mistaken for a C stack-limit pointer. The caller supplies the public
31,744-byte compressor and 17,408-byte decompressor workspaces. Tests surround
these and output buffers with canaries.

## Build and current gates

With the existing accepted ROM prerequisites built:

```
python3 tools/build_squash.py
python3 tools/build_basic_utilities.py
python3 tools/verify_candidate_patches.py
python3 tools/build_arclibre_rom.py --with-squash
python3 tests/run_squash.py --probe
python3 tools/build_arclibre_rom.py --with-basic-utilities
```

The default desktop profile now includes these components. These explicit
comparison profiles never auto-install. Their artifacts are under
`build/arclibre-squash` and `build/arclibre-basic-utilities` respectively.
The full three-cold-reset Squash gate is `python3 tests/run_squash.py`.

Squash is fixed-address linked at its actual ROM position. The AOF/linker-map
checker independently decodes its ARM2 instructions, resolved relocations,
code/data boundaries and status returns. It contains no FPA instructions.
The live client exercises public SWIs, fast and restartable cross-decoding,
size queries and genuine translated errors; macOS gzip independently decodes
captured Unix-compress streams. Alternating-workspace and boundary tests passed across three identical cold
boots. The absent-module negative control fails at the first real SWI. The
retained release-wide gates still precede promotion.

Chars/Help modules have two normal assemblies plus an observer assembly, with
identical objects and independently decoded ARM2 code. BASIC program bytes are
kept in ROM as typed &FFB files. Other selected resources are the pinned UK
messages, Help text, Obey launchers and templates (Help's original flat 2D
variant). No desktop artwork is extracted from a ROM.

The original Messages Makefile appends global HelpTokens to the Help application
messages file. The candidate join implements that same composition, replacing
the previous tokens-only record rather than registering duplicate ResourceFS
names. Chars/Help launch and UI lifecycle gates pass across three identical cold runs:
character Select/Shift events, original font menu and outline-font rendering,
interactive Filer help, Quit and restart. The separate release-wide gates remain
required for distribution.

This document records a candidate, not a claim that these utilities or the ROM
are complete. DOSFS source/asset review and the wider RISC OS 3.11 audit remain
separate outstanding work.
