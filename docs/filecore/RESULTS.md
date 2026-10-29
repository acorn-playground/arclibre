# Delivered FileCore: formatting without FSLock

FileCore 3.60 (`src/FileCore`) checks every `SWI DiscOp` write with
`EnsureFSLock` (`s/GenSWIs`). Two things went wrong on a RISC OS 3.11-class
ROM:

1. The routine means to skip floppy drives (`CMP r2,#4` then
   `Pull ...,LO`), but `CLRV` sits between them. In 26-bit RISC OS, `CLRV`
   is the macro `CMP pc,#0`, which always sets C. So the `LO` return never
   happened, and floppies were checked too.
2. The check calls `FSLock_Status` (SWI &44781). FSLock was in the 3.60 ROM,
   so 3.60 never noticed the first defect. RISC OS 3.11 had no FSLock, and
   neither does ArcLibre, so the SWI is unknown.

As a result, `*Format` failed for every format at "Formatting track 1" with
`SWI &44781 not known`. ADFS and DOSFS were both affected, as was any
`ADFS_DiscOp` write, floppy or hard disc.

## The change

`patches/restoration/0032-filecore-without-fslock.patch` is guarded by
`ArcLibreDelivered`:

- V is cleared before the drive comparison, so floppies return at once.
- For hard discs, an FSLock that is absent ("SWI not known", &1E6) means no
  lock. Any other FSLock error is returned as before.

`tools/build.py --desktop-defaults` predefines `ArcLibreDelivered` for the
kernel and the baseline modules, and the delivered ROM takes FileCore from
that build. `tools/build.py --baseline` still reproduces the frozen baseline
ROM, kernel and every module exactly. The delivered kernel's bytes are
unchanged. The previous release with only the baseline FileCore is rebuilt
byte for byte by `tools/build_arclibre_rom.py --baseline-filecore` (`9f7f9196…`).

## Gate

`tests/run_format.py` uses `FormatProbe`. It boots with an ADFS floppy and a
generated ST506 hard disc. At the real F12 command line it runs, on three cold
boots each:

- **E format:** `*Format 0 E` (160 tracks). BASIC then writes a 3,000-byte
  patterned file, and `ADFS_DiscOp` writes a 256-byte sector to drive 4 and
  reads it back.
  - The host reader (`tests/adfs_newmap.py`) is written from the documented
    structures and shares no code with FileCore or the fixture writer.
  - It checks the zone check byte, both map copies, the disc record (1024-byte
    sectors, 5 per track, 2 heads, double density, idlen 15, 128 bytes per
    map bit, root &203, 819,200 bytes), the exact fragment tiling and free
    chain, the root `Nick` directory, and the file's bytes.
- **D format:** the same steps. The reader checks FileCore 3.60's `Nick` root
  at &400, the old free-space map and the file's bytes.
- **Negative control:** the same ROM with the baseline FileCore fails `*Format`
  at the first track and the `DiscOp` write with `SWI &44781 not known`, and
  the floppy is unchanged.

The DOSFS gate now formats a PC disc too ([DOSFS results](../dosfs/RESULTS.md)).

Not exercised: IDE discs, multi-zone (F-format and hard-disc) maps, the
Filer's format menu, and physical drives.
