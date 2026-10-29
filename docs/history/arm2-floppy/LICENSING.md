# Licensing and provenance

This milestone uses public source snapshots and original generated test data. No proprietary ROM code, disc content, font or other ROM resource was extracted or used.

FileCore and ADFS are pinned public cleaned-3.60 imports. Both full snapshots include their original Apache-2.0 LICENSE files and Acorn source notices. Original help and message data remain in those snapshots and are built with public tools. Historical ancillary files are preserved for provenance; unrelated prebuilt utilities and test programs are not executed or joined into the ROM. Exact repository URLs, revisions and per-file hashes are in `manifests/`.

The disc generator and its three files are original work under Apache-2.0. The layout follows the pinned public FileCore documentation and implementation. The test program consists of original ARM2 instructions calling OS_Write0 and OS_Exit. It contains no Acorn ROM binary or commercial application. The generator does not import or copy MacArch's hard-disc formatter implementation into the ROM.

The implementation baseline is the original public source release's cleaned RISC OS 3.60 cohort with the documented restoration patches; RO26 is not the implementation baseline.

All inherited license qualifications still apply. In particular, the original UK territory snapshot lacks a standalone LICENSE; source notices and the separately retained resource-provenance comparison are documented in `../arm2-territory/LICENSING.md`. The later comparison is evidence only, not a runtime source substitution. International's public font data and the existing kernel font are source-derived.

The host Squash compressor/decompressor retains Jon Thackray's BSD three-clause notice in `licenses/Squash-BSD3`. AsAsm and its observation-only host patch retain GPL-2.0-or-later licensing. Tokenise and other host dependencies retain their original notices in the prior evidence chain. No host tool is embedded in the ROM.

New restoration adaptations, generators and harnesses are Apache-2.0 unless individually stated otherwise. MacArch remains an unchanged GPL-covered testing dependency at the pinned revision; `licenses/MacArch-GPL3` and source-hash provenance are retained. No emulator source or executable is joined into the ROM.

This is an experimental source-built command-line ROM and original test disc, not a proprietary release image or a claim of complete RISC OS 3.11 compatibility.
