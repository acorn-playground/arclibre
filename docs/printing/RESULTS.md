# Printing on a disc

RISC OS 3.11 has !Printers, PDriver, PDriverDP, PDumperSupport and PDumperDM
in ROM, about 114 KB. By owner decision ArcLibre ships them on their own
floppy, `dist/arclibre-printing.adf`, built by `tools/build_printing_disc.py`.
The ROM is unchanged.

## What is on the disc

The disc holds !Printers in the original disc install layout (the pinned
PrinterManager Makefile's `install` target), with all three of RISC OS 3.11's
printer classes: dot matrix (`dp`), LaserJet (`lj`) and PostScript (`ps`). The
modules are where the classes' support code loads them:

- `!Printers.Modules`: PDriver 3.25, PDriverDP 4.35, PDriverPS 4.35 and
  PDumperSupport 1.18;
- `!Printers.PDumpers`: PDumperDM and PDumperLJ 1.14.

`ps.PSFiles` holds the seven prologue and encoding files, unshrunk: Acorn's
psshrink isn't public, and PDriverPS drops their `%` comments as it inserts
them. `ps.Adobe` holds the two font encodings. PrintDefs has `FX-80` (Epson
FX-80), `LW` (Apple LaserWriter) and `LasJet-II` (HP LaserJet II), in the
tagged forms from PrintDefs 763f4ca. A ReadMe explains how to install a
printer. The disc has 242,688 bytes free.

| Item | Bytes |
|---|---:|
| !RunImage (crunched, not squished) | 134,568 |
| dp support code | 26,888 |
| Code (assembled by SuppSrc) | 5,952 |
| PDriver | 4,796 |
| PDriverDP | 29,180 |
| PDumperSupport | 7,168 |
| PDumperDM | 5,076 |
| SetPrint | 704 |
| lj support code (crunched) | 28,003 |
| ps support code (crunched) | 28,749 |
| PDriverPS | 31,932 |
| PDumperLJ | 5,196 |
| ps.PSFiles (7 files) | 86,244 |

### LaserJet and PostScript

PDriverPS needed the same ARM2/AsAsm contracts as PDriverDP: `KernelEntry`,
and one settling `MOV r0, r0`. It also needed one AsAsm difference fixed.
AsAsm reads `\` in a string as an escape and aasm didn't, so `#"\"` becomes
`#92` and `"(\177) "` is written `"(\\177) "`. Otherwise the job would carry a
raw &7F rather than PostScript's `(\177)`. PDumperLJ builds unchanged.
SupportLJ and SupportPS route their trace calls through `Ftracef`, as
SupportDP does, and SupportPS leaves out two other `VDU:` debug lines.

SupportPS loads MakePSFont only if it's on the disc. MakePSFont is a 1994 C
module that maps and downloads outline fonts; it wasn't in 3.11 and isn't
built here. PDriverPS already ignores its absence.

The gate installs each definition by drag and prints the BASIC page:

- **LaserJet.** The host decodes the PCL (`tests/pcl_fixture.py`): 150 dpi
  raster graphics 600 dots wide, a solid 600 × 151-row rectangle, and text
  that reads "ArcLibre" in the kernel's system font (`tests/sysfont_fixture.py`).
- **PostScript.** The host checks the DSC structure, the prologue and
  epilogue, and the page operators. It then runs the job in an independent
  Level 1 interpreter (`tests/postscript_fixture.py`) at 300 dpi: one page,
  a 1200 × 302-pixel rectangle 1 inch from the left and 8 inches up (the
  extra two rows are the driver's outline stroke), and "ArcLibre" text.

Each class also has a negative control: the disc without PDumperDM, without
PDumperLJ, or without PDriverPS. Each install reports "Module … not found"
and nothing prints.

## Sources and how they are built

The sources are pinned in `manifests/printing-inputs.json` and imported by
`tools/import_printing.py`:

- PrinterManager, PDriver, PDModules, PDumperSpt and PDumpers at their
  cleaned-3.60 revisions (5 November 1996), and two headers from HdrSrc.
- The FX-80 definition from PrintDefs at `763f4ca` (2003). This is the tagged
  (`cl:`) definition format !Printers 1.46 reads, Squash-compressed as
  distributed. PrintDefs' 1996 files use an older format, which !Printers
  rejects.
- `src/ArcLibre/hdr/SprExtend` is a new header listing SpriteExtend's JPEG SWIs
  in the order of its own SWI table; PDriverDP needs their names.

The modules are built by the `printing` group of `tools/build_system_modules.py`
with the same static ARM2 checks as the ROM modules. `patches/printing` holds
every change:

- **ARM2 assembly contracts**, as in the hardware and network patches:
  - `AREA` for `LEADR`;
  - `KernelEntry` for `ENTRY`;
  - SWI chunks from Hdr:SWIs;
  - settling `MOV r0,r0` after PSR writes.
- **PDriver's messages block** keeps ResourceFile's layout, but with the
  file's Text type and a fixed zero datestamp instead of the host file's
  attributes, so the build is deterministic.
- **PDriverDP flags.** Two `STRB pc, flag` stores (a non-zero flag from PC's
  low byte) become `MOV`/`STRB` through a register that's dead at that point.
  Only zero/non-zero is ever tested.
- **!Run** loads PDriver from the disc (3.11 had it in ROM) and drops the AUN
  remote printing modules, which have no public source. The WimpSlot is 224K
  rather than 128K, because !RunImage isn't squished (below).
- **SupportDP's 52 trace calls** (`VDU: PROCftracef(...)`) go through
  `Trace.h`'s `Ftracef`, as RunImage's already do. `PROCftracef` exists only
  in trace builds, and Acorn's squish presumably removed them; unpatched, the
  dot-matrix support stopped with "No such function/procedure".

!Printers' BASIC is built as its Makefile does, with public tools:

1. The C preprocessor: the bundled GCC 3.4.6's, `-E -P -DDISC`, without
   `-DSparrow` (the AUN remote printing build).
2. Line numbers, one per line from 1. `TEXTLOAD` would number in tens, past
   BASIC's last line.
3. `TEXTLOAD` and `CRUNCH -1` (the original crunch scripts) in the ROM's own
   BASIC 1.14 under the pinned MacArch core.
4. `SuppSrc`, after the `CONST_name%` substitution of Acorn's Constants tool,
   is run by BASIC to assemble `Code`.

The two builds must match. Acorn's squish isn't public, and the ArcLibre squish
tool refuses !Printers: it resolves names at run time (`OVERLAY`, `EVAL` of
`"FN"+class+"_support"`) and shares global names with its support overlay. So
the programs are crunched but not squished. That costs disc space and
96K more application memory while !Printers runs.

## The gate

`tests/run_printing.py` (PrintProbe) builds the disc. It then boots the
delivered ROM three times on an emulated A440/1 with the disc in drive 0 and
uses the real desktop:

1. It opens the floppy and double-clicks !Printers; its icon appears on the
   icon bar.
2. It opens PrintDefs and drags FX-80 to that icon. !Printers installs the
   printer, loading PDriverDP, PDumperSupport and PDumperDM from the disc.
3. At the command line, a BASIC client (`tests/fixtures/PrintTest.bas`) prints
   one page as an application does: `PDriver_SelectJob` on a file, a filled
   rectangle in black (ColourTrans) and a line of VDU 5 text.

`PDriver_Info` reports a dot-matrix driver at 120 × 72 dpi. The host decodes
the 6,372-byte file's Epson commands:

- `ESC C 70`, then `ESC A`/LF strips of `ESC L` double-density bit images, a
  form feed and `ESC @`;
- the rectangle is exactly 480 × 72 dots, solidly filled (4 × 1 inches);
- the text is 81 × 12 dots of system-font glyphs, which render as "ArcLibre".

The three cold boots give identical files.

The negative control is the same disc built without PDumperDM. Installing the
printer reports "Module PDumperDM not found" and nothing is printed.

## Limits

- Output goes to a file. The parallel port itself is covered by the hardware
  gate, and reads BUSY in MacArch.
- One definition per class is exercised, at its defaults (the LaserJet II at
  150 dpi, uncompressed). Colour, fonts, sprites and JPEGs in print jobs,
  and PCL compression modes, are untested.
- Without MakePSFont, outline fonts on PostScript printers, and plain-text
  printing to them, are expected to fail with a missing SWI.
- The PostScript is checked by the gate's own interpreter, not Ghostscript
  (not installed on this host) or a printer.
- Printing from Draw, Paint and Edit's own Print menu items is untested.
- !Printers 1.46 is the 3.60-era version, not 3.11's. It requires
  UtilityModule 3.10, which ArcLibre reports.
- Physical printers are untested.
