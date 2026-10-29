# Original networking modules (in the delivered ROM)

The owner chose networking in ROM as the next milestone. They are in the
delivered ROM, as in RISC OS 3.11; to make room, !Alarm moved to its own disc
by owner decision (28 Oct 2026; `docs/desktop-utilities/RESULTS.md`). These are the
original cleaned-3.60 sources, pinned in `manifests/network-inputs.json` by
`tools/import_network.py`:

| Module | Source | Revision |
|---|---|---|
| Econet | Networking/Econet | `413ae41f105d` |
| BBCEconet | Networking/BBCEconet | `5a1db236887c` |
| NetFS | FileSys/NetFS/NetFS | `3b392f000e60` |
| NetFiler | FileSys/NetFS/NetFiler | `e0076648687f` |
| NetPrint | FileSys/NetPrint | `c7aa0ed87482` |
| NetStatus | Networking/NetStatus | `3e8e96c5cbff` |

`Hdr:PoduleReg` comes from Programmer/HdrSrc at `403c6dd8bce9`, the revision
already pinned for public allocation headers. BroadcastLoader has no public
source.

## ARM2 build

`make network-components` (`tools/build_system_modules.py network`) runs the
same checks as the other system modules:

- the same output from two normal builds and one observer build;
- an independent ARM2 decode of every instruction;
- no branch into data, no fall-through into data, and settling after PSR
  writes;
- no absolute `ADR`, and no unresolved symbols or relocations.

NetFS and NetPrint tokenise their `HelpTexts` with the kernel dictionary, as
their Makefiles do.

`patches/network/0001-arm2-build.patch` changes 19 of the 56 files, and
`tools/verify_candidate_patches.py` checks it in both directions. Each
modified file carries a notice. The changes:

- **Assembler syntax.**
  - `AREA` directives; NetFiler's `LEADR` is dropped.
  - Acorn shift shorthand written out (`ASR r13, 8` → `MOV r13, r13, ASR #8`;
    `RRX r0, S` → `MOVS r0, r0, RRX`).
  - Acorn's `ENTRY` macro renamed to `KernelEntry`, to avoid AsAsm's
    directive.
  - `ALIGN` before code labels that follow text.
- **Fixed addresses written as `MOV #…`** rather than `ADR`: IOC, the FIQ
  vector, `NextJump`, `ModuleWorkspace`, `Registers`, `ReceiveHandles` and
  `ScratchSpace`.
- **SWI chunks.** NetFS's and NetPrint's are written as the header's chunk
  base: `NetFS_ReadFSNumber` and `NetPrintSWI_Base`.
- **Econet's `SetFIQ` macro** no longer emits the ARM6 `MRS`/`MSR` 32-bit mode
  switch. Its guards were a literal `{TRUE}` ("cope with 32bit CPUs"), and ARM2
  and ARM3 have no 32-bit mode.
- **Byte stores of the PC** (an Acorn "non-zero flag" shortcut) become
  `MOV rN, #1` plus a store, using a free register at each of the three sites.
- **Econet's FIQ "get registers"** user-bank `STMIA r9!,{r0-r14}^` (writeback
  with `^`, which ARM2 forbids) becomes `STMIA r9, {...}^`, a settling NOP,
  then `ADD r9, r9, #60`.
- **A settling `MOV r0, r0`** after every PSR-writing compare that lacked one.

`ALIGN 16,12` padding inside Econet's FIQ code is recorded in
`alignment-padding.json`; it is never executed.

## Exact size

| Module | Bytes |
|---|---|
| Econet | 12,880 |
| BBCEconet | 2,172 |
| NetFS | 24,820 |
| NetFiler | 8,308 |
| NetPrint | 8,144 |
| NetStatus | 800 |
| Size words | 24 |
| Resources in ROM (comments stripped): Econet 2,164; NetFS 3,676; NetFiler 1,704 + Templates 908; NetPrint 1,616 | 10,068 |
| **Total** | **67,216** |

Before the move the ROM had 30,864 bytes free, a shortfall of 36,352 bytes.
Moving Alarm out freed 83,796 bytes. The colour dialogue fix in the same
batch (`docs/graphics-apps/RESULTS.md`) and !Configure's Net section (below)
took a few KB; the delivered ROM now has **20,716 bytes free** with all six
modules in it.

## On a machine without Econet

