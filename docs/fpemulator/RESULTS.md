# ARM2 software floating point

**PASS:** the public FPEmulator executes Wimp's real FPA instruction encodings on MacArch's ARM2 core through the undefined-instruction vector. Three independent cold boots produce identical results. This resolves the missing software-FPA prerequisite; it does not establish Wimp initialization or general numerical/application conformance.

## Artifact and source

`build/fpemulator/module.bin` is a 26,700-byte relocatable RISC OS module:

```text
SHA-256 be6a5904849685002e9e862fe859cdf5369eaf55d0b9590546b949d5ff1cb665
```

The baseline ROM and kernel remain unchanged. The test loads the real module through `OS_Module 11`, which copies it into the RMA and calls its initialization entry. It registers the original FPEmulator error messages with ResourceFS. The test does not install a substitute undefined handler or implement floating point in the host.

The public FPASC vendor snapshot is pinned to `827b16098de462b3dadc6caadf62d30ed664c926`: ARM core 1.13 and the RISC OS module 4.28 wrapper/veneer from the **same** tree. The earlier cleaned-3.60 snapshot lacks the ARM core, so this later complete component is an explicit dependency exception. `src/FPASC` retains the earlier interface provenance; `src/FPEmulator` contains the complete runtime. The kernel remains the pinned restored 3.60 kernel and RISC OS 3.11 remains the compatibility target.

[fpemulator.json](../../manifests/fpemulator.json) records all 31 selected inputs and original/maintained hashes. [The licensing assessment](../../licenses/FPEmulator-assessment.md) explains the ARM BSD three-clause core and Acorn/Apache distribution terms. Both are retained in the delivered component LICENSE. No ROM image or proprietary core is used.

## Changes

[0001-arm2-build.patch](../../patches/fpemulator/0001-arm2-build.patch) changes four files:

- Select the upstream `SoftOnly` flavour using the existing `Arm600 = FALSE` wrapper. `ARM2Safe` is true, multiple contexts enabled, 64-bit multiply and CLZ disabled. The software implementation, packed formats and transcendental operations remain present.
- Remove the unused `DynamicRounding` assignment. That option is absent from core 1.13 and has no reference there; inventing a variable would hide a wrapper/core mismatch.
- Insert explicit ARM2 settling NOPs at ten source sites after 26-bit PSR changes. Macro expansion produces 28 additional instructions. All original functionality remains.

No dummy implementation, fabricated workspace or ARM600 runtime is added. The real core detects absence of FP hardware using a temporary trap handler, then activates its software path.

## Static verification

Two normal AsAsm runs and the observation-only assembler produce identical objects. The object has one relocatable area, zero unresolved symbols and zero relocations. Source emission observations match every byte and the AOF code/data map. Direct branches target emitted instructions; all integer operations pass the independent strict ARM2 decoder; processor-mode and banked-register changes have settling instructions. There is no absolute ADR materialization.

The module contains **5,584 integer ARM2 instructions** and **396 separately classified FPA instructions**. The latter are intentional: hardware probing and software-recursive arithmetic used by packed/transcendental functions. They are not mislabelled ARM2 integer operations. Only floating-point coprocessors 1/2 are accepted; the strict kernel integer gate is unchanged. Six of these instructions are in hardware-detection/interface paths, the others in recursive FP routines. Runtime evidence checks executed module bytes against the assembled artifact.

The workspace is the upstream contract: FPEAnchor at `&FF4`, SVC stack top `&01C02000`, and a 136-byte context (eight four-word internal register slots plus FPSR and disable information). The module allocates its declared global workspace through `OS_Module`; its private word equals FPEAnchor. It creates a RAM vector trampoline and chains the original undefined handler. It restores the original vector on finalization. Neither a new kernel workspace layout nor an emulator extension is required.

## Runtime verification

Each of three cold boots executes 12 FP cases and three error-path cases:

- The original Wimp conditional `WFSEQ` initializes FPSR to `&70000`.
- Integer conversion, addition, multiplication, division and truncating FIX produce independently checked values, in SVC26 and USR26.
- The exact encodings of all 21 Wimp FPA sites occur in the exercised client. All eight extended registers and FPSR survive save/clear/restore using Wimp's 100-byte block layout.
- Sine, square root, natural logarithm and exponential produce checked results. The transcendental case enters the real undefined handler 28 times, exercising nested software emulation.
- Masked division by zero yields infinity and the cumulative status bit.
- Two separately allocated and initialized contexts retain different register and FPSR values through repeated switching.
- Enabled division by zero delivers the real translated error `&80000202` to an application error handler.
- An unsupported coprocessor instruction passes through to the kernel's real undefined-instruction error, `&80000000`.
- After module finalization, a real FPA instruction again reaches the kernel's undefined-instruction error. This negative control demonstrates that the emulator was necessary.

The kernel's undefined-instruction message reports the saved exception return address (instruction +4). Both installed pass-through and uninstalled controls verify that existing behaviour. Normal FP cases preserve the SVC stack; all return in 26-bit mode. There are no prefetch/data aborts, address exceptions or unexpected FIQ exceptions. The test application error handler only records arrival; the kernel fills the error buffer and performs the real error transfer.

## Reproduction and evidence

```sh
make fpemulator  # standalone component and client, with static audit
make fpe-test    # exact baseline build, desktop candidates, fresh cold boots and FP tests
```

Full traces, module source emissions, resolved symbols, instruction classification, memory results and cold boot snapshots are under `build/fpemulator/`. `acceptance.json` is emitted only after all repetitions and independent comparisons pass. Compact reports are retained [here](reports/acceptance.json). The native harness uses the existing pinned MacArch core with the previously approved disc-change patch; no new emulator change was made.

The component was first distributed on its own, with its module, resource pack, licence, source manifest and build and result documentation; it is now part of every ArcLibre ROM. The complete maintained source export includes the matching source, source patch, build tools and test harness. Full generated evidence is archived separately.

## Remaining scope

This is sampled functional testing, not exhaustive IEEE/FPA instruction, rounding, exception, denormal, packed-format, transcendental-accuracy or asynchronous context-switch conformance. FIQ use is not supported by the original core contract; IRQ floating point is discouraged there, and SVC floating point has its documented R13/R14 restrictions. ARM3 hardware timing is untested. The tests do not launch Wimp or a desktop and do not claim unmodified RISC OS 3.11 application compatibility.

The subsequent [rendering](../renderers/RESULTS.md), [font](../font-stack/RESULTS.md) and [isolated Wimp](../wimp-stack/RESULTS.md) gates now pass with this runtime. Multi-task scheduling and desktop startup remain; preserve the existing baseline gate.
