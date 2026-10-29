# Restoration result

**PASS — the kernel-only static milestone succeeded.** The assembled component contains 142,148 bytes (about 138.8 KiB), originates at `&03800000`, and has zero unresolved AOF symbols and zero relocations. Two fresh source restores and normal assemblies produced byte-identical objects. An independently instrumented AsAsm build produced the identical object while supplying emission and symbol observations.

| Gate | Result | Evidence |
|---|---|---|
| Pinned sources and patch replay | 201 cohort files preserved; 10 later public-header/licence files verified; 210 restored files reproduced with patch fuzz 0 | Provenance report |
| Resolved assembly | Exit 0; no unresolved symbols or relocations; 43 reviewed warnings | Assembly invocation, diagnostics |
| Reproducibility | Both normal builds and observed build have identical AOF bytes | Reproducibility |
| Independent ARM2 decoding | 27,751 instruction words; zero rejected instructions; 11 deliberate invalid-opcode controls rejected | Verification |
| Branches and exceptions | 5,040 direct branch targets land in identified code; relocated vectors, default handlers and PSR/bank transitions checked | Exception paths |
| MEMC and queries | 10,240 CAM encoding cases; 12 reset CAM cases; packed CAM update; four hardware query cases pass | Emitted-routine tests |
| Workspace | Original `hdr/Old/NewSpace` unchanged; fixed allocations and RAM copies checked | [Contract](MEMORY_CONTRACT.md) |

All 113 actual assembly inputs have revision, licence and content-hash records. The 303 consumed definitions from the later public interface registration headers have individual values, callers and restoration decisions. No ARM600 workspace or AMB implementation was added. No dummy routine, guessed workspace member, proprietary ROM code or ROM-extracted resource was used.

The substantive fixes were original-board hardware selection and identity handling, the MEMC1 flag contract, explicit assembly alignment, the relocated 26-bit IRQ vector, ARM2 bank-selection settling, and removal of the ARM3 coprocessor probe from this fixed ARM2 build. The real reset and kernel implementations remain. The existing non-POST path is selected; this does not constitute a restored hardware self-test.

## Remaining issues

1. **No boot has been attempted.** Reset-time RAM discovery, physical device responses, DMA, video timing, keyboard protocol and interrupt timing still need execution against the selected A440/1 machine. Static instructions and bounded routine checks do not prove these behaviours.
2. **The binary is not a complete ROM.** ROM layout/metadata, module termination and runtime providers such as FileSwitch, MessageTrans and territory support remain separate work. Zero unresolved assembler symbols does not mean every runtime SWI has a provider.
3. **RISC OS 3.11 compatibility is open.** The source identifies itself as 3.60; version reporting was not falsified. Error wording, CMOS defaults, VDU/palette/font behaviour, application slots, dynamic areas, callback timing, module ABI, OS_Byte/OS_Word and games' direct hardware use require the comparison matrix in [VERIFICATION.md](VERIFICATION.md). No later-desktop compatibility target has been substituted.
4. **Timing and performance need measurement.** The conservative bank-settling patch adds instructions, including some where the original next instruction might already have been safe. It preserves registers/flags and fixed copied block sizes, but its effects on latency-sensitive games and handlers are unmeasured.
5. **Static reachability has limits.** Resident instruction encodings and direct branches are exhaustively checked over the identified code. Indirect vectors, installed callbacks and module SWI handlers can point to future client code. This is not a formal proof of every possible dynamic execution path.
6. **Warning and historical-source limitations remain visible.** The 43 warnings are ADR/ADRL optimisation hints and an unused literal-pool slot/location note, all reviewed against emitted code. The original informational `AddTintToColour`/ECF warning is retained. These sources are the publicly cleaned 3.60 import, not a claim to an untouched original release CD or to a complete 3.11 source set.

## Next milestone

Proceed next to a separately scoped **reset-to-pre-module-initialisation ROM boot experiment**, following [FIRST_ROM_BOOT.md](FIRST_ROM_BOOT.md). First establish actual memory mapping, stack/vector setup, VIDC/IOC operation and repeatable reset. Keep desktop integration and broad application testing for subsequent milestones. No ROM container was created, no joining performed and no emulator changes made here.
