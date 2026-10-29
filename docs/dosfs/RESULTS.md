# DOSFS 0.62 as a disc-loaded module

The original cleaned-3.60 DOSFS 0.62
([FileSys/ImageFS/DOSFS](https://gitlab.4corn.co.uk/RiscOS/Sources/FileSys/ImageFS/DOSFS)
@ `ec870faf21127aba600c58b3571115ac164e40f3`) now builds as a self-relocating
module loaded from floppy, `*RMLoad` or a Filer double-click. **It is not in
the ROM**; the ROM and `tools/build_arclibre_rom.py` are unchanged. The
distributable floppy `build/dosfs/arclibre-dosfs.adf` (old-map ADFS D, disc
name `DOSFS`) holds the module `DOSFS` (filetype &FFA) and a `ReadMe`
(`src/ArcLibre/dosfs/ReadMe`).

```sh
make dosfs-disc                   # or: python3 tools/build_dosfs.py
python3 tests/run_dosfs.py        # 3 cold boots + negative control (builds first)
python3 tests/run_dosfs.py --probe            # one cold boot
python3 tools/verify_candidate_patches.py     # includes the dosfs series
python3 tools/import_dosfs.py check           # maintainers: re-derive pins from references/
```

The gate tests the ROM in `build/arclibre` (`ARCLIBRE_INSTALL_ROM=0 make
arclibre-rom`). Evidence for this milestone, on ROM
`f7375c27546fda22c4dade9cdcb50215fc9d8b281a5bf304d9fff5f5fbdd0cef`, is in
[reports/](reports/): `acceptance.json` (runtime), `module.json` (static
checks) and `disc.json` (floppy contents).

## Sources and the two blockers

`manifests/dosfs-inputs.json` pins 34 files; `patches/dosfs` changes two
(unquoted AsAsm `GET` paths in `s/DOSFSctl`; a pointer to the replacement boot
sector in `s/StaticDefs`). Not imported: `c/BOOTblock` (a second copy of the
template), `s/init` (a ROM-only guard that refuses RAM loading), the unused
`c/DOSfsiface` and the pre-internationalisation `Help`/`Syntax` files.

1. **Boot-sector template.** The upstream `s/StaticDefs` default sector
   (`MSDOS3.3` OEM text, IO.SYS/MSDOS.SYS names, opaque x86 code) is not
   redistributed. `tools/import_dosfs.py` excises exactly that block from the
   import baseline; the manifest records the complete upstream file hash
   (`6b65d120…`), the excised lines (197–285, 4,717 bytes, `a50aecc8…`) and the
   baseline hash, and the patch verifier reverses to that
   baseline. The replacement `src/ArcLibre/s/DOSFSBoot` is independently
   written: jump `EB 3C 90`, OEM `ARCLIBRE`, a DOS/M (720K) BPB, zeroed
   hidden/32-bit fields and no extended-BPB signature, then 38 bytes of x86
   code that prints "Non-system disc: ArcLibre DOSFS data disc. …", waits for
   a key (INT 16h) and calls INT 19h (HLT loop if that returns), and `55 AA`.
   `tools/check_dosfs_boot.py` checks every BPB field of the template and of
   the sector `DOSFS_LayoutStructure` derives for each of DOSFS's own format
   table entries (DOS/Q, M, H, N, P, T, U, Atari M, N; read from the linked
   module), each as a consistent FAT12 volume, and executes the code in a
   minimal real-mode model from both `0000:7C00` and `07C0:0000` (869
   instructions, only INT 10h/0Eh, INT 16h, INT 19h).
2. **Module header.** CMHG/CMunge output is not used.
   `src/ArcLibre/s/DOSFSHdr` implements the `cmhg/DOSFShdr` contract by hand:
   title, help `DOSFS 0.62`, initialisation through the original RAM
   SharedCLibrary stubs (`_clib_initialisemodule`, statics copied to RMA) then
   `init_fs`; finalisation through `_clib_finalisemodule` (runs `init_fs`'s
   `atexit` handler); the 11-entry service filter for `fs_service`; SWI chunk
   &44B00 with the `DOSFS DiscFormat LayoutStructure` table; `*DOSMap` and
   `*CopyBoot` with international help tokens; messages file
   `Resources:$.Resources.DOSFS.Messages`. C entries use DOSFS's own `Ccall`
   stack convention (SVC stack base + 540, library/client relocation words
   saved and restored). For disc loading it also registers the unmodified
   `Resources/UK/Messages` with ResourceFS after library initialisation,
   re-registers on Service_ResourceFSStarting and deregisters on finalisation.

**Relocation.** The objects are linked as binaries at &8000 and &1238000. The
words that differ (each by the base difference) are the absolute address
words: 181, all of them word relocations in their object files and identical
to the table `drlink -rmf` computes for the same objects. The build appends
ArcLibre's `src/ArcLibre/s/DOSFSReloc` at the image end (where `-rmf` puts
`__RelocCode`, so the header's and the stubs' calls reach it) followed by the
table (183 entries with its own two address words) and -1; drlink's own
relocation code is not shipped. Applying the table in a host simulation
reproduces the second link exactly, and a second pass is a no-op.

