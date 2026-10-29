# Licensing and provenance

No proprietary ROM code, font, dictionary or other ROM resource was used. The original public source snapshots are preserved and hash-listed; source adaptations occur only in the isolated work tree.

The pinned **Inter** and **IntKey** repositories both contain Apache-2.0 LICENSE files. Inter also retains per-source Acorn notices, including its original font data. Some historical IntKey files lack individual notice blocks; their original repository license and complete snapshot are retained rather than inventing per-file notices. The source distribution includes historical layout/editor/generator files; the build does not run their prebuilt executables or tokenized BASIC programs. It assembles the original shared handler, UK A1 structure/tables and public character constants.

International's message resource, country/alphabet tables, Latin1 glyphs and generated help come from its pinned public source. Its font service legitimately modifies the runtime soft font; no resource was taken from an existing ROM image. The original help generator and public Tokenise tool are used with their recorded source provenance.

All inherited source/license qualifications remain applicable, including the original UK territory snapshot's lack of a standalone LICENSE and the separately retained resource-provenance comparison. See `../arm2-territory/LICENSING.md` and the original notices. That later comparison is not a runtime source substitution.

The host Squash compressor/decompressor retains Jon Thackray's BSD three-clause notice (`licenses/Squash-BSD3`); other source files retain their own Apache notices. AsAsm and the observation-only host patch retain GPL-2.0-or-later licensing. Tokenise and other host tools retain their original licenses/provenance in the prior evidence chain. No host tool executable is included in the ROM.

New module adaptations, harnesses and scripts are Apache-2.0 unless explicitly stated otherwise. MacArch remains an unchanged GPL-covered host testing dependency at the pinned revision. Its license and core source-hash provenance are included; no emulator binary/source is joined to the ROM and no emulator modification was made.

The artifact is an experimental source-built command-line ROM, not a copy of a proprietary RISC OS release or a claim of complete RISC OS 3.11 compatibility.
