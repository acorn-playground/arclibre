# The 4 MB ROM

`make arclibre-test-4m` builds a 4 MB (4,194,304-byte) ROM with everything in
it, tests it, and copies it to `dist/arclibre-4m.rom`, with a SHA-256 sidecar
and `dist/arclibre-4m.machine.json` for MacArch. It is a second build path;
the delivered 2 MB ROM, its discs and its release are unchanged.

## What is in it

It is the 2 MB ROM, module for module and resource for resource, plus what
the 2 MB ROM ships on discs:

| Addition | Bytes | Form |
|---|---:|---|
| !Alarm | 63,156 | the ROM wrapper module, as in RISC OS 3.11 (`build_basic_utilities.py with-alarm`) |
| PDriver, PDriverDP, PDriverPS, PDumperSupport, PDumperDM, PDumperLJ | 83,348 | the printing disc's modules (dot matrix, LaserJet, PostScript) |
| !Printers | — | in ResourceFS as `Resources:$.Apps.!Printers` (the printing disc's application, without its Modules and PDumpers directories) |
| DOSFS | 49,136 | its original ROM form: see below |

It uses 2,718,968 bytes, leaving 1,475,336 free. The extra modules lie above
the 2 MB boundary (DOSFS at &3A8BD04).

### DOSFS in ROM

The disc DOSFS relocates itself, and its RAM C stubs patch their vectors into
the module. Both write to the module's own image, and in ROM those writes
would program MEMC's address translator. The original DOSFS Makefile instead
links the module at its ROM address with the ROM C stubs (`romcstubs`, from
`clib/s/cl_stub_rm`), whose vectors live in RMA.

The 4 MB build does the same:

1. `tools/build_dosfs.py` also assembles `src/ArcLibre/s/DOSFSHdr` with
   `ArcLibreDOSFSROM` (no relocation call, ROM help string) and the CLib ROM
   stubs.
2. `tools/build_arclibre_rom.py --four-meg` links those objects with drlink
   at the module's address in this ROM, against the absolute addresses of
   the shared library the same build has just linked.

The compiled DOSFS objects are the disc module's. The disc DOSFS is unchanged
(`arclibre-dosfs.adf` remains `bf85248d…`).

## The gate

`tests/run_rom_4m.py`, three cold boots each, on an emulated A440/1:

- **DOSFS from ROM**, with nothing `*RMLoad`ed:
  - `*Help DOSFS` reports the ROM build;
  - `OS_Module 18` gives DOSFS's base address in this ROM;
  - it catalogues a host-made PC 720K disc and copies a file each way. The
    5,000-byte file arrives intact on ADFS, and the independent FAT parser
    finds the ReadMe on the PC disc.
- **The desktop**:
  - !Printers and !Alarm are double-clicked in `Resources:$.Apps`, and both
    run as tasks ("Printer Manager", "Alarm").
  - The FX-80 is dragged to !Printers from a floppy that holds only its
    definition, so the dot-matrix support code can only find PDriverDP,
    PDumperSupport and PDumperDM in ROM.
  - The printing gate's BASIC client prints its page. The Epson output is
    byte-identical to the printing disc gate's (`dd3f61c4…`).

The negative control is the 2 MB ROM: the same `RMEnsure` checks report
DOSFS, PDriver, PDriverDP, PDumperSupport, PDumperDM, PDriverPS, PDumperLJ
and !Alarm missing.

The other runtime gates that take a ROM directory were also run against
`build/arclibre-4m` in probe mode (one cold boot). They include the desktop
gate, whose trace check decodes every executed instruction of every module,
the new ones included.

## Limits

- The full release suite runs on the 2 MB ROM. The 4 MB ROM shares every byte
  of its modules and resources, except that the C modules are relinked at
  their positions in this ROM.
- The kernel is the 2 MB ROM's, assembled with `IMAGESIZE=2048K`. Only
  `OS_Memory` uses that constant, and like RISC OS 3.11 this ARM2 kernel has
  no `OS_Memory` (3.60 assembles it only for ARM6 and later processors;
  `SYS "OS_Memory"` gives "SWI &68 not known" on both ROMs). The module
  chain is walked by length, so the whole 4 MB is used.
- !Printers in ResourceFS can't save its choices, because ResourceFS is
  read-only.
- Building the 4 MB ROM relinks the shared C modules (Draw, Paint, Edit,
  SharedCLib, FilerAct, Squash) at its addresses. `make arclibre-rom` relinks
  them for the 2 MB ROM before any 2 MB gate.
- No 4 MB ROM board has been tested. Earlier research found that the A3000
  and A400 series take at most 2 MB of ROM (four 4 Mbit chips). The A5000's
  links take 8 Mbit chips, which give 4 MB, but this kernel is the
  A440/A3000 profile (see the hardware results).