**Static result** (`reports/module.json`): 50,992 bytes
(`6dc485d8…`, image 50,188 + 68 bytes of relocation code + table), 10,086
independently decoded ARM2 integer instructions, no FPA instructions, every
byte mapped to an object area with only relocated bytes differing, branches
inside code, PSR-changing returns followed by ARM2 settling no-ops, and two
identical assemblies of every object. RMA: the module plus a 4,948-byte
workspace (4,936-byte RW template + 12 header bytes), confirmed at runtime.
The build is reproducible (identical module on repeated builds).

## Runtime gate

`tests/run_dosfs.py` boots the current ROM cold (A440, ARM2, 4 MB, two
floppies, `Truncate` on) with the distributable floppy in drive 0 and a PC
720K disc in drive 1, types at the real F12 command line (`DOSFSProbe`, no
guest code injection) and reads the discs back on the host. The PC discs are
written by `tests/fat12_fixture.py`, an independent FAT12 writer and strict
parser (both FATs equal, media byte, chains, no lost or cross-linked clusters,
sizes against chain lengths, `.`/`..`), and recorded as MFM tracks by
`tests/hfe_fixture.py`. **PASS on three identical cold boots plus the
negative control:**

- `*RMLoad ADFS::0.$.DOSFS` loads it at &1821494 in the RMA (relocated);
  `*Help DOSFS` and `*Help DOSMap`/`CopyBoot` show the international help
  from the registered Messages.
- Reading: `*Cat`/`*Ex` list the host disc (`HOSTDISC`, names as `HELLO/TXT`,
  host date/time and sizes); `*Copy` of a 5,000-byte random file and a nested
  1,500-byte file to ADFS give identical bytes; BASIC `BGET` until `EOF#`
  counts 35 bytes with `EXT#`=`PTR#`=35; an empty file has `EXT#` 0 and `EOF#`.
- Writing, checked by the host parser: `README.TXT` (2,148 bytes, RISC OS
  date kept as DOS date 27-Oct-2026), a 3,000-byte `BPUT` file extended to
  3,001 bytes via `PTR#`, an empty file, `LongFileName/TXT` truncated to
  `LONGFILE.TXT`, `*CDir NEWDIR` with a file inside (correct `.`/`..`),
  `*Delete` (cluster freed), `*Rename` (same chain and date). Untouched files
  keep their chains; the boot sector is unchanged.
- Mapping and errors: `*DOSMap TXT FFF` makes `.TXT` files Text;
  `Bad/Text` gives DOSFS's "contains characters that can not be converted";
  `*Type` of a missing file "File '…' not found"; `*Delete` of a non-empty
  directory DOSFS's "Directory 'SUBDIR' not empty"; `OPENIN` returns 0.
