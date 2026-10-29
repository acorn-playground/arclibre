# Original character-stream restoration

The pinned cleaned-3.60 DeviceFS 0.30, SystemDevices 1.25 and PipeFS 0.15
modules now assemble as original ARM2/APCS-26 modules and pass three identical
cold runtime gates on ROM `1059cfb0b5b4b87ca1828a428a5cf8f0fa01c9b1f305ec6f1f395fbf813624ee`.
They are selected in the default build. The [final integration report](../archimedes-desktop/reports/integration.json)
records the completed release-wide gates. Runtime scope is described below.

`manifests/stream-inputs.json` preserves all 42 selected upstream file hashes.
`patches/streams/series` reverses and reapplies without fuzz. The first patch:

- supplies explicit relocatable code areas, replaces obsolete LEADR, and uses
  the already restored KernelEntry macro instead of AsAsm's ENTRY directive;
- normalises source include paths/case and the literal backslash spelling;
- uses DeviceFSSWI_Base (&42740), avoiding the legacy double-added SWI base;
- inserts eight explicit ARM2 PSR settling slots;
- widens one PipeFS address calculation to ADRL;
- makes PipeFS's Escape return unconditional after the no-Escape branch and
  its genuine CopyError call, so no path can fall into inline error data.

No hardware driver, stream operation or workspace is replaced by a stub.
SystemDevices retains its original independent pseudo-filing-system providers;
DeviceFS is a separate driver registration/buffering framework. This cohort
intentionally does not export serial: from SystemDevices: that requires the
real serial driver in a later hardware milestone. Printer streams still depend
on the genuine kernel/driver destination, not a synthetic printer.

The builder compares two normal assemblies with the observer AOF, independently
decodes every emitted instruction, rejects unresolved symbols and relocations,
checks branch targets and status-register settling, and checks code/data
boundaries. Adjacent complementary conditional returns are accepted only when
both write PC: the non-taken first return cannot change flags. DeviceFS's public
ESC_Status import is checked against the actual kernel symbol (&104).
The original module-defined RMA structures are retained.

Code sizes are DeviceFS 8,016, SystemDevices 3,424 and PipeFS 4,352 bytes.
See [assembly](reports/assembly.json) and [workspace](reports/workspace-contract.json).
The UK messages are the sole selected assets, with their original component
Apache-2.0 licences; see [licensing](../../LICENSING.md).

```sh
python3 tools/build_streams.py
ARCLIBRE_INSTALL_ROM=0 python3 tools/build_arclibre_rom.py --with-streams
```

The public `!StrTest` fixture is loaded through the real desktop/FileSwitch
path. It registers its own genuine DeviceFS endpoint from guest-claimed RMA;
this test driver is not in the ROM. Its bytes, callbacks, stream limits,
24-byte buffered RX/TX transfers, EOF and deregistration are checked. The
current driver ABI uses r3 bit 0 for direction and r2 for the opaque external
handle. The cohort's DeviceFS implementation and original Serial6551/Parallel
initialise callbacks agree; the older Doc/Calls r2-bit description is stale.
Specific interface evidence: Serial `4d0e504f000ea706a6d07c69e35d82380b02c797`,
`s/Serial6551` openACIA; Parallel `f9e3bcbbcc5849d4965077d5abafdd99db5954f0`,
`s/Common`. Those drivers are not imported or claimed as working here.

The test exercises real null:, vdu:, rawvdu: and rawkbd: streams, 769-byte pipe
contents and EOF, empty-reader and full-writer sleep/wakeup through TaskWindow,
read-past-EOF error 223, refusal to delete an open pipe, and explicit cleanup
of a killed writer's global file handle. TaskWindow does not own all ordinary
FileSwitch handles: killing the task alone does not close them. FileSwitch also
may deallocate a handle after an unsuccessful close; the test does not promise
handle preservation after a close error.

A separate caller-owned RMA poll word exercises public UpCall_Sleep (6) and
UpCall_SleepNoMore (7). It exposed a genuine original TaskWindow bug: its error
return followed the next vector owner instead of claiming the vector. Another
owner could clear V while leaving the error pointer in r0. The four-byte
[TaskWindow correction](../../patches/task-services/0002-claim-sleepnomore-error.patch)
pops the caller return before CopyError. The live sleep-word removal now
returns error &A84 with V set; signalling the word wakes the real child.
[Pre-fix observation](reports/sleepnomore-before.json) records the lost V bit.
A one-instruction negative control replaces the
claiming pop with NOP and reproduces failure in the same public sleep-word test.

[Acceptance](reports/acceptance.json) records three identical cold boots, all
assertions, sampled ROM/guest instruction verification and every undefined
exception classified as an expected software-FPA trap. There are no data or
prefetch aborts. A ROM omitting the three providers fails at the first null:
open with the real `Filing system or path null: not present` error. No emulator
or kernel change, fake success handler or host-injected guest code is involved.

```sh
ARCLIBRE_INSTALL_ROM=0 make arclibre-rom
python3 tests/run_streams.py
python3 tests/check_stream_sleep_negative.py
```

Serial/parallel hardware, printer output, DeviceFS object registration variants,
all flow-control/threshold combinations and exhaustive 3.11 compatibility are
not established by this gate. The intermediate 8c6678ad stream ROM used 1,900,020 bytes and left
197,132 free: 7,060 more free bytes than the previous released ROM, despite
adding three real services. The applications remain in ROM.

The [intermediate integration report](reports/integration.json) records all 15
retained gates passing on that exact stream ROM before adding RAM filing. It
includes only compact metadata for the privately supplied game checks.
