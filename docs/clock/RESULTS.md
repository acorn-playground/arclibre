# Original IIC and RTCAdjust

The default ROM now includes the original cleaned-3.60 IIC 0.14 and RTCAdjust
0.04 modules. The kernel's own CMOS routines do not provide the public
`IIC_Control` SWI (&240); on RISC OS 3.x that comes from the separate IIC
module. IIC 0.14 is the original-machine implementation: it drives the bus by
bit-banging IOC's control register, as an A3000 does. RTCAdjust compares the
IOC-driven software clock with the PCF8583 real-time clock every hour and
retunes IOC timer 0's latch (18000–22000, default 20000).

- IIC `3a9726dcc5cf61a5722dbcec9bc52f2468e9e57a`: 1,096 bytes, 238 decoded ARM2
  instructions.
- RTCAdjust `a0f37cd91cdd45e99d1643c77512a76b0f875d0e`: 1,836 bytes, 405 decoded
  ARM2 instructions.

Both assemble identically twice and under the observer build, with no
relocations or unresolved symbols ([assembly report](reports/assembly.json)).
[`patches/clock/0001-arm2-build.patch`](../../patches/clock/0001-arm2-build.patch)
only adds relocatable AREAs, uses the maintained `KernelEntry` spelling and
inserts ARM2 PSR-settling no-ops. Their original UK message files are installed
as `Resources.IIC.Messages` and `Resources.RTCAdjust.Messages`. Together they
add 3,136 bytes; 137,988 bytes remain free.

```sh
python3 tools/build_system_modules.py clock
python3 tests/run_clock.py
```

## Runtime gate

`tests/run_clock.py` boots the exact ROM with the `ClockProbe` harness. Guest
actions are typed at the real F12 command line; no guest code is injected. The
only hardware change is moving the emulated PCF8583's time, as a drifting
crystal would. It records:

- `IIC_Control` writes four bytes to the PCF8583's alarm registers (pointer
  9, auto-incrementing; the alarm is disabled), which the emulated chip then
  holds, and reads them back. Together with reads and NoAck this covers the
  RISC OS 3.11 IIC API, which is that one SWI.
- `IIC_Control` reads the PCF8583's actual date registers; an absent device
  (&D0) returns error &20300, "No acknowledge from IIC device", looked up from
  the installed messages.
- RTCAdjust registers its hourly ticker (`OS_CallEvery`, 359,999 cs) twice:
  once at initialisation and again on the power-on `Service_Reset`, as the
  original source does. Each hour therefore brings two recalibrations about a
  second apart.
- Every recalibration's latch equals the module's formula, computed
  independently with its truncating 64-bit divides, and IOC timer 0 holds the
  latch minus one.
- With the RTC three seconds behind, the first recalibration lengthens the
  tick (20000 → 20033) and the second applies the `(P+C)/P` factor again
  (→ 20049). `*RMKill RTCAdjust` then restores 20000 (IOC latch 19999). Three
  cold boots give identical observations.
- 1999-12-31 23:30 → 2000-01-01 (century wrap in RTCAdjust's year logic) and
  2000-02-28 → 29 February both recalibrate without failure, with the software
  clock within 2 cs of the RTC.
- The `--without-clock` profile, byte-identical to the previous release ROM,
  reports `SWI name not known` and never changes the latch.

## Limits

The doubled hourly registration is original 0.04 behaviour and is retained: on
a genuinely drifting clock it roughly doubles the per-hour correction. Only
the original-machine IIC path is built; there is no IOMD support. Physical
PCF8583 and BMU timing, and real crystal drift, are not tested.
