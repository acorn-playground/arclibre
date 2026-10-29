# RAM filing and free-space restoration

RamFS 1,684 bytes, RAMFSFiler 2,432 bytes and Free 4,704 bytes now assemble
reproducibly for ARM2. They now pass three identical cold runtime gates on ROM
`1059cfb0b5b4b87ca1828a428a5cf8f0fa01c9b1f305ec6f1f395fbf813624ee`.
This source set is the default ROM profile. The [final integration report](../archimedes-desktop/reports/integration.json)
records the completed release-wide gates; the result below is the dedicated RAM gate. The [assembly report](reports/assembly.json)
covers two normal AOF assemblies and an independent observer assembly with
identical bytes, no relocations/unresolved symbols, independent instruction
and branch decoding, code/data boundaries and ARM2 PSR settling checks.

The 50 selected files are pinned in `manifests/ram-filing-inputs.json`.
`patches/ram-filing/series` reverses to those exact upstream hashes and reapplies
without fuzz. Changes supply explicit areas, normalise include/link paths,
rename the colliding ENTRY macro, correct the incomplete `:OR` spelling,
use the canonical RamFS/Free SWI bases, and add Free's PSR settling instruction.
OS_GenerateError is treated as a non-returning transfer where the original
RAMFSFiler intentionally falls into an inline error block otherwise.

The Free profile registers the real ADFS and RAM providers, and (since
networking joined the ROM) NetFS's (`ArcLibre_NetFSFreeProvider`; Free is now
5,108 bytes; tested by [the NetFS gate](../network/RESULTS.md)). The SCSI and
NFS adapters remain in source but are excluded because those filing systems
are absent from this ROM. Free's public provider registration interface remains;
there are no fabricated free-space answers for unsupported filing systems.
The flat original `Template2D` is selected as `Resources.Free.Templates`.
See [asset hashes](reports/resources.json) and [licensing](../../LICENSING.md).

RamFS uses the original `OS_ReadRAMFsLimits` contract, its own declared RMA
workspace, and real FileCore_Create/FloppyStructure/DiscOp services. It remains
dormant when no RAM disk is allocated. RAMFSFiler retains the original dynamic
area sizing and desktop service logic. No fixed kernel workspace has been
invented or substituted. The runtime gate below checks resize, contents, full/error behaviour, icon
lifecycle and Free's live updates.

```sh
python3 tools/build_ram_filing.py
ARCLIBRE_INSTALL_ROM=0 python3 tools/build_arclibre_rom.py --with-ram-filing
```

Neither assembly nor module presence establishes RISC OS 3.11 compatibility.

## Desktop startup order

The candidate must start TaskManager before Filer. TaskManager allocates its
workspace during Service_StartWimp and records Filer's task handle during
Service_StartFiler. The earlier ArcLibre order started Filer first; the service
arrived before TaskManager had workspace, so later RAM resizing could not
restart RAMFSFiler. The [captured failure](reports/startup-order-before.json)
records that ordering. The ROM joiner now places Switcher before Filer for the
desktop profiles, preserving Desktop's configured language index. No module
code, service number or emulator behaviour is changed to bypass the dependency.

The expanded guest test checks real mouse opening of the RAM icon, Free's own
window totals against RamFS_FreeSpace, nonempty-resize error &1C3, full-disk
error &117C6, and restoration after deletion. [Repeated runtime acceptance](reports/acceptance.json) now passes on three
identical cold machines, with sampled ROM and guest instructions independently
verified and all undefined exceptions classified as expected software-FPA traps.
There are no data or prefetch aborts. The otherwise working stream ROM without
these providers fails at the first real RAM: access. No emulator change or
code injection is used.

## Runtime memory and filing contract

The public client agrees OS_ReadDynamicArea area 5's base/size with
OS_ReadRAMFsLimits' start/end at every checked size. Empty disks grow from zero
to 256 KiB to 512 KiB, shrink to 256 KiB, and return to zero. A nonempty disk
refuses resizing with &1C3, leaving its size and 65,536-byte payload unchanged.
Filling the disk produces FileCore's RAM filing error &117C6; the existing
payload remains readable. Deleting all fixture files restores exactly the
original free space.

The real TaskManager command `*ChangeDynamicArea -RamFsSize 256K` drives the
RAMFSFiler restart service. A mouse click on its actual icon opens
`RAM::RamDisc0.$`; [capture](reports/ram-disc-open.png). The original Free task's
window records agree with the public RamFS_FreeSpace result: total 262,144,
free 257,024 and used 5,120 bytes before writing; free 191,488 and used 70,656
after the 65,536-byte write; then the original totals after deletion. The
window's high words remain zero. Removing the disk removes its task and returns
to the seven persistent desktop tasks, without altering the other filers.

The intermediate 41fd4e95 RAM/stream candidate used 1,910,996 bytes, leaving 186,156 bytes in the 2 MiB
container. It retains the original applications in ROM. This is not exhaustive
coverage of every disk size, low-memory condition, Free provider or application.

```sh
python3 tests/run_ram_filing.py
```

The [intermediate integration report](reports/integration.json) records all
retained desktop, filing, editing, sound, stream and private launch gates
passing on the 41fd4e95 RAM/stream image before adding standard utilities.
Nevryon's observation boundary was corrected to allow a real sound IRQ to
return; the ROM and game bytes were unchanged.
