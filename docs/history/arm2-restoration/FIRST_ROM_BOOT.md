# Recommended first actual ROM boot experiment

The next milestone should establish **real cold-reset execution on the original A440/1 profile through memory/vector setup**, then extend toward the boundary before runtime module initialisation. It should not attempt the desktop or claim RISC OS 3.11 compatibility.

This document is a recommendation only. No ROM container, joined image, boot run or MacArch modification was made in this phase.

## Input and scope

Freeze this component by its SHA-256 (`6fb97a29134f6cea155d4b1ec0e9ca80f3c9f8e61672dd238eea32585a6851f1`) and retain the complete source/patch evidence. Use ARM2, 4 MiB RAM, MEMC1a, VIDC1a, IOC-A1, WD1772 and original keyboard configuration. Supply an explicit legal ROM layout, module-list termination and any genuinely required runtime data as a separately reviewed change. The `IMAGESIZE=2048K` source setting is not by itself a joined image specification.

Use existing emulator trace/breakpoint facilities first; this recommendation does not presume permission to modify MacArch. If existing facilities cannot observe a required event, record the observation limitation and scope any instrumentation change separately. Do not patch return-success stubs into the kernel to get past a missing runtime provider.

## Checkpoints and observable success

The following addresses are for the delivered binary. boot-checkpoints.json includes source locations and additional handlers; regenerate addresses after any source change.

| Stage | Checkpoint | Required observations |
|---|---|---|
| Reset entry | Cold reset vector aliases ROM; `CONT=&0380DCDC` | First load through offset `118` reaches physical ROM. Mode is SVC26 with expected interrupt masking; no CP15 access or undefined instruction. |
| Memory controller | `InitMEMC=&0380F8FC`, `MemSize=&0380F908`, `TimeCPU=&0380FA6C` | MEMC programming addresses/values, real RAM discovery (4 MiB and 32 KiB pages), timer-based CPU measurement, no unintended IOMD access. |
| Fixed mappings | `EmptyCamEntries=&0380DD70`, then the three SlapIn32K calls | CAM invalidation and the low-workspace, heap and cursor mappings match [MEMORY_CONTRACT.md](MEMORY_CONTRACT.md). RAM reads/writes land in the expected non-overlapping physical pages. |
| Workspace/IRQ installation | `ResetPart1Done=&0380E264`, `CopyDefaultIRQ1V=&0380E298` | Valid SVC/IRQ stacks, unchanged fixed block sizes, correct RAM vector contents and live early-keyboard IRQ branch. Reset/Break indirection behaves as intended. |
| Kernel device setup | `VduInit=&0380FB9C`, `ExecuteInit=&0381F58C`, `KeyInit=&03821DB0`, `MouseInit=&038228CC` | Actual VIDC palette/timing and DMA, CMOS and identity initialisation, keyboard handshake, mouse and timer operation. Unexpected runtime SWIs are recorded with provider requirements. |
| Pre-module boundary | `InitVariables=&038075D4`, then entry to `ModuleInit=&0380419C` | Reach with valid workspace/heap and interrupt state. Stop before module discovery/initialisation for this first experiment; do not treat that boundary as a completed OS boot. |

The first successful gate is the **reset/MEMC/fixed-mapping stage**. Later checkpoints may expose runtime dependencies before ModuleInit. Identify and provide legitimate required implementations/data in a subsequent scoped payload, rather than assuming a kernel-only file can initialise the whole OS.

Trace every hardware write, first unexpected exception and module SWI dependency encountered on this path. Preserve CPU registers including combined PC/PSR, banked stack pointers, relevant RAM words and the source-correlated trace. Separately repeat cold reset and Break after the first stable run; a single successful entry into ROM is insufficient.

After those gates, add targeted SWI/IRQ/FIQ/abort/callback execution fixtures and dynamic-area/protection cases. Such tests should check return PC/flags, nested masking and actual memory access permissions. Static rejection of later-ARM opcodes has already passed, so the purpose is now behavioural validation.

## Exit criteria and following work

Accept the first boot milestone only with repeatable reset, measured hardware/memory contracts and a clearly identified stopping point. Report any unmet provider dependency as such, not as an assembler import. Preserve the real 3.60 version identity while testing the 3.11-facing contract.

Only after kernel execution is stable should a separate ROM payload milestone select legally redistributable runtime modules and start 3.11 API regressions. Original-compatible desktop, games and utilities remain the final target; no later-desktop integration is proposed as a substitute.
