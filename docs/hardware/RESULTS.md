# Expansion cards, serial and parallel ports

RISC OS 3.11 has four hardware modules in ROM that ArcLibre lacked: the Podule
Manager (expansion cards), SerialDeviceDriver, SerialDeviceSupport and
ParallelDeviceDriver. Without them `*Podules` was unknown, expansion card ROMs
were never started, `devices:$` was empty and nothing could be sent to the
serial or printer ports. They are now in the delivered ROM.

## Sources and changes

The originals come from the cleaned-3.60 HWSupport repositories at the
revisions in `manifests/hardware-inputs.json` (all 5 November 1996), imported by
`tools/import_hardware.py` and built and statically checked by the `hardware`
group of `tools/build_system_modules.py`. `patches/hardware/0001-arm2-build.patch`
holds every change:

- **Podule** is configured as 3.11's Podule Manager: four IOC slots
  (&33C0000–&33CC000), no network card slot and no EASI space. 3.60 built eight
  slots, the network slot and EASI space for the Risc PC. On an IOC machine
  slots 4–7 would decode a different IOC bank, and the network slot's speed
  call writes IOMD's IOTCR, which IOC aliases onto a timer register.
- **SerialDeviceDriver and ParallelDeviceDriver** are built with `OldHardware`
  on, as 3.11 was: the 6551 ACIA and the IOC printer port of the A3000 and
  A300/A400 series. 3.60 had switched these off "to save space for RO Black".
  The 82C710 code (`NewHardware`) stays in.
- **ARM2 assembly contracts**, as in the network and clock patches:
  - an `AREA` for AsAsm (replacing `LEADR`);
  - `KernelEntry` for the old `ENTRY` macro;
  - Podule's SWI chunk from `PoduleSWI_Base`;
  - a settling `MOV r0,r0` after every PSR write. Two of these, in
    `Serial710`, switch between IRQ and SVC mode, where ARM2 needs one before
    the banked `lr` is used.
- **Podule's messages and help** use 3.11's wording ("Podule 0: No installed
  podule", "Bad podule number") instead of 3.60's "expansion card".

| Module | 3.11 (reference) | ArcLibre |
|---|---:|---:|
| Podule | 6,684 | 5,816 |
| SerialDeviceDriver | 5,756 | 6,280 |
| SerialDeviceSupport | 1,672 | 1,700 |
| ParallelDeviceDriver | 3,040 | 4,240 |

With their messages, the ROM grows by 19,780 bytes. Podule follows Desktop,
which must stay the ninth module for the configured language. The drivers
follow DeviceFS, as in 3.11.

## The gate

`tests/run_hardware.py` (HardwareProbe) boots the delivered ROM three times
each on an emulated A440/1 and A3000 and types at the F12 command line:

- `*Podules` lists four empty slots in 3.11's wording, and `*Help Podules` matches.
- `Podule_ReadID` and `Podule_ReadHeader` return the real &502 "No installed
  podule" error, as 3.11 does for every slot number.
- `devices:$` holds `Parallel` (write) and `Serial` (read/write).
- `OS_SerialOp` 5 and 6 set receive 9600 and transmit 19200 and read them back.
  The 6551's control register is written with the baud generator code (&8,
  then &F).
- `OS_SerialOp` 1 writes the data format into the 6551's control and command
  registers (&BF and &5F for &15). It reads the format back from the chip,
  as 3.11 does.
- `serial:` opens and closes.
- Bytes written to `parallel:` stay queued while the printer reports BUSY.
  The driver enables the acknowledge interrupt, and nothing is written to the
  printer data latch.

The probe records guest writes to the 6551 and the printer latch through the
emulator's report of unmodelled accesses. No guest code is injected and the
emulator is unchanged.

The negative control is the ROM without the four modules (byte-identical to
ArcLibre 0.8, d83d2e8c). There, `*Podules` is unknown, the Podule SWI names are
unknown, `devices:$` is empty, `OS_SerialOp` is unclaimed and `parallel:` is
not present.

### Compared with 3.11

The same calls were checked by hand on the owner's 3.11 ROM on the same
emulated A3000 and A440/1. The comparison isn't automated: 3.11 takes data
aborts while it boots, which the probe treats as faults. The checks:

- `Podule_ReadID`: &502 for slots 0–8.
- `*Podules`: the same text.
- `OS_SerialOp` 0 (flags): &200C0000.
- `OS_SerialOp` 1 reads &3F whatever was written.

Baud and printer settings differ only because each kernel stores different
CMOS defaults.

## Limits

- MacArch models no 6551 and no printer. Serial bytes can't be shown on a
  line, and the IOC printer port always reads BUSY, so no character is strobed
  out.
- No expansion card is fitted. Only the empty-slot scan and its errors are
  exercised; loading a card's ROM modules is untested.
- The delivered kernel is the A440/A3000 profile, which never probes for IOEB.
  On an A5000 or ARM250 machine `OS_ReadSysInfo 2` returns 0 (3.11 returns
  IOEB and 82C710), so the drivers' 82C710 paths are built but never reached.
  ADFS also uses the 1772 path there. Supporting those machines is separate
  kernel work.
- Physical hardware is untested.

## Modules not restored

3.11 also has IRQUtils 2.50 and WindowUtils 2.50, 84 and 88 bytes each. They
have a title and a help string and no code, so that RISC OS 2-era
`RMEnsure` lines succeed. Nothing found refers to them, so they're left out.
ADFSUtils 0.05 patches background floppy completion on the 82C711. That fix is
already in ArcLibre's ADFS (`src/ADFS/s/Fixes`, fix 9).
