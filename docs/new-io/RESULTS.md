# The A5000 family: IOEB and the 82C710/711

RISC OS 3.11 was one ROM for every machine. At reset its kernel probes for the
IOEB and an 82C710/711 combination chip, which the A5000, A3010, A3020 and
A4000 have and the A300, A400 series and A3000 don't, and reports what it
finds through `OS_ReadSysInfo 2` and `3`. ADFS, Serial and Parallel then pick
their drivers at initialisation: the 1772 or the 765 floppy controller, IDE,
the 6551 or the 82C711's UART, the printer latch or the 82C711's port.

The cleaned 3.60 kernel still has that probe (`ReadMachineType` and
`Configure82C710` in `s/PMF/osinit`). The A440/1 profile that ArcLibre
restored from had switched it off (`HasIOEB`), so on an A5000 the kernel
reported old I/O and ADFS drove a 1772 that isn't there.

## The change

`Hdr:Machine.A440` sets `HasIOEB` for the delivered ROM (`ArcLibreDelivered`),
so it probes as 3.11 did. The frozen baseline keeps `{FALSE}` and its exact
bytes. `tools/verify.py` checks each profile's value. The probe's two
`TEQP`s gained the settling `MOV r0, r0` ARM2 needs (its first had a `MOVNV`,
which the ARM2 checks don't accept). Nothing else changed: the IRQ tables
for IOC-A1 and IOEB put the same bits on the same devices, and the kernel
already programs the IOEB's pixel clock and reads the monitor ID lines when an
IOEB is present. The ROM grew by 76 bytes.

On an A440/1 or A3000 the probe reads no IOEB, as on 3.11. Every other gate
runs on those machines and is unchanged.

## The gate

`tests/run_new_io.py` (NewIOProbe) boots the delivered ROM to the desktop,
three cold boots each, on an emulated A5000 (ARM3, IDE), A3010 (ARM250, no
IDE) and A3020 (ARM250, IDE), and types at the F12 command line:

| Check | Result |
|---|---|
| `OS_ReadSysInfo 2` | IOEB, 82C710-class chip: `1 1 0`, as RISC OS 3.11 on the same emulated A5000 |
| `OS_ReadSysInfo 3` | `101111`: the 82C710's IDE, FDC, parallel, serial and config sub-units |
| 765 floppy | catalogues an ADFS D disc and writes a copy of a file to it |
| IDE (A5000, A3020) | catalogues a host-built ADFS hard disc and copies a file each way; both checked on the host |
| Serial | `OS_SerialOp` 9600 baud sets the UART's divisor latch to 12 (1.8432 MHz / 16 / 9600), from MacArch's trace of 82C711 writes |
| Parallel | a byte for the printer reaches the 82C711's data port, strobed through its control port |
| Monitor (A5000) | the ID lines read as monitor types 0, 1 and 3 for standard, multisync and VGA; on VGA the 25.175 MHz pixel clock is selected |

The negative control is the frozen baseline ROM (`HasIOEB` false) on the same
A5000: its ADFS drives the absent 1772, never touches the 82C711, and
catalogues nothing.

DOSFS on the 765 (1.44M and FAT16 partitions on IDE) is in
[the DOSFS formats gate](../dosfs/RESULTS.md).

## Limits

- MacArch models no 82C711 serial line or printer, so the UART and the
  printer port are checked by the values written to them. Only the first
  printer byte goes, because no acknowledge comes back.
- MacArch's 765 raises disc changed only while a drive is empty. Real drives
  also raise it from power-on until a step, and that is how ADFS learns the
  line works. Without it ADFS treats each motor start as "maybe changed", so
  FileCore re-identifies floppies more often than on real hardware (see the
  DOSFS results for the one place it shows).
- The A4000 (like the A3020) and the A5000 with other processors aren't run
  separately.
- No physical A5000-family machine has been tested.
- The 4 MB ROM fits only the A5000's ROM sockets. This kernel has no
  `OS_Memory` (3.60 assembles it only for ARM6 and later, and RISC OS 3.11
  had none), so nothing reports the ROM size.
