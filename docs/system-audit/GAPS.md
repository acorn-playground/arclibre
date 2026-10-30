# RISC OS 3.11 gaps and implementation status

This matrix began with names absent from the original audit ROM. Rows now mark
subsequently implemented services; unmarked rows remain work to do. Full source
pins are in [source-candidates.json](reports/source-candidates.json); actual
module presence is in the [current inventory](reports/current-inventory.json).
Presence and bounded gates do not certify complete 3.11 compatibility.

## Desktop and common services

| Reference title | Cleaned-3.60 candidate | Assessment |
|---|---|---|
| TaskWindow | `Desktop/TaskWindow` @ `9d0a32bfcc51` | Implemented; pre-emption and Edit/BASIC gates. |
| FilterManager | `Desktop/Filter` @ `0728a78f554b` | Implemented; ordered filters, removal and task-death gates. |
| Free | `Desktop/Free` @ `ad049d9991c6` | Implemented; live original free-space window checked against RAM filing. |
| RamFS | `FileSys/RAMFS/RAMFS` @ `ef43a7ada8c3` | Implemented; resize, contents, full-disk and cleanup gates. |
| RAMFSFiler | `FileSys/RAMFS/RAMFSFiler` @ `be30ead145d8` | Implemented; real icon opening and resize/restart lifecycle. |
| PipeFS | `FileSys/PipeFS` @ `614e2725452d` | Implemented; contents, EOF, blocked reader/writer wake-up and cleanup. |
| DeviceFS | `HWSupport/DeviceFS` @ `1d464cee133c` | Implemented; real registration, stream limits and buffered RX/TX. |
| SystemDevices | `HWSupport/SystemDevs` @ `32481c2bf1a8` | Implemented; null/vdu/rawvdu/rawkbd gate; serial/parallel drivers remain absent. |
| DOSFS | `FileSys/ImageFS/DOSFS` @ `ec870faf2112` | Disc-loaded module (owner decision), [verified](../dosfs/RESULTS.md) read/write/map/CopyBoot; independent boot sector and header. `*Format DOS/M` works with the delivered FileCore. 1.44M (A5000), 360K and FAT16 partition images also [gated](../dosfs/RESULTS.md#other-formats). |
| Squash | `Programmer/Squash` @ `a21ce91e3d0a` | Implemented; fast/restartable SWIs, interleaved workspaces, boundary/error and independent gzip gates. |
| ScreenBlanker | `Video/Render/ScrBlank` @ `9d17f822bccc` | Implemented; real frames/palette, timer, character-output wake-up and flashing. |
| RTCAdjust | `HWSupport/RTCAdjust` @ `a0f37cd91cdd` | Implemented; hourly recalibration matches its formula, drift, century and leap-day gates. |
| StringLib | `HWSupport/Sound/Voices/StringLib` @ `38468e6b6208` | Implemented; four original named voices execute in RAM and emit sound DMA. |
| Debugger | `Programmer/Debugger` @ `973b1967d8ff` | Implemented; disassembly/memory checked against ROM, breakpoint stop, registers and Continue. |

## Bundled utilities and Palette

| Reference title | Cleaned-3.60 candidate | Assessment |
|---|---|---|
| !Alarm | `Apps/Alarm` @ `ea4dc989e312` | Implemented; set/deliver with sound, browser runs generated Code, Quit/restart; alarm-file persistence untested. |
| !Calc | Not established (unpublished) | New ArcLibre `!Calc` 1.00 reproducing the 3.1 layout and four-function behaviour; not the original code. |
| !Chars | `Apps/Chars` @ `6360d0336eff` | Implemented from original BASIC/resources; Select/Shift, outline-font menu and task-close gates. |
| !Help | `Apps/Help` @ `01f0e2d2ee06` | Implemented from original BASIC/resources; real Filer help exchange, Quit/restart and flat template. |
| !Configure | Not established (3.11 unpublished; 3.60 C version ~105 KB) | New ArcLibre `!Configure` 1.00 reproducing the 3.1 Configuration window and eleven sections on original-machine CMOS settings, with Save/Load; Net shaded (no NetFS); not the original code. |
| PaletteUtil | Not established (unpublished) | New ArcLibre `PaletteUtil` 0.10 reproducing the 3.1 window, menu, save/load and grey coupling; not the original code. |

## Printing

| Reference title | Cleaned-3.60 candidate | Assessment |
|---|---|---|
| Printers | `Printing/PrinterManager` @ `8b91b0070ad8` | On the printing disc ([results](../printing/RESULTS.md)): !Printers 1.46 with the dot-matrix, LaserJet and PostScript classes; each installs a definition by drag and prints; crunched, not squished. |
| PDriver | `Printing/Modules/PDriver` @ `de4185f8a1dc` | On the printing disc; a print job's rectangles and VDU 5 text reach the file as Epson output. |
| PDriverDP | `Printing/Modules/PDModules` @ `d5db212e1513` | On the printing disc; renders the page at 120 x 72 dpi for the FX-80. |
| PDumperSupport | `Printing/Modules/PDumperSpt` @ `0748768b18f5` | On the printing disc, loaded by !Printers. |
| PDumperDM | `Printing/PDumpers` @ `45c309a19b63` | On the printing disc; its ESC L bit images are decoded and checked; without it the printer cannot be installed. |
| PDriverPS | `Printing/Modules/PDModules` @ `d5db212e1513` | On the printing disc with !Printers' `ps` class; an Apple LaserWriter job is checked as PostScript and rasterised on the host. No MakePSFont, so outline fonts on PostScript printers are untested. |
| PDumperLJ | `Printing/PDumpers` @ `45c309a19b63` | On the printing disc with !Printers' `lj` class; an HP LaserJet II job's PCL raster is decoded and checked. |
| ParallelDeviceDriver | `HWSupport/Parallel` @ `f9e3bcbbcc58` | Implemented with the IOC port restored; output queues while the printer is BUSY (no printer is modelled); on the A5000 family the first byte reaches the 82C711 port, strobed. |

## Hardware profile

| Reference title | Cleaned-3.60 candidate | Assessment |
|---|---|---|
| Podule | `HWSupport/Podule` @ `b33cb3fa3237` | Implemented as 3.11's four-slot IOC manager (no EASI or network slot); empty-slot scan, errors and 3.11 wording gated ([results](../hardware/RESULTS.md)); card ROMs untested. |
| ARM3Support | Not established (unpublished) | New ArcLibre `ARM3Support` 1.00: `Cache_` SWIs, `*Cache`, `*Configure Cache`; cache on at start on an ARM3 (4.7× faster loop), dormant on an ARM2; not the original code. |
| IIC | `HWSupport/IIC` @ `3a9726dcc5cf` | Implemented; original IOC bit-banged `IIC_Control`, real PCF8583 reads and writes and NoAck error. |
| Joystick | `HWSupport/Joystick` @ `2575b028f54b` | Board/podule-specific hardware; dormant on supplied reference. |
| SerialDeviceDriver | `HWSupport/Serial` @ `4d0e504f000e` | Implemented with the 6551 path restored; `serial:` device and 6551 baud/format programming gated; the 82C711 UART's baud divisor gated on the A5000 family; no line traffic (MacArch models neither line). |
| SerialDeviceSupport | `HWSupport/SerialSpt` @ `36b69cb232a2` | Implemented; `OS_SerialOp` baud and format calls gated through the driver. |
| Portable | `HWSupport/Portable` @ `e5f03547d739` | Dormant reference; portable-machine policy outside A440 target profile. |
| A5000-family I/O (kernel) | `Kernel` `s/PMF/osinit` (`ReadMachineType`, `Configure82C710`) | Implemented: the delivered kernel probes for the IOEB and 82C710/711 as 3.11 did; ADFS (765 floppy, IDE), Serial and Parallel choose their hardware from it. A5000, A3010 and A3020 [gated](../new-io/RESULTS.md); physical machines untested. |

## Networking

| Reference title | Cleaned-3.60 candidate | Assessment |
|---|---|---|
| Econet | `Networking/Econet` @ `413ae41f105d` | Implemented in ROM ([results](../network/RESULTS.md)); two-station transmit/receive and broadcast gated; dormant without an Econet module, as on 3.11. |
| BBCEconet | `Networking/BBCEconet` @ `5a1db236887c` | Implemented in ROM; answers `*Help`; its BBC calls are untested. |
| NetFS | `FileSys/NetFS/NetFS` @ `3b392f000e60` | Implemented in ROM; logon, catalogue, load, save, open files, directory changes, errors and logoff gated against a host-side file server. |
| BroadcastLoader | Not established | No public source; not in 3.11's ROM either. !Configure stores its two CMOS bits. |
| NetFiler | `FileSys/NetFS/NetFiler` @ `e0076648687f` | Implemented in ROM; logon box, server icon, viewers, FS list, Free and Bye gated on the desktop. |
| NetPrint | `FileSys/NetPrint` @ `c7aa0ed87482` | Implemented in ROM; answers `*Help` and `*Configure PS`; printing to a printer server is untested. |
| NetStatus | `Networking/NetStatus` @ `3e8e96c5cbff` | Implemented in ROM; NetFS's progress upcalls drive the hourglass percentage in the NetFS gate. |
| NetUtils | `Networking/NetUtils` — no matching pin | Repository exists, but no exact cleaned-360 import subject found. |

## Historical patch identities

| Reference title | Cleaned-3.60 candidate | Assessment |
|---|---|---|
| IRQUtils | `Utilities/Patches/IRQUtils2` @ `1984643f955e` | Cohort IRQUtils2 is the historical empty patch-marker module; no runtime implementation to restore. |
| WindowUtils | `Desktop/WimpUtils` @ `717510785f21` | Use s/WimpUtils2 assessment: original empty 2.50 marker, not s/WimpUtils old Wimp-2.00 patch. |
| ADFSUtils | `FileSys/ADFS/ADFS` @ `b32ebc4dd794` | Maintained ADFS s/Fixes fix 9 records incorporation; do not layer old patch onto current ADFS. |

## Known behaviour differences

| Area | RISC OS 3.11 | ArcLibre | Effect |
|---|---|---|---|
| The library (`%`) when none is set | Canonicalising `%` gives `#:%` | FileSwitch (from 3.60) falls back to a `$.Library` on the disc last used, which can be a floppy | Both make Acorn C/C++'s installer fail at its Library step: 3.11 with "#:% could not be installed", ArcLibre by asking for the installer's disc again. With a hard disc holding `$.Library` mounted (`*Configure Drive 4`, or `*Mount :4`), the library is set and both work. Found with Acorn C/C++ 5 on an emulated A5000, 30 October 2026. |
