# Build, development and distribution strategy

25 October 2026. No build, tool installation, emulator launch or machine configuration change was performed. The verified actions were public source retrieval, metadata/history inspection and read-only local source inspection.

## Pinned inputs and reproducibility limits

RO26 is a set of component branches under [gitlab.4corn.co.uk](https://gitlab.4corn.co.uk/explore), assembled through `Products/All`. The [full branch inventory](SOURCE_AND_LICENSES.md#complete-twentysix-ref-inventory) records the exact heads observed. The parent product has only a `master` head in the observed refs; it does not itself have a `twentysix` head. The author's instructions switch each component to that branch. A floating `--remote` submodule update is therefore not a reproducibility lock.

Verified retrieval examples (executed into temporary audit storage, not build instructions):

```sh
git clone --depth 1 https://gitlab.4corn.co.uk/Products/All.git /tmp/archimedes-rom-audit/All
git clone --depth 1 --branch twentysix https://gitlab.4corn.co.uk/RiscOS/Sources/Kernel.git /tmp/archimedes-rom-audit/Kernel
```

Pin `All` to `253a8a2b99705d81033a31ae1174dbf345ed1beb`; selected RO26 Kernel is `724ffabb1ce232949bbcafec10ea59aa6d62891e`. Preferred experimental Kernel is **`24044755f08dc3b99779833a57eecf3899561ce6`**, the parent of the April 2000 32-bit conversion; historical original-machine HdrSrc is **`c9113ab79d9ca2ccc49a9b7518911132ca9ffa1b`**. Their combination is a research candidate, not a verified historical release or complete build configuration. [P1](SOURCE_AND_LICENSES.md#p1) [H2](SOURCE_AND_LICENSES.md#h2)

Before a reproducible build can be claimed, replace every selected component with an exact commit lock; resolve includes/generated headers, export order, filetypes and case-sensitive filename behaviour; record compiler/linker versions and hashes, host/guest OS, locale, environment, timestamp controls and exact output recipe. Preserve failed-build logs and identify whether files came from source, generated artifacts or a preinstalled build library. Never satisfy a missing input by quietly copying bytes from an original ROM or an undocumented old build tree.

## Toolchain findings

| Dependency | Evidence | Consequence |
|---|---|---|
| RISC OS build environment | RO26 documents an RPCEmu guest under Linux and a contemporary tool set; Env selects Morris/Ursula/APCS-R/4096K. [Author's build procedure](https://www.marutan.net/ro26/), [B1](SOURCE_AND_LICENSES.md#b1). | This is the documented reproduction path, not native macOS ARM cross-compilation. The guest ROM/tool entitlement also matters. |
| aasm kernel assembly | Kernel Makefile sets `AS=aasm`, `SOURCE=s.GetAll`; old build notes discuss lack of aasm source and migration to objasm. [K19](SOURCE_AND_LICENSES.md#k19) [B4](SOURCE_AND_LICENSES.md#b4). | Cannot assume clang/GNU as accepts the old dialect or that replacing a command name is enough. |
| DDE/Norcroft tools | Official [How to build RISC OS](https://www.riscosopen.org/wiki/documentation/show/How%20to%20build%20RISC%20OS) says the tools are purchased and a free GCC toolchain cannot currently build the OS. | Treat as a **build-time** dependency. This does not alone make resulting OS code proprietary; embedded runtime libraries/templates need their own licences. |
| romlinker | Published source, pinned version 0.03; product uses it. [B2](SOURCE_AND_LICENSES.md#b2) [B5](SOURCE_AND_LICENSES.md#b5) [B6](SOURCE_AND_LICENSES.md#b6). | Source availability is positive, but its own libraries/build prerequisites and footer behaviour remain to verify. |
| Build phases | [Developer build guide](https://www.riscosopen.org/wiki/documentation/show/Developer%27s%20guide%20to%20RISC%20OS%20builds) describes exports, libraries, resources, ROM and join phases. | Resource export is part of the payload audit. A successful kernel assembly skips much of the later integration work. |
| Open alternatives | [OSLib's tool documentation](https://ro-oslib.sourceforge.io/usage.html) distinguishes AsAsm/ObjAsm AOF workflows from GCC/GNU assembler workflows. | Investigate AsAsm/GCCSDK as separately scoped tool-port work; neither a complete free RO26 toolchain nor an ARM2-safe build was verified. Do not publish speculative commands as a working recipe. |

A modern Mac can orchestrate retrieval and comparisons; the verified MacArch source supplies a native Swift emulator/CLI. Whether a chosen DDE version is available, lawful to run in the intended guest and compatible with the old kernel is unresolved. A fully redistributable ROM and an entirely free bootstrap toolchain are distinct deliverables; the former still requires all linked payload inputs to be cleared.

## MacArch inspection

The MacArch repository, committed baseline **`45b2b7bff2aa38292b33db2b826052b50365a717`**. The checkout has pre-existing modified and untracked files, including debugger work. Claims here use committed files read with `git show`; the worktree and settings were not changed. Local evidence does not establish that the remote repository is publicly accessible.

| Capability | Verified source | Limits |
|---|---|---|
| A440/1 and ARM2/ARM3 | `MachineModel`, default 4 MiB and old I/O/ST506. [M1](SOURCE_AND_LICENSES.md#m1) | Select explicitly; default A3000 is not the primary target. ARM3 turbo modes are separate non-historical profiles. |
| Custom ROM input | Core `ROMImage.build`, headless `--rom`, MEMC power-of-two ROM buffer. [M2](SOURCE_AND_LICENSES.md#m2) [M5](SOURCE_AND_LICENSES.md#m5) [M11](SOURCE_AND_LICENSES.md#m11) | Core input is more permissive than library importer; no run was attempted. Use power-of-two logical images to avoid accidental padding aliases. |
| Library import | Recognised sizes plus version/expected-size checks. [M3](SOURCE_AND_LICENSES.md#m3) [M4](SOURCE_AND_LICENSES.md#m4) | A tiny original image or 4 MiB RO26 image can be rejected by the library while accepted by the core. No need to change the emulator merely to plan the core-path experiment. |
| Reset/instruction diagnostics | CPU reset at zero; trace, execution breakpoints, conditional data watchpoints and logpoints. [M13](SOURCE_AND_LICENSES.md#m13) [M9](SOURCE_AND_LICENSES.md#m9) [M10](SOURCE_AND_LICENSES.md#m10) | Enable tracing before advancement. `power_cycle` advances toward idle, so low-level reset tracing should use direct headless/core setup or a verified pause-at-reset sequence. |
| Deterministic input/time | `set_real_time`, scheduled run/input operations. [M8](SOURCE_AND_LICENSES.md#m8). `MachineConfiguration.rtcEpoch` supplies a fixed-epoch option. [M14](SOURCE_AND_LICENSES.md#m14) | Test clock, media and peripheral state explicitly; no complete deterministic regression harness was executed. |
| Snapshots | Per-ROM state; same hash enforced. [M7](SOURCE_AND_LICENSES.md#m7) | No cross-ROM snapshots. Hard-disc contents do not roll back with restore. |
| Output capture | Screenshot, CLI WAV and trace capture. [M12](SOURCE_AND_LICENSES.md#m12) | Screen text heuristics may depend on the system font; use original test buffers and raw rendering observations for a new ROM. |
| SWI/IO observability | CPU instruction trace/watchpoints can inspect calls and MMIO writes. | A structured all-SWI entry/exit/duration logger is a harness design requirement, not a verified existing tool. Memory peeks avoid side-effectful I/O; don't infer device state from a normal RAM peek. |

For future acceptance, use separately reset machines with identical logical inputs. Measure output at API/application checkpoints, not equal PCs or equal instruction counts across different implementations. Keep all proprietary reference states and traces private.

## Independent emulator

[Eichhörnchen](https://github.com/RichardBrown384/Eichhoernchen) is the appropriate second candidate: its author describes an A3000 emulator and support for 3.1x ROMs. Its inspected README documents four chip files, an ADFS disc argument, and limitations including disc changes not being saved at exit. This is author documentation, not an audit of its ROM loader or a test run. Pin its commit, inspect its real ROM assembly/size handling, and validate the common A3000/ARM2/floppy subset before using it as independent evidence. Do not demand A440/1/ST506 testing from a documented A3000-only environment.

[RPCEmu Extended](https://github.com/andrewtimmins/rpcemu-extended) remains useful for reproducing later Risc PC behaviour and separating RO26 integration regressions from original-machine port work. Its different chipset cannot certify MEMC/VIDC1/IOC or ARM2 correctness. Pyromaniac provides useful testing/API ideas, but its [author says it is not currently distributed](https://pyromaniac.riscos.online/); it is not a released ARM2 ROM source base or a substitute baseline.

## Validation and release gates

After approval of a future implementation phase: validate source hashes/licences and include closure first; audit emitted instruction ranges and link/ROM metadata second; attempt reset checkpoints only when those checks pass; then use the tiered [compatibility plan](COMPATIBILITY_TEST_PLAN.md). This is a development strategy, not authorisation to execute it now.

A release needs an exact payload bill of materials (code and assets), source/build recipe, licence texts and applicable notices, source-to-image map, reproducibility results, footprint and RAM budget, qualified 3.11 corpus results, known failures and per-model image/chip layout. No proprietary reference ROM, reference snapshot or extracted resource belongs in that bundle.

Hardware manufacture is later work: verify board revision, socket/carrier layout, byte lanes, address decoding, voltage, access timing and startup behaviour; retain a recovery path and observe ESD/insertion polarity. No boards or ROM devices were ordered or programmed. Emulator-only success may precede board compatibility, but it must be labelled with that limitation.