As on RISC OS 3.11 (observed on the owner's own 3.11 ROM): Econet finds no
Econet module and does not start, so neither do NetFS, NetPrint and
BBCEconet. NetFiler and NetStatus stay listed; NetFiler starts no task and
puts no Net icon on the icon bar. Every other gate runs this way, with the
same task counts as before. !Configure's Net section is shaded.

## Running them

`tests/run_network.py` (NetProbe) puts two A440s on one emulated Econet line,
as stations 1 and 2, and runs three cold boots:

- **Econet 5.70.**
  - Station 2 opens a receive on port &50 for station 1. Station 1's
    `Econet_DoTransmit` returns 0. Station 2 reads status 9 (received),
    port &50, sender 1, 15 bytes, `HELLO ARCLIBRE`.
  - A broadcast from station 2 reaches station 1's wildcard receive on
    port &51.
  - `Econet_ReadLocalStationAndNet` gives 1.0 and 2.0.
- **NetFS.**
  - Its tokenised `*Help` works, as do `*Configure FS 0.254` and
    `*Status FS` ("File server 254").
  - `*I Am Syst` with no server gives NetFS's own error, "The network station
    254 cannot be found…".
- **NetPrint and BBCEconet** answer `*Help`.
- **Negative control.** On the same ROM built without the networking
  modules (`build_arclibre_rom.py --without-network`), the same commands
  give "No help found" and "SWI name not known".

## !Configure's Net section

On an Econet station NetFS starts, and !Configure's Net section is no longer
shaded. Its window follows the 3.60 template, which matches 3.11's (observed
on the owner's ROM with an emulated Econet station): This station, File
server and Print server (each a writable field and a menu button), Use
Arthurlib, and a Broadcast Loader group (Enable; Colour hourglass when used,
shaded while broadcast loading is off). Servers are set through NetFS's and
NetPrint's own `*Configure FS` / `*Configure PS`, and shown from CMOS RAM as
NetFS keeps them: a station number, or a name. The menu buttons list file
servers (`NetFS_EnumerateFSList`) and printer servers
(`NetPrint_ListServers`, which listens for five seconds). The options write
CMOS &11 bit 1 and &C3 bits 6 and 7. BroadcastLoader itself has no public
source and is not in the ROM (nor was it in 3.11's), so those two bits are
only stored.

`tests/run_basic_utilities.py` has a ConfigureNet trial in each of its three
cold boots (`DesktopLaunchProbe ... !Configure net`, station 1, no other
stations):

- the window shows station 0.1 and all the 3.11 controls;
- `0.254` sets the file server by number (CMOS &01 = 254, &02 = 0);
- `Fred` sets it by name (&01 = 0, &02 = "F", &9E onwards "red");
- `0.235` sets the printer server (&03 = 235, &04 = 0);
- Use Arthurlib and Enable toggle their bits, Colour hourglass is shaded
  only while broadcast loading is off, and both menu buttons open no menu
  and report no error, because no server answers;
- NetFiler is one more desktop task, as on 3.11.

On this emulated machine's CMOS defaults broadcast loading starts off
(&C3 bit 6 set); on the 3.11 machine it started on. Only the stored bit
differs, since neither ROM has BroadcastLoader.

## Savings measured (not applied)

| Source | Saving |
|---|---|
| Dictionary-tokenising international `*Help` and syntax messages | 7,162 bytes for modules, plus about 4 KB for the kernel's help |
| Post-3.11 Wimp, Sound0 and FileCore switches that switch off cleanly (`tools/measure_feature_switches.py`) | About 1.1 KB |
| Larger post-3.11 features: outline-font desktop, window tiling, Medusa memory, BigDisc | Unknown: the 3.60 sources no longer build without them, so source surgery would be needed |
| Unreferenced C functions in Draw, Paint and FilerAction | None |
| `-ffunction-sections` | Has no effect in GCCSDK 3.4's AOF output |
| `-mno-apcs-frame` | Has no effect under `-mlibscl -mmodule` |

These savings come to about 12 KB. They were not needed once Alarm moved to
disc and are not applied.

## NetFS, NetFiler and NetStatus against a file server

`tests/run_netfs.py` (NetFSProbe) puts an A440/1 at station 1 on an emulated
line with a file server at station 254 that runs on the host. The server is
the gate's own in-memory Acorn file server, written from the PRM's
file-server protocol and the NetFS client source. It is attached through
MacArch's public `EconetGateway`, which answers for stations that aren't
emulated machines; there are no MacArch changes and no guest code. Three cold
boots must observe the same.

At the command line:

- the server's own errors reach the user: unknown user, wrong password,
  non-empty directory;
- `*ListFS` finds the server by broadcast;
- `*I Am`, `*Cat`, `*Ex`, `*Free` and `*Info` show its catalogue and space;
- BASIC loads a file whose checksum matches the server's bytes, saves files
  with `OS_File` and `SAVE`, `CHAIN`s one back, and writes and reads a file
  with `OPENOUT`, `BPUT`, `OPENIN`, `PTR`, `BGET`, `EXT` and `EOF`;
- `*CDir`, `*Rename`, `*Access`, `*Dir` and `*Delete` change the store, and
  `*Bye` logs off.

The server's store is compared byte for byte with what the client wrote.

On the desktop:

- NetFiler's Net icon opens its logon box;
- logging on makes the server's icon and a Filer viewer of its root, and a
  subdirectory viewer opens;
- the file server list is filled by broadcast;
- a 76,800-byte file loads into Edit, while NetStatus turns NetFS's upcalls
  into the hourglass percentage;
- Free opens "Free space on Harness" with the server's figures (file server
  functions 26 and 30);
- Bye restores the Net icon.

Screenshots of each state are kept.

The negative control is the same logon with nothing answering for station
254: NetFS reports that the station cannot be found.

### Free's NetFS provider

The gate found that NetFiler's Free failed with "Unknown filing system". The
Free module's NetFS provider had been assembled out with its SCSIFS and NFS
providers (`ArcLibre_ExternalFreeProviders`) before NetFS was in the ROM. A
separate `ArcLibre_NetFSFreeProvider` now includes only the NetFS one. SCSIFS
and NFS are still absent.

### Limits

- The server isn't an Acorn one: one disc, two users, owner access only,
  24-bit files. Functions 28, 31 and 33 onwards answer "Bad command"; NetFS
  doesn't use them.
- There's one client station; two clients aren't tested sharing the server.
- NetStatus is seen through its `Hourglass_Percentage` calls and the
  screenshots. Its colour hourglass for broadcast load/save isn't exercised.
- Reading the source turned up two original slips that this gate doesn't
  reach:
  - NetStatus's label 35 passes the wrong register to `Hourglass_Percentage`
    on a nested start.
  - NetFS's `*Cat` asks for 14 entries of 19 bytes, which a full reply
    would overflow its 258-byte buffer with; the gate's server sends at
    most 13.
