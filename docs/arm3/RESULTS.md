# ArcLibre ARM3Support

ArcLibre runs on an ARM3 because the ARM3 executes ARM2 code. Until this
module, though, nothing turned the ARM3's 4 KB cache on, so an ARM3 ran at
memory speed. RISC OS 3.11 had an `ARM3Support` ROM module, dormant on ARM2
machines, but its source was never published. The public HWSupport/ARM module
initialises only for ARM600-class processors and has no `Cache_` SWIs.
`src/ARM3Support` is therefore new Apache-2.0 ArcLibre code, written from the
documented interface. The kernel is unchanged: its own ARM3 set-up stays out
of the ARM2 build, as in the frozen baseline.

## Behaviour

- **Initialisation.** The module reads CP15 register 0, briefly pointing the
  undefined-instruction vector at a return with interrupts off. On an ARM2 the
  MRC traps harmlessly. Any processor other than an ARM3 (`&xxxx03xx`) fails
  initialisation, so the ROM module stays **Dormant**, as on 3.11.
- **On an ARM3** it sets the 3.60 kernel's default areas from `s/NewReset`:
  - cacheable `&FC007CFF`: ROM and non-screen logical RAM;
  - updateable `&7FFF`: logical RAM;
  - disruptive `&F0000000`: the MEMC CAM, so page remapping, such as Wimp
    task switches, flushes the cache.

  It then flushes the cache and turns it on (control 3), unless CMOS byte &C3
  bit 5 (`*Configure Cache Off`) says otherwise.
- **SWIs** (chunk &280): `Cache_Control`, `Cache_Cacheable`,
  `Cache_Updateable` and `Cache_Disruptive` take an EOR mask in R0 and an AND
  mask in R1. They set the register to (old AND R1) EOR R0 and return the old
  value. Turning the cache on flushes it first. `Cache_Flush` flushes.
- **Commands:** `*Cache [On|Off]` (no parameter shows "Cache on/off"),
  `*Configure Cache On|Off` and `*Status Cache`. The wording is that of the
  3.60 ARM module's messages.
- **Size:** 1,156 bytes. `tools/inspect_image.py` accepts the CP15
  MRC/MCR transfers for this module only.

## Gate

`tests/run_arm3.py` uses `ARM3Probe`, which reads MacArch's CP15 registers
after each command. It runs three cold boots on each processor.

**ARM3**
- At the desktop the cache is on, with exactly the default areas and control
  value 3.
- A 100,000-iteration BASIC loop takes 32 cs with the cache on and 152 cs with
  it off (the gate requires at least 3×).
- `Cache_Control` returns 3, then 2; `Cache_Cacheable` toggles bit 8 and
  restores it; `Cache_Flush` works.
- `*Cache Off/On` changes the controller.
- `*Cache Sideways` gives the syntax error.
- `*Configure Cache Off` writes only the CMOS bit and leaves the running state.
- `*RMReInit` applies the configured state, off and then on.

**ARM2**
- The same ROM boots normally. `*ROMModules` shows `ARM3Support 1.00 Dormant`,
  and both `*Cache` and the SWIs are unknown.

**Negative control**
- The ROM without the module, on an ARM3: the cache stays off (control 0) and
  the loop takes 152 cs.

The gate also found and fixed a defect before release: `*Configure Cache`
wrote to the wrong CMOS byte, because the keyword parser used r1.

## Limits

- MacArch models the ARM3 cache for timing only. It never returns stale data,
  so a missing flush cannot show up here, and physical ARM3 hardware is
  untested.
- The disruptive CAM area covers the flushes RISC OS needs for remapping; code
  that modifies itself without a flush is also untested.