- Formatting pieces: `DOSFS_DiscFormat` returns 512-byte, 9-sector, MFM,
  80×2-track, first-ID-1 for DOS/M; `DOSFS_LayoutStructure` into a file
  writes exactly the ArcLibre boot sector, two fresh FATs (`F9 FF FF`) and a
  root with the volume label; the *Format structure stage (whole-disc
  `OS_Find` of `adfs::1` + LayoutStructure, as ADFS's `s/MFormat` does) gives
  a disc that DOSFS then mounts as `ARCFMT`, accepts new files on and that the
  host parser and boot-sector check accept.
- `*CopyBoot 1 0` onto a second host disc copies the jump, OEM name and the
  480-byte code area (the destination then prints the ArcLibre message in the
  x86 model) and keeps its BPB, FATs and files.
- `*RMKill DOSFS` makes the disc "Disc not understood"; `*Run` of the module
  file (the run type a Filer double-click uses) loads it again and it works.
- Negative control (same discs, DOSFS not loaded): "No help found.", "Disc
  not understood - has it been formatted?", `SWI name not known`; the PC disc
  is unchanged.

## Limits and open issues

- **`*Format` now works.** It was blocked on earlier ROMs, for every format,
  by FileCore 3.60's `EnsureFSLock`: its `CLRV` (`CMP pc,#0`) overwrote the
  floppy test, so every DiscOp write called the absent FSLock SWI &44781.
  The delivered FileCore fixes this ([FileCore results](../filecore/RESULTS.md)).
  The gate formats drive 1 as `DOS/M`: all 160 tracks are written, the fresh
  disc takes a file, and the host parser reads a 720K FAT12 volume with the
  ArcLibre boot sector and the DOS/M BPB. `*CopyBoot` then copies from that
  formatted disc.
- MacArch presents raw sector images only in Acorn geometries (a 737,280-byte
  PC image is "unknown"), so the PC disc is an HFE MFM track image. Reads,
  sector writes and track formatting of 512-byte sectors all work in it. An
  earlier note here predicted, from reading the emulator, that formatting
  would write 1,024-byte sectors to HFE images; the formatted disc disproves
  that.
- 1.44M, 360K and FAT16 partitions are in the formats gate below. DOS/H
  (1.2M), DOS/P, DOS/T, DOS/U and the Atari formats, formatting other than
  DOS/M, the desktop Filer/format menu, Service_ResourceFSStarting
  re-registration, low-memory errors and physical hardware are untested.
- DOSFS pads the volume label written by LayoutStructure with NULs rather
  than spaces (original behaviour, kept).

## Other formats

`tests/run_dosfs_formats.py` (NewIOProbe) runs DOSFS, loaded from its disc,
three cold boots each. The host writes the PC media with
`tests/fat12_fixture.py` (now also FAT16, chosen from 4,085 clusters as the
published rule says, and PC partition tables) and `tests/hfe_fixture.py`
(now also 18-sector tracks at 500 kbit/s, and 40-track discs as an 80-track
drive reads them). The same strict parser checks the media afterwards.

| Medium | Machine | Exercised |
|---|---|---|
| 1.44M DOS/Q | A5000 (765, high density) | catalogue; a file copied to the ADFS disc; `*Save` from memory and `*Copy` within the PC disc |
| 360K DOS/N, 40 tracks | A440/1 (1772) | DOSFS double-steps; catalogue and a copy each way |
| FAT16 partition: a 4 MB partitioned image, filetype &FC8, 8,063 clusters | A5000, on the IDE disc | opened as an image directory; catalogue of it and a subdirectory; a 300,000-byte file copied out to ADFS and a file copied in from the floppy |

The negative control is the A5000 media without DOSFS loaded: the floppy is
"Disc not understood" and the partition "is a file".

Writes to a PC floppy that alternate with another drive aren't run on the
765 machines, because of an emulator limit. MacArch's 765 raises disc changed
only while a drive is empty (a real drive also raises it from power-on until
a step), so ADFS never learns the line works and marks the drive "maybe
changed" at each motor start. FileCore then re-identifies the disc in the
middle of the copy. A DOS disc's identity is its FAT's checksum, and DOSFS
has already advertised the new FAT's, so FileCore asks for the disc again
("Please insert disc"). Reads across drives, and writes on the 1772 machines,
work.
